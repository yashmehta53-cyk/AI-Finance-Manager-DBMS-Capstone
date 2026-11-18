# AI Finance Manager — Premium Indian Edition

An enterprise-grade, luxury AI-powered financial management operating system designed for Indian businesses. Grounded in real commercial records from an Indian textile manufacturing and trading enterprise (*Aura TexFab Mills Ltd.*).

---

## 🏛️ Creative & Architectural Identity

- **Design Ethos**: **LUXURY FINANCIAL EDITORIAL × MODERN BRUTALISM × INTELLIGENT FINANCIAL TERMINAL**
- **Palette**: Warm Ivory (`#F4F0E8`), Primary Wine (`#481D2B`), Antique Brass (`#A78A56`), Deep Charcoal (`#191817`), Secondary Ivory (`#EAE4D9`), Architectural Hairline Borders (`#D6CEC1`).
- **Typography**: Editorial Headings in **Cormorant Garamond** (Google Fonts) with UI & tabular data in **Inter** and **JetBrains Mono**.
- **Product Focus**: 100% focused on financial intelligence, corporate cash flow, working capital, tax compliance, and predictive modeling. (Not an ERP or inventory system).

---

## 🇮🇳 Indian Financial & Statutory Localization

- **Functional Currency**: Indian Rupee (INR - **₹**).
- **Numbering System**: Indian grouping conventions (**Lakhs & Crores**):
  - `₹1,000.00`
  - `₹25,000.00`
  - `₹1,25,000.00`
  - `₹10,00,000.00`
  - `₹1,25,00,000.00`
- **Calendar & Financial Cycle**: April 1 to March 31 (**FY 2026-27**).
- **Date Presentation**: Indian convention (`DD-MM-YYYY`).
- **GST Ready**:
  - Registered GSTIN: `33AABCT1332L1Z4` (Tamil Nadu / Tirupur textile hub).
  - Monthly statutory return reconciliation: **GSTR-1** (outward supplies) and **GSTR-3B** (summary tax and Input Tax Credit).
  - Standard textile tax slabs: **5%** (cotton fabric/yarn), **12%** (synthetics & dyes), **18%** (commercial services).
  - Indian payment modes: **UPI**, **NEFT/RTGS**, **Net Banking**, **Cheque**, **Cash**.

---

## ⚡ Key Modules & Navigation

### 1. Executive Dashboard
- **Top Financial KPIs**: Total Revenue, Total Expenses, Net Operating Profit, Quick Liquidity (Bank + Cash), Accounts Receivable (AR), Accounts Payable (AP), Monthly Pacing Variance, Operating EBITDA Margin.
- **Visual Analytics**: Interactive 6-month Revenue vs. Outlay trend line chart and Cost Structure Doughnut chart (Chart.js styled in Wine and Antique Brass).
- **Recent Real-Time Ledger Postings**: Party, payment instrument, GST breakdown, and amount.
- **AI Executive Summary Banner**: Highlights cash runway, working capital exposure, and operational recommendations.

### 2. Financial Management & Ledger
- **General Transactions Ledger**: Search by party or memo, filter by account, category, type (Inflow/Outflow), or custom date range. Pagination support.
- **Post Transaction**: Journal voucher logging with support for UPI, NEFT, Cheque, Party Name, Party GSTIN, and automated GST calculations.
- **Double-Entry Fund Transfers**: Move capital between bank accounts, factory petty cash, and credit lines with atomic balance updates.
- **CSV Data Management**: Batch transaction import with automated NLP categorization and one-click CSV export.

### 3. AI Financial Intelligence Hub
- **Conversational AI Assistant**: Interactive terminal answering executive inquiries grounded exclusively in live ledger aggregations:
  - *"How much did the company spend this month?"*
  - *"What is our current net profit?"*
  - *"How much money is outstanding from customers?"*
  - *"What are our largest operating expenses?"*
  - *"How is cash flow changing?"*
  - *"What financial risks should management review?"*
- **Predictive Spending Forecaster**: Scikit-Learn `LinearRegression` projecting future monthly operational outlays with statistical metrics (MAE, RMSE, trend slope).
- **Statistical Spending Anomaly Detector**: Z-Score deviation engine identifying outlier disbursements exceeding 2.5 standard deviations above category norms.
- **Corporate Risk Surveillance**: Live audits monitoring credit line draws, customer receivable lockup, and raw material cost volatility.

### 4. Customers & Receivables (AR)
- Client directory with registered GSTINs, state jurisdictions, and credit limits.
- Sales order feed mapped directly from the textile enterprise `orders` table.
- Record payment collection modal to settle invoices and update bank balances.

### 5. Suppliers & Payables (AP)
- Creditor directory covering ginning mills, polyester suppliers, chemical dye suppliers, packaging, and state electricity boards.
- Disbursement modal to settle vendor bills with automated account deductions.

### 6. Statutory Financial Reports
- **Profit and Loss Statement (Ind AS)**: Categorized revenue from operations, cost of goods sold, operating overheads, and net operating profit.
- **Balance Sheet Asset & Liability Summary**: Current assets (bank, cash, AR, inventory valuation) vs. current liabilities (AP, cash credit facility).
- **GST Tax Summary**: GSTR-1 and GSTR-3B filings breakdown with taxable turnover, CGST, SGST, IGST, and Input Tax Credit claimed.

### 7. Corporate Settings
- Registered company name, GSTIN, currency parameters, active database engine diagnostics (MySQL 8+ and SQLite fallback), and AI engine parameters.

---

## 🗄️ Database Architecture & Migration

### Dual-Engine Resilience
The application supports **MySQL 8+** via `PyMySQL` with connection pooling, while gracefully falling back to a synchronized local **SQLite** database if MySQL is restarting or offline.

### MySQL Database Setup (`textile_factory`)
To initialize the MySQL database and import the raw SQL dataset:

```powershell
# 1. Ensure your .env has MySQL credentials:
USE_MYSQL=True
DB_USER=root
DB_PASSWORD=YOUR_ACTUAL_PASSWORD
DB_HOST=localhost
DB_PORT=3306
DB_NAME=textile_factory

# 2. Run the automated database initializer:
python init_mysql_database.py
```

### Safe Migration & Import (`migrate_textile_mysql.py`)
Parses `textile-factory-v4-sql-mysql.sql` and populates:
- `products`: 100 textile products (cotton, polyester, specialty).
- `inventory`: 120 inventory stock items with asset valuation.
- `orders`: 500 sales orders spanning FY commercial activity.
- `shifts`: 300 manufacturing shifts and machine utilization records.
- Synchronizes `customers`, `suppliers`, and `tax_records` idempotently without overwriting any existing user data.

```powershell
python migrate_textile_mysql.py
```

### Idempotent INR Currency Migration (`currency_migration.py`)
Converts legacy USD transactions into Indian Rupees at the benchmark RBI exchange rate (1 USD = ₹83.50 INR) with complete reversibility logged in `currency_migration_log`.

```powershell
python currency_migration.py
```

---

## 🧪 Automated Test Suite

Run the full pytest suite:

```powershell
pytest -v test_app.py
```

Covers:
- User authentication and Werkzeug password hashing.
- Atomic balance adjustment upon transaction creation and deletion.
- Budget vs. actual spending calculations (Query A).
- Budget overrun danger alert triggering.
- Goal completion velocity percentage (Query C).
- CSV import with automated column normalization and NLP categorization.
- Scikit-Learn NLP text classification accuracy.
- Indian numbering system formatting (Lakhs and Crores grouping).
- Executive financial metrics calculation (AR, AP, Revenue, Expenses).
- AI Conversational Assistant grounded database query responses.
- Inter-account double-entry fund transfer balance verification.

---

## 🚀 Quickstart & Application Startup

1. **Install Dependencies**:
   ```powershell
   pip install -r requirements.txt
   ```

2. **Run Migrations (if needed)**:
   ```powershell
   python migrate_textile_mysql.py
   python currency_migration.py
   ```

3. **Start the Web Application**:
   ```powershell
   python app.py
   ```

4. **Access the Application**:
   Open [http://localhost:5000](http://localhost:5000) in your browser.

   **Demo Logins**:
   - Username: `alice` | Password: `password123` *(Full Aura TexFab Mills corporate dataset)*
   - Username: `bob` | Password: `password123` *(Standard user profile)*
