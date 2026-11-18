-- Lab 10 Part B: Initial Customer Load

-- Load customers once and store the initial CDC watermark
INSERT INTO dbr_dev_ua5816bd.viktoriia_kalenichenko_lab10.dim_customer_scd2 (
    customer_id, title, first_name, middle_name, last_name,
    suffix, company_name, sales_person, email_address, phone,
    modified_date, valid_from, valid_to, is_current, is_deleted,
    start_lsn, end_lsn
) 
SELECT c.CustomerID, c.Title, c.FirstName, c.MiddleName, c.LastName,c.Suffix, c.CompanyName, c.SalesPerson,
    c.EmailAddress, c.Phone, c.ModifiedDate,
    current_timestamp(),
    CAST(NULL AS TIMESTAMP),
    true,
    false,
    (SELECT MAX(start_lsn)
     FROM victoriya44250_lab10_adventureworkslt.cdc.lsn_time_mapping),
    CAST(NULL AS BINARY)
FROM victoriya44250_lab10_adventureworkslt.saleslt.customer c
WHERE NOT EXISTS (
    SELECT 1
    FROM dbr_dev_ua5816bd.viktoriia_kalenichenko_lab10.dim_customer_scd2
);

-- COMMAND ----------

-- Verify initial customer records
SELECT
    COUNT(*) AS total_versions,
    COUNT_IF(is_current) AS current_customers,
    COUNT_IF(is_deleted) AS deleted_customers,
    COUNT_IF(start_lsn IS NOT NULL) AS rows_with_lsn
FROM dbr_dev_ua5816bd.viktoriia_kalenichenko_lab10.dim_customer_scd2;
