"""Read the configuration and check existing Databricks resources."""

from pathlib import Path

import yaml


def load_config(path):
    config = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if config["cluster"]["num_workers"] != 0:
        raise ValueError("This scenario requires num_workers: 0")
    if not 10 <= config["cluster"]["autotermination_minutes"] <= 30:
        raise ValueError("Use 10-30 minutes for auto-termination")
    for key in ("cluster_start_seconds", "notebook_run_seconds", "poll_interval_seconds"):
        if type(config["timeouts"][key]) is not int or config["timeouts"][key] <= 0:
            raise ValueError(f"{key} must be a positive integer")
    return config


def prepare(client, config):
    """Read metadata only: no clusters or runs are created here."""
    if client.config.host.rstrip("/") != config["workspace"]["host"].rstrip("/"):
        raise ValueError("Profile points to another Workspace")
    user = client.current_user.me().user_name
    if not user:
        raise ValueError("Current user is unavailable")
    client.cluster_policies.get(policy_id=config["cluster"]["policy_id"])
    versions = client.clusters.spark_versions().versions or []
    if config["cluster"]["spark_version"] not in [version.key for version in versions]:
        raise ValueError("Configured Runtime is unavailable")

    matches = list(client.jobs.list(name=config["job"]["name"]))
    if len(matches) != 1:
        raise ValueError(f"Expected one LAB 8 Job, found {len(matches)}")
    job = client.jobs.get(job_id=matches[0].job_id)
    if job.settings is None:
        raise ValueError("Job settings are unavailable")
    tasks = [task for task in job.settings.tasks or []
             if task.task_key == config["job"]["notebook_task_key"]]
    if len(tasks) != 1 or tasks[0].notebook_task is None:
        raise ValueError("Expected one notebook task")
    notebook = tasks[0].notebook_task
    if (getattr(notebook.source, "value", notebook.source) == "GIT"
            or not notebook.notebook_path.startswith("/")):
        raise ValueError("Expected an absolute Workspace notebook path")
    item = client.workspace.get_status(path=notebook.notebook_path)
    if getattr(item.object_type, "value", item.object_type) != "NOTEBOOK":
        raise ValueError("The path does not point to a notebook")
    for key, value in config["notebook_parameters"].items():
        if (notebook.base_parameters or {}).get(key) != value:
            raise ValueError(f"Notebook parameter differs from LAB 8: {key}")
    return user, notebook.notebook_path


def show_plan(config, notebook_path):
    cluster = config["cluster"]
    print(f"Workspace: {config['workspace']['host']}")
    print(f"Notebook: {notebook_path}")
    print(f"Compute: {cluster['node_type_id']}, single node, {cluster['spark_version']}")
    print(f"Idle auto-termination: {cluster['autotermination_minutes']} minutes")
    print(f"Notebook timeout: {config['timeouts']['notebook_run_seconds']} seconds")
    print(f"Parameters: {config['notebook_parameters']}")
    print("Scope: run data_quality only; keep the existing LAB 8 Job unchanged.")
