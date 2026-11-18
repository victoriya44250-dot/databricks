# Lab 10: Incremental CDC Merge (SCD Type 2)

# COMMAND ----------

SOURCE = "victoriya44250_lab10_adventureworkslt"
TARGET = "dbr_dev_ua5816bd.viktoriia_kalenichenko_lab10.dim_customer_scd2"

# COMMAND ----------

# Check the initial state before processing changes.
display(spark.sql(f"""
SELECT
    COUNT(*) AS total_versions,
    COUNT_IF(is_current) AS current_customers,
    MAX(start_lsn) AS latest_start_lsn
FROM {TARGET}
"""))

# COMMAND ----------

# Process only new CDC events in one atomic Delta MERGE.
# Operation codes: 1=DELETE, 2=INSERT, 4=UPDATE AFTER.

merge_sql = f"""
MERGE INTO {TARGET} AS t
USING (
    WITH events AS (
        SELECT
            ct.`__$start_lsn` AS lsn,
            ct.`__$seqval` AS seqval,
            ct.`__$operation` AS op,
            m.tran_end_time AS change_time,
            ct.CustomerID AS customer_id,
            ct.Title AS title,
            ct.FirstName AS first_name,
            ct.MiddleName AS middle_name,
            ct.LastName AS last_name,
            ct.Suffix AS suffix,
            ct.CompanyName AS company_name,
            ct.SalesPerson AS sales_person,
            ct.EmailAddress AS email_address,
            ct.Phone AS phone,
            ct.ModifiedDate AS modified_date
        FROM {SOURCE}.cdc.saleslt_customer_ct ct
        JOIN {SOURCE}.cdc.lsn_time_mapping m
          ON ct.`__$start_lsn` = m.start_lsn
        WHERE ct.`__$operation` IN (1, 2, 4)
          AND ct.`__$start_lsn` > (
              SELECT COALESCE(
                  GREATEST(MAX(start_lsn), MAX(end_lsn)),
                  X'00'
              )
              FROM {TARGET}
          )
    ),
    ordered AS (
        SELECT *,
            ROW_NUMBER() OVER w AS event_no,
            LEAD(op) OVER w AS next_op,
            LEAD(change_time) OVER w AS next_time,
            LEAD(lsn) OVER w AS next_lsn
        FROM events
        WINDOW w AS (
            PARTITION BY customer_id
            ORDER BY lsn, seqval
        )
    )

    -- Close the existing current version, if present.
    SELECT
        customer_id AS merge_key,
        op, change_time, lsn,
        customer_id, title, first_name, middle_name,
        last_name, suffix, company_name, sales_person,
        email_address, phone, modified_date,
        CAST(NULL AS TIMESTAMP) AS valid_from,
        CAST(NULL AS TIMESTAMP) AS valid_to,
        CAST(NULL AS BOOLEAN) AS is_current,
        CAST(NULL AS BOOLEAN) AS is_deleted,
        CAST(NULL AS BINARY) AS end_lsn
    FROM ordered
    WHERE event_no = 1

    UNION ALL

    -- Create every INSERT/UPDATE version, preserving intermediate changes.
    SELECT
        CAST(NULL AS INT) AS merge_key,
        op, change_time, lsn,
        customer_id, title, first_name, middle_name,
        last_name, suffix, company_name, sales_person,
        email_address, phone, modified_date,
        change_time AS valid_from,
        next_time AS valid_to,
        next_time IS NULL AS is_current,
        COALESCE(next_op = 1, false) AS is_deleted,
        next_lsn AS end_lsn
    FROM ordered
    WHERE op IN (2, 4)
) AS s
ON t.customer_id = s.merge_key AND t.is_current = true

WHEN MATCHED THEN UPDATE SET
    t.valid_to = s.change_time,
    t.is_current = false,
    t.is_deleted = (s.op = 1),
    t.end_lsn = s.lsn

WHEN NOT MATCHED AND s.merge_key IS NULL THEN INSERT (
    customer_id, title, first_name, middle_name,
    last_name, suffix, company_name, sales_person,
    email_address, phone, modified_date,
    valid_from, valid_to, is_current, is_deleted,
    start_lsn, end_lsn
) VALUES (
    s.customer_id, s.title, s.first_name, s.middle_name,
    s.last_name, s.suffix, s.company_name, s.sales_person,
    s.email_address, s.phone, s.modified_date,
    s.valid_from, s.valid_to, s.is_current, s.is_deleted,
    s.lsn, s.end_lsn
)
"""

spark.sql(merge_sql)

# COMMAND ----------

# Verify customer history after the merge.
display(spark.sql(f"""
SELECT
    customer_id,
    company_name,
    email_address,
    phone,
    valid_from,
    valid_to,
    is_current,
    is_deleted
FROM {TARGET}
WHERE customer_id IN (30119, 30120, 30121)
ORDER BY customer_id, valid_from, start_lsn
"""))

# COMMAND ----------

# Check final version counts.
display(spark.sql(f"""
SELECT
    COUNT(*) AS total_versions,
    COUNT_IF(is_current) AS current_customers,
    COUNT_IF(is_deleted) AS deleted_versions
FROM {TARGET}
"""))


# COMMAND ----------

# Validate historical, current and deleted versions
display(spark.sql(f"""
SELECT
    customer_id,
    COUNT(*) AS versions,
    COUNT_IF(is_current) AS current_versions,
    COUNT_IF(is_deleted) AS deleted_versions
FROM {TARGET}
WHERE customer_id IN (30119, 30120, 30121)
GROUP BY customer_id
ORDER BY customer_id
"""))

