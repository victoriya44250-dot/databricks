-- Password stored in Azure Key Vault (secret: victoriya44250-sql-reader).
-- Initial setup only. Replace the placeholder before execution.

CREATE USER databricks_reader
WITH PASSWORD = '<password from Azure Key Vault>';

ALTER ROLE db_datareader ADD MEMBER databricks_reader;
