"""Run the existing LAB 8 ETL Job with its deployed settings."""

import logging
from uuid import uuid4

from platform_ops.runs import cancel_run, wait_for_run
from platform_ops.settings import check_workspace, find_job

LOG = logging.getLogger("lab9")


def prepare_etl(client, config):
    """Read metadata and check the full pipeline before allowing execution."""
    user = check_workspace(client, config)
    etl = config["etl"]
    if type(etl["timeout_seconds"]) is not int or etl["timeout_seconds"] <= 0:
        raise ValueError("ETL timeout_seconds must be a positive integer")
    expected = etl["expected_tasks"]
    if (not isinstance(expected, list) or not expected
            or any(not isinstance(key, str) or not key for key in expected)
            or len(set(expected)) != len(expected)):
        raise ValueError("ETL expected_tasks must contain unique task names")
    job = find_job(client, config)
    tasks = job.settings.tasks or []
    if {task.task_key for task in tasks} != set(expected):
        raise ValueError("Deployed Job tasks differ from ETL expected_tasks")
    # Each task retains its own parameters; check the known catalog/schema values.
    for task in tasks:
        if task.notebook_task is None:
            raise ValueError(f"Expected a notebook task: {task.task_key}")
        parameters = task.notebook_task.base_parameters or {}
        for key, value in config["notebook_parameters"].items():
            if (key in parameters or key == "catalog") and parameters.get(key) != value:
                raise ValueError(f"ETL parameter differs: {task.task_key}.{key}")
    return user, job


def show_etl_plan(config, job):
    print(f"Workspace: {config['workspace']['host']}")
    print(f"Full ETL Job: {job.settings.name} (ID: {job.job_id})")
    print("Scope: run ALL deployed tasks, including data_quality.")
    print("Uses deployed notebooks and parameters; ETL may update Bronze/Silver/Gold data.")
    for task in job.settings.tasks:
        compute = (f"existing cluster {task.existing_cluster_id}" if task.existing_cluster_id
                   else f"job cluster {task.job_cluster_key}" if task.job_cluster_key
                   else "task-specific new cluster" if task.new_cluster
                   else f"serverless environment {task.environment_key}" if task.environment_key
                   else "Job-managed compute")
        print(f"  {task.task_key}: {compute}")
    print(f"Local monitoring timeout: {config['etl']['timeout_seconds']} seconds")
    print("No separate LAB 9 cluster is created; existing Job settings are not edited.")


def execute_etl(client, config, job_id):
    active_run = None
    succeeded = False
    try:
        # Avoid another run if this ETL is already active or queued.
        active = next(iter(client.jobs.list_runs(job_id=job_id, active_only=True, limit=1)), None)
        if active is not None:
            raise RuntimeError(f"Job already has active run {active.run_id}; no new run submitted")
        token = uuid4().hex
        LOG.info("Starting full ETL Job %s; request token: %s", job_id, token)
        # No 'only' filter: Databricks runs the complete deployed task graph.
        response = client.jobs.run_now(job_id=job_id, idempotency_token=token)
        active_run = response.run_id
        if not active_run:
            active_run = None
            raise RuntimeError("Run-now response has no run ID; inspect Job runs before retrying")
        LOG.info("Submitted ETL run ID: %s", active_run)
        succeeded = wait_for_run(
            client, config, active_run,
            timeout_seconds=config["etl"]["timeout_seconds"],
            expected_tasks=config["etl"]["expected_tasks"],
        )
        active_run = None  # The run reached a terminal state.
    except (Exception, KeyboardInterrupt) as error:
        LOG.error("ETL execution failed: %s", error or "Interrupted by user")
    finally:
        if active_run is not None:
            try:
                cancel_run(client, active_run)
            except Exception as error:
                LOG.error("CHECK ETL RUN %s: cancellation failed: %s", active_run, error)
    LOG.info("Overall ETL result: %s", "SUCCESS" if succeeded else "FAILED")
    return 0 if succeeded else 1
