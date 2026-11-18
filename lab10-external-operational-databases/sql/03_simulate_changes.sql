-- Lab 10 Part B: Customer Lifecycle Simulation
-- Run once in Azure SQL after the initial SCD2 load

-- 1. Register two B2B customers
INSERT INTO SalesLT.Customer (FirstName, LastName, CompanyName, EmailAddress, Phone, PasswordHash, PasswordSalt, ModifiedDate)
VALUES
('Olivia', 'Morgan', 'Northstar Cycling Supply',
 'olivia.morgan@example.com', '555-0101',
 'LAB10_NOT_A_REAL_HASH', 'LAB10TEST', GETDATE()),
('Daniel', 'Reed', 'Urban Trail Distribution',
 'daniel.reed@example.com', '555-0102',
 'LAB10_NOT_A_REAL_HASH', 'LAB10TEST', GETDATE());

-- 2. Company rebranding
UPDATE SalesLT.Customer
SET CompanyName = 'Northstar Mobility Group', ModifiedDate = GETDATE()
WHERE CustomerID = 30119;

-- 3. Sequential contact updates
UPDATE SalesLT.Customer
SET EmailAddress = 'daniel.reed@urbantrail.example.com', ModifiedDate = GETDATE()
WHERE CustomerID = 30120;

UPDATE SalesLT.Customer
SET Phone = '555-0199', ModifiedDate = GETDATE()
WHERE CustomerID = 30120;

-- 4. Register a temporary customer
INSERT INTO SalesLT.Customer (FirstName, LastName, CompanyName, EmailAddress, Phone, PasswordHash, PasswordSalt, ModifiedDate)
VALUES ('Ethan', 'Brooks', 'Summit Trail Retail',
        'ethan.brooks@example.com', '555-0103',
        'LAB10_NOT_A_REAL_HASH', 'LAB10TEST', GETDATE());

-- 5. Delete the temporary customer
DELETE FROM SalesLT.Customer
WHERE CustomerID = 30121 AND EmailAddress = 'ethan.brooks@example.com';

-- 6. No-op update test
UPDATE SalesLT.Customer
SET CompanyName = 'Northstar Mobility Group'
WHERE CustomerID = 30119;
