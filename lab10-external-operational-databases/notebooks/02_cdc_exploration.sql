-- Databricks notebook source
-- Lab 10 Part B: CDC Exploration

-- COMMAND ----------

-- 1. Verify CDC tables and LSN mapping
SHOW TABLES IN victoriya44250_lab10_adventureworkslt.cdc;

SELECT start_lsn, tran_end_time
FROM victoriya44250_lab10_adventureworkslt.cdc.lsn_time_mapping
ORDER BY tran_end_time DESC
LIMIT 10;

-- COMMAND ----------

-- 2. Check INSERT events for Olivia and Daniel
SELECT `__$operation` AS operation, CustomerID,FirstName, LastName, CompanyName
FROM victoriya44250_lab10_adventureworkslt.cdc.saleslt_customer_ct
WHERE CustomerID IN (30119, 30120)
  AND `__$operation` = 2
ORDER BY CustomerID;

-- COMMAND ----------

-- 3. Check company rebranding (Olivia)
SELECT `__$operation` AS operation, CustomerID, CompanyName, ModifiedDate
FROM victoriya44250_lab10_adventureworkslt.cdc.saleslt_customer_ct
WHERE CustomerID = 30119
ORDER BY `__$start_lsn`, `__$seqval`, `__$operation`;

-- COMMAND ----------

-- 4. Check sequential email and phone updates (Daniel)
SELECT `__$operation` AS operation, CustomerID, EmailAddress, Phone
FROM victoriya44250_lab10_adventureworkslt.cdc.saleslt_customer_ct
WHERE CustomerID = 30120
ORDER BY `__$start_lsn`, `__$seqval`, `__$operation`;

-- COMMAND ----------

-- 5. Check INSERT and DELETE events (Ethan)
SELECT `__$operation` AS operation, CustomerID,  FirstName, LastName
FROM victoriya44250_lab10_adventureworkslt.cdc.saleslt_customer_ct
WHERE CustomerID = 30121
ORDER BY `__$start_lsn`, `__$seqval`, `__$operation`;

-- COMMAND ----------

-- 6. Check CDC event counts after no-op UPDATE (Olivia)
SELECT `__$operation` AS operation, COUNT(*) AS event_count
FROM victoriya44250_lab10_adventureworkslt.cdc.saleslt_customer_ct
WHERE CustomerID = 30119
GROUP BY `__$operation`
ORDER BY `__$operation`;
