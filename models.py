from datetime import datetime, timezone, date
from decimal import Decimal
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

def utc_now():
    return datetime.now(timezone.utc)

# -------------------------------------------------------------
# Core User & Authentication Model
# -------------------------------------------------------------
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    email = db.Column(db.String(100), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='Admin', nullable=False)
    company_name = db.Column(db.String(150), default='Aura TexFab Mills (India) Ltd.', nullable=True)
    gstin = db.Column(db.String(20), default='33AABCT1332L1Z4', nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now, server_default=db.func.now())
    
    # Relationships
    accounts = db.relationship('Account', backref='owner', cascade='all, delete-orphan', lazy='dynamic')
    transactions = db.relationship('Transaction', backref='owner', cascade='all, delete-orphan', lazy='dynamic')
    budgets = db.relationship('Budget', backref='owner', cascade='all, delete-orphan', lazy='dynamic')
    goals = db.relationship('Goal', backref='owner', cascade='all, delete-orphan', lazy='dynamic')
    investments = db.relationship('Investment', backref='owner', cascade='all, delete-orphan', lazy='dynamic')
    categories = db.relationship('Category', backref='owner', cascade='all, delete-orphan', lazy='dynamic')
    customers = db.relationship('Customer', backref='owner', cascade='all, delete-orphan', lazy='dynamic')
    suppliers = db.relationship('Supplier', backref='owner', cascade='all, delete-orphan', lazy='dynamic')
    transfers = db.relationship('Transfer', backref='owner', cascade='all, delete-orphan', lazy='dynamic')
    tax_records = db.relationship('TaxRecord', backref='owner', cascade='all, delete-orphan', lazy='dynamic')

    def get_id(self):
        return str(self.user_id)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username!r}>'


# -------------------------------------------------------------
# Financial Account Model (Bank, Cash, CC, Reserves)
# -------------------------------------------------------------
class Account(db.Model):
    __tablename__ = 'accounts'
    
    account_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.Enum('Checking', 'Savings', 'Credit', 'Cash', name='account_types'), nullable=False)
    balance = db.Column(db.Numeric(14, 2), default=Decimal('0.00'), nullable=False)
    account_number = db.Column(db.String(50), nullable=True)
    bank_name = db.Column(db.String(100), nullable=True)
    ifsc_code = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now, server_default=db.func.now())
    
    transactions = db.relationship('Transaction', backref='account', cascade='all, delete-orphan', lazy='dynamic')
    transfers_from = db.relationship('Transfer', foreign_keys='Transfer.from_account_id', backref='from_account', lazy='dynamic')
    transfers_to = db.relationship('Transfer', foreign_keys='Transfer.to_account_id', backref='to_account', lazy='dynamic')

    def __repr__(self):
        return f'<Account {self.name!r} ({self.type}) Balance: {self.balance}>'


# -------------------------------------------------------------
# Transaction Category Model
# -------------------------------------------------------------
class Category(db.Model):
    __tablename__ = 'categories'
    __table_args__ = (
        db.UniqueConstraint('user_id', 'name', name='uq_user_category_name'),
    )
    
    category_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='CASCADE'), nullable=True, index=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.Enum('Expense', 'Income', name='category_types'), nullable=False)
    hsn_sac_code = db.Column(db.String(20), nullable=True)
    default_gst_rate = db.Column(db.Numeric(5, 2), default=Decimal('5.00'), nullable=True)
    
    transactions = db.relationship('Transaction', backref='category', lazy='dynamic')
    budgets = db.relationship('Budget', backref='category', cascade='all, delete-orphan', lazy='dynamic')

    def __repr__(self):
        return f'<Category {self.name!r} ({self.type})>'


# -------------------------------------------------------------
# Transaction Model (Full Indian Tax, UPI/NEFT, GST Support)
# -------------------------------------------------------------
class Transaction(db.Model):
    __tablename__ = 'transactions'
    
    txn_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False, index=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.account_id', ondelete='CASCADE'), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.category_id', ondelete='CASCADE'), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, index=True)
    amount = db.Column(db.Numeric(14, 2), nullable=False)
    description = db.Column(db.Text, nullable=True)
    txn_type = db.Column(db.Enum('Expense', 'Income', name='txn_types'), nullable=False)
    
    # Indian Financial Fields
    payment_method = db.Column(db.String(30), default='Bank Transfer', nullable=True) # UPI, NEFT/RTGS, Bank Transfer, Cash, Cheque, Credit Note, Debit Note
    reference_no = db.Column(db.String(50), nullable=True) # UTR, UPI Ref, Cheque No, Invoice Ref
    party_name = db.Column(db.String(120), nullable=True) # Customer or Supplier entity
    party_gstin = db.Column(db.String(20), nullable=True) # GSTIN of transacting party
    hsn_code = db.Column(db.String(20), nullable=True) # HSN / SAC Code
    gst_rate = db.Column(db.Numeric(5, 2), default=Decimal('0.00'), nullable=True) # 0%, 5%, 12%, 18%, 28%
    cgst_amount = db.Column(db.Numeric(12, 2), default=Decimal('0.00'), nullable=True)
    sgst_amount = db.Column(db.Numeric(12, 2), default=Decimal('0.00'), nullable=True)
    igst_amount = db.Column(db.Numeric(12, 2), default=Decimal('0.00'), nullable=True)
    
    created_at = db.Column(db.DateTime, default=utc_now, server_default=db.func.now())

    def __repr__(self):
        return f'<Transaction {self.txn_id}: {self.txn_type} ₹{self.amount} on {self.date}>'


# -------------------------------------------------------------
# Transfer Model (Between Bank, Cash, Credit Accounts)
# -------------------------------------------------------------
class Transfer(db.Model):
    __tablename__ = 'transfers'
    
    transfer_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False, index=True)
    from_account_id = db.Column(db.Integer, db.ForeignKey('accounts.account_id', ondelete='CASCADE'), nullable=False)
    to_account_id = db.Column(db.Integer, db.ForeignKey('accounts.account_id', ondelete='CASCADE'), nullable=False)
    amount = db.Column(db.Numeric(14, 2), nullable=False)
    transfer_date = db.Column(db.Date, default=date.today, nullable=False)
    reference_no = db.Column(db.String(50), nullable=True)
    notes = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now, server_default=db.func.now())

    def __repr__(self):
        return f'<Transfer {self.transfer_id}: ₹{self.amount} from {self.from_account_id} to {self.to_account_id}>'


# -------------------------------------------------------------
# Budget Model
# -------------------------------------------------------------
class Budget(db.Model):
    __tablename__ = 'budgets'
    __table_args__ = (
        db.UniqueConstraint('user_id', 'category_id', 'month', name='uq_user_category_month'),
    )
    
    budget_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.category_id', ondelete='CASCADE'), nullable=False)
    month = db.Column(db.String(7), nullable=False)  # Stored as 'YYYY-MM'
    limit_amount = db.Column(db.Numeric(14, 2), nullable=False)

    def __repr__(self):
        return f'<Budget User:{self.user_id} Cat:{self.category_id} Month:{self.month} Limit:{self.limit_amount}>'


# -------------------------------------------------------------
# Goal Model (Reserve Funds, Capital Outlay, Modernization)
# -------------------------------------------------------------
class Goal(db.Model):
    __tablename__ = 'goals'
    
    goal_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    target_amount = db.Column(db.Numeric(14, 2), nullable=False)
    saved_amount = db.Column(db.Numeric(14, 2), default=Decimal('0.00'), nullable=False)
    due_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now, server_default=db.func.now())

    @property
    def percent_complete(self):
        if not self.target_amount or self.target_amount <= 0:
            return 0.0
        return min(100.0, round(float(self.saved_amount / self.target_amount) * 100, 1))

    def __repr__(self):
        return f'<Goal {self.name!r} Saved: {self.saved_amount}/{self.target_amount}>'


# -------------------------------------------------------------
# Investment Model (Treasury, Liquid Mutual Funds, Bonds)
# -------------------------------------------------------------
class Investment(db.Model):
    __tablename__ = 'investments'
    
    inv_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False, index=True)
    instrument = db.Column(db.String(100), nullable=False)  # Stock, T-Bill, Mutual Fund
    quantity = db.Column(db.Integer, nullable=False)
    buy_price = db.Column(db.Numeric(14, 2), nullable=False)
    buy_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now, server_default=db.func.now())

    @property
    def total_cost(self):
        return Decimal(self.quantity) * self.buy_price

    def __repr__(self):
        return f'<Investment {self.instrument!r} Qty: {self.quantity} @ {self.buy_price}>'


# -------------------------------------------------------------
# Customers & Receivables Model
# -------------------------------------------------------------
class Customer(db.Model):
    __tablename__ = 'customers'
    
    customer_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False, index=True)
    contact_person = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    gstin = db.Column(db.String(20), nullable=True)
    state = db.Column(db.String(50), default='Tamil Nadu', nullable=True)
    credit_limit = db.Column(db.Numeric(14, 2), default=Decimal('1000000.00'), nullable=False)
    outstanding_balance = db.Column(db.Numeric(14, 2), default=Decimal('0.00'), nullable=False)
    payment_terms = db.Column(db.String(50), default='Net 30 Days', nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now, server_default=db.func.now())

    def __repr__(self):
        return f'<Customer {self.name!r} O/S: ₹{self.outstanding_balance}>'


# -------------------------------------------------------------
# Suppliers & Payables Model
# -------------------------------------------------------------
class Supplier(db.Model):
    __tablename__ = 'suppliers'
    
    supplier_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False, index=True)
    category = db.Column(db.String(100), default='Raw Material Supplier', nullable=True)
    contact_person = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    gstin = db.Column(db.String(20), nullable=True)
    state = db.Column(db.String(50), default='Gujarat', nullable=True)
    payment_terms = db.Column(db.String(50), default='Net 45 Days', nullable=True)
    outstanding_balance = db.Column(db.Numeric(14, 2), default=Decimal('0.00'), nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now, server_default=db.func.now())

    def __repr__(self):
        return f'<Supplier {self.name!r} O/S: ₹{self.outstanding_balance}>'


# -------------------------------------------------------------
# Tax & GST Records Model
# -------------------------------------------------------------
class TaxRecord(db.Model):
    __tablename__ = 'tax_records'
    
    record_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False, index=True)
    period = db.Column(db.String(7), nullable=False) # 'YYYY-MM'
    return_type = db.Column(db.String(20), default='GSTR-3B', nullable=False) # GSTR-1, GSTR-3B
    taxable_amount = db.Column(db.Numeric(14, 2), default=Decimal('0.00'), nullable=False)
    cgst = db.Column(db.Numeric(14, 2), default=Decimal('0.00'), nullable=False)
    sgst = db.Column(db.Numeric(14, 2), default=Decimal('0.00'), nullable=False)
    igst = db.Column(db.Numeric(14, 2), default=Decimal('0.00'), nullable=False)
    total_tax = db.Column(db.Numeric(14, 2), default=Decimal('0.00'), nullable=False)
    itc_claimed = db.Column(db.Numeric(14, 2), default=Decimal('0.00'), nullable=False) # Input Tax Credit
    net_tax_payable = db.Column(db.Numeric(14, 2), default=Decimal('0.00'), nullable=False)
    status = db.Column(db.String(20), default='Filed', nullable=False) # Draft, Pending, Filed
    filing_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now, server_default=db.func.now())

    def __repr__(self):
        return f'<TaxRecord {self.return_type} {self.period} Tax: ₹{self.total_tax}>'


# -------------------------------------------------------------
# Textile Company Imported Database Models
# Directly matches schema from textile-factory-v4-sql-mysql.sql
# -------------------------------------------------------------
class Product(db.Model):
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(80), nullable=False)
    type = db.Column(db.String(20), nullable=False) # cotton, polyester, specialty
    price_per_unit = db.Column(db.Numeric(14, 2), nullable=False) # Base catalog price
    
    # Financial helpers
    orders = db.relationship('Order', backref='product', lazy='dynamic')
    inventory_items = db.relationship('Inventory', backref='product', lazy='dynamic')

    @property
    def price_inr(self):
        """Standard Indian Rupee commercial price (at 83.50 exchange conversion)"""
        return Decimal(self.price_per_unit) * Decimal('83.50')

    def __repr__(self):
        return f'<Product {self.id}: {self.name} ({self.type}) @ {self.price_per_unit}>'


class Inventory(db.Model):
    __tablename__ = 'inventory'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False, index=True)
    stock_level = db.Column(db.Integer, nullable=False)
    last_updated = db.Column(db.DateTime, nullable=False)
    reorder_level = db.Column(db.Integer, nullable=False)
    stock_value = db.Column(db.Numeric(14, 2), nullable=False) # Asset value on Balance Sheet

    @property
    def stock_value_inr(self):
        """Inventory asset valuation in INR"""
        return Decimal(self.stock_value) * Decimal('83.50')

    def __repr__(self):
        return f'<Inventory {self.id}: Product {self.product_id} Stock: {self.stock_level} Value: {self.stock_value}>'


class Order(db.Model):
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False, index=True)
    customer_name = db.Column(db.String(120), nullable=False, index=True)
    quantity = db.Column(db.Integer, nullable=False)
    order_date = db.Column(db.DateTime, nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, index=True) # fulfilled, pending, cancelled

    @property
    def order_value_usd(self):
        if self.product:
            return Decimal(self.quantity) * Decimal(self.product.price_per_unit)
        return Decimal('0.00')

    @property
    def order_value_inr(self):
        """Actual order commercial revenue in INR"""
        return self.order_value_usd * Decimal('83.50')

    def __repr__(self):
        return f'<Order {self.id}: {self.customer_name} Qty: {self.quantity} Status: {self.status}>'


class Shift(db.Model):
    __tablename__ = 'shifts'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    employee_name = db.Column(db.String(120), nullable=False)
    shift_date = db.Column(db.DateTime, nullable=False, index=True)
    line_number = db.Column(db.Integer, nullable=False)
    performance_score = db.Column(db.Integer, nullable=False)
    machine_utilization = db.Column(db.Numeric(14, 2), nullable=False)

    def __repr__(self):
        return f'<Shift {self.id}: Line {self.line_number} Employee: {self.employee_name}>'


# -------------------------------------------------------------
# Currency Migration Audit Log Model
# -------------------------------------------------------------
class CurrencyMigrationLog(db.Model):
    __tablename__ = 'currency_migration_log'
    
    log_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    migrated_at = db.Column(db.DateTime, default=utc_now, server_default=db.func.now())
    table_name = db.Column(db.String(50), nullable=False)
    record_id = db.Column(db.Integer, nullable=False)
    field_name = db.Column(db.String(50), nullable=False)
    original_currency = db.Column(db.String(10), default='USD', nullable=False)
    original_value = db.Column(db.Numeric(14, 2), nullable=False)
    exchange_rate = db.Column(db.Numeric(10, 4), default=Decimal('83.5000'), nullable=False)
    converted_value = db.Column(db.Numeric(14, 2), nullable=False)

    def __repr__(self):
        return f'<CurrencyMigrationLog {self.table_name} #{self.record_id} {self.original_currency}->INR>'
