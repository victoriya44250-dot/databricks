from pathlib import Path

import yaml
from databricks.sdk import WorkspaceClient

# 1. Read the configuration file
config_path = Path(__file__).resolve().parents[1] / "config.yml"
config = yaml.safe_load(config_path.read_text(encoding="utf-8"))

# 2. Connect to the Workspace
client = WorkspaceClient(profile=config["workspace"]["profile"])

expected_host = config["workspace"]["host"].rstrip("/")
if client.config.host.rstrip("/") != expected_host:
    raise RuntimeError("Host does not match expected value")

# 3. Find the job by name
job_name = config["job"]["name"]
matches = list(client.jobs.list(name=job_name))

if len(matches) != 1:
    raise RuntimeError(f"Expected exactly one job named {job_name}, found {len(matches)}")

# 4. Get the job details
job = client.jobs.get(job_id=matches[0].job_id)

if job.settings is None:
    raise RuntimeError("Job settings are unavailable")

# 5. Find the notebook task
task_key = config["job"]["notebook_task_key"]
tasks = [
    task
    for task in job.settings.tasks or []
    if task.task_key == task_key
]

if len(tasks) != 1 or tasks[0].notebook_task is None:
    raise RuntimeError(f"Notebook task not found: {task_key}")

notebook = tasks[0].notebook_task
# 6. Check that the notebook parameters match
deployed_parameters = notebook.base_parameters or {}

for name, value in config["notebook_parameters"].items():
    if deployed_parameters.get(name) != value:
        raise RuntimeError(
            f"Parameter mismatch for {name}: "
            f"config={value}, job={deployed_parameters.get(name)}"
        )

# 7. Display the results
print(f"Job found: {job.settings.name}")
print(f"Job ID: {job.job_id}")
print(f"Task found: {task_key}")
print(f"Notebook path: {notebook.notebook_path}")
print("Notebook parameters match")
print("Preflight checks passed — no compute started")

# Select a runtime for the job
runtime = client.clusters.select_spark_version(
    long_term_support=True,
    latest=True,
    ml=False,
    gpu=False,
    scala="2.12",
)

print(f"Selected runtime: {runtime}")
