
-- Lab 10 Part B: SQL Server CDC setup
-- Run in Azure SQL Database: free-sql-db-adventureworks

-- 1. Check database-level CDC status
SELECT name, is_cdc_enabled
FROM sys.databases
WHERE name = DB_NAME();

-- 2. Enable CDC for the database (run once)
EXEC sys.sp_cdc_enable_db;

-- 3. Enable CDC for SalesLT.Customer (run once)
EXEC sys.sp_cdc_enable_table
    @source_schema = N'SalesLT',
    @source_name = N'Customer',
    @role_name = NULL,
    @supports_net_changes = 0,
    @captured_column_list = N'CustomerID, Title, FirstName, MiddleName,
                              LastName, Suffix, CompanyName, SalesPerson,
                              EmailAddress, Phone, ModifiedDate';

-- 4. Verify CDC configuration
SELECT name, is_tracked_by_cdc
FROM sys.tables
WHERE schema_id = SCHEMA_ID('SalesLT')
  AND name = 'Customer';

EXEC sys.sp_cdc_help_change_data_capture;
