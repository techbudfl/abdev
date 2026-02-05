#!/usr/bin/env python3
"""
Credit Card Payment Report for Actual Budget - WORKING VERSION

This tool generates a report showing which credit card accounts have received
payments within +/- 2 weeks of the report run date.

Requirements:
- actualpy library (pip install actualpy)
- Access to an Actual Budget server
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass

from actual import Actual
from actual.queries import get_accounts


@dataclass
class PaymentInfo:
    """Information about a credit card payment"""
    date: int  # YYYYMMDD format
    amount: float
    notes: Optional[str] = None


@dataclass
class AccountReport:
    """Report data for a single credit card account"""
    account_name: str
    has_payment: bool
    payment_info: Optional[PaymentInfo] = None


def is_credit_card_account(account) -> bool:
    """Check if an account is a credit card (name starts with 💳)"""
    return account.name and account.name.startswith('💳')


def date_to_int(date_obj: datetime) -> int:
    """Convert datetime to YYYYMMDD integer format used by Actual"""
    return int(date_obj.strftime('%Y%m%d'))


def int_to_date(date_int: int) -> datetime:
    """Convert YYYYMMDD integer to datetime"""
    date_str = str(date_int)
    return datetime.strptime(date_str, '%Y%m%d')


def find_payment_in_range(
    account, 
    session, 
    start_date_int: int, 
    end_date_int: int
) -> Optional[PaymentInfo]:
    """
    Find if a payment was made to this credit card account in the date range.
    A payment is a transfer where the payee's transfer_acct points to another account.
    """
    from sqlalchemy import and_
    from actual.database import Transactions, Payees
    
    # Get all transactions for this account in the date range
    transactions = session.query(Transactions).filter(
        and_(
            Transactions.acct == account.id,
            Transactions.date >= start_date_int,
            Transactions.date <= end_date_int,
            Transactions.tombstone == 0,
            Transactions.is_parent == 0
        )
    ).all()
    
    # Check each transaction to see if it's a transfer (payment)
    for trans in transactions:
        if trans.payee_id:
            # Get the payee
            payee = session.query(Payees).filter(Payees.id == trans.payee_id).first()
            
            if payee and payee.transfer_acct:
                # This is a transfer!
                # For credit cards, a payment is when money comes IN (positive amount)
                # OR when the payee's transfer_acct is different from this account
                
                if payee.transfer_acct != account.id:
                    # This is a transfer FROM another account TO this one
                    # (or vice versa, but we only care about payments TO the CC)
                    
                    # Check if money came in (for CC, this means negative amount usually)
                    # But let's be smart: if this is a CC, payment reduces the balance
                    # In Actual, CC payments show as positive amounts
                    if trans.amount > 0:
                        return PaymentInfo(
                            date=trans.date,
                            amount=trans.amount / 100.0,  # Convert from cents
                            notes=trans.notes
                        )
    
    return None


def generate_report(
    base_url: str,
    password: str,
    file: str,
    encryption_password: Optional[str] = None,
    data_dir: Optional[str] = None,
    cert: Optional[str] = None
) -> Dict[str, List[AccountReport]]:
    """
    Generate the credit card payment report.
    
    Returns a dict with two keys:
    - 'missing': list of accounts without payments
    - 'passed': list of accounts with payments
    """
    # Calculate date range: +/- 2 weeks from today
    today = datetime.now()
    start_date = today - timedelta(weeks=2)
    end_date = today + timedelta(weeks=2)
    
    # Convert to YYYYMMDD integer format
    start_date_int = date_to_int(start_date)
    end_date_int = date_to_int(end_date)
    
    print(f"🔍 Checking for payments between {start_date.date()} and {end_date.date()}")
    print(f"📅 Report run date: {today.date()}\n")
    
    with Actual(
        base_url=base_url,
        password=password,
        file=file,
        encryption_password=encryption_password,
        data_dir=data_dir,
        cert=cert
    ) as actual:
        # Get all accounts
        accounts = get_accounts(actual.session)
        
        # Filter for credit card accounts
        credit_cards = [acc for acc in accounts if is_credit_card_account(acc)]
        
        print(f"💳 Found {len(credit_cards)} credit card accounts\n")
        
        missing_payments = []
        has_payments = []
        
        for account in credit_cards:
            payment = find_payment_in_range(
                account, 
                actual.session, 
                start_date_int, 
                end_date_int
            )
            
            report = AccountReport(
                account_name=account.name,
                has_payment=payment is not None,
                payment_info=payment
            )
            
            if payment:
                has_payments.append(report)
            else:
                # Only include in missing payments if balance is not zero
                # Account balance is in cents, but can be None for closed/inactive accounts
                if account.balance_current is not None and account.balance_current != 0:
                    missing_payments.append(report)
        
        return {
            'missing': missing_payments,
            'passed': has_payments
        }


def print_report(results: Dict[str, List[AccountReport]]):
    """Print the report to console"""
    print("=" * 80)
    print("CREDIT CARD PAYMENT REPORT")
    print("=" * 80)
    print()
    
    # Print missing payments first
    if results['missing']:
        print("⚠️  MISSING PAYMENTS (No payment found in date range)")
        print("-" * 80)
        for report in results['missing']:
            print(f"  • {report.account_name}")
        print()
    else:
        print("✅ All credit card accounts have payments!")
        print()
    
    # Print accounts with payments
    if results['passed']:
        print("✅ PAYMENTS FOUND")
        print("-" * 80)
        for report in results['passed']:
            info = report.payment_info
            # Convert date integer back to readable format
            date_obj = int_to_date(info.date)
            date_str = date_obj.strftime('%Y-%m-%d')
            notes_str = f" | {info.notes}" if info.notes else ""
            print(f"  • {report.account_name} | {date_str} | ${info.amount:,.2f}{notes_str}")
        print()


def main():
    """
    Main entry point for the script.
    
    Configuration can be done here or via environment variables.
    """
    # TODO: Configure these settings for your Actual Budget server
    config = {
        'base_url': 'http://localhost:5006',  # Your Actual server URL
        'password': 'your_password',           # Server password
        'file': 'My Budget',                   # Budget file name or ID
        'encryption_password': None,           # Optional: encryption password
        'data_dir': None,                      # Optional: data directory
        'cert': None,                          # Optional: cert file path
    }
    
    try:
        results = generate_report(**config)
        print_report(results)
    except Exception as e:
        print(f"❌ Error generating report: {e}")
        raise


if __name__ == '__main__':
    main()