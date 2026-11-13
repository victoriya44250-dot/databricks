from databricks.sdk import WorkspaceClient


client = WorkspaceClient(profile="prod_azure")

expected_host = "https://adb-7405604651938730.10.azuredatabricks.net"

if client.config.host.rstrip("/") != expected_host:
    raise RuntimeError("Host does not match expected value")

user = client.current_user.me()
print(f"Connected as: {user.user_name}")

policy = client.cluster_policies.get(
    policy_id="00173C9A6978A23D"
)
print(f"Policy found: {policy.name}")

print("Connection checks passed")