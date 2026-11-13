"""Full ETL tests with mocked API responses: no Databricks connection."""

from types import SimpleNamespace as NS
from unittest.mock import MagicMock

import pytest
import yaml
from databricks.sdk.service.jobs import (
    Job, JobSettings, NotebookTask, Run, RunLifeCycleState, RunResultState,
    RunState, RunTask, Task,
)

import automation
from platform_ops import etl, runs


@pytest.fixture
def config():
    return {
        "workspace": {"profile": "test", "host": "https://example.azuredatabricks.net"},
        "job": {"name": "prod_lab8_pipeline", "notebook_task_key": "data_quality"},
        "notebook_parameters": {"catalog": "test_catalog", "gold_schema": "test_gold"},
        "cluster": {"num_workers": 0, "autotermination_minutes": 15},
        "timeouts": {"cluster_start_seconds": 1200, "notebook_run_seconds": 900,
                     "poll_interval_seconds": 15},
        "etl": {"timeout_seconds": 3600, "expected_tasks": [
            "bootstrap", "bronze_ingestion", "silver_climate", "silver_environment",
            "country_scd1", "gold_transformations", "data_quality",
        ]},
    }


def finished_run(config, result="SUCCESS"):
    return Run(
        run_id=456, run_page_url="https://example/run/456",
        state=RunState(life_cycle_state=RunLifeCycleState.TERMINATED,
                       result_state=RunResultState(result)),
        tasks=[RunTask(task_key=key, run_id=800 + index,
                       state=RunState(result_state=RunResultState(result)))
               for index, key in enumerate(config["etl"]["expected_tasks"])],
    )


@pytest.fixture
def client(config):
    client = MagicMock()
    client.config.host = config["workspace"]["host"]
    client.current_user.me.return_value = NS(user_name="student@example.com")
    client.jobs.list.return_value = [Job(job_id=123)]
    client.jobs.get.return_value = Job(job_id=123, settings=JobSettings(
        name="prod_lab8_pipeline", tasks=[
            Task(task_key=key, environment_key="default", notebook_task=NotebookTask(
                notebook_path=f"/Workspace/{key}",
                base_parameters=dict(config["notebook_parameters"])))
            for key in config["etl"]["expected_tasks"]
        ],
    ))
    client.jobs.list_runs.return_value = []
    client.jobs.run_now.return_value.run_id = 456
    client.jobs.get_run.return_value = finished_run(config)
    return client


def run_main(tmp_path, config, client, monkeypatch, *flags):
    path = tmp_path / "config.yml"
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    monkeypatch.setattr(automation, "WorkspaceClient", lambda **kwargs: client)
    return automation.main(["--config", str(path), "--scenario", "etl", *flags])


@pytest.mark.parametrize("flags", [[], ["--plan"]])
def test_etl_preview_reads_metadata_only(tmp_path, config, client, monkeypatch, capsys, flags):
    assert run_main(tmp_path, config, client, monkeypatch, *flags) == 0
    client.jobs.run_now.assert_not_called()
    client.jobs.submit.assert_not_called()
    assert not client.clusters.mock_calls
    client.cluster_policies.get.assert_not_called()
    assert not (tmp_path / "logs").exists()
    assert "PLAN ONLY: no compute started." in capsys.readouterr().out


def test_etl_executes_all_tasks_and_preserves_existing_compute(tmp_path, config, client, monkeypatch):
    assert run_main(tmp_path, config, client, monkeypatch, "--execute") == 0
    request = client.jobs.run_now.call_args.kwargs
    assert request["job_id"] == 123
    assert set(request) == {"job_id", "idempotency_token"}  # No task subset or parameter overrides.
    assert len(request["idempotency_token"]) == 32
    client.jobs.run_now.assert_called_once()
    client.jobs.submit.assert_not_called()
    client.jobs.update.assert_not_called()
    client.jobs.reset.assert_not_called()
    client.jobs.cancel_run.assert_not_called()
    assert not client.clusters.mock_calls
    log = next((tmp_path / "logs").glob("*.log")).read_text(encoding="utf-8")
    assert "Submitted ETL run ID: 456" in log
    assert "Overall ETL result: SUCCESS" in log
    for key in config["etl"]["expected_tasks"]:
        assert key in log


def test_etl_task_drift_prevents_paid_request(tmp_path, config, client, monkeypatch):
    client.jobs.get.return_value.settings.tasks.pop()
    assert run_main(tmp_path, config, client, monkeypatch, "--execute") == 1
    client.jobs.run_now.assert_not_called()


def test_etl_wrong_catalog_prevents_paid_request(tmp_path, config, client, monkeypatch):
    client.jobs.get.return_value.settings.tasks[0].notebook_task.base_parameters["catalog"] = "wrong"
    assert run_main(tmp_path, config, client, monkeypatch, "--execute") == 1
    client.jobs.run_now.assert_not_called()


def test_etl_active_run_prevents_duplicate(client, config):
    client.jobs.list_runs.return_value = [NS(run_id=999)]
    assert etl.execute_etl(client, config, 123) == 1
    client.jobs.run_now.assert_not_called()
    client.jobs.cancel_run.assert_not_called()


@pytest.mark.parametrize("result", ["FAILED", "CANCELED", "TIMEDOUT"])
def test_etl_failed_run_returns_nonzero(client, config, result):
    client.jobs.get_run.return_value = finished_run(config, result)
    assert etl.execute_etl(client, config, 123) == 1
    client.jobs.cancel_run.assert_not_called()  # Already terminal.


@pytest.mark.parametrize("task_result", ["FAILED", "EXCLUDED", "CANCELED"])
def test_overall_success_requires_every_task_to_succeed(client, config, task_result):
    client.jobs.get_run.return_value.tasks[0].state.result_state = RunResultState(task_result)
    assert etl.execute_etl(client, config, 123) == 1


def test_etl_missing_task_result_is_not_success(client, config):
    client.jobs.get_run.return_value.tasks.pop()
    assert etl.execute_etl(client, config, 123) == 1


@pytest.mark.parametrize("error", [TimeoutError("deadline"), KeyboardInterrupt()])
def test_etl_interrupted_monitor_cancels_only_own_run(client, config, monkeypatch, error):
    def interrupted(*args, **kwargs):
        raise error
    monkeypatch.setattr(etl, "wait_for_run", interrupted)
    assert etl.execute_etl(client, config, 123) == 1
    client.jobs.cancel_run.assert_called_once_with(run_id=456)
    assert not client.clusters.mock_calls


def test_etl_monitor_uses_its_own_timeout(client, config, monkeypatch):
    client.jobs.get_run.return_value = Run(state=RunState(life_cycle_state=RunLifeCycleState.RUNNING))
    ticks = iter([0, 1500, 3601])  # Exceeds DQ timeout first, then the ETL timeout.
    monkeypatch.setattr(runs.time, "monotonic", lambda: next(ticks))
    monkeypatch.setattr(runs.time, "sleep", lambda seconds: None)
    assert etl.execute_etl(client, config, 123) == 1
    assert client.jobs.get_run.call_count == 2
    client.jobs.cancel_run.assert_called_once_with(run_id=456)


def test_etl_cancellation_failure_reports_run_id(client, config, monkeypatch, caplog):
    def interrupted(*args, **kwargs):
        raise TimeoutError("deadline")
    monkeypatch.setattr(etl, "wait_for_run", interrupted)
    client.jobs.cancel_run.side_effect = RuntimeError("Permission denied")
    assert etl.execute_etl(client, config, 123) == 1
    assert "CHECK ETL RUN 456" in caplog.text


def test_missing_run_id_never_reports_success(client, config):
    client.jobs.run_now.return_value.run_id = None
    assert etl.execute_etl(client, config, 123) == 1
    client.jobs.get_run.assert_not_called()
    client.jobs.cancel_run.assert_not_called()


@pytest.mark.parametrize("value", [0, -1, "3600", True])
def test_bad_etl_timeout_prevents_execution(tmp_path, config, client, monkeypatch, value):
    config["etl"]["timeout_seconds"] = value
    assert run_main(tmp_path, config, client, monkeypatch, "--execute") == 1
    client.jobs.run_now.assert_not_called()
