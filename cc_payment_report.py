#!/usr/bin/env python3
"""
Credit Card Payment Report for Actual Budget - v3.1

NEW in v3.1: Beautiful table-based reports using the Rich library

Requirements:
- actualpy library (pip install actualpy)
- rich library (pip install rich)
- Access to an Actual Budget server
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass
import json

from actual import Actual
from actual.queries import get_accounts
from rich.console import Console
from rich.table import Table
from rich import box


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
    """Report data for a monitored payee"""
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
    """Find if a payment was made to this credit card account in the date range."""
    from sqlalchemy import and_
    from actual.database import Transactions, Payees
    
    transactions = session.query(Transactions).filter(
        and_(
            Transactions.acct == account.id,
            Transactions.date >= start_date_int,
            Transactions.date <= end_date_int,
            Transactions.tombstone == 0,
            Transactions.is_parent == 0
        )
    ).all()
    
    for trans in transactions:
        if trans.payee_id:
            payee = session.query(Payees).filter(Payees.id == trans.payee_id).first()
            
            if payee and payee.transfer_acct:
                if payee.transfer_acct != account.id:
                    if trans.amount > 0:
                        return PaymentInfo(
                            date=trans.date,
                            amount=trans.amount / 100.0,
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
    """Find if a payment is SCHEDULED for this credit card account."""
    from actual.database import Rules
    
    rules = session.query(Rules).filter(
        Rules.tombstone == 0
    ).all()
    
    for rule in rules:
        try:
            conditions = json.loads(rule.conditions) if rule.conditions else []
            
            rule_date = None
            rule_amount = None
            rule_acct = None
            
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
                elif field == 'acct':
                    rule_acct = value
            
            if (rule_acct == account.id and 
                rule_date is not None and
                rule_amount is not None and
                start_date_int <= rule_date <= end_date_int and
                rule_date > today_int and
                rule_amount != 0):
                
                actions = json.loads(rule.actions) if rule.actions else []
                has_schedule = any(action.get('op') == 'link-schedule' for action in actions)
                
                if has_schedule and rule_amount > 0:
                    notes = None
                    for action in actions:
                        if action.get('op') == 'set' and action.get('field') == 'notes':
                            notes = action.get('value')
                    
                    return PaymentInfo(
                        date=rule_date,
                        amount=rule_amount / 100.0,
                        notes=notes,
                        is_scheduled=True
                    )
                    
        except Exception:
            continue
    
    return None


def find_payee_payment_in_range(
    payee_name: str,
    session,
    start_date_int: int,
    end_date_int: int
) -> Optional[PaymentInfo]:
    """Find if a payment was made to a specific payee."""
    from sqlalchemy import and_
    from actual.database import Transactions, Payees
    
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
    
    transactions = session.query(Transactions).filter(
        and_(
            Transactions.payee_id == matching_payee.id,
            Transactions.date >= start_date_int,
            Transactions.date <= end_date_int,
            Transactions.amount < 0,
            Transactions.tombstone == 0,
            Transactions.is_parent == 0
        )
    ).order_by(Transactions.date.desc()).all()
    
    if transactions:
        trans = transactions[0]
        return PaymentInfo(
            date=trans.date,
            amount=abs(trans.amount / 100.0),
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
    """Find if a payment is SCHEDULED to a specific payee."""
    from actual.database import Rules, Payees
    
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
            
            if (rule_description == matching_payee.id and
                rule_date is not None and
                rule_amount is not None and
                start_date_int <= rule_date <= end_date_int and
                rule_date > today_int and
                rule_amount != 0):
                
                actions = json.loads(rule.actions) if rule.actions else []
                has_schedule = any(action.get('op') == 'link-schedule' for action in actions)
                
                if has_schedule and rule_amount < 0:
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
    """Generate the payment report."""
    today = datetime.now()
    start_date = today - timedelta(weeks=2)
    end_date = today + timedelta(weeks=2)
    
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
        # Credit card logic
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
        
        # Monitored payee logic
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
        
        print()
        
        return {
            'cc_missing': cc_missing_payments,
            'cc_passed': cc_has_payments,
            'payee_missing': payee_missing_payments,
            'payee_passed': payee_has_payments
        }


def print_report(results: Dict[str, List]):
    """NEW v3.1: Print beautiful table-based report using Rich"""
    console = Console()
    
    # === CREDIT CARD PAYMENTS TABLE ===
    if results['cc_missing'] or results['cc_passed']:
        cc_table = Table(
            title="💳 Credit Card Payments",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold magenta",
            title_style="bold cyan",
            border_style="bright_blue"
        )
        
        cc_table.add_column("Account", style="cyan", no_wrap=True)
        cc_table.add_column("Status", justify="center", style="bold")
        cc_table.add_column("Date", justify="center", style="yellow")
        cc_table.add_column("Amount", justify="right", style="green")
        cc_table.add_column("Notes", style="dim")
        
        # Add missing payments first (in red)
        for report in results['cc_missing']:
            cc_table.add_row(
                report.account_name,
                "[bold red]⚠️  MISSING[/bold red]",
                "-",
                "-",
                "-"
            )
        
        # Add successful payments (in green)
        for report in results['cc_passed']:
            info = report.payment_info
            date_obj = int_to_date(info.date)
            date_str = date_obj.strftime('%Y-%m-%d')
            
            status = "[bold green]✅ PAID[/bold green]"
            if info.is_scheduled:
                status = "[bold yellow]📅 SCHEDULED[/bold yellow]"
            
            notes_display = info.notes if info.notes else ""
            
            cc_table.add_row(
                report.account_name,
                status,
                date_str,
                f"${info.amount:,.2f}",
                notes_display
            )
        
        console.print(cc_table)
        console.print()
    
    # === MONITORED PAYEE PAYMENTS TABLE ===
    if results['payee_missing'] or results['payee_passed']:
        payee_table = Table(
            title="👤 Monitored Payee Payments",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold magenta",
            title_style="bold cyan",
            border_style="bright_blue"
        )
        
        payee_table.add_column("Payee", style="cyan", no_wrap=True)
        payee_table.add_column("Status", justify="center", style="bold")
        payee_table.add_column("Date", justify="center", style="yellow")
        payee_table.add_column("Amount", justify="right", style="green")
        payee_table.add_column("Notes", style="dim")
        
        # Add missing payments first
        for report in results['payee_missing']:
            payee_table.add_row(
                report.payee_name,
                "[bold red]⚠️  MISSING[/bold red]",
                "-",
                "-",
                "-"
            )
        
        # Add successful payments
        for report in results['payee_passed']:
            info = report.payment_info
            date_obj = int_to_date(info.date)
            date_str = date_obj.strftime('%Y-%m-%d')
            
            status = "[bold green]✅ PAID[/bold green]"
            if info.is_scheduled:
                status = "[bold yellow]📅 SCHEDULED[/bold yellow]"
            
            notes_display = info.notes if info.notes else ""
            
            payee_table.add_row(
                report.payee_name,
                status,
                date_str,
                f"${info.amount:,.2f}",
                notes_display
            )
        
        console.print(payee_table)


def main():
    """Main entry point for the script."""
    config = {
        'base_url': 'http://localhost:5006',
        'password': 'your_password',
        'file': 'My Budget',
        'monitored_payees': ['Target', 'BMW Financing'],
        'encryption_password': None,
        'data_dir': None,
        'cert': None,
    }
    
    try:
        results = generate_report(**config)
        print_report(results)
    except Exception as e:
        print(f"❌ Error generating report: {e}")
        raise


if __name__ == '__main__':
    main()
