"""
Centralized Currency Formatting Utility for AI Finance Manager
Enforces Indian Rupee (INR - ₹) standard formatting with Lakh/Crore grouping.
"""

from decimal import Decimal

DEFAULT_CURRENCY = 'INR'
CURRENCY_SYMBOL = '₹'
CURRENCY_LOCALE = 'en-IN'

def format_inr(val, symbol=True, decimals=2):
    """
    Format numeric values into Indian numbering system format.
    Example:
        125000 -> ₹1,25,000.00
        10000000 -> ₹1,00,00,000.00
        -450.5 -> -₹450.50
        0 -> ₹0.00
        None -> ₹0.00
    """
    if val is None or val == '':
        sym = CURRENCY_SYMBOL if symbol else ''
        return f"{sym}0.00" if decimals > 0 else f"{sym}0"
        
    try:
        num = float(val)
    except (ValueError, TypeError):
        return str(val)

    is_negative = num < 0
    num = abs(num)
    
    if decimals > 0:
        formatted_dec = f"{num:.{decimals}f}"
        int_part, dec_part = formatted_dec.split('.')
    else:
        int_part = str(int(round(num)))
        dec_part = ""

    if len(int_part) <= 3:
        grouped_int = int_part
    else:
        last3 = int_part[-3:]
        remaining = int_part[:-3]
        groups = []
        while len(remaining) > 2:
            groups.insert(0, remaining[-2:])
            remaining = remaining[:-2]
        if remaining:
            groups.insert(0, remaining)
        grouped_int = ",".join(groups) + "," + last3

    res = grouped_int + (f".{dec_part}" if decimals > 0 else "")
    prefix = "-" if is_negative else ""
    sym = CURRENCY_SYMBOL if symbol else ""
    return f"{prefix}{sym}{res}"

def format_inr_short(val, symbol=True):
    """
    Formats large values into human-readable Indian notations (Lakhs, Crores).
    Example:
        1500000 -> ₹15.00 L
        25000000 -> ₹2.50 Cr
    """
    if val is None:
        return f"{CURRENCY_SYMBOL if symbol else ''}0"
    try:
        num = float(val)
    except (ValueError, TypeError):
        return str(val)
        
    is_neg = num < 0
    num = abs(num)
    prefix = "-" if is_neg else ""
    sym = CURRENCY_SYMBOL if symbol else ""

    if num >= 10000000:
        return f"{prefix}{sym}{num / 10000000:.2f} Cr"
    elif num >= 100000:
        return f"{prefix}{sym}{num / 100000:.2f} L"
    elif num >= 1000:
        return f"{prefix}{sym}{num / 1000:.1f} k"
    else:
        return f"{prefix}{sym}{num:.2f}"
