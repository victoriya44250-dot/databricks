"""LAB 9: preview by default; --execute enables paid compute."""

import argparse
import logging
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

from databricks.sdk import WorkspaceClient

from platform_ops.compute import remove_cluster, request_cluster
from platform_ops.etl import execute_etl, prepare_etl, show_etl_plan
from platform_ops.runs import cancel_run, submit_notebook, wait_for_run
from platform_ops.settings import load_config, prepare, show_plan

LOG = logging.getLogger("lab9")


def execute(client, config, user, notebook_path):
    cluster_id, active_run = None, None
    succeeded = False
    try:
        # 1. Create compute and remember its ID before waiting for startup.
        waiter = request_cluster(client, config, user)
        cluster_id = waiter.cluster_id
        if not cluster_id:
            raise RuntimeError("Create response did not include a cluster ID")
        LOG.info("Created cluster ID: %s", cluster_id)
        waiter.result(timeout=timedelta(seconds=config["timeouts"]["cluster_start_seconds"]))
        # 2. Submit the notebook and monitor this particular run.
        active_run = submit_notebook(client, config, cluster_id, notebook_path)
        LOG.info("Submitted run ID: %s", active_run)
        succeeded = wait_for_run(client, config, active_run)
        active_run = None  # A terminal state was reached; cancellation is unnecessary.
    except (Exception, KeyboardInterrupt) as error:
        LOG.error("Execution failed: %s", error or "Interrupted by user")
    finally:
        # 3. On interruption/timeout, try cancellation and still attempt cleanup.
        if active_run is not None:
            try:
                cancel_run(client, active_run)
            except Exception as error:
                LOG.error("Check run %s: cancellation failed: %s", active_run, error)
        if cluster_id is not None:
            try:
                remove_cluster(client, cluster_id)
            except Exception as error:
                succeeded = False
                LOG.error("CHECK CLUSTER %s: cleanup failed: %s", cluster_id, error)
    LOG.info("Overall result: %s", "SUCCESS" if succeeded else "FAILED")
    return 0 if succeeded else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("config.yml"))
    parser.add_argument("--profile", help="Override profile; 'env' uses CI authentication")
    parser.add_argument("--scenario", choices=("dq", "etl"), default="dq",
                        help="dq: temporary cluster + notebook; etl: full existing LAB 8 Job")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--plan", action="store_true", help="Preview only (default)")
    mode.add_argument("--execute", action="store_true", help="Enable PAID execution of the selected scenario")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(message)s")
    LOG.setLevel(logging.INFO)
    try:
        config = load_config(args.config)
        profile = args.profile or config["workspace"]["profile"]
        client = WorkspaceClient() if profile == "env" else WorkspaceClient(profile=profile)
        if args.scenario == "etl":
            user, job = prepare_etl(client, config)
            show_etl_plan(config, job)
        else:
            user, notebook_path = prepare(client, config)
            show_plan(config, notebook_path)
        if not args.execute:
            print("PLAN ONLY: no compute started.")
            return 0
        # Open a persistent log BEFORE creating compute; IDs are saved as received.
        log_dir = args.config.resolve().parent / "logs"
        log_dir.mkdir(exist_ok=True)
        log_path = log_dir / f"run-{datetime.now():%Y%m%d-%H%M%S}-{uuid4().hex[:8]}.log"
        handler = logging.FileHandler(log_path, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        LOG.addHandler(handler)
        try:
            if args.scenario == "etl":
                LOG.info("Log: %s; caller: %s; Job ID: %s", log_path, user, job.job_id)
                return execute_etl(client, config, job.job_id)
            LOG.info("Log: %s; user: %s; notebook: %s", log_path, user, notebook_path)
            LOG.info("Cluster settings: %s", config["cluster"])
            return execute(client, config, user, notebook_path)
        finally:
            LOG.removeHandler(handler)
            handler.close()
    except Exception as error:
        LOG.error("%s", error)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
