-- =====================================================================
-- Sample Data Script: AI Finance Manager
-- Textile Raw-Material Manufacturing & Trading Demonstration Data
-- Currency: INR (₹)
-- =====================================================================

USE finance_db;

-- 1. Users (Passwords hashed via Werkzeug scrypt/pbkdf2: password 'password123')
INSERT INTO users (user_id, username, email, password_hash) VALUES
(1, 'alice', 'alice@example.com', 'scrypt:32768:8:1$x8k4y7H9oP2q$0f2e2fa9d6bf08ceca761be945ea45cfddadfaae4714bf485e9e8f1bb8ec19ff1c9bcf281a8c9b33a76ef4829ad4dc351fc8aa7899be4ea5bc755609ff0e2712'),
(2, 'bob', 'bob@example.com', 'scrypt:32768:8:1$x8k4y7H9oP2q$0f2e2fa9d6bf08ceca761be945ea45cfddadfaae4714bf485e9e8f1bb8ec19ff1c9bcf281a8c9b33a76ef4829ad4dc351fc8aa7899be4ea5bc755609ff0e2712')
ON DUPLICATE KEY UPDATE username=username;

-- 2. Accounts (Alice has Current and Credit accounts, Bob has Checking)
INSERT INTO accounts (account_id, user_id, name, type, balance) VALUES
(1, 1, 'HDFC Current Account (Operations)', 'Checking', 1845200.00),
(2, 1, 'SBI Cash Credit (CC) Facility', 'Credit', 3250000.00),
(3, 2, 'Bob Checking', 'Checking', 120000.00),
(4, 1, 'Factory Petty Cash (Coimbatore)', 'Cash', 85400.00)
ON DUPLICATE KEY UPDATE balance=VALUES(balance);

-- 3. Categories (Global categories have user_id = NULL)
INSERT INTO categories (category_id, user_id, name, type) VALUES
(1, NULL, 'Sales revenue', 'Income'),
(2, NULL, 'Raw cotton purchases', 'Expense'),
(3, NULL, 'Cotton yarn and polyester fibre purchases', 'Expense'),
(4, NULL, 'Factory electricity and utilities', 'Expense'),
(5, NULL, 'Transportation and freight', 'Expense'),
(6, NULL, 'Employee wages', 'Expense'),
(7, NULL, 'Customer receipts', 'Income'),
(8, NULL, 'Machine maintenance', 'Expense'),
(9, NULL, 'Packaging materials', 'Expense'),
(10, NULL, 'Textile dyes, pigments, and processing chemicals', 'Expense'),
(11, 1, 'Gaming', 'Expense') -- Alice-specific custom category
ON DUPLICATE KEY UPDATE name=VALUES(name);

-- 4. Transactions (Sample historical & current textile transactions)
INSERT INTO transactions (txn_id, user_id, account_id, category_id, date, amount, description, txn_type) VALUES
(1, 1, 1, 1, '2026-10-01', 520000.00, 'Sale of 3,500 kg carded yarn to Arvind Texfab Mills (Inv #TX-2601)', 'Income'),
(2, 1, 2, 2, '2026-10-02', 240000.00, 'Purchase of 2,000 kg raw cotton Shankar-6 from Gujarat Cotton Traders Co.', 'Expense'),
(3, 1, 1, 4, '2026-10-03', 145000.00, 'State Electricity Board HT industrial power bill - Spinning Unit 1', 'Expense'),
(4, 2, 3, 2, '2026-10-01', 1850.00, 'Dinner at Local Bistro', 'Expense'),
(5, 1, 1, 3, '2026-10-10', 88000.00, 'Purchase of 800 kg cotton yarn 40s from Vardhman Spinning Mills', 'Expense'),
(6, 1, 1, 5, '2026-10-12', 18500.00, 'Freight charges for raw cotton shipment from Rajkot to Coimbatore mill', 'Expense'),
(7, 1, 1, 6, '2026-10-15', 285000.00, 'Monthly floor operator wages & spinning technicians payroll', 'Expense'),
(8, 1, 1, 8, '2026-10-18', 35000.00, 'Machine maintenance & spindle overhaul - Ring Frame Loom #4', 'Expense')
ON DUPLICATE KEY UPDATE amount=VALUES(amount);

-- 5. Budgets (Alice sets monthly budgets in INR for October 2026)
INSERT INTO budgets (budget_id, user_id, category_id, month, limit_amount) VALUES
(1, 1, 2, '2026-10', 650000.00),
(2, 1, 3, '2026-10', 480000.00),
(3, 1, 4, '2026-10', 175000.00),
(4, 1, 6, '2026-10', 340000.00)
ON DUPLICATE KEY UPDATE limit_amount=VALUES(limit_amount);

-- 6. Goals (Capital expenditure and plant modernization goals in INR)
INSERT INTO goals (goal_id, user_id, name, target_amount, saved_amount, due_date) VALUES
(1, 1, 'High-Speed Ring Frame Loom Upgrade', 2500000.00, 1650000.00, '2026-12-31'),
(2, 1, 'Rooftop Solar PV Installation (150 kW)', 1800000.00, 920000.00, '2027-03-31')
ON DUPLICATE KEY UPDATE saved_amount=VALUES(saved_amount);

-- 7. Investments (Textile and industrial corporate equities in INR)
INSERT INTO investments (inv_id, user_id, instrument, quantity, buy_price, buy_date) VALUES
(1, 1, 'KPR Mill Ltd (Textile Manufacturing)', 150, 840.00, '2026-05-14'),
(2, 1, 'Vardhman Textiles Ltd', 300, 465.00, '2026-06-20')
ON DUPLICATE KEY UPDATE quantity=VALUES(quantity);
