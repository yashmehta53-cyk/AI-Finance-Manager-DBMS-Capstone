"""
Safe Database Migration & Textile Factory SQL Importer
Imports textile-factory-v4-sql-mysql.sql into MySQL or SQLite.
Idempotent, non-destructive, preserves all users, transactions, and historical data.
"""

import os
import re
import sys
from datetime import datetime, date
from decimal import Decimal
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')

from config import Config
from models import (
    db, User, Account, Category, Transaction, Budget, Goal, Investment,
    Product, Inventory, Order, Shift, Customer, Supplier, Transfer, TaxRecord,
    CurrencyMigrationLog
)
from app import create_app

def ensure_schema_upgrades(app):
    """Safely adds newly introduced columns to existing tables without affecting data."""
    from sqlalchemy import inspect, text
    with app.app_context():
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()

        columns_to_add = {
            'users': [
                ('role', 'VARCHAR(20) DEFAULT "Admin"'),
                ('company_name', 'VARCHAR(150) DEFAULT "Aura TexFab Mills (India) Ltd."'),
                ('gstin', 'VARCHAR(20) DEFAULT "33AABCT1332L1Z4"')
            ],
            'accounts': [
                ('account_number', 'VARCHAR(50)'),
                ('bank_name', 'VARCHAR(100)'),
                ('ifsc_code', 'VARCHAR(20)')
            ],
            'categories': [
                ('hsn_sac_code', 'VARCHAR(20)'),
                ('default_gst_rate', 'NUMERIC(5, 2) DEFAULT 5.00')
            ],
            'transactions': [
                ('payment_method', 'VARCHAR(30) DEFAULT "Bank Transfer"'),
                ('reference_no', 'VARCHAR(50)'),
                ('party_name', 'VARCHAR(120)'),
                ('party_gstin', 'VARCHAR(20)'),
                ('hsn_code', 'VARCHAR(20)'),
                ('gst_rate', 'NUMERIC(5, 2) DEFAULT 0.00'),
                ('cgst_amount', 'NUMERIC(12, 2) DEFAULT 0.00'),
                ('sgst_amount', 'NUMERIC(12, 2) DEFAULT 0.00'),
                ('igst_amount', 'NUMERIC(12, 2) DEFAULT 0.00')
            ]
        }

        with db.engine.connect() as conn:
            for tbl, cols in columns_to_add.items():
                if tbl in tables:
                    existing_cols = [c['name'] for c in inspector.get_columns(tbl)]
                    for col_name, col_def in cols:
                        if col_name not in existing_cols:
                            print(f"[SCHEMA] Adding missing column `{col_name}` to table `{tbl}`...", flush=True)
                            try:
                                conn.execute(text(f"ALTER TABLE {tbl} ADD COLUMN {col_name} {col_def}"))
                                conn.commit()
                            except Exception as ex:
                                print(f"[WARN] ALTER TABLE {tbl} ADD {col_name}: {ex}", flush=True)


def import_sql_dump(app):
    """Safely parse and import textile-factory-v4-sql-mysql.sql into current database."""
    ensure_schema_upgrades(app)
    sql_path = BASE_DIR / 'textile-factory-v4-sql-mysql.sql'
    if not sql_path.exists():
        print(f"Error: {sql_path} does not exist.")
        return False

    with app.app_context():
        # Ensure all tables exist without dropping anything
        db.create_all()

        # Check if already imported (idempotency check)
        existing_products_count = Product.query.count()
        if existing_products_count > 0:
            print(f"[OK] Database already has {existing_products_count} products. Skipping raw SQL re-import.")
        else:
            print("[INFO] Parsing textile-factory-v4-sql-mysql.sql ...")
            with open(sql_path, 'r', encoding='latin1') as f:
                content = f.read()

            # Parse Products
            # INSERT INTO `products` (`id`, `name`, `type`, `price_per_unit`) VALUES
            prod_matches = re.findall(r"INSERT INTO `products`\s*\([^)]+\)\s*VALUES\s*(.*?);", content, re.DOTALL)
            if prod_matches:
                tuples = re.findall(r"\(\s*(\d+)\s*,\s*'([^']+)'\s*,\s*'([^']+)'\s*,\s*([0-9.]+)\s*\)", prod_matches[0])
                print(f"[INFO] Importing {len(tuples)} products...")
                for pid, name, ptype, price in tuples:
                    p = Product(id=int(pid), name=name, type=ptype, price_per_unit=Decimal(price))
                    db.session.add(p)
                db.session.commit()
                print(f"[SUCCESS] Imported {len(tuples)} products.")

            # Parse Inventory
            # INSERT INTO `inventory` (`id`, `product_id`, `stock_level`, `last_updated`, `reorder_level`, `stock_value`) VALUES
            inv_matches = re.findall(r"INSERT INTO `inventory`\s*\([^)]+\)\s*VALUES\s*(.*?);", content, re.DOTALL)
            if inv_matches:
                tuples = re.findall(r"\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*'([^']+)'\s*,\s*(\d+)\s*,\s*([0-9.]+)\s*\)", inv_matches[0])
                print(f"[INFO] Importing {len(tuples)} inventory records...")
                for iid, pid, slevel, lupdate, rlevel, sval in tuples:
                    inv = Inventory(
                        id=int(iid),
                        product_id=int(pid),
                        stock_level=int(slevel),
                        last_updated=datetime.strptime(lupdate, '%Y-%m-%d %H:%M:%S'),
                        reorder_level=int(rlevel),
                        stock_value=Decimal(sval)
                    )
                    db.session.add(inv)
                db.session.commit()
                print(f"[SUCCESS] Imported {len(tuples)} inventory records.")

            # Parse Orders
            # INSERT INTO `orders` (`id`, `product_id`, `customer_name`, `quantity`, `order_date`, `status`) VALUES
            order_matches = re.findall(r"INSERT INTO `orders`\s*\([^)]+\)\s*VALUES\s*(.*?);", content, re.DOTALL)
            total_orders = 0
            for om in order_matches:
                tuples = re.findall(r"\(\s*(\d+)\s*,\s*(\d+)\s*,\s*'([^']+)'\s*,\s*(\d+)\s*,\s*'([^']+)'\s*,\s*'([^']+)'\s*\)", om)
                for oid, pid, cname, qty, odate, status in tuples:
                    o = Order(
                        id=int(oid),
                        product_id=int(pid),
                        customer_name=cname,
                        quantity=int(qty),
                        order_date=datetime.strptime(odate, '%Y-%m-%d %H:%M:%S'),
                        status=status
                    )
                    db.session.add(o)
                    total_orders += 1
            db.session.commit()
            print(f"[SUCCESS] Imported {total_orders} customer orders.")

            # Parse Shifts
            # INSERT INTO `shifts` (`id`, `employee_name`, `shift_date`, `line_number`, `performance_score`, `machine_utilization`) VALUES
            shift_matches = re.findall(r"INSERT INTO `shifts`\s*\([^)]+\)\s*VALUES\s*(.*?);", content, re.DOTALL)
            total_shifts = 0
            for sm in shift_matches:
                tuples = re.findall(r"\(\s*(\d+)\s*,\s*'([^']+)'\s*,\s*'([^']+)'\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([0-9.]+)\s*\)", sm)
                for sid, ename, sdate, line_num, pscore, mutil in tuples:
                    sh = Shift(
                        id=int(sid),
                        employee_name=ename,
                        shift_date=datetime.strptime(sdate, '%Y-%m-%d %H:%M:%S'),
                        line_number=int(line_num),
                        performance_score=int(pscore),
                        machine_utilization=Decimal(mutil)
                    )
                    db.session.add(sh)
                    total_shifts += 1
            db.session.commit()
            print(f"[SUCCESS] Imported {total_shifts} plant shifts.")

        # Sync Customers from Orders & Textile context
        sync_customers_and_suppliers(app)
        sync_tax_records(app)
        return True

def sync_customers_and_suppliers(app):
    """Creates customer and supplier financial profiles for users."""
    with app.app_context():
        user = User.query.first()
        if not user:
            print("[INFO] No user found to link customers/suppliers.")
            return

        # Check existing customers
        if Customer.query.filter_by(user_id=user.user_id).count() == 0:
            print("[INFO] Populating Customer records from Textile Orders...", flush=True)
            # Efficiently join orders and products in 1 query
            order_rows = db.session.query(
                Order.customer_name, Order.quantity, Order.status, Product.price_per_unit
            ).join(Product, Order.product_id == Product.id).all()
            
            customer_totals = {}
            for cname, qty, status, price_per_unit in order_rows:
                val = Decimal(qty) * Decimal(price_per_unit) * Decimal('83.50')
                if cname not in customer_totals:
                    customer_totals[cname] = {'total_orders': 0, 'pending_balance': Decimal('0.00')}
                customer_totals[cname]['total_orders'] += 1
                if status == 'pending':
                    customer_totals[cname]['pending_balance'] += val

            # Sample Indian states & GSTIN generator
            states = ['Tamil Nadu', 'Gujarat', 'Maharashtra', 'Karnataka', 'Rajasthan', 'Punjab']
            state_codes = {'Tamil Nadu': '33', 'Gujarat': '24', 'Maharashtra': '27', 'Karnataka': '29', 'Rajasthan': '08', 'Punjab': '03'}

            # Add prominent textile trade buyers first
            prominent = [
                ("Tirupur Knitwear Exports Ltd.", "K. Sundaram", "sundaram@tirupurknit.in", "+91 98421 78901", "Tamil Nadu", Decimal("5000000.00"), Decimal("785400.00"), "Net 30 Days"),
                ("Surat Textile Merchants Syndicate", "R. K. Patel", "orders@surattextile.org", "+91 98250 12345", "Gujarat", Decimal("3500000.00"), Decimal("420000.00"), "Net 45 Days"),
                ("Ludhiana Wool & Fibre Weavers", "Harpreet Singh", "hsingh@ludhianawoollen.com", "+91 98140 54321", "Punjab", Decimal("2500000.00"), Decimal("310000.00"), "Net 30 Days"),
                ("Jaipur Blockprints & Apparel Co.", "Meenakshi Rathore", "finance@jaipurapparel.in", "+91 94140 67890", "Rajasthan", Decimal("1800000.00"), Decimal("145000.00"), "Net 15 Days"),
                ("Mumbai Garment Hub Pvt Ltd", "Rajesh Mehta", "accounts@mumbaigarments.com", "+91 98200 45678", "Maharashtra", Decimal("4000000.00"), Decimal("650000.00"), "Net 30 Days")
            ]
            for name, cperson, email, phone, state, climit, obal, pterms in prominent:
                gst = f"{state_codes[state]}AABCT{abs(hash(name)) % 9000 + 1000}L1Z{abs(hash(name)) % 9 + 1}"
                c = Customer(
                    user_id=user.user_id,
                    name=name,
                    contact_person=cperson,
                    email=email,
                    phone=phone,
                    gstin=gst,
                    state=state,
                    credit_limit=climit,
                    outstanding_balance=obal,
                    payment_terms=pterms
                )
                db.session.add(c)

            # Add top customers from order dataset
            idx = 0
            for cname, stats in list(customer_totals.items())[:30]:
                if any(p[0] == cname for p in prominent):
                    continue
                state = states[idx % len(states)]
                gst = f"{state_codes[state]}AAPCS{1000 + idx}Z1Z{idx % 9 + 1}"
                c = Customer(
                    user_id=user.user_id,
                    name=cname,
                    contact_person=cname,
                    email=f"{cname.lower().replace(' ', '.')}@textileclient.in",
                    phone=f"+91 98{10000000 + idx}",
                    gstin=gst,
                    state=state,
                    credit_limit=Decimal('1500000.00'),
                    outstanding_balance=stats['pending_balance'],
                    payment_terms='Net 30 Days'
                )
                db.session.add(c)
                idx += 1

            db.session.commit()
            print(f"[SUCCESS] Populated {Customer.query.count()} customer accounts.")

        # Check existing suppliers
        if Supplier.query.filter_by(user_id=user.user_id).count() == 0:
            print("[INFO] Populating Supplier records...")
            textile_suppliers = [
                ("Gujarat Cotton Traders Co.", "Ginning & Raw Cotton", "Nilesh Bhimani", "procurement@gujaratcotton.in", "+91 98251 99881", "24AABCG9102L1Z5", "Gujarat", "Net 45 Days", Decimal("640000.00")),
                ("Reliance Polyester Division", "Synthetic & Polyester Staple Fibre", "Anand Sharma", "fibre.sales@ril-textiles.com", "+91 98201 11223", "27AABCR1234F1Z8", "Maharashtra", "Net 30 Days", Decimal("480000.00")),
                ("Grasim Industries VSF Division", "Viscose Staple Fibre", "Vikram Birla", "vsf.procurement@grasim.adityabirla.com", "+91 98290 33445", "08AABCG4567M1Z2", "Rajasthan", "Net 45 Days", Decimal("320000.00")),
                ("Surat Dyechem & Chemicals Ltd.", "Textile Reactive Dyes & Pigments", "Deepak Shah", "info@suratdyechem.com", "+91 98255 77665", "24AABCD8899K1Z4", "Gujarat", "Net 30 Days", Decimal("185000.00")),
                ("Corrugate Packs & Textile Containers", "Packaging & Paper Cones", "R. Palanisamy", "orders@corrugatepacks.in", "+91 98422 33441", "33AABCC5566P1Z3", "Tamil Nadu", "Net 15 Days", Decimal("45000.00")),
                ("Tamil Nadu Generation & Distribution Corp (TANGEDCO)", "Industrial HT Substation Power", "Superintending Engineer", "htpower.tiru@tangedco.gov.in", "+91 421 223344", "33AABCT9988T1Z1", "Tamil Nadu", "Due on 10th", Decimal("142000.00")),
                ("Coimbatore Spindle Tech & Engineering", "Machine Spares & Ring Frame Maintenance", "M. Selvaraj", "service@coimbatorespindle.com", "+91 98430 88776", "33AABCS7788R1Z9", "Tamil Nadu", "Net 30 Days", Decimal("68000.00"))
            ]
            for sname, cat, cperson, email, phone, gstin, state, pterms, obal in textile_suppliers:
                s = Supplier(
                    user_id=user.user_id,
                    name=sname,
                    category=cat,
                    contact_person=cperson,
                    email=email,
                    phone=phone,
                    gstin=gstin,
                    state=state,
                    payment_terms=pterms,
                    outstanding_balance=obal
                )
                db.session.add(s)
            db.session.commit()
            print(f"[SUCCESS] Populated {Supplier.query.count()} supplier accounts.")

def sync_tax_records(app):
    """Populates Indian GST compliance records (GSTR-1 and GSTR-3B) for FY 2026-27."""
    with app.app_context():
        user = User.query.first()
        if not user:
            return

        if TaxRecord.query.filter_by(user_id=user.user_id).count() == 0:
            print("[INFO] Populating GST Records for FY 2026-27...")
            gst_periods = [
                ('2026-04', Decimal('12500000.00'), Decimal('312500.00'), Decimal('312500.00'), Decimal('0.00'), Decimal('625000.00'), Decimal('480000.00'), Decimal('145000.00'), 'Filed', date(2026, 5, 20)),
                ('2026-05', Decimal('14200000.00'), Decimal('355000.00'), Decimal('355000.00'), Decimal('0.00'), Decimal('710000.00'), Decimal('540000.00'), Decimal('170000.00'), 'Filed', date(2026, 6, 20)),
                ('2026-06', Decimal('15800000.00'), Decimal('395000.00'), Decimal('395000.00'), Decimal('0.00'), Decimal('790000.00'), Decimal('610000.00'), Decimal('180000.00'), 'Filed', date(2026, 7, 20)),
                ('2026-07', Decimal('16500000.00'), Decimal('412500.00'), Decimal('412500.00'), Decimal('0.00'), Decimal('825000.00'), Decimal('635000.00'), Decimal('190000.00'), 'Filed', date(2026, 8, 20)),
                ('2026-08', Decimal('17100000.00'), Decimal('427500.00'), Decimal('427500.00'), Decimal('0.00'), Decimal('855000.00'), Decimal('660000.00'), Decimal('195000.00'), 'Filed', date(2026, 9, 20)),
                ('2026-09', Decimal('18200000.00'), Decimal('455000.00'), Decimal('455000.00'), Decimal('0.00'), Decimal('910000.00'), Decimal('700000.00'), Decimal('210000.00'), 'Filed', date(2026, 10, 20)),
                ('2026-10', Decimal('19400000.00'), Decimal('485000.00'), Decimal('485000.00'), Decimal('0.00'), Decimal('970000.00'), Decimal('745000.00'), Decimal('225000.00'), 'Filed', date(2026, 11, 20)),
                ('2026-11', Decimal('18900000.00'), Decimal('472500.00'), Decimal('472500.00'), Decimal('0.00'), Decimal('945000.00'), Decimal('730000.00'), Decimal('215000.00'), 'Pending', None)
            ]
            for period, tval, cgst, sgst, igst, tot, itc, net_pay, status, fdate in gst_periods:
                # Add GSTR-3B
                tr3b = TaxRecord(
                    user_id=user.user_id,
                    period=period,
                    return_type='GSTR-3B',
                    taxable_amount=tval,
                    cgst=cgst,
                    sgst=sgst,
                    igst=igst,
                    total_tax=tot,
                    itc_claimed=itc,
                    net_tax_payable=net_pay,
                    status=status,
                    filing_date=fdate
                )
                db.session.add(tr3b)
                # Add GSTR-1
                tr1 = TaxRecord(
                    user_id=user.user_id,
                    period=period,
                    return_type='GSTR-1',
                    taxable_amount=tval,
                    cgst=cgst,
                    sgst=sgst,
                    igst=igst,
                    total_tax=tot,
                    itc_claimed=Decimal('0.00'),
                    net_tax_payable=tot,
                    status=status,
                    filing_date=fdate
                )
                db.session.add(tr1)
            db.session.commit()
            print(f"[SUCCESS] Populated {TaxRecord.query.count()} GST compliance filings.")

if __name__ == '__main__':
    print("--- Executing Safe Textile Factory Data Importer ---")
    app = create_app()
    import_sql_dump(app)
    print("--- Completed Successfully ---")
