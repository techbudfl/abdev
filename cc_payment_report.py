#!/usr/bin/env python3
"""
Credit Card Payment Report for Actual Budget - v3.0

This tool generates a report showing:
1. Credit card accounts that have received payments
2. Monitored payees that have received payments

NEW in v3.0: Monitor specific payees (like Target, BMW Financing) for payments

Requirements:
- actualpy library (pip install actualpy)
- Access to an Actual Budget server
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass
import json

from actual import Actual
from actual.queries import get_accounts


@dataclass
class PaymentInfo:
    """Information about a credit card payment"""
    date: int  # YYYYMMDD format
    amount: float
    notes: Optional[str] = None
    is_scheduled: bool = False


@dataclass
class AccountReport:
    """Report data for a single credit card account"""
    account_name: str
    has_payment: bool
    payment_info: Optional[PaymentInfo] = None


@dataclass  
class PayeeReport:
    """NEW v3.0: Report data for a monitored payee"""
    payee_name: str
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
    
    This checks for COMPLETED payments (past or future-dated transactions).
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
                            notes=trans.notes,
                            is_scheduled=False
                        )
    
    return None


def find_scheduled_payment_in_range(
    account,
    session,
    start_date_int: int,
    end_date_int: int,
    today_int: int
) -> Optional[PaymentInfo]:
    """
    Find if a payment is SCHEDULED for this credit card account in the date range.
    
    v2.0: Checks the Rules table for scheduled transactions.
    
    Scheduled transactions are stored as Rules with:
    - date condition (the scheduled date)
    - amount condition (in cents) 
    - acct condition (the credit card account)
    - link-schedule action
    
    Note: Ignores $0 amounts (these are reminders, not actual payments)
    """
    from actual.database import Rules
    
    # Get all rules (these include scheduled transactions)
    rules = session.query(Rules).filter(
        Rules.tombstone == 0
    ).all()
    
    for rule in rules:
        try:
            # Parse the rule conditions
            conditions = json.loads(rule.conditions) if rule.conditions else []
            
            # Extract relevant conditions
            rule_date = None
            rule_amount = None
            rule_acct = None
            
            for cond in conditions:
                field = cond.get('field')
                value = cond.get('value')
                
                if field == 'date':
                    # Date is stored as string like "2026-02-12"
                    if isinstance(value, str):
                        try:
                            rule_date = int(value.replace('-', ''))
                        except:
                            pass
                    elif isinstance(value, int):
                        rule_date = value
                        
                elif field == 'amount':
                    rule_amount = value
                    
                elif field == 'acct':
                    rule_acct = value
            
            # Check if this rule matches our criteria
            if (rule_acct == account.id and 
                rule_date is not None and
                rule_amount is not None and
                start_date_int <= rule_date <= end_date_int and
                rule_date > today_int and  # Only future scheduled payments
                rule_amount != 0):  # Ignore $0 reminders
                
                # Check if there's a link-schedule action (confirms it's a scheduled transaction)
                actions = json.loads(rule.actions) if rule.actions else []
                has_schedule = any(action.get('op') == 'link-schedule' for action in actions)
                
                if has_schedule and rule_amount > 0:  # Positive amount = payment TO credit card
                    # Extract notes if present
                    notes = None
                    for action in actions:
                        if action.get('op') == 'set' and action.get('field') == 'notes':
                            notes = action.get('value')
                    
                    return PaymentInfo(
                        date=rule_date,
                        amount=rule_amount / 100.0,  # Convert from cents
                        notes=notes,
                        is_scheduled=True
                    )
                    
        except Exception:
            # Skip rules that don't match the expected format
            continue
    
    return None


def find_payee_payment_in_range(
    payee_name: str,
    session,
    start_date_int: int,
    end_date_int: int
) -> Optional[PaymentInfo]:
    """
    NEW v3.0: Find if a payment was made to a specific payee in the date range.
    
    This looks for ANY transaction (from any account) to the specified payee.
    Negative amounts indicate money going OUT (payment being made).
    """
    from sqlalchemy import and_, or_
    from actual.database import Transactions, Payees
    
    # Find the payee by name (case-insensitive partial match)
    payees = session.query(Payees).filter(
        Payees.tombstone == 0
    ).all()
    
    matching_payee = None
    for p in payees:
        if p.name and payee_name.lower() in p.name.lower():
            matching_payee = p
            break
    
    if not matching_payee:
        return None
    
    # Find transactions to this payee in the date range
    transactions = session.query(Transactions).filter(
        and_(
            Transactions.payee_id == matching_payee.id,
            Transactions.date >= start_date_int,
            Transactions.date <= end_date_int,
            Transactions.amount < 0,  # Negative = money going out (payment)
            Transactions.tombstone == 0,
            Transactions.is_parent == 0
        )
    ).order_by(Transactions.date.desc()).all()
    
    if transactions:
        # Return the most recent payment
        trans = transactions[0]
        return PaymentInfo(
            date=trans.date,
            amount=abs(trans.amount / 100.0),  # Make positive for display
            notes=trans.notes,
            is_scheduled=False
        )
    
    return None


def find_scheduled_payee_payment_in_range(
    payee_name: str,
    session,
    start_date_int: int,
    end_date_int: int,
    today_int: int
) -> Optional[PaymentInfo]:
    """
    NEW v3.0: Find if a payment is SCHEDULED to a specific payee.
    
    Looks in the Rules table for scheduled transactions to this payee.
    """
    from actual.database import Rules, Payees
    
    # Find the payee by name
    payees = session.query(Payees).filter(
        Payees.tombstone == 0
    ).all()
    
    matching_payee = None
    for p in payees:
        if p.name and payee_name.lower() in p.name.lower():
            matching_payee = p
            break
    
    if not matching_payee:
        return None
    
    # Get all rules
    rules = session.query(Rules).filter(
        Rules.tombstone == 0
    ).all()
    
    for rule in rules:
        try:
            conditions = json.loads(rule.conditions) if rule.conditions else []
            
            rule_date = None
            rule_amount = None
            rule_description = None
            
            for cond in conditions:
                field = cond.get('field')
                value = cond.get('value')
                
                if field == 'date':
                    if isinstance(value, str):
                        try:
                            rule_date = int(value.replace('-', ''))
                        except:
                            pass
                    elif isinstance(value, int):
                        rule_date = value
                        
                elif field == 'amount':
                    rule_amount = value
                    
                elif field == 'description':
                    rule_description = value
            
            # Check if this rule matches the payee and date range
            if (rule_description == matching_payee.id and
                rule_date is not None and
                rule_amount is not None and
                start_date_int <= rule_date <= end_date_int and
                rule_date > today_int and
                rule_amount != 0):
                
                actions = json.loads(rule.actions) if rule.actions else []
                has_schedule = any(action.get('op') == 'link-schedule' for action in actions)
                
                if has_schedule and rule_amount < 0:  # Negative = payment out
                    notes = None
                    for action in actions:
                        if action.get('op') == 'set' and action.get('field') == 'notes':
                            notes = action.get('value')
                    
                    return PaymentInfo(
                        date=rule_date,
                        amount=abs(rule_amount / 100.0),
                        notes=notes,
                        is_scheduled=True
                    )
                    
        except Exception:
            continue
    
    return None


def generate_report(
    base_url: str,
    password: str,
    file: str,
    monitored_payees: Optional[List[str]] = None,
    encryption_password: Optional[str] = None,
    data_dir: Optional[str] = None,
    cert: Optional[str] = None
) -> Dict[str, List]:
    """
    Generate the payment report.
    
    v3.0: Returns both credit card payments AND monitored payee payments
    
    Returns a dict with four keys:
    - 'cc_missing': list of credit cards without payments
    - 'cc_passed': list of credit cards with payments
    - 'payee_missing': list of payees without payments (NEW v3.0)
    - 'payee_passed': list of payees with payments (NEW v3.0)
    """
    # Calculate date range: +/- 2 weeks from today
    today = datetime.now()
    start_date = today - timedelta(weeks=2)
    end_date = today + timedelta(weeks=2)
    
    # Convert to YYYYMMDD integer format
    start_date_int = date_to_int(start_date)
    end_date_int = date_to_int(end_date)
    today_int = date_to_int(today)
    
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
        # === CREDIT CARD LOGIC (v1.x/v2.x) ===
        accounts = get_accounts(actual.session)
        credit_cards = [acc for acc in accounts if is_credit_card_account(acc)]
        
        print(f"💳 Found {len(credit_cards)} credit card accounts")
        
        cc_missing_payments = []
        cc_has_payments = []
        
        for account in credit_cards:
            payment = find_payment_in_range(
                account, 
                actual.session, 
                start_date_int, 
                end_date_int
            )
            
            if not payment:
                payment = find_scheduled_payment_in_range(
                    account,
                    actual.session,
                    start_date_int,
                    end_date_int,
                    today_int
                )
            
            report = AccountReport(
                account_name=account.name,
                has_payment=payment is not None,
                payment_info=payment
            )
            
            if payment:
                cc_has_payments.append(report)
            else:
                if account.balance_current is not None and account.balance_current != 0:
                    cc_missing_payments.append(report)
        
        # === NEW v3.0: MONITORED PAYEE LOGIC ===
        payee_missing_payments = []
        payee_has_payments = []
        
        if monitored_payees:
            print(f"👤 Checking {len(monitored_payees)} monitored payee(s)")
            
            for payee_name in monitored_payees:
                payment = find_payee_payment_in_range(
                    payee_name,
                    actual.session,
                    start_date_int,
                    end_date_int
                )
                
                if not payment:
                    payment = find_scheduled_payee_payment_in_range(
                        payee_name,
                        actual.session,
                        start_date_int,
                        end_date_int,
                        today_int
                    )
                
                report = PayeeReport(
                    payee_name=payee_name,
                    has_payment=payment is not None,
                    payment_info=payment
                )
                
                if payment:
                    payee_has_payments.append(report)
                else:
                    payee_missing_payments.append(report)
        
        print()  # Blank line before report
        
        return {
            'cc_missing': cc_missing_payments,
            'cc_passed': cc_has_payments,
            'payee_missing': payee_missing_payments,
            'payee_passed': payee_has_payments
        }


def print_report(results: Dict[str, List]):
    """Print the report to console"""
    print("=" * 80)
    print("PAYMENT REPORT")
    print("=" * 80)
    print()
    
    # === CREDIT CARD SECTION ===
    print("💳 CREDIT CARD PAYMENTS")
    print("-" * 80)
    
    if results['cc_missing']:
        print("\n⚠️  MISSING PAYMENTS")
        for report in results['cc_missing']:
            print(f"  • {report.account_name}")
    
    if results['cc_passed']:
        print("\n✅ PAYMENTS FOUND")
        for report in results['cc_passed']:
            info = report.payment_info
            date_obj = int_to_date(info.date)
            date_str = date_obj.strftime('%Y-%m-%d')
            scheduled_marker = " (scheduled)" if info.is_scheduled else ""
            notes_str = f" | {info.notes}" if info.notes else ""
            print(f"  • {report.account_name} | {date_str} | ${info.amount:,.2f}{scheduled_marker}{notes_str}")
    
    if not results['cc_missing'] and not results['cc_passed']:
        print("  No credit card accounts to report")
    
    # === NEW v3.0: MONITORED PAYEE SECTION ===
    if results['payee_missing'] or results['payee_passed']:
        print("\n\n👤 MONITORED PAYEE PAYMENTS")
        print("-" * 80)
        
        if results['payee_missing']:
            print("\n⚠️  MISSING PAYMENTS")
            for report in results['payee_missing']:
                print(f"  • {report.payee_name}")
        
        if results['payee_passed']:
            print("\n✅ PAYMENTS FOUND")
            for report in results['payee_passed']:
                info = report.payment_info
                date_obj = int_to_date(info.date)
                date_str = date_obj.strftime('%Y-%m-%d')
                scheduled_marker = " (scheduled)" if info.is_scheduled else ""
                notes_str = f" | {info.notes}" if info.notes else ""
                print(f"  • {report.payee_name} | {date_str} | ${info.amount:,.2f}{scheduled_marker}{notes_str}")
    
    print("\n" + "=" * 80)


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
        'monitored_payees': ['Target', 'BMW Financing'],  # NEW v3.0
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
