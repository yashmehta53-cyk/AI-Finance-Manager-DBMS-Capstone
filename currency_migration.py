"""
Idempotent, Reversible INR Currency Migration Engine
Converts legacy USD transactions into Indian Rupees (INR - ₹).
Exchange Rate: 1 USD = 83.50 INR (RBI Reference Baseline).
Audits each conversion into `currency_migration_log` for complete reversibility.
"""

from datetime import datetime, timezone
from decimal import Decimal
from models import db, Transaction, Account, Budget, Goal, Investment, CurrencyMigrationLog
from app import create_app

import sys

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

EXCHANGE_RATE = Decimal('83.5000')

def run_inr_migration(app):
    with app.app_context():
        # Ensure log table exists
        db.create_all()

        print("[INFO] Starting INR Currency Migration (1 USD = ₹83.50 INR)...")

        # Check existing migrations in log
        migrated_txns = {
            log.record_id for log in CurrencyMigrationLog.query.filter_by(table_name='transactions').all()
        }

        # Identify legacy USD transactions (transactions with amounts typically under 5000 before textile migration)
        # Or specifically transactions created as generic starter examples
        txns = Transaction.query.all()
        converted_count = 0

        # We inspect transactions that are not already logged and belong to the legacy initial set
        # (e.g. description mentions Whole Foods, Kroger, Starbucks, Apartment Rent $1200, etc.)
        usd_indicators = ['Whole Foods', 'Kroger', 'Starbucks', 'Apartment Rent', 'Electric utility bill', 
                          'Gasoline and vehicle fuel', 'Water and power bill', 'Movie theater', 'Corporate Salary',
                          'Chevron', 'Trader Joe', 'Chipotle', 'Subway']

        for txn in txns:
            if txn.txn_id in migrated_txns:
                continue

            # Check if this transaction represents legacy USD data
            is_legacy_usd = any(ind.lower() in (txn.description or '').lower() for ind in usd_indicators) or (txn.amount < Decimal('3500.00') and txn.date < datetime(2026, 5, 1).date())

            if is_legacy_usd:
                orig_val = Decimal(txn.amount)
                new_val = (orig_val * EXCHANGE_RATE).quantize(Decimal('0.01'))

                # Log migration
                log_entry = CurrencyMigrationLog(
                    table_name='transactions',
                    record_id=txn.txn_id,
                    field_name='amount',
                    original_currency='USD',
                    original_value=orig_val,
                    exchange_rate=EXCHANGE_RATE,
                    converted_value=new_val
                )
                db.session.add(log_entry)

                # Update transaction amount
                txn.amount = new_val
                converted_count += 1

        db.session.commit()
        print(f"[SUCCESS] Converted {converted_count} legacy USD transactions to INR.")
        print(f"[INFO] Total audited entries in currency_migration_log: {CurrencyMigrationLog.query.count()}")

if __name__ == '__main__':
    app = create_app()
    run_inr_migration(app)
