"""
Seed Data Script for AI Finance Manager
Populates database with sample users, accounts, categories, transactions,
budgets, goals, and investment assets using realistic textile manufacturing
trading data and INR currency formatting. Idempotent and safe to run repeatedly.
"""

from datetime import date, timedelta
from decimal import Decimal
from app import create_app
from models import db, User, Account, Category, Transaction, Budget, Goal, Investment
from ai_engine import classifier
from seed_textile_data import seed_textile_dataset

def seed_database():
    app = create_app()
    with app.app_context():
        # Create all tables if not exist
        db.create_all()
        print("Database schema verified.")

        # 1. Base Users: Alice and Bob
        alice = User.query.filter_by(username='alice').first()
        if not alice:
            alice = User(username='alice', email='alice@example.com')
            alice.set_password('password123')
            db.session.add(alice)
            db.session.flush()
            print("Created user 'alice' (password: password123)")

        bob = User.query.filter_by(username='bob').first()
        if not bob:
            bob = User(username='bob', email='bob@example.com')
            bob.set_password('password123')
            db.session.add(bob)
            db.session.flush()
            print("Created user 'bob' (password: password123)")

        # 2. Base Accounts for Bob
        bob_checking = Account.query.filter_by(user_id=bob.user_id, name='Bob Checking').first()
        if not bob_checking:
            bob_checking = Account(user_id=bob.user_id, name='Bob Checking', type='Checking', balance=Decimal('120000.00'))
            db.session.add(bob_checking)
            db.session.flush()

        # 3. Seed Comprehensive Realistic Textile Trading & Manufacturing Dataset for Alice
        seed_textile_dataset('alice')

        # 4. Optional Bob transaction for multi-user isolation check
        today = date.today()
        food_cat = Category.query.filter_by(name='Food').first()
        if food_cat:
            bob_txn = Transaction.query.filter_by(user_id=bob.user_id, description='Dinner at Local Bistro').first()
            if not bob_txn:
                bob_txn = Transaction(
                    user_id=bob.user_id,
                    account_id=bob_checking.account_id,
                    category_id=food_cat.category_id,
                    date=today,
                    amount=Decimal('1850.00'),
                    description='Dinner at Local Bistro',
                    txn_type='Expense'
                )
                db.session.add(bob_txn)

        db.session.commit()
        
        # Retrain NLP classifier with user transaction descriptions
        try:
            classifier.retrain_with_user_data()
        except Exception as e:
            print(f"Classifier retrain note: {e}")
            
        print("AI Finance Manager seed completed successfully (INR / Textile dataset loaded)!")

if __name__ == '__main__':
    seed_database()
