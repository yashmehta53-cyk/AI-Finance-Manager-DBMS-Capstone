"""
Financial and Localization Utilities for AI Finance Manager
Implements Indian Rupee (INR) currency formatting, Indian number grouping (Lakhs/Crores),
Indian date presentation (DD-MM-YYYY), and Indian Financial Year calculations.
"""

from datetime import date, datetime
from decimal import Decimal

def format_inr(value, include_symbol=True):
    """
    Formats a numeric value using the Indian Numbering System (Lakhs, Crores).
    Examples:
        850.00       -> ₹850.00
        12500.00     -> ₹12,500.00
        125000.00    -> ₹1,25,000.00
        1250000.00   -> ₹12,50,000.00
        -2500.00     -> -₹2,500.00
        0            -> ₹0.00

    Keeps the underlying value strictly numeric; formatting is purely for presentation.
    """
    if value is None:
        value = 0.0

    try:
        val = float(value)
    except (ValueError, TypeError):
        return f"₹{value}" if include_symbol else str(value)

    is_negative = val < 0
    val = abs(val)

    # Split into integer and two decimal places
    parts = f"{val:.2f}".split(".")
    int_part = parts[0]
    dec_part = parts[1]

    if len(int_part) <= 3:
        formatted_int = int_part
    else:
        last_three = int_part[-3:]
        remaining = int_part[:-3]
        groups = []
        while remaining:
            groups.insert(0, remaining[-2:])
            remaining = remaining[:-2]
        formatted_int = ",".join(groups) + "," + last_three

    result = f"{formatted_int}.{dec_part}"
    sym = "₹" if include_symbol else ""
    return f"-{sym}{result}" if is_negative else f"{sym}{result}"


def format_in_date(dt):
    """
    Formats dates into Indian convention: DD-MM-YYYY.
    Handles datetime, date, and ISO string inputs.
    """
    if not dt:
        return ""
    if isinstance(dt, str):
        try:
            dt = datetime.strptime(dt[:10], "%Y-%m-%d").date()
        except Exception:
            return dt
    if isinstance(dt, datetime):
        dt = dt.date()
    return dt.strftime("%d-%m-%Y")


def get_financial_year(dt=None):
    """
    Calculates the Indian Financial Year (April 1 to March 31).
    Example: October 2026 -> 'FY 2026-27'
             January 2027 -> 'FY 2026-27'
    """
    if dt is None:
        dt = date.today()
    if isinstance(dt, str):
        try:
            dt = datetime.strptime(dt[:10], "%Y-%m-%d").date()
        except Exception:
            dt = date.today()
    year = dt.year
    if dt.month >= 4:
        return f"FY {year}-{str(year + 1)[-2:]}"
    else:
        return f"FY {year - 1}-{str(year)[-2:]}"


def get_financial_year_range(dt=None):
    """Returns start and end dates of the Indian Financial Year for the given date."""
    if dt is None:
        dt = date.today()
    year = dt.year
    if dt.month >= 4:
        return date(year, 4, 1), date(year + 1, 3, 31)
    else:
        return date(year - 1, 4, 1), date(year, 3, 31)
