"""Offline tests: the Databricks client is mocked; no cloud resources are used."""
from copy import deepcopy
from types import SimpleNamespace as NS
from unittest.mock import MagicMock

import pytest
import yaml
from databricks.sdk.service.jobs import RunLifeCycleState, RunResultState

import automation
from platform_ops import compute, runs, settings


@pytest.fixture
def config():
    return {
        "workspace": {"profile": "prod_azure", "host": "https://example.azuredatabricks.net"},
        "job": {"name": "prod_lab8_pipeline", "notebook_task_key": "data_quality"},
        "notebook_parameters": {"catalog": "catalog", "silver_schema": "silver", "gold_schema": "gold"},
        "cluster": {"name_prefix": "lab9-test", "policy_id": "policy-1",
                    "node_type_id": "Standard_D4ds_v5", "num_workers": 0,
                    "autotermination_minutes": 15, "spark_version": "16.4.x-scala2.12"},
        "timeouts": {"cluster_start_seconds": 1200, "notebook_run_seconds": 900,
                     "poll_interval_seconds": 15},
    }


def make_run(lifecycle, result=None):
    return NS(state=NS(life_cycle_state=RunLifeCycleState(lifecycle),
                       result_state=RunResultState(result) if result else None, state_message=""),
              run_page_url="https://example/run/456", tasks=[])


@pytest.fixture
def client(config):
    client = MagicMock()
    client.config.host = config["workspace"]["host"]
    client.current_user.me.return_value = NS(user_name="student@example.com")
    client.clusters.spark_versions.return_value = NS(versions=[NS(key="16.4.x-scala2.12")])
    client.jobs.list.return_value = [NS(job_id=123)]
    notebook = NS(notebook_path="/Workspace/lab8/05_data_quality", source="WORKSPACE",
                  base_parameters=deepcopy(config["notebook_parameters"]))
    client.jobs.get.return_value = NS(job_id=123, settings=NS(name="prod_lab8_pipeline",
        tasks=[NS(task_key="data_quality", notebook_task=notebook)]))
    client.workspace.get_status.return_value = NS(object_type="NOTEBOOK")
    client.clusters.create.return_value.cluster_id = "our-cluster"
    client.jobs.submit.return_value.run_id = 456
    client.jobs.get_run.return_value = make_run("TERMINATED", "SUCCESS")
    client.clusters.list.return_value = []
    return client


def run_main(tmp_path, config, client, monkeypatch, *flags):
    path = tmp_path / "config.yml"
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    monkeypatch.setattr(automation, "WorkspaceClient", lambda **kwargs: client)
    return automation.main(["--config", str(path), *flags])


@pytest.mark.parametrize("flags", [[], ["--plan"]])
def test_preview_never_creates_or_runs_anything(tmp_path, config, client, monkeypatch, flags):
    assert run_main(tmp_path, config, client, monkeypatch, *flags) == 0
    client.clusters.create.assert_not_called()
    client.jobs.submit.assert_not_called()
    client.jobs.run_now.assert_not_called()
    client.clusters.delete.assert_not_called()
    client.clusters.permanent_delete.assert_not_called()
    assert not (tmp_path / "logs").exists()


def test_full_success_with_mocked_client(tmp_path, config, client, monkeypatch):
    assert run_main(tmp_path, config, client, monkeypatch, "--execute") == 0
    client.clusters.delete.assert_called_once_with(cluster_id="our-cluster")
    client.clusters.permanent_delete.assert_called_once_with(cluster_id="our-cluster")
    client.jobs.run_now.assert_not_called()
    client.jobs.cancel_run.assert_not_called()
    task = client.jobs.submit.call_args.kwargs["tasks"][0]
    assert task.existing_cluster_id == "our-cluster"
    assert task.notebook_task.base_parameters == config["notebook_parameters"]
    assert client.clusters.create.call_args.kwargs["autotermination_minutes"] == 15
    log = next((tmp_path / "logs").glob("*.log")).read_text(encoding="utf-8")
    assert "our-cluster" in log and "456" in log and "Overall result: SUCCESS" in log


def test_wrong_workspace_stops_before_requests(config, client):
    client.config.host = "https://wrong.example.com"
    with pytest.raises(ValueError, match="another Workspace"):
        settings.prepare(client, config)
    client.current_user.me.assert_not_called()


@pytest.mark.parametrize("ids", [[], [1, 2]])
def test_no_guessing_job_identity(config, client, ids):
    client.jobs.list.return_value = [NS(job_id=i) for i in ids]
    with pytest.raises(ValueError, match="Expected one LAB 8 Job"):
        settings.prepare(client, config)


def test_parameter_drift_stops_run(config, client):
    config["notebook_parameters"]["gold_schema"] = "another_gold"
    with pytest.raises(ValueError, match="parameter differs"):
        settings.prepare(client, config)


def test_runtime_must_exist(config, client):
    config["cluster"]["spark_version"] = "missing"
    with pytest.raises(ValueError, match="Runtime is unavailable"):
        settings.prepare(client, config)


def test_startup_timeout_still_cleans_cluster(config, client):
    client.clusters.create.return_value.result.side_effect = TimeoutError("Startup timeout")
    assert automation.execute(client, config, "student", "/Workspace/notebook") == 1
    client.jobs.submit.assert_not_called()
    client.clusters.permanent_delete.assert_called_once_with(cluster_id="our-cluster")


def test_failed_notebook_is_not_success(config, client):
    client.jobs.get_run.return_value = make_run("TERMINATED", "FAILED")
    assert automation.execute(client, config, "student", "/Workspace/notebook") == 1
    client.clusters.permanent_delete.assert_called_once()


def test_cleanup_error_fails_overall_result(config, client):
    client.clusters.permanent_delete.side_effect = RuntimeError("Deletion denied")
    assert automation.execute(client, config, "student", "/Workspace/notebook") == 1


def test_monitor_timeout_cancels_run_and_deletes_cluster(config, client, monkeypatch):
    def timed_out(*args):
        raise TimeoutError("Run timeout")
    monkeypatch.setattr(automation, "wait_for_run", timed_out)
    assert automation.execute(client, config, "student", "/Workspace/notebook") == 1
    client.jobs.cancel_run.assert_called_once_with(run_id=456)
    client.clusters.permanent_delete.assert_called_once_with(cluster_id="our-cluster")


def test_cancellation_failure_does_not_skip_cleanup(config, client, monkeypatch):
    def interrupted(*args):
        raise KeyboardInterrupt()
    monkeypatch.setattr(automation, "wait_for_run", interrupted)
    client.jobs.cancel_run.side_effect = RuntimeError("API unavailable")
    assert automation.execute(client, config, "student", "/Workspace/notebook") == 1
    client.clusters.permanent_delete.assert_called_once()


def test_failed_termination_still_attempts_permanent_delete(client):
    client.clusters.delete.return_value.result.side_effect = TimeoutError("Termination timeout")
    with pytest.raises(RuntimeError, match="Termination timeout"):
        compute.remove_cluster(client, "our-cluster")
    client.clusters.permanent_delete.assert_called_once_with(cluster_id="our-cluster")


def test_monitor_has_a_deadline(config, client, monkeypatch):
    client.jobs.get_run.return_value = make_run("RUNNING")
    ticks = iter([0, 1201])
    monkeypatch.setattr(runs.time, "monotonic", lambda: next(ticks))
    with pytest.raises(TimeoutError):
        runs.wait_for_run(client, config, 456)


def test_monitor_polls_and_reports_task_error(config, client, monkeypatch, caplog):
    failed = make_run("TERMINATED", "FAILED")
    failed.tasks = [NS(task_key="data_quality", run_id=789,
                       state=NS(result_state=RunResultState.FAILED))]
    client.jobs.get_run.side_effect = [make_run("PENDING"), make_run("RUNNING"), failed]
    client.jobs.get_run_output.return_value = NS(error="Empty Gold table")
    monkeypatch.setattr(runs.time, "sleep", lambda seconds: None)
    assert not runs.wait_for_run(client, config, 456)
    assert "Empty Gold table" in caplog.text


@pytest.mark.parametrize("key,value", [("poll_interval_seconds", 0), ("notebook_run_seconds", -1)])
def test_invalid_timeouts_fail_before_connection(tmp_path, config, client, monkeypatch, key, value):
    config["timeouts"][key] = value
    assert run_main(tmp_path, config, client, monkeypatch) == 1
    client.current_user.me.assert_not_called()
