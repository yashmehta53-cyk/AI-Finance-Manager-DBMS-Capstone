"""
Deterministic Textile Manufacturing Sample Data Generator
Generates realistic financial data for a fictional textile raw-material manufacturing
and trading business ('Aura TexFab Mills / Raw Materials Division').
Does not wipe existing data. Safe to execute repeatedly (idempotent).
All figures in Indian Rupees (INR - ₹).
"""

from datetime import date, timedelta
from decimal import Decimal
from models import db, User, Account, Category, Transaction, Budget, Goal, Investment
from ai_engine import classifier

# 1. Categories
TEXTILE_CATEGORIES = [
    # Expense
    ("Raw cotton purchases", "Expense"),
    ("Cotton yarn and polyester fibre purchases", "Expense"),
    ("Viscose fibre purchases", "Expense"),
    ("Textile dyes, pigments, and processing chemicals", "Expense"),
    ("Packaging materials", "Expense"),
    ("Supplier payments", "Expense"),
    ("Factory electricity and utilities", "Expense"),
    ("Employee wages", "Expense"),
    ("Transportation and freight", "Expense"),
    ("Machine maintenance", "Expense"),
    ("Rent and administration", "Expense"),
    ("Bank charges and taxes", "Expense"),
    # General categories to maintain compatibility
    ("Food", "Expense"),
    ("Rent", "Expense"),
    ("Utilities", "Expense"),
    ("Transportation", "Expense"),
    ("Entertainment", "Expense"),
    ("Shopping", "Expense"),
    ("Healthcare", "Expense"),
    
    # Income
    ("Sales revenue", "Income"),
    ("Customer receipts", "Income"),
    ("Salary", "Income"),
    ("Freelance", "Income"),
    ("Investment Payout", "Income")
]

def seed_textile_dataset(target_username='alice'):
    """Populates realistic 6-month textile trading & manufacturing data for user."""
    user = User.query.filter_by(username=target_username).first()
    if not user:
        user = User(username=target_username, email=f"{target_username}@example.com")
        user.set_password('password123')
        db.session.add(user)
        db.session.flush()

    # 1. Ensure Categories exist
    cat_map = {}
    for name, c_type in TEXTILE_CATEGORIES:
        cat = Category.query.filter_by(name=name, user_id=None).first()
        if not cat:
            cat = Category.query.filter_by(name=name, user_id=user.user_id).first()
        if not cat:
            cat = Category(name=name, type=c_type, user_id=None)
            db.session.add(cat)
            db.session.flush()
        cat_map[name] = cat

    # Custom category for user
    gaming_cat = Category.query.filter_by(name='Gaming', user_id=user.user_id).first()
    if not gaming_cat:
        gaming_cat = Category(name='Gaming', type='Expense', user_id=user.user_id)
        db.session.add(gaming_cat)
        db.session.flush()
    cat_map['Gaming'] = gaming_cat

    # 2. Business Accounts
    accounts_config = [
        ("HDFC Current Account (Operations)", "Checking", Decimal('1845200.00')),
        ("SBI Cash Credit (CC) Facility", "Credit", Decimal('3250000.00')),
        ("Factory Petty Cash (Coimbatore)", "Cash", Decimal('85400.00')),
        ("Treasury & Reserve Account", "Savings", Decimal('2460000.00')),
        ("Checking Account", "Checking", Decimal('150000.00')),
        ("Savings Account", "Savings", Decimal('350000.00'))
    ]

    acct_map = {}
    for name, a_type, default_bal in accounts_config:
        acct = Account.query.filter_by(user_id=user.user_id, name=name).first()
        if not acct:
            acct = Account(user_id=user.user_id, name=name, type=a_type, balance=default_bal)
            db.session.add(acct)
            db.session.flush()
        acct_map[name] = acct

    hdfc = acct_map["HDFC Current Account (Operations)"]
    sbi = acct_map["SBI Cash Credit (CC) Facility"]
    cash = acct_map["Factory Petty Cash (Coimbatore)"]
    treasury = acct_map["Treasury & Reserve Account"]

    # 3. Reference Dates for 6-Month Span
    today = date.today()
    cur_year = today.year
    cur_month = today.month

    # Generate multi-month transaction template (Month -5 to Current Month)
    # Total ~120 to 140 realistic transactions
    txns_to_create = []

    # Helper to add transaction definition
    def add_txn(days_ago, txn_type, amount_str, category_name, description, account_obj):
        txns_to_create.append((
            today - timedelta(days=days_ago),
            txn_type,
            Decimal(amount_str),
            cat_map[category_name],
            description,
            account_obj
        ))

    # --- Month -5 (Approx 150-175 days ago) ---
    add_txn(175, 'Income', '485000.00', 'Sales revenue', 'Sale of 3,200 kg carded cotton yarn to Arvind Texfab Mills (Inv #TX-2601)', hdfc)
    add_txn(173, 'Expense', '240000.00', 'Raw cotton purchases', 'Purchase of 2,000 kg raw cotton Shankar-6 from Gujarat Cotton Traders Co.', sbi)
    add_txn(170, 'Expense', '85000.00', 'Cotton yarn and polyester fibre purchases', 'Purchase of 800 kg polyester staple fibre 1.4D from Reliance Polyester Div', sbi)
    add_txn(168, 'Expense', '18500.00', 'Transportation and freight', 'Freight charges for raw cotton shipment from Rajkot to Coimbatore mill', hdfc)
    add_txn(165, 'Income', '320000.00', 'Customer receipts', 'Customer receipt: Part settlement against Inv #TX-2601 from Arvind Texfab', hdfc)
    add_txn(162, 'Expense', '42000.00', 'Textile dyes, pigments, and processing chemicals', 'Reactive dyes and bleaching chemicals lot from Surat Dyechem', hdfc)
    add_txn(160, 'Expense', '142000.00', 'Factory electricity and utilities', 'State Electricity Board HT industrial power bill - Spinning Unit 1', hdfc)
    add_txn(158, 'Expense', '285000.00', 'Employee wages', 'Monthly floor operator wages & spinning technicians payroll', hdfc)
    add_txn(156, 'Expense', '22000.00', 'Machine maintenance', 'Preventive machine maintenance and spindle bearing replacement - Ring Frame #1', hdfc)
    add_txn(155, 'Expense', '14500.00', 'Packaging materials', 'Poly woven yarn packing bags and corrugated cartons from Corrugate Packs', cash)
    add_txn(154, 'Expense', '65000.00', 'Rent and administration', 'Mill shed lease rent & corporate office administration charges', hdfc)
    add_txn(152, 'Expense', '12000.00', 'Bank charges and taxes', 'Bank letter of credit LC processing charges and GST trade settlement', hdfc)
    add_txn(151, 'Expense', '125000.00', 'Supplier payments', 'Supplier payment: Cleared raw cotton invoice #GCT-7102 to Gujarat Cotton Traders', sbi)

    # --- Month -4 (Approx 120-149 days ago) ---
    add_txn(145, 'Income', '560000.00', 'Sales revenue', 'Sale of 2,800 kg combed cotton yarn 40s to Tirupur Knitwear Exports (Inv #TX-2615)', hdfc)
    add_txn(143, 'Expense', '290000.00', 'Raw cotton purchases', 'Purchase of 2,400 kg of raw cotton Shankar-6 from Gujarat Cotton Traders Co.', sbi)
    add_txn(140, 'Expense', '92000.00', 'Cotton yarn and polyester fibre purchases', 'Purchase of 900 kg polyester fibre from Reliance Polyester Div', sbi)
    add_txn(138, 'Expense', '54000.00', 'Viscose fibre purchases', 'Purchase of 500 kg viscose staple fibre from Grasim Industries', sbi)
    add_txn(136, 'Income', '390000.00', 'Customer receipts', 'Customer receipt: Full settlement of Inv #TX-2615 from Tirupur Knitwear Exports', hdfc)
    add_txn(135, 'Expense', '21500.00', 'Transportation and freight', 'Interstate container freight charges for polyester shipment from Hazira', hdfc)
    add_txn(133, 'Expense', '38500.00', 'Textile dyes, pigments, and processing chemicals', 'Sodium hydrosulfite and disperse dyeing auxiliary chemicals from Surat Dyechem', hdfc)
    add_txn(130, 'Expense', '148000.00', 'Factory electricity and utilities', 'Factory electricity tariff bill for Weaving & Spinning Shed', hdfc)
    add_txn(128, 'Expense', '290000.00', 'Employee wages', 'Monthly floor operator wages and weaving technicians payroll', hdfc)
    add_txn(126, 'Expense', '18000.00', 'Machine maintenance', 'Loom motor servicing and oil filtration for Ring Frame #2', hdfc)
    add_txn(125, 'Expense', '16200.00', 'Packaging materials', 'Yarn paper cones and plastic stretch wrap film procurement', cash)
    add_txn(124, 'Expense', '65000.00', 'Rent and administration', 'Industrial premises lease rent and compliance audit expenses', hdfc)
    add_txn(122, 'Expense', '15000.00', 'Bank charges and taxes', 'Trade finance documentation charges and monthly GST settlement', hdfc)
    add_txn(121, 'Expense', '160000.00', 'Supplier payments', 'Supplier payment: Part payment against viscose invoice to Grasim Industries', sbi)

    # --- Month -3 (Approx 90-119 days ago) ---
    add_txn(118, 'Income', '620000.00', 'Sales revenue', 'Sale of 4,000 kg poly-cotton blended yarn to Bhilwara Suiting Co. (Inv #TX-2630)', hdfc)
    add_txn(115, 'Expense', '310000.00', 'Raw cotton purchases', 'Purchase of 2,600 kg of raw cotton Shankar-6 from Gujarat Cotton Traders Co.', sbi)
    add_txn(113, 'Expense', '110000.00', 'Cotton yarn and polyester fibre purchases', 'Purchase of 1,100 kg combed cotton yarn 30s from Vardhman Spinning Mills', sbi)
    add_txn(111, 'Expense', '24000.00', 'Transportation and freight', 'Freight charges for raw-material shipment from Surat dye hub', hdfc)
    add_txn(108, 'Income', '450000.00', 'Customer receipts', 'Customer receipt: Invoice payment received from Bhilwara Suiting Co.', hdfc)
    add_txn(105, 'Expense', '46000.00', 'Textile dyes, pigments, and processing chemicals', 'Reactive black and navy blue dye pigments from Surat Dyechem', hdfc)
    add_txn(103, 'Expense', '152000.00', 'Factory electricity and utilities', 'Factory electricity and industrial utility power bill', hdfc)
    add_txn(100, 'Expense', '295000.00', 'Employee wages', 'Monthly floor operator wages & spinning technicians payroll', hdfc)
    add_txn(98, 'Expense', '34000.00', 'Machine maintenance', 'Major spindle overhaul and roller bearing replacement - Carding Unit #2', hdfc)
    add_txn(96, 'Expense', '19500.00', 'Packaging materials', 'Heavy duty poly woven textile bale wraps and cardboard cones', cash)
    add_txn(95, 'Expense', '65000.00', 'Rent and administration', 'Mill shed lease rent & corporate office administration charges', hdfc)
    add_txn(93, 'Expense', '13500.00', 'Bank charges and taxes', 'Bank trade loan interest debit and RTGS remittance fee', hdfc)
    add_txn(91, 'Expense', '180000.00', 'Supplier payments', 'Supplier payment: Settled outstanding invoice with Vardhman Spinning Mills', sbi)
    add_txn(90, 'Income', '35000.00', 'Investment Payout', 'Quarterly dividend payout from KPR Mill & Vardhman Textiles holdings', treasury)

    # --- Month -2 (Approx 60-89 days ago) ---
    add_txn(88, 'Income', '590000.00', 'Sales revenue', 'Sale of 3,500 kg carded weaving yarn to Ichalkaranji Powerloom Syndicate (Inv #TX-2645)', hdfc)
    add_txn(85, 'Expense', '330000.00', 'Raw cotton purchases', 'Purchase of 2,800 kg of raw cotton Shankar-6 from Gujarat Cotton Traders Co.', sbi)
    add_txn(83, 'Expense', '98000.00', 'Cotton yarn and polyester fibre purchases', 'Purchase of 950 kg polyester fibre 1.4D from Reliance Polyester Div', sbi)
    add_txn(80, 'Expense', '62000.00', 'Viscose fibre purchases', 'Purchase of 600 kg viscose fibre from Grasim Industries', sbi)
    add_txn(78, 'Income', '410000.00', 'Customer receipts', 'Customer receipt: Payment against Inv #TX-2645 from Ichalkaranji Powerloom Syndicate', hdfc)
    add_txn(76, 'Expense', '26500.00', 'Transportation and freight', 'Freight charges for raw-material shipment from Rajkot to Coimbatore', hdfc)
    add_txn(74, 'Expense', '44000.00', 'Textile dyes, pigments, and processing chemicals', 'Textile processing scouring agents and optical brighteners from Surat Dyechem', hdfc)
    add_txn(71, 'Expense', '155000.00', 'Factory electricity and utilities', 'Factory electricity and utilities bill - Substation 3', hdfc)
    add_txn(69, 'Expense', '300000.00', 'Employee wages', 'Monthly floor operator wages & spinning technicians payroll', hdfc)
    add_txn(67, 'Expense', '21000.00', 'Machine maintenance', 'Preventive maintenance and belt replacements for Combing Unit', hdfc)
    add_txn(65, 'Expense', '17800.00', 'Packaging materials', 'Cardboard cartons and moisture barrier poly bags', cash)
    add_txn(63, 'Expense', '65000.00', 'Rent and administration', 'Mill shed lease rent & corporate administration expenses', hdfc)
    add_txn(61, 'Expense', '16500.00', 'Bank charges and taxes', 'Bank trade finance processing fees & GST tax remittance', hdfc)
    add_txn(60, 'Expense', '210000.00', 'Supplier payments', 'Supplier payment: Cleared raw cotton invoice #GCT-7890 to Gujarat Cotton Traders', sbi)

    # --- Month -1 (Approx 30-59 days ago) ---
    add_txn(58, 'Income', '680000.00', 'Sales revenue', 'Sale of 4,200 kg high-strength polyester-cotton yarn to Shahi Garments (Inv #TX-2660)', hdfc)
    add_txn(55, 'Expense', '350000.00', 'Raw cotton purchases', 'Purchase of 3,000 kg of raw cotton Shankar-6 from Gujarat Cotton Traders Co.', sbi)
    add_txn(53, 'Expense', '125000.00', 'Cotton yarn and polyester fibre purchases', 'Purchase of 1,200 kg cotton yarn 40s from Vardhman Spinning Mills', sbi)
    add_txn(50, 'Expense', '29000.00', 'Transportation and freight', 'Container freight charges for finished yarn delivery to Bangalore garment hub', hdfc)
    add_txn(48, 'Income', '520000.00', 'Customer receipts', 'Customer receipt: Part payment received against customer invoice #TX-2660 from Shahi Garments', hdfc)
    add_txn(46, 'Expense', '51000.00', 'Textile dyes, pigments, and processing chemicals', 'Textile dyes, pigments, and processing chemicals from Surat Dyechem', hdfc)
    add_txn(43, 'Expense', '158000.00', 'Factory electricity and utilities', 'Factory electricity tariff and water treatment plant utility charges', hdfc)
    add_txn(40, 'Expense', '310000.00', 'Employee wages', 'Monthly floor operator wages and spinning machine technicians', hdfc)
    add_txn(38, 'Expense', '27500.00', 'Machine maintenance', 'Ring frame spindle alignment & gearbox maintenance by LMW service engineers', hdfc)
    add_txn(36, 'Expense', '21000.00', 'Packaging materials', 'Poly woven yarn packing bags and shrink film rolls', cash)
    add_txn(34, 'Expense', '65000.00', 'Rent and administration', 'Industrial mill premises lease rent and municipal fees', hdfc)
    add_txn(32, 'Expense', '18000.00', 'Bank charges and taxes', 'Trade finance documentation and monthly GST electronic cash ledger settlement', hdfc)
    add_txn(31, 'Expense', '240000.00', 'Supplier payments', 'Supplier payment: Cleared yarn raw materials invoice #VSM-4512 to Vardhman Spinning', sbi)

    # --- Current Month (Days 1 to 28) ---
    add_txn(27, 'Income', '720000.00', 'Sales revenue', 'Sale of textile materials: 4,500 kg carded cotton yarn to Arvind Texfab Mills (Inv #TX-2675)', hdfc)
    add_txn(25, 'Expense', '380000.00', 'Raw cotton purchases', 'Purchase of 3,200 kg of raw cotton Shankar-6 from Gujarat Cotton Traders Co.', sbi)
    add_txn(23, 'Expense', '140000.00', 'Cotton yarn and polyester fibre purchases', 'Purchase of 800 kg of cotton yarn and 500 kg polyester fibre lot', sbi)
    add_txn(21, 'Expense', '68000.00', 'Viscose fibre purchases', 'Purchase of 650 kg viscose fibre from Grasim Industries', sbi)
    add_txn(19, 'Income', '580000.00', 'Customer receipts', 'Customer receipt: Electronic RTGS payment received against customer invoice #TX-2675 from Arvind Texfab', hdfc)
    add_txn(18, 'Expense', '32500.00', 'Transportation and freight', 'Freight charges for raw-material shipment from Rajkot ginning mills', hdfc)
    add_txn(16, 'Expense', '48000.00', 'Textile dyes, pigments, and processing chemicals', 'Azo-free reactive dye pigments and sodium hydrosulfite from Surat Dyechem', hdfc)
    add_txn(14, 'Expense', '162000.00', 'Factory electricity and utilities', 'Payment for factory electricity - Substation 3 HT industrial feeder', hdfc)
    add_txn(12, 'Expense', '315000.00', 'Employee wages', 'Monthly floor operator wages & spinning technicians payroll', hdfc)
    add_txn(10, 'Expense', '45000.00', 'Machine maintenance', 'Machine maintenance & spindle overhaul - Ring Frame Loom #4', hdfc)
    add_txn(8, 'Expense', '23500.00', 'Packaging materials', 'Corrugated cardboard boxes and poly woven textile packing bags', cash)
    add_txn(6, 'Expense', '65000.00', 'Rent and administration', 'Mill shed lease rent & corporate administrative office charges', hdfc)
    add_txn(5, 'Expense', '19200.00', 'Bank charges and taxes', 'Bank charges, trade finance credit card fee, and state GST settlement', hdfc)
    add_txn(4, 'Expense', '260000.00', 'Supplier payments', 'Supplier payment: Outstanding payment due to fictional fibre supplier Gujarat Cotton Traders (Inv #GCT-9230)', sbi)
    add_txn(3, 'Income', '380000.00', 'Customer receipts', 'Partial payment received against customer invoice #TX-2660 from Shahi Garments', hdfc)
    add_txn(2, 'Expense', '18500.00', 'Transportation and freight', 'Local logistics freight for yarn consignment dispatch to Tirupur', cash)
    add_txn(1, 'Expense', '15000.00', 'Machine maintenance', 'Emergency replacement of pneumatic valve on blowroom carder', cash)

    # 4. Insert Transactions Safely (Idempotent: Avoid duplicates)
    inserted_count = 0
    for dt, ttype, amt, cat_obj, desc, acct in txns_to_create:
        exists = Transaction.query.filter_by(
            user_id=user.user_id,
            date=dt,
            amount=amt,
            description=desc
        ).first()

        if not exists:
            txn = Transaction(
                user_id=user.user_id,
                account_id=acct.account_id,
                category_id=cat_obj.category_id,
                date=dt,
                amount=amt,
                description=desc,
                txn_type=ttype
            )
            db.session.add(txn)
            inserted_count += 1

    # 5. Budgets for Current and Recent Months
    cur_month_str = today.strftime('%Y-%m')
    prev_month_date = today.replace(day=1) - timedelta(days=1)
    prev_month_str = prev_month_date.strftime('%Y-%m')

    budget_configs = [
        # Current month
        (cat_map['Raw cotton purchases'], cur_month_str, Decimal('650000.00')),
        (cat_map['Cotton yarn and polyester fibre purchases'], cur_month_str, Decimal('480000.00')),
        (cat_map['Factory electricity and utilities'], cur_month_str, Decimal('175000.00')),
        (cat_map['Employee wages'], cur_month_str, Decimal('340000.00')),
        (cat_map['Machine maintenance'], cur_month_str, Decimal('85000.00')),
        (cat_map['Transportation and freight'], cur_month_str, Decimal('95000.00')),
        (cat_map['Textile dyes, pigments, and processing chemicals'], cur_month_str, Decimal('120000.00')),
        (cat_map['Packaging materials'], cur_month_str, Decimal('55000.00')),
        (cat_map['Food'], cur_month_str, Decimal('25000.00')),
        (cat_map['Rent'], cur_month_str, Decimal('70000.00')),
        # Prior month
        (cat_map['Raw cotton purchases'], prev_month_str, Decimal('600000.00')),
        (cat_map['Factory electricity and utilities'], prev_month_str, Decimal('165000.00')),
        (cat_map['Employee wages'], prev_month_str, Decimal('330000.00')),
        (cat_map['Machine maintenance'], prev_month_str, Decimal('80000.00')),
    ]

    for cat_obj, m_str, limit_val in budget_configs:
        b_exists = Budget.query.filter_by(user_id=user.user_id, category_id=cat_obj.category_id, month=m_str).first()
        if not b_exists:
            new_b = Budget(
                user_id=user.user_id,
                category_id=cat_obj.category_id,
                month=m_str,
                limit_amount=limit_val
            )
            db.session.add(new_b)

    # 6. Textile Strategic Capital Goals
    goals_config = [
        ("High-Speed Ring Frame Loom Upgrade", Decimal('2500000.00'), Decimal('1650000.00'), date(2026, 12, 31)),
        ("Rooftop Solar PV Installation (150 kW)", Decimal('1800000.00'), Decimal('920000.00'), date(2027, 3, 31)),
        ("Effluent Water Treatment Plant (ETP) Expansion", Decimal('1200000.00'), Decimal('875000.00'), date(2027, 6, 30)),
        ("Car Savings", Decimal('1000000.00'), Decimal('450000.00'), date(2027, 12, 31)),
        ("Emergency Working Capital Reserve", Decimal('1500000.00'), Decimal('1200000.00'), date(2027, 9, 30))
    ]

    for g_name, target_amt, saved_amt, due in goals_config:
        g_exists = Goal.query.filter_by(user_id=user.user_id, name=g_name).first()
        if not g_exists:
            g = Goal(
                user_id=user.user_id,
                name=g_name,
                target_amount=target_amt,
                saved_amount=saved_amt,
                due_date=due
            )
            db.session.add(g)

    # 7. Textile & Manufacturing Investment Holdings
    investments_config = [
        ("KPR Mill Ltd (Textile Manufacturing)", 150, Decimal('840.00'), date(2026, 5, 14)),
        ("Vardhman Textiles Ltd", 300, Decimal('465.00'), date(2026, 6, 20)),
        ("Page Industries Ltd", 6, Decimal('37200.00'), date(2026, 7, 10)),
        ("Nifty India Manufacturing ETF", 1200, Decimal('128.50'), date(2026, 8, 18)),
        ("HDFC Liquid Fund - Direct Growth", 400, Decimal('1150.00'), date(2026, 9, 5)),
        ("AAPL", 10, Decimal('18500.00'), date(2026, 9, 15)),
        ("NVDA", 5, Decimal('11200.00'), date(2026, 10, 5))
    ]

    for inst, qty, price, b_date in investments_config:
        inv_exists = Investment.query.filter_by(user_id=user.user_id, instrument=inst).first()
        if not inv_exists:
            inv = Investment(
                user_id=user.user_id,
                instrument=inst,
                quantity=qty,
                buy_price=price,
                buy_date=b_date
            )
            db.session.add(inv)

    db.session.commit()
    print(f"Textile sample dataset verified. Seeded {inserted_count} new transactions for '{target_username}'.")
    return inserted_count
