"""Create and remove the temporary single-node cluster."""

import logging
import time
from datetime import timedelta
from uuid import uuid4

from databricks.sdk.errors import NotFound
from databricks.sdk.service.compute import (
    AzureAttributes, AzureAvailability, DataSecurityMode, RuntimeEngine,
)

LOG = logging.getLogger("lab9")


def request_cluster(client, config, user):
    """Return the SDK waiter immediately so the caller can save the cluster ID."""
    cluster = config["cluster"]
    return client.clusters.create(
        cluster_name=f"{cluster['name_prefix']}-{uuid4().hex[:8]}",
        policy_id=cluster["policy_id"], apply_policy_default_values=True,
        node_type_id=cluster["node_type_id"], spark_version=cluster["spark_version"],
        num_workers=0, autotermination_minutes=cluster["autotermination_minutes"],
        data_security_mode=DataSecurityMode.SINGLE_USER, single_user_name=user,
        runtime_engine=RuntimeEngine.STANDARD,
        azure_attributes=AzureAttributes(availability=AzureAvailability.ON_DEMAND_AZURE),
        spark_conf={"spark.databricks.cluster.profile": "singleNode", "spark.master": "local[*]"},
        custom_tags={"ResourceClass": "SingleNode", "ManagedBy": "lab9-viktoriia"},
    )


def remove_cluster(client, cluster_id):
    """Terminate, request permanent deletion, then verify list visibility."""
    errors = []
    try:
        client.clusters.delete(cluster_id=cluster_id).result(timeout=timedelta(minutes=10))
        LOG.info("Cluster %s is terminated", cluster_id)
    except NotFound:
        return
    except Exception as error:
        errors.append(f"Termination: {error}")
    # Still attempt deletion if waiting for termination failed.
    try:
        client.clusters.permanent_delete(cluster_id=cluster_id)
        deadline = time.monotonic() + 90
        while any(c.cluster_id == cluster_id for c in client.clusters.list()):
            if time.monotonic() >= deadline:
                raise TimeoutError("Cluster is still visible after deletion request")
            time.sleep(5)
        LOG.info("Permanent deletion accepted; cluster %s is absent from the list", cluster_id)
    except NotFound:
        pass
    except Exception as error:
        errors.append(f"Permanent deletion: {error}")
    if errors:
        raise RuntimeError("; ".join(errors))
