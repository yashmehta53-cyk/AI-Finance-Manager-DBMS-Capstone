import io
import csv
from datetime import datetime, date, timedelta
from decimal import Decimal
import pandas as pd
from flask import Flask, render_template, request, redirect, flash, url_for, jsonify, Response, send_file
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func, or_, and_

from config import Config
from models import (
    db, User, Account, Category, Transaction, Budget, Goal, Investment,
    Product, Inventory, Order, Shift, Customer, Supplier, Transfer, TaxRecord,
    CurrencyMigrationLog
)
from ai_engine import (
    classifier, analyze_spending, forecast_spending, detect_spending_anomalies, 
    get_month_range, get_executive_financial_metrics, answer_financial_query,
    get_financial_risk_alerts, AI_DISCLAIMER
)
from currency import format_inr, format_inr_short, CURRENCY_SYMBOL, DEFAULT_CURRENCY
from utils import format_in_date, get_financial_year

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize SQLAlchemy database
    try:
        db.init_app(app)
    except Exception as e:
        print(f"[WARN] Database initialization error: {e}")
    
    login_manager = LoginManager(app)
    login_manager.login_view = 'login'
    login_manager.login_message = 'Please log in to access the AI Finance Manager.'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Register custom Jinja filters for Indian currency formatting
    @app.template_filter('inr')
    def inr_filter(val, symbol=True, decimals=2):
        return format_inr(val, symbol=symbol, decimals=decimals)

    @app.template_filter('inr_short')
    def inr_short_filter(val, symbol=True):
        return format_inr_short(val, symbol=symbol)

    @app.template_filter('currency')
    def currency_filter(val, symbol=True, decimals=2):
        return format_inr(val, symbol=symbol, decimals=decimals)

    @app.template_filter('in_date')
    def in_date_filter(dt):
        return format_in_date(dt)

    # Helper context processor for templates
    @app.context_processor
    def inject_globals():
        return {
            'now': datetime.now(),
            'current_month_str': date.today().strftime('%Y-%m'),
            'today_date': date.today().strftime('%Y-%m-%d'),
            'currency_symbol': CURRENCY_SYMBOL,
            'currency_code': DEFAULT_CURRENCY,
            'format_inr': format_inr,
            'format_inr_short': format_inr_short,
            'format_in_date': format_in_date,
            'financial_year': get_financial_year(),
            'zip': zip,
            'app_name': 'AI Finance Manager'
        }

    # -------------------------------------------------------------
    # Authentication Routes
    # -------------------------------------------------------------
    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))

        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')
            confirm_password = request.form.get('confirm_password', '')
            company_name = request.form.get('company_name', 'Aura TexFab Mills Ltd.').strip()
            gstin = request.form.get('gstin', '33AABCT1332L1Z4').strip()

            if not username or not email or not password:
                flash('All required fields must be filled.', 'danger')
                return render_template('register.html')

            if password != confirm_password:
                flash('Passwords do not match.', 'danger')
                return render_template('register.html')

            if len(password) < 6:
                flash('Password must be at least 6 characters long.', 'danger')
                return render_template('register.html')

            if User.query.filter_by(username=username).first():
                flash('Username is already registered. Please choose another.', 'danger')
                return render_template('register.html')

            if User.query.filter_by(email=email).first():
                flash('Email is already registered. Please sign in.', 'danger')
                return render_template('register.html')

            new_user = User(
                username=username, 
                email=email,
                company_name=company_name,
                gstin=gstin,
                role='Admin'
            )
            new_user.set_password(password)
            db.session.add(new_user)
            
            try:
                db.session.commit()
                # Create default primary Indian corporate accounts for new user
                hdfc_curr = Account(
                    user_id=new_user.user_id, 
                    name='HDFC Current Account (Operations)', 
                    type='Checking', 
                    balance=Decimal('1500000.00'),
                    bank_name='HDFC Bank',
                    account_number='50200088991122',
                    ifsc_code='HDFC0000123'
                )
                petty_cash = Account(
                    user_id=new_user.user_id, 
                    name='Factory Petty Cash (Coimbatore)', 
                    type='Cash', 
                    balance=Decimal('75000.00'),
                    bank_name='Cash in Hand'
                )
                sbi_cc = Account(
                    user_id=new_user.user_id, 
                    name='SBI Cash Credit (CC) Facility', 
                    type='Credit', 
                    balance=Decimal('2500000.00'),
                    bank_name='State Bank of India',
                    account_number='33112244556',
                    ifsc_code='SBIN0001234'
                )
                db.session.add_all([hdfc_curr, petty_cash, sbi_cc])
                db.session.commit()

                flash('Account created successfully! Please log in.', 'success')
                return redirect(url_for('login'))
            except Exception as e:
                db.session.rollback()
                flash(f'Registration error: {str(e)}', 'danger')
                return render_template('register.html')

        return render_template('register.html')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))

        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')

            user = User.query.filter((User.username == username) | (User.email == username.lower())).first()

            if user and user.check_password(password):
                login_user(user, remember=request.form.get('remember') == 'on')
                flash(f'Welcome back, {user.username}!', 'success')
                next_page = request.args.get('next')
                return redirect(next_page or url_for('dashboard'))
            else:
                flash('Invalid corporate credentials. Please verify your username and password.', 'danger')

        return render_template('login.html')

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        flash('Session terminated safely.', 'info')
        return redirect(url_for('login'))

    # -------------------------------------------------------------
    # Executive Dashboard
    # -------------------------------------------------------------
    @app.route('/')
    @app.route('/dashboard')
    @login_required
    def dashboard():
        today = date.today()
        current_month = today.strftime('%Y-%m')
        start_date, end_date = get_month_range(today.year, today.month)

        # 1. Complete Executive Financial KPIs
        metrics = get_executive_financial_metrics(current_user.user_id)

        # 2. Accounts List
        accounts = Account.query.filter_by(user_id=current_user.user_id).all()

        # 3. Category Expenses Breakdown (for Chart.js)
        category_spending_raw = db.session.query(
            Category.name,
            func.sum(Transaction.amount)
        ).join(Category, Transaction.category_id == Category.category_id).filter(
            Transaction.user_id == current_user.user_id,
            Transaction.txn_type == 'Expense'
        ).group_by(Category.name).order_by(func.sum(Transaction.amount).desc()).limit(7).all()

        chart_category_labels = [row[0] for row in category_spending_raw]
        chart_category_values = [float(row[1]) for row in category_spending_raw]

        # 4. Last 6 Months Income vs Expense (for Cash Flow Trend Chart)
        six_months_ago = today - timedelta(days=180)
        trend_records = db.session.query(
            Transaction.date,
            Transaction.txn_type,
            Transaction.amount
        ).filter(
            Transaction.user_id == current_user.user_id,
            Transaction.date >= six_months_ago
        ).order_by(Transaction.date.asc()).all()

        monthly_trends = {}
        for r in trend_records:
            m_key = r.date.strftime('%Y-%m')
            if m_key not in monthly_trends:
                monthly_trends[m_key] = {'Income': 0.0, 'Expense': 0.0}
            monthly_trends[m_key][r.txn_type] += float(r.amount)

        sorted_months = sorted(monthly_trends.keys())[-6:]
        trend_labels = sorted_months
        trend_income = [round(monthly_trends[m]['Income'], 2) for m in sorted_months]
        trend_expense = [round(monthly_trends[m]['Expense'], 2) for m in sorted_months]

        # 5. Recent Transactions
        recent_txns = Transaction.query.filter_by(user_id=current_user.user_id)\
            .order_by(Transaction.date.desc(), Transaction.txn_id.desc())\
            .limit(8).all()

        # 6. AI Quick Insights & Risk Flags
        ai_analysis = analyze_spending(current_user.user_id, current_month)
        risk_alerts = get_financial_risk_alerts(current_user.user_id)

        return render_template(
            'dashboard.html',
            metrics=metrics,
            accounts=accounts,
            recent_transactions=recent_txns,
            chart_category_labels=chart_category_labels,
            chart_category_values=chart_category_values,
            trend_labels=trend_labels,
            trend_income=trend_income,
            trend_expense=trend_expense,
            ai_recommendations=ai_analysis['recommendations'][:3],
            risk_alerts=risk_alerts[:2]
        )

    # -------------------------------------------------------------
    # Financial Management: Transactions & Ledger
    # -------------------------------------------------------------
    @app.route('/transactions')
    @login_required
    def view_transactions():
        page = request.args.get('page', 1, type=int)
        per_page = 20
        
        search_query = request.args.get('q', '').strip()
        txn_type = request.args.get('type', '')
        category_id = request.args.get('category', type=int)
        account_id = request.args.get('account', type=int)
        start_date = request.args.get('start_date', '')
        end_date = request.args.get('end_date', '')

        query = Transaction.query.filter_by(user_id=current_user.user_id)

        if search_query:
            query = query.filter(or_(
                Transaction.description.ilike(f'%{search_query}%'),
                Transaction.party_name.ilike(f'%{search_query}%'),
                Transaction.reference_no.ilike(f'%{search_query}%')
            ))

        if txn_type in ('Income', 'Expense'):
            query = query.filter(Transaction.txn_type == txn_type)

        if category_id:
            query = query.filter(Transaction.category_id == category_id)

        if account_id:
            query = query.filter(Transaction.account_id == account_id)

        if start_date:
            try:
                s_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
                query = query.filter(Transaction.date >= s_dt)
            except ValueError:
                pass

        if end_date:
            try:
                e_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
                query = query.filter(Transaction.date <= e_dt)
            except ValueError:
                pass

        pagination = query.order_by(Transaction.date.desc(), Transaction.txn_id.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        categories = Category.query.filter(
            or_(Category.user_id == current_user.user_id, Category.user_id.is_(None))
        ).order_by(Category.name.asc()).all()

        accounts = Account.query.filter_by(user_id=current_user.user_id).all()

        # Summary figures for filtered set
        total_income = query.filter(Transaction.txn_type == 'Income').with_entities(func.coalesce(func.sum(Transaction.amount), 0)).scalar()
        total_expense = query.filter(Transaction.txn_type == 'Expense').with_entities(func.coalesce(func.sum(Transaction.amount), 0)).scalar()

        return render_template(
            'transactions.html',
            transactions=pagination.items,
            pagination=pagination,
            categories=categories,
            accounts=accounts,
            search_query=search_query,
            txn_type=txn_type,
            category_id=category_id,
            account_id=account_id,
            start_date=start_date,
            end_date=end_date,
            total_income=total_income,
            total_expense=total_expense
        )

    @app.route('/transactions/add', methods=['GET', 'POST'])
    @login_required
    def add_transaction():
        if request.method == 'POST':
            account_id = request.form.get('account_id', type=int)
            category_id = request.form.get('category_id', type=int)
            date_str = request.form.get('date', '')
            amount_val = request.form.get('amount', '')
            description = request.form.get('description', '').strip()
            txn_type = request.form.get('txn_type', 'Expense')
            payment_method = request.form.get('payment_method', 'Bank Transfer')
            reference_no = request.form.get('reference_no', '').strip()
            party_name = request.form.get('party_name', '').strip()
            party_gstin = request.form.get('party_gstin', '').strip()
            gst_rate_val = request.form.get('gst_rate', '0.00')

            if not account_id or not category_id or not date_str or not amount_val:
                flash('Account, category, date, and amount are required.', 'danger')
                return redirect(url_for('add_transaction'))

            try:
                amount = Decimal(str(amount_val))
                gst_rate = Decimal(str(gst_rate_val or '0.00'))
                txn_date = datetime.strptime(date_str, '%Y-%m-%d').date()

                # Verify ownership of account
                account = Account.query.filter_by(account_id=account_id, user_id=current_user.user_id).first_or_404()

                # Calculate CGST/SGST/IGST breakdown
                cgst = (amount * (gst_rate / Decimal('200'))).quantize(Decimal('0.01')) if gst_rate > 0 else Decimal('0.00')
                sgst = cgst
                igst = Decimal('0.00')

                new_txn = Transaction(
                    user_id=current_user.user_id,
                    account_id=account_id,
                    category_id=category_id,
                    date=txn_date,
                    amount=amount,
                    description=description,
                    txn_type=txn_type,
                    payment_method=payment_method,
                    reference_no=reference_no,
                    party_name=party_name,
                    party_gstin=party_gstin,
                    gst_rate=gst_rate,
                    cgst_amount=cgst,
                    sgst_amount=sgst,
                    igst_amount=igst
                )

                # Atomically update account balance
                if txn_type == 'Income':
                    account.balance += amount
                else:
                    account.balance -= amount

                db.session.add(new_txn)
                db.session.commit()
                flash('Transaction recorded successfully.', 'success')
                return redirect(url_for('view_transactions'))
            except Exception as e:
                db.session.rollback()
                flash(f"Transaction failed: {str(e)}", 'danger')
                return redirect(url_for('add_transaction'))

        categories = Category.query.filter(
            or_(Category.user_id == current_user.user_id, Category.user_id.is_(None))
        ).order_by(Category.name.asc()).all()
        accounts = Account.query.filter_by(user_id=current_user.user_id).all()
        return render_template('add_transaction.html', categories=categories, accounts=accounts)

    @app.route('/transactions/edit/<int:id>', methods=['GET', 'POST'])
    @login_required
    def edit_transaction(id):
        txn = Transaction.query.filter_by(txn_id=id, user_id=current_user.user_id).first_or_404()
        
        if request.method == 'POST':
            account_id = request.form.get('account_id', type=int)
            category_id = request.form.get('category_id', type=int)
            date_str = request.form.get('date', '')
            amount_val = request.form.get('amount', '')
            description = request.form.get('description', '').strip()
            txn_type = request.form.get('txn_type', txn.txn_type)
            payment_method = request.form.get('payment_method', txn.payment_method)
            reference_no = request.form.get('reference_no', '').strip()
            party_name = request.form.get('party_name', '').strip()

            try:
                new_amount = Decimal(str(amount_val))
                new_date = datetime.strptime(date_str, '%Y-%m-%d').date()

                old_acct = Account.query.get(txn.account_id)
                new_acct = Account.query.get(account_id)

                # Revert old balance effect
                if txn.txn_type == 'Income':
                    old_acct.balance -= txn.amount
                else:
                    old_acct.balance += txn.amount

                # Apply new balance effect
                if txn_type == 'Income':
                    new_acct.balance += new_amount
                else:
                    new_acct.balance -= new_amount

                txn.account_id = account_id
                txn.category_id = category_id
                txn.date = new_date
                txn.amount = new_amount
                txn.description = description
                txn.txn_type = txn_type
                txn.payment_method = payment_method
                txn.reference_no = reference_no
                txn.party_name = party_name

                db.session.commit()
                flash('Transaction updated successfully.', 'success')
                return redirect(url_for('view_transactions'))
            except Exception as e:
                db.session.rollback()
                flash(f"Update failed: {str(e)}", 'danger')

        categories = Category.query.filter(
            or_(Category.user_id == current_user.user_id, Category.user_id.is_(None))
        ).order_by(Category.name.asc()).all()
        accounts = Account.query.filter_by(user_id=current_user.user_id).all()
        return render_template('edit_transaction.html', txn=txn, categories=categories, accounts=accounts)

    @app.route('/transactions/delete/<int:id>', methods=['POST'])
    @login_required
    def delete_transaction(id):
        txn = Transaction.query.filter_by(txn_id=id, user_id=current_user.user_id).first_or_404()
        acct = Account.query.get(txn.account_id)

        try:
            if acct:
                if txn.txn_type == 'Income':
                    acct.balance -= txn.amount
                else:
                    acct.balance += txn.amount

            db.session.delete(txn)
            db.session.commit()
            flash('Transaction deleted and balance adjusted.', 'info')
        except Exception as e:
            db.session.rollback()
            flash(f"Error deleting transaction: {str(e)}", 'danger')

        return redirect(url_for('view_transactions'))

    @app.route('/transactions/export')
    @login_required
    def export_transactions():
        txns = Transaction.query.filter_by(user_id=current_user.user_id).order_by(Transaction.date.desc()).all()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Txn ID', 'Date', 'Type', 'Amount (INR)', 'Category', 'Account', 'Payment Method', 'Party', 'Reference', 'Description'])
        for t in txns:
            writer.writerow([
                t.txn_id,
                t.date.strftime('%d-%m-%Y'),
                t.txn_type,
                f"{t.amount:.2f}",
                t.category.name if t.category else '',
                t.account.name if t.account else '',
                t.payment_method or '',
                t.party_name or '',
                t.reference_no or '',
                t.description or ''
            ])
        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment;filename=transactions_export_{date.today().strftime('%Y%m%d')}.csv"}
        )

    @app.route('/transactions/import', methods=['POST'])
    @login_required
    def import_transactions():
        file = request.files.get('file')
        if not file or not file.filename.endswith('.csv'):
            flash('Please upload a valid CSV file.', 'danger')
            return redirect(url_for('view_transactions'))

        try:
            stream = io.StringIO(file.stream.read().decode("utf-8-sig"), newline=None)
            reader = csv.DictReader(stream)
            
            # Check required columns
            fieldnames = [f.lower().strip() for f in (reader.fieldnames or [])]
            if not all(col in fieldnames for col in ['date', 'amount', 'type']):
                flash('CSV must contain at least date, amount, and type columns.', 'danger')
                return redirect(url_for('view_transactions'))

            imported_count = 0
            default_account = Account.query.filter_by(user_id=current_user.user_id).first()

            if not default_account:
                flash('Please create an account before importing transactions.', 'warning')
                return redirect(url_for('view_transactions'))

            for row in reader:
                # normalize keys
                row_norm = {k.lower().strip(): v for k, v in row.items() if k}
                amt_str = row_norm.get('amount', '0')
                amt = Decimal(str(amt_str.replace('₹', '').replace(',', '').strip()))
                t_type = row_norm.get('type', 'Expense').capitalize()
                desc = row_norm.get('description', '')
                date_str = row_norm.get('date', date.today().strftime('%Y-%m-%d'))
                
                try:
                    txn_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                except ValueError:
                    txn_date = date.today()

                cat_name = row_norm.get('category')
                if not cat_name or cat_name.lower() in ('uncategorized', 'unknown'):
                    cat_name, _ = classifier.predict(desc)

                category = Category.query.filter_by(name=cat_name).first()
                if not category:
                    category = Category(name=cat_name, type=t_type, user_id=current_user.user_id)
                    db.session.add(category)
                    db.session.flush()

                txn = Transaction(
                    user_id=current_user.user_id,
                    account_id=default_account.account_id,
                    category_id=category.category_id,
                    date=txn_date,
                    amount=amt,
                    description=desc,
                    txn_type=t_type,
                    payment_method='Bank Transfer'
                )

                if t_type == 'Income':
                    default_account.balance += amt
                else:
                    default_account.balance -= amt

                db.session.add(txn)
                imported_count += 1

            db.session.commit()
            flash(f"Successfully imported {imported_count} transactions.", 'success')
        except Exception as e:
            db.session.rollback()
            flash(f"CSV import error: {str(e)}", 'danger')

        return redirect(url_for('view_transactions'))

    # -------------------------------------------------------------
    # Financial Management: Accounts & Cash/Bank Management
    # -------------------------------------------------------------
    @app.route('/accounts')
    @login_required
    def accounts():
        user_accounts = Account.query.filter_by(user_id=current_user.user_id).all()
        total_balance = sum([Decimal(str(a.balance)) for a in user_accounts])
        bank_accounts = [a for a in user_accounts if a.type in ('Checking', 'Savings')]
        cash_accounts = [a for a in user_accounts if a.type == 'Cash']
        credit_facilities = [a for a in user_accounts if a.type == 'Credit']

        return render_template(
            'accounts.html',
            accounts=user_accounts,
            bank_accounts=bank_accounts,
            cash_accounts=cash_accounts,
            credit_facilities=credit_facilities,
            total_balance=total_balance
        )

    @app.route('/accounts/add', methods=['POST'])
    @login_required
    def add_account():
        name = request.form.get('name', '').strip()
        acc_type = request.form.get('type')
        balance_val = request.form.get('balance', '0.00')
        bank_name = request.form.get('bank_name', '').strip()
        account_number = request.form.get('account_number', '').strip()
        ifsc_code = request.form.get('ifsc_code', '').strip()

        if not name or not acc_type:
            flash('Account title and type are mandatory.', 'danger')
            return redirect(url_for('accounts'))

        try:
            balance = Decimal(str(balance_val or '0.00'))
            new_acc = Account(
                user_id=current_user.user_id,
                name=name,
                type=acc_type,
                balance=balance,
                bank_name=bank_name,
                account_number=account_number,
                ifsc_code=ifsc_code
            )
            db.session.add(new_acc)
            db.session.commit()
            flash(f"Account '{name}' registered successfully.", 'success')
        except Exception as e:
            db.session.rollback()
            flash(f"Failed to create account: {str(e)}", 'danger')

        return redirect(url_for('accounts'))

    @app.route('/accounts/edit/<int:id>', methods=['POST'])
    @login_required
    def edit_account(id):
        acc = Account.query.filter_by(account_id=id, user_id=current_user.user_id).first_or_404()
        name = request.form.get('name', '').strip()
        balance_val = request.form.get('balance')
        bank_name = request.form.get('bank_name', '').strip()
        ifsc_code = request.form.get('ifsc_code', '').strip()

        if name:
            acc.name = name
        if bank_name:
            acc.bank_name = bank_name
        if ifsc_code:
            acc.ifsc_code = ifsc_code
        if balance_val:
            try:
                acc.balance = Decimal(str(balance_val))
            except Exception:
                pass

        db.session.commit()
        flash('Account details updated.', 'success')
        return redirect(url_for('accounts'))

    @app.route('/accounts/delete/<int:id>', methods=['POST'])
    @login_required
    def delete_account(id):
        acc = Account.query.filter_by(account_id=id, user_id=current_user.user_id).first_or_404()
        db.session.delete(acc)
        db.session.commit()
        flash('Account removed from ledger.', 'info')
        return redirect(url_for('accounts'))

    # -------------------------------------------------------------
    # Financial Management: Fund Transfers
    # -------------------------------------------------------------
    @app.route('/transfers')
    @login_required
    def transfers_view():
        transfers = Transfer.query.filter_by(user_id=current_user.user_id).order_by(Transfer.transfer_date.desc()).all()
        accounts = Account.query.filter_by(user_id=current_user.user_id).all()
        return render_template('transfers.html', transfers=transfers, accounts=accounts)

    @app.route('/transfers/add', methods=['POST'])
    @login_required
    def add_transfer():
        from_acc_id = request.form.get('from_account_id', type=int)
        to_acc_id = request.form.get('to_account_id', type=int)
        amount_val = request.form.get('amount')
        date_str = request.form.get('transfer_date', date.today().strftime('%Y-%m-%d'))
        reference_no = request.form.get('reference_no', '').strip()
        notes = request.form.get('notes', '').strip()

        if not from_acc_id or not to_acc_id or not amount_val:
            flash('Origin, destination, and transfer amount required.', 'danger')
            return redirect(url_for('transfers_view'))

        if from_acc_id == to_acc_id:
            flash('Origin and destination accounts must be distinct.', 'danger')
            return redirect(url_for('transfers_view'))

        try:
            amt = Decimal(str(amount_val))
            if amt <= 0:
                flash('Transfer amount must be greater than zero.', 'danger')
                return redirect(url_for('transfers_view'))

            from_acc = Account.query.filter_by(account_id=from_acc_id, user_id=current_user.user_id).first_or_404()
            to_acc = Account.query.filter_by(account_id=to_acc_id, user_id=current_user.user_id).first_or_404()

            if from_acc.balance < amt and from_acc.type != 'Credit':
                flash(f"Insufficient funds in '{from_acc.name}'.", 'warning')
                return redirect(url_for('transfers_view'))

            t_date = datetime.strptime(date_str, '%Y-%m-%d').date()

            # Double-entry balance adjustment
            from_acc.balance -= amt
            to_acc.balance += amt

            transfer = Transfer(
                user_id=current_user.user_id,
                from_account_id=from_acc_id,
                to_account_id=to_acc_id,
                amount=amt,
                transfer_date=t_date,
                reference_no=reference_no,
                notes=notes
            )
            db.session.add(transfer)
            db.session.commit()
            flash(f"Transferred {format_inr(amt)} from '{from_acc.name}' to '{to_acc.name}'.", 'success')
        except Exception as e:
            db.session.rollback()
            flash(f"Transfer failed: {str(e)}", 'danger')

        return redirect(url_for('transfers_view'))

    # -------------------------------------------------------------
    # Customers & Receivables
    # -------------------------------------------------------------
    @app.route('/receivables')
    @login_required
    def receivables_view():
        customers = Customer.query.filter_by(user_id=current_user.user_id).order_by(Customer.outstanding_balance.desc()).all()
        total_ar = sum([Decimal(str(c.outstanding_balance)) for c in customers])
        
        # Real orders from imported textile database
        recent_orders = Order.query.order_by(Order.order_date.desc()).limit(15).all()

        return render_template(
            'receivables.html',
            customers=customers,
            total_ar=total_ar,
            recent_orders=recent_orders
        )

    @app.route('/receivables/record-payment', methods=['POST'])
    @login_required
    def record_customer_payment():
        customer_id = request.form.get('customer_id', type=int)
        amount_val = request.form.get('amount')
        account_id = request.form.get('account_id', type=int)
        reference_no = request.form.get('reference_no', '').strip()

        customer = Customer.query.filter_by(customer_id=customer_id, user_id=current_user.user_id).first_or_404()
        try:
            amt = Decimal(str(amount_val))
            customer.outstanding_balance = max(Decimal('0.00'), customer.outstanding_balance - amt)

            # Credit into account if selected
            if account_id:
                acct = Account.query.filter_by(account_id=account_id, user_id=current_user.user_id).first()
                if acct:
                    acct.balance += amt

            db.session.commit()
            flash(f"Collection of {format_inr(amt)} recorded for '{customer.name}'.", 'success')
        except Exception as e:
            db.session.rollback()
            flash(f"Collection error: {str(e)}", 'danger')

        return redirect(url_for('receivables_view'))

    # -------------------------------------------------------------
    # Suppliers & Payables
    # -------------------------------------------------------------
    @app.route('/payables')
    @login_required
    def payables_view():
        suppliers = Supplier.query.filter_by(user_id=current_user.user_id).order_by(Supplier.outstanding_balance.desc()).all()
        total_ap = sum([Decimal(str(s.outstanding_balance)) for s in suppliers])
        
        # Textile supplier expense transactions
        recent_purchases = Transaction.query.filter(
            Transaction.user_id == current_user.user_id,
            Transaction.txn_type == 'Expense'
        ).order_by(Transaction.date.desc()).limit(12).all()

        return render_template(
            'payables.html',
            suppliers=suppliers,
            total_ap=total_ap,
            recent_purchases=recent_purchases
        )

    @app.route('/payables/record-payment', methods=['POST'])
    @login_required
    def record_supplier_payment():
        supplier_id = request.form.get('supplier_id', type=int)
        amount_val = request.form.get('amount')
        account_id = request.form.get('account_id', type=int)
        reference_no = request.form.get('reference_no', '').strip()

        supplier = Supplier.query.filter_by(supplier_id=supplier_id, user_id=current_user.user_id).first_or_404()
        try:
            amt = Decimal(str(amount_val))
            supplier.outstanding_balance = max(Decimal('0.00'), supplier.outstanding_balance - amt)

            # Debit from account if selected
            if account_id:
                acct = Account.query.filter_by(account_id=account_id, user_id=current_user.user_id).first()
                if acct:
                    acct.balance -= amt

            db.session.commit()
            flash(f"Disbursement of {format_inr(amt)} to '{supplier.name}' cleared.", 'success')
        except Exception as e:
            db.session.rollback()
            flash(f"Payment error: {str(e)}", 'danger')

        return redirect(url_for('payables_view'))

    # -------------------------------------------------------------
    # AI Financial Intelligence Hub
    # -------------------------------------------------------------
    @app.route('/ai-advisory')
    @app.route('/recommendations')
    @login_required
    def ai_advisory():
        target_month = request.args.get('month', date.today().strftime('%Y-%m'))
        analysis = analyze_spending(current_user.user_id, target_month)
        forecast = forecast_spending(current_user.user_id, horizon_months=3)
        anomalies = detect_spending_anomalies(current_user.user_id)
        risk_alerts = get_financial_risk_alerts(current_user.user_id)
        metrics = get_executive_financial_metrics(current_user.user_id)

        return render_template(
            'recommendations.html',
            analysis=analysis,
            forecast=forecast,
            anomalies=anomalies,
            risk_alerts=risk_alerts,
            metrics=metrics,
            target_month=target_month,
            disclaimer=AI_DISCLAIMER
        )

    @app.route('/api/ai-chat', methods=['POST'])
    @login_required
    def api_ai_chat():
        data = request.get_json() or {}
        question = data.get('question', '').strip()
        if not question:
            return jsonify({'error': 'Please provide a financial query.'}), 400

        result = answer_financial_query(current_user.user_id, question)
        return jsonify(result)

    # -------------------------------------------------------------
    # Financial Reports (P&L, Balance Sheet, GST Tax Summary)
    # -------------------------------------------------------------
    @app.route('/reports')
    @login_required
    def financial_reports():
        metrics = get_executive_financial_metrics(current_user.user_id)
        
        # P&L Breakdown
        category_breakdown = db.session.query(
            Category.name,
            Category.type,
            func.sum(Transaction.amount).label('total')
        ).join(Category, Transaction.category_id == Category.category_id).filter(
            Transaction.user_id == current_user.user_id
        ).group_by(Category.name, Category.type).order_by(func.sum(Transaction.amount).desc()).all()

        income_categories = [c for c in category_breakdown if c[1] == 'Income']
        expense_categories = [c for c in category_breakdown if c[1] == 'Expense']

        # Inventory Asset Value
        inv_sum = db.session.query(func.coalesce(func.sum(Inventory.stock_value), 0)).scalar()
        inventory_valuation_inr = Decimal(str(inv_sum or '0.00')) * Decimal('83.50')

        return render_template(
            'reports.html',
            metrics=metrics,
            income_categories=income_categories,
            expense_categories=expense_categories,
            inventory_valuation=inventory_valuation_inr
        )

    @app.route('/reports/tax')
    @login_required
    def tax_reports():
        tax_records = TaxRecord.query.filter_by(user_id=current_user.user_id).order_by(TaxRecord.period.desc()).all()
        gstr1_records = [r for r in tax_records if r.return_type == 'GSTR-1']
        gstr3b_records = [r for r in tax_records if r.return_type == 'GSTR-3B']
        
        total_taxable = sum([Decimal(str(r.taxable_amount)) for r in gstr3b_records])
        total_gst_paid = sum([Decimal(str(r.total_tax)) for r in gstr3b_records])
        total_itc_claimed = sum([Decimal(str(r.itc_claimed)) for r in gstr3b_records])

        return render_template(
            'tax_reports.html',
            gstr1_records=gstr1_records,
            gstr3b_records=gstr3b_records,
            total_taxable=total_taxable,
            total_gst_paid=total_gst_paid,
            total_itc_claimed=total_itc_claimed
        )

    # -------------------------------------------------------------
    # Corporate Settings
    # -------------------------------------------------------------
    @app.route('/settings')
    @login_required
    def settings_view():
        return render_template('settings.html')

    @app.route('/settings/update-profile', methods=['POST'])
    @login_required
    def update_profile():
        company_name = request.form.get('company_name', '').strip()
        gstin = request.form.get('gstin', '').strip()
        if company_name:
            current_user.company_name = company_name
        if gstin:
            current_user.gstin = gstin
        db.session.commit()
        flash('Corporate entity profile saved.', 'success')
        return redirect(url_for('settings_view'))

    # -------------------------------------------------------------
    # Budgets, Goals, Categories, Investments (Maintained)
    # -------------------------------------------------------------
    @app.route('/budgets')
    @login_required
    def budgets():
        target_month = request.args.get('month', date.today().strftime('%Y-%m'))
        year, month = map(int, target_month.split('-'))
        start_date, end_date = get_month_range(year, month)

        user_budgets = Budget.query.filter_by(user_id=current_user.user_id, month=target_month).all()
        budget_cards = []
        total_budgeted = 0.0
        total_spent = 0.0

        for b in user_budgets:
            spent = db.session.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
                Transaction.user_id == current_user.user_id,
                Transaction.category_id == b.category_id,
                Transaction.txn_type == 'Expense',
                Transaction.date >= start_date,
                Transaction.date <= end_date
            ).scalar()

            spent_amt = float(spent or 0.0)
            limit_amt = float(b.limit_amount)
            pct = round((spent_amt / limit_amt * 100), 1) if limit_amt > 0 else 0.0

            total_budgeted += limit_amt
            total_spent += spent_amt

            budget_cards.append({
                'budget_id': b.budget_id,
                'category_id': b.category_id,
                'category_name': b.category.name if b.category else 'Unknown',
                'limit_amount': limit_amt,
                'spent_amount': spent_amt,
                'remaining': max(0.0, limit_amt - spent_amt),
                'percent': min(pct, 100.0),
                'actual_percent': pct,
                'status': 'danger' if pct > 100 else ('warning' if pct >= 85 else 'success')
            })

        categories = Category.query.filter(
            Category.type == 'Expense',
            or_(Category.user_id == current_user.user_id, Category.user_id.is_(None))
        ).order_by(Category.name.asc()).all()

        return render_template(
            'budgets.html',
            budgets=budget_cards,
            categories=categories,
            target_month=target_month,
            total_budgeted=total_budgeted,
            total_spent=total_spent,
            total_remaining=max(0.0, total_budgeted - total_spent)
        )

    @app.route('/budgets/add', methods=['POST'])
    @login_required
    def add_budget():
        category_id = request.form.get('category_id', type=int)
        target_month = request.form.get('month', date.today().strftime('%Y-%m'))
        limit_val = request.form.get('limit_amount')

        if not category_id or not limit_val:
            flash('Category and monthly limit are required.', 'danger')
            return redirect(url_for('budgets', month=target_month))

        try:
            limit = Decimal(str(limit_val))
            existing = Budget.query.filter_by(
                user_id=current_user.user_id,
                category_id=category_id,
                month=target_month
            ).first()

            if existing:
                existing.limit_amount = limit
                flash(f'Budget for {target_month} updated.', 'info')
            else:
                new_budget = Budget(
                    user_id=current_user.user_id,
                    category_id=category_id,
                    month=target_month,
                    limit_amount=limit
                )
                db.session.add(new_budget)
                flash(f'Budget for {target_month} created.', 'success')

            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash(f'Failed to save budget: {str(e)}', 'danger')

        return redirect(url_for('budgets', month=target_month))

    @app.route('/budgets/delete/<int:id>', methods=['POST'])
    @login_required
    def delete_budget(id):
        b = Budget.query.filter_by(budget_id=id, user_id=current_user.user_id).first_or_404()
        m = b.month
        db.session.delete(b)
        db.session.commit()
        flash('Budget removed.', 'info')
        return redirect(url_for('budgets', month=m))

    @app.route('/categories')
    @login_required
    def categories():
        user_cats = Category.query.filter(
            or_(Category.user_id == current_user.user_id, Category.user_id.is_(None))
        ).order_by(Category.type.asc(), Category.name.asc()).all()
        return render_template('categories.html', categories=user_cats)

    @app.route('/categories/add', methods=['POST'])
    @login_required
    def add_category():
        name = request.form.get('name', '').strip()
        c_type = request.form.get('type', 'Expense')
        hsn = request.form.get('hsn_sac_code', '').strip()
        gst_rate = request.form.get('default_gst_rate', '5.00')

        if not name or c_type not in ('Expense', 'Income'):
            flash('Valid category title and classification required.', 'danger')
            return redirect(url_for('categories'))

        try:
            new_cat = Category(
                user_id=current_user.user_id,
                name=name,
                type=c_type,
                hsn_sac_code=hsn,
                default_gst_rate=Decimal(str(gst_rate))
            )
            db.session.add(new_cat)
            db.session.commit()
            flash(f"Category '{name}' registered.", 'success')
        except Exception as e:
            db.session.rollback()
            flash(f"Failed to add category: {str(e)}", 'danger')

        return redirect(url_for('categories'))

    @app.route('/categories/delete/<int:id>', methods=['POST'])
    @login_required
    def delete_category(id):
        cat = Category.query.filter_by(category_id=id, user_id=current_user.user_id).first_or_404()
        db.session.delete(cat)
        db.session.commit()
        flash('Category deleted.', 'info')
        return redirect(url_for('categories'))

    @app.route('/goals')
    @login_required
    def goals():
        user_goals = Goal.query.filter_by(user_id=current_user.user_id).order_by(Goal.due_date.asc().nullslast()).all()
        accounts = Account.query.filter_by(user_id=current_user.user_id).all()
        return render_template('goals.html', goals=user_goals, accounts=accounts)

    @app.route('/goals/add', methods=['POST'])
    @login_required
    def add_goal():
        name = request.form.get('name', '').strip()
        target_val = request.form.get('target_amount')
        saved_val = request.form.get('saved_amount', '0.00')
        due_date_str = request.form.get('due_date')

        if not name or not target_val:
            flash('Goal title and target amount required.', 'danger')
            return redirect(url_for('goals'))

        try:
            target = Decimal(str(target_val))
            saved = Decimal(str(saved_val or '0.00'))
            due = datetime.strptime(due_date_str, '%Y-%m-%d').date() if due_date_str else None

            goal = Goal(
                user_id=current_user.user_id,
                name=name,
                target_amount=target,
                saved_amount=saved,
                due_date=due
            )
            db.session.add(goal)
            db.session.commit()
            flash(f"Goal '{name}' established.", 'success')
        except Exception as e:
            db.session.rollback()
            flash(f"Error creating goal: {str(e)}", 'danger')

        return redirect(url_for('goals'))

    @app.route('/goals/contribute/<int:id>', methods=['POST'])
    @login_required
    def contribute_goal(id):
        goal = Goal.query.filter_by(goal_id=id, user_id=current_user.user_id).first_or_404()
        amount_val = request.form.get('amount')
        account_id = request.form.get('account_id', type=int)

        try:
            amt = Decimal(str(amount_val))
            if account_id:
                acc = Account.query.filter_by(account_id=account_id, user_id=current_user.user_id).first()
                if acc and acc.balance >= amt:
                    acc.balance -= amt

            goal.saved_amount += amt
            db.session.commit()
            flash(f"Contributed {format_inr(amt)} to '{goal.name}'.", 'success')
        except Exception as e:
            db.session.rollback()
            flash(f"Contribution error: {str(e)}", 'danger')

        return redirect(url_for('goals'))

    @app.route('/goals/delete/<int:id>', methods=['POST'])
    @login_required
    def delete_goal(id):
        goal = Goal.query.filter_by(goal_id=id, user_id=current_user.user_id).first_or_404()
        db.session.delete(goal)
        db.session.commit()
        flash('Goal removed.', 'info')
        return redirect(url_for('goals'))

    @app.route('/investments')
    @login_required
    def investments():
        user_invs = Investment.query.filter_by(user_id=current_user.user_id).order_by(Investment.buy_date.desc()).all()
        total_cost = sum([Decimal(str(inv.total_cost)) for inv in user_invs])
        return render_template('investments.html', investments=user_invs, total_invested=total_cost)

    @app.route('/investments/add', methods=['POST'])
    @login_required
    def add_investment():
        instrument = request.form.get('instrument', '').strip().upper()
        quantity_val = request.form.get('quantity')
        price_val = request.form.get('buy_price')
        date_str = request.form.get('buy_date')

        try:
            qty = int(quantity_val)
            price = Decimal(str(price_val))
            b_date = datetime.strptime(date_str, '%Y-%m-%d').date()

            inv = Investment(
                user_id=current_user.user_id,
                instrument=instrument,
                quantity=qty,
                buy_price=price,
                buy_date=b_date
            )
            db.session.add(inv)
            db.session.commit()
            flash(f"Treasury investment in '{instrument}' logged.", 'success')
        except Exception as e:
            db.session.rollback()
            flash(f"Investment error: {str(e)}", 'danger')

        return redirect(url_for('investments'))

    @app.route('/investments/delete/<int:id>', methods=['POST'])
    @login_required
    def delete_investment(id):
        inv = Investment.query.filter_by(inv_id=id, user_id=current_user.user_id).first_or_404()
        db.session.delete(inv)
        db.session.commit()
        flash('Treasury holding removed.', 'info')
        return redirect(url_for('investments'))

    @app.route('/api/predict-category', methods=['POST'])
    @login_required
    def api_predict_category():
        data = request.get_json() or {}
        description = data.get('description', '')
        if not description:
            return jsonify({'predicted_category': None, 'confidence': 0.0})

        pred_name, confidence = classifier.predict(description)
        return jsonify({
            'predicted_category': pred_name,
            'confidence': confidence
        })

    return app

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        db.create_all()
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
