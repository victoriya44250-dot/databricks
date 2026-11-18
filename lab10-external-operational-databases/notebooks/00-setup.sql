-- Lab 10: External Operational Databases
-- Setup: Azure SQL connection

CREATE CONNECTION IF NOT EXISTS
  victoriya44250_lab10_azure_sql_conn
TYPE sqlserver
OPTIONS (
  host 'sql-victoriya44250-lab10.database.windows.net',
  port '1433',
  user 'databricks_reader',
  password secret('default', 'victoriya44250-sql-reader')
);

DESCRIBE CONNECTION victoriya44250_lab10_azure_sql_conn;

CREATE FOREIGN CATALOG IF NOT EXISTS
  viktoriia_kalenichenko_lab10
USING CONNECTION victoriya44250_lab10_azure_sql_conn
OPTIONS (database 'free-sql-db-adventureworks');


-- COMMAND ----------

-- Create an empty Delta table for customer CDC history (SCD Type 2)
CREATE TABLE IF NOT EXISTS
dbr_dev_ua5816bd.viktoriia_kalenichenko_lab10.dim_customer_scd2 (
    customer_id     INT,
    title           STRING,
    first_name      STRING,
    middle_name     STRING,
    last_name       STRING,
    suffix          STRING,
    company_name    STRING,
    sales_person    STRING,
    email_address   STRING,
    phone           STRING,
    modified_date   TIMESTAMP,
    valid_from      TIMESTAMP,
    valid_to        TIMESTAMP,
    is_current      BOOLEAN,
    is_deleted      BOOLEAN,
    start_lsn       BINARY,
    end_lsn         BINARY
)
USING DELTA
COMMENT 'Customer history with SCD Type 2 and SQL Server CDC';
