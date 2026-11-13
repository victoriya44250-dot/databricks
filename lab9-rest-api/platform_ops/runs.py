"""Submit a notebook and monitor its execution."""

import logging
import time
from datetime import timedelta
from uuid import uuid4

from databricks.sdk.service.jobs import NotebookTask, Source, SubmitTask

LOG = logging.getLogger("lab9")
TERMINAL = {"TERMINATED", "SKIPPED", "INTERNAL_ERROR"}


def submit_notebook(client, config, cluster_id, notebook_path):
    run = client.jobs.submit(
        run_name="lab9-data-quality", idempotency_token=uuid4().hex,
        timeout_seconds=config["timeouts"]["notebook_run_seconds"],
        tasks=[SubmitTask(
            task_key="data_quality", existing_cluster_id=cluster_id,
            notebook_task=NotebookTask(notebook_path=notebook_path,
                                      source=Source.WORKSPACE,
                                      base_parameters=config["notebook_parameters"]),
        )],
    )
    if not run.run_id:
        raise RuntimeError("Submit response did not include a run ID")
    return run.run_id


def wait_for_run(client, config, run_id, *, timeout_seconds=None, expected_tasks=None):
    # Wait longer locally so Databricks can report its own notebook timeout first.
    if timeout_seconds is None:
        timeout_seconds = config["timeouts"]["notebook_run_seconds"] + 300
    deadline = time.monotonic() + timeout_seconds
    previous = None
    while True:
        run = client.jobs.get_run(run_id=run_id)
        state = run.state
        lifecycle = state.life_cycle_state.value if state and state.life_cycle_state else None
        result = state.result_state.value if state and state.result_state else None
        if (lifecycle, result) != previous:
            LOG.info("Run %s: %s / %s", run_id, lifecycle, result)
            previous = lifecycle, result
        if lifecycle in TERMINAL:
            LOG.info("Run page: %s", run.run_page_url)
            succeeded = result == "SUCCESS"
            if expected_tasks is not None:
                outcomes = {
                    task.task_key: task.state.result_state.value
                    if task.state and task.state.result_state else None
                    for task in run.tasks or []
                }
                LOG.info("Task results: %s", outcomes)
                succeeded = (succeeded and set(outcomes) == set(expected_tasks)
                             and all(value == "SUCCESS" for value in outcomes.values()))
            if not succeeded:
                log_failure(client, run)
            return succeeded
        if time.monotonic() >= deadline:
            raise TimeoutError(f"Run {run_id} exceeded local timeout")
        time.sleep(config["timeouts"]["poll_interval_seconds"])


def log_failure(client, run):
    LOG.error("Run failed: %s", run.state.state_message)
    for task in run.tasks or []:
        if task.state and task.state.result_state and task.state.result_state.value == "SUCCESS":
            continue
        try:
            output = client.jobs.get_run_output(run_id=task.run_id)
            LOG.error("Task %s: %s", task.task_key, output.error)
        except Exception as error:
            LOG.warning("Could not read task output: %s", error)


def cancel_run(client, run_id):
    client.jobs.cancel_run(run_id=run_id).result(timeout=timedelta(minutes=5))
    LOG.info("Run %s cancellation finished", run_id)
