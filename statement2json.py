#!/usr/bin/env python3
"""
Financial Transaction Extractor

OVERVIEW:
=========
This script extracts financial transactions from PDF bank statements and outputs them
to a structured JSON format for budgeting and financial analysis. It supports three
types of financial statements:
- Checking account statements
- Savings account statements  
- Credit card statements

The script is designed with security in mind, automatically masking sensitive information
like account numbers (showing only last 4 digits) and sanitizing transaction descriptions
to remove potentially sensitive data like phone numbers, emails, and reference numbers.

SUPPORTED FORMATS:
==================
Currently optimized for Bank of America PDF statements, but can be adapted for other
banks by modifying the regex patterns in the extraction functions.

INPUT:
======
- PDF files in the same directory as the script
- Files should be named with keywords: 'checking', 'savings', or 'credit'
- Example filenames: credit_2025-08-26.pdf, checking_statement.pdf, savings_jan2025.pdf

OUTPUT:
=======
- JSON file: financial_transactions.json
- Contains metadata and array of transaction objects
- Each transaction includes: date, description, amount, account type, transaction type

SECURITY FEATURES:
==================
- Account numbers masked (shows only last 4 digits: ****1234)
- Transaction descriptions sanitized (removes phone numbers, emails, reference numbers)
- Debug output masks sensitive information

DEPENDENCIES:
=============
Required: pypdf, pandas, re, json, os, datetime

Installation:
pip install pypdf pandas

USAGE:
======
1. Place PDF statements in same directory as script
2. Run: python3 financial_extractor.py
3. Review output in financial_transactions.json
4. Delete files when analysis complete

Last Updated: September 2025
"""

# Import required libraries with proper error handling
try:
    import pypdf
except ImportError:
    print("Error: pypdf is required but not installed.")
    print("Please install it with: pip install pypdf")
    exit(1)

try:
    import pandas as pd
except ImportError:
    print("Error: pandas is required but not installed.")
    print("Please install it with: pip install pandas")
    exit(1)

import re
import json
import os
from datetime import datetime

# Global debug flag - set to True only when debugging is needed
DEBUG_MODE = False

def debug_print(message):
    """Print debug messages only when DEBUG_MODE is enabled"""
    if DEBUG_MODE:
        print(message)

def extract_pdf_text(pdf_path):
    """
    Extract text content from PDF file using pypdf
    
    Args:
        pdf_path (str): Path to the PDF file
        
    Returns:
        str: Extracted text from all pages, or empty string if extraction fails
    """
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = pypdf.PdfReader(file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
        return text
    except Exception as e:
        debug_print(f"Error reading PDF {pdf_path}: {e}")
        return ""

def extract_statement_period(text):
    """
    Extract statement period (start/end dates) from PDF text to determine year context
    
    Args:
        text (str): Full PDF text content
        
    Returns:
        tuple: (start_date, end_date) as datetime objects, or (None, None) if not found
    """
    patterns = [
        # Pattern 1: "July 27 - August 26, 2025" or "July 27, 2024 to August 26, 2024"
        r'([A-Za-z]+)\s+(\d{1,2})(?:,?\s*(\d{4}))?\s*[-to]+\s*([A-Za-z]+)\s+(\d{1,2}),?\s*(\d{4})',
        
        # Pattern 2: "07/27/2024 to 08/26/2024" or "Statement Period: 01/01/24 - 01/31/24"
        r'(\d{1,2})/(\d{1,2})/(\d{2,4})\s*[-to]+\s*(\d{1,2})/(\d{1,2})/(\d{2,4})',
        
        # Pattern 3: "Account # XXXX July 27 - August 26, 2025" (from header lines)
        r'Account\s*#.*?([A-Za-z]+)\s+(\d{1,2})\s*-\s*([A-Za-z]+)\s+(\d{1,2}),?\s*(\d{4})',
    ]
    
    month_names = {
        'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6,
        'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12,
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'jun': 6, 'jul': 7, 'aug': 8, 
        'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
    }
    
    for pattern in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            try:
                groups = match.groups()
                
                if len(groups) == 6:  # Month name pattern
                    start_month = month_names.get(groups[0].lower())
                    start_day = int(groups[1])
                    start_year = int(groups[2]) if groups[2] else None
                    end_month = month_names.get(groups[3].lower())
                    end_day = int(groups[4])
                    end_year = int(groups[5])
                    
                    # If start year not specified, use end year (handle cross-year periods)
                    if not start_year:
                        start_year = end_year if start_month <= end_month else end_year - 1
                    
                    start_date = datetime(start_year, start_month, start_day)
                    end_date = datetime(end_year, end_month, end_day)
                    
                elif len(groups) >= 6:  # Numeric date pattern
                    start_month, start_day, start_year = int(groups[0]), int(groups[1]), int(groups[2])
                    end_month, end_day, end_year = int(groups[3]), int(groups[4]), int(groups[5])
                    
                    # Handle 2-digit years
                    if start_year < 100:
                        start_year += 2000
                    if end_year < 100:
                        end_year += 2000
                    
                    start_date = datetime(start_year, start_month, start_day)
                    end_date = datetime(end_year, end_month, end_day)
                
                elif len(groups) == 5:  # Account header pattern
                    start_month = month_names.get(groups[0].lower())
                    start_day = int(groups[1])
                    end_month = month_names.get(groups[2].lower())
                    end_day = int(groups[3])
                    year = int(groups[4])
                    
                    start_year = year if start_month <= end_month else year - 1
                    
                    start_date = datetime(start_year, start_month, start_day)
                    end_date = datetime(year, end_month, end_day)
                
                else:
                    continue
                
                # Validate the date range makes sense
                if (start_date.year >= 2020 and end_date.year <= 2030 and 
                    start_date <= end_date and 
                    (end_date - start_date).days <= 40):
                    
                    return start_date, end_date
                    
            except (ValueError, KeyError, TypeError):
                continue
    
    return None, None

def standardize_date(date_str, statement_start=None, statement_end=None):
    """
    Convert various date formats to standardized YYYY-MM-DD format using statement context
    
    Args:
        date_str (str): Date in various formats (MM/DD/YY, MM/DD/YYYY, MM/DD)
        statement_start (datetime): Start date of statement period for year context
        statement_end (datetime): End date of statement period for year context
        
    Returns:
        str: Date in YYYY-MM-DD format, or original string if conversion fails
    """
    try:
        if '/' in date_str:
            parts = date_str.split('/')
            if len(parts) == 3:
                # Full date with year
                month, day, year = parts
                if len(year) == 2:
                    year = '20' + year
                return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
            elif len(parts) == 2 and statement_start and statement_end:
                # Month/day only - use statement period for year context
                month, day = int(parts[0]), int(parts[1])
                
                # For cross-year periods, determine year based on which part of statement period the month falls in
                if statement_start.year != statement_end.year:
                    # Cross-year period - determine year by month proximity to statement dates
                    
                    # Try statement start year first
                    try:
                        candidate_start_year = datetime(statement_start.year, month, day)
                        if statement_start <= candidate_start_year <= statement_end:
                            return f"{statement_start.year}-{month:02d}-{day:02d}"
                    except ValueError:
                        pass
                    
                    # Try statement end year
                    try:
                        candidate_end_year = datetime(statement_end.year, month, day)
                        if statement_start <= candidate_end_year <= statement_end:
                            return f"{statement_end.year}-{month:02d}-{day:02d}"
                    except ValueError:
                        pass
                    
                    # If neither works exactly, use logic based on month proximity
                    # If month is closer to statement start month, use start year
                    if abs(month - statement_start.month) <= abs(month - statement_end.month):
                        return f"{statement_start.year}-{month:02d}-{day:02d}"
                    else:
                        return f"{statement_end.year}-{month:02d}-{day:02d}"
                
                else:
                    # Same year period - straightforward
                    try:
                        candidate_date = datetime(statement_start.year, month, day)
                        if statement_start <= candidate_date <= statement_end:
                            return f"{statement_start.year}-{month:02d}-{day:02d}"
                    except ValueError:
                        pass
                    
                    # Default to statement year
                    return f"{statement_start.year}-{month:02d}-{day:02d}"
            
            elif len(parts) == 2:
                # Fallback to current year if no statement context
                month, day = parts
                year = str(datetime.now().year)
                return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
    except:
        pass
    return date_str

def mask_account_number(account_number):
    """
    Mask account number for security, showing only last 4 digits
    
    Args:
        account_number (str): Full account number (may include spaces/formatting)
        
    Returns:
        str: Masked account number (e.g., "************1234")
    """
    if not account_number:
        return ""
    
    clean_number = re.sub(r'\s+', '', account_number)
    
    if len(clean_number) >= 4:
        masked = '*' * (len(clean_number) - 4) + clean_number[-4:]
        return masked
    else:
        return '*' * len(clean_number)

def mask_sensitive_data(text):
    """
    Mask potentially sensitive information in text for debug output
    
    Args:
        text (str): Raw text that may contain sensitive information
        
    Returns:
        str: Text with sensitive patterns replaced with placeholders
    """
    # Mask potential account numbers
    text = re.sub(r'\b\d{4}\s*\d{4}\s*\d{4}\s*\d{4}\b', '****-****-****-****', text)
    text = re.sub(r'\b\d{4}\s*\d{4}\s*\d{4}\b', '****-****-****', text)
    
    # Mask potential SSN patterns
    text = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '***-**-****', text)
    text = re.sub(r'\b\d{9}\b', '*********', text)
    
    # Mask potential routing numbers
    text = re.sub(r'\b[01]\d{8}\b', '*********', text)
    
    return text

def sanitize_description(description):
    """
    Remove potentially sensitive information from transaction descriptions
    
    Args:
        description (str): Raw transaction description from PDF
        
    Returns:
        str: Cleaned description with sensitive data replaced by placeholders
    """
    description = description.lower().strip()
    
    # Remove potential account numbers
    description = re.sub(r'\b\d{4}\s*\d{4}\s*\d{4}\s*\d{4}\b', '[ACCOUNT]', description)
    description = re.sub(r'\b\d{4}\s*\d{4}\s*\d{4}\b', '[ACCOUNT]', description)
    
    # Remove potential confirmation numbers
    description = re.sub(r'\b\d{8,}\b', '[REF#]', description)
    
    # Remove potential phone numbers
    description = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE]', description)
    
    # Remove potential email patterns
    description = re.sub(r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b', '[EMAIL]', description)
    
    # Clean up multiple spaces
    description = re.sub(r'\s+', ' ', description).strip()
    
    return description

def extract_account_number(text, statement_type):
    """
    Extract and mask account number from statement text
    
    Args:
        text (str): Full PDF text content
        statement_type (str): "checking", "savings", or "credit"
        
    Returns:
        str: Masked account number showing only last 4 digits
    """
    patterns = {
        'checking': r'Account #\s*(\d{4}\s+\d{4}\s+\d{4})',
        'savings': r'Account #\s*(\d{4}\s+\d{4}\s+\d{4})',
        'credit': r'Account #\s*(\d{4}\s+\d{4}\s+\d{4}\s+\d{4})'
    }
    
    pattern = patterns.get(statement_type, '')
    if not pattern:
        return ""
    
    match = re.search(pattern, text)
    if match:
        full_number = match.group(1).replace(' ', '')
        return mask_account_number(full_number)
    return ""

def extract_checking_transactions(text, account_num=""):
    """
    Extract transactions from checking account statements
    
    Args:
        text (str): Full text extracted from PDF
        account_num (str): Masked account number for this statement
        
    Returns:
        list: List of transaction dictionaries
    """
    transactions = []
    
    deposit_pattern = r'(\d{2}/\d{2}/\d{2,4})\s+([^-\d]*?)\s+(\d{1,3}(?:,\d{3})*\.\d{2})(?:\s|$)'
    withdrawal_pattern = r'(\d{2}/\d{2}/\d{2,4})\s+([^-\d]*?)\s+-(\d{1,3}(?:,\d{3})*\.\d{2})(?:\s|$)'
    
    # Process withdrawals
    for match in re.finditer(withdrawal_pattern, text, re.MULTILINE):
        date_str = match.group(1)
        description = match.group(2).strip()
        amount = -float(match.group(3).replace(',', ''))
        
        description = sanitize_description(description)
        
        transactions.append({
            'date': date_str,
            'description': description,
            'amount': amount,
            'account_type': 'checking',
            'account_number': account_num,
            'transaction_type': 'withdrawal'
        })
    
    # Process deposits
    for match in re.finditer(deposit_pattern, text, re.MULTILINE):
        date_str = match.group(1)
        description = match.group(2).strip()
        amount = float(match.group(3).replace(',', ''))
        
        # Skip if this amount also appears as a withdrawal nearby
        line = match.group(0)
        if '-' + match.group(3) in text[max(0, match.start()-50):match.end()+50]:
            continue
            
        description = sanitize_description(description)
        
        transactions.append({
            'date': date_str,
            'description': description,
            'amount': amount,
            'account_type': 'checking',
            'account_number': account_num,
            'transaction_type': 'deposit'
        })
    
    return transactions

def extract_savings_transactions(text, account_num=""):
    """
    Extract transactions from savings account statements
    
    Args:
        text (str): Full text extracted from PDF
        account_num (str): Masked account number for this statement
        
    Returns:
        list: List of transaction dictionaries
    """
    transactions = []
    
    withdrawal_pattern = r'(\d{2}/\d{2}/\d{2,4})\s+([^-\d]*?)\s+-(\d{1,3}(?:,\d{3})*\.\d{2})(?:\s|$)'
    deposit_pattern = r'(\d{2}/\d{2}/\d{2,4})\s+([^-\d]*?)\s+(\d{1,3}(?:,\d{3})*\.\d{2})(?:\s|$)'
    
    # Process withdrawals
    for match in re.finditer(withdrawal_pattern, text, re.MULTILINE):
        date_str = match.group(1)
        description = match.group(2).strip()
        amount = -float(match.group(3).replace(',', ''))
        
        description = sanitize_description(description)
        
        transactions.append({
            'date': date_str,
            'description': description,
            'amount': amount,
            'account_type': 'savings',
            'account_number': account_num,
            'transaction_type': 'withdrawal'
        })
    
    # Process deposits
    for match in re.finditer(deposit_pattern, text, re.MULTILINE):
        date_str = match.group(1)
        description = match.group(2).strip()
        amount = float(match.group(3).replace(',', ''))
        
        # Skip if this is part of a withdrawal
        line = match.group(0)
        if '-' + match.group(3) in text[max(0, match.start()-50):match.end()+50]:
            continue
            
        description = sanitize_description(description)
        
        transactions.append({
            'date': date_str,
            'description': description,
            'amount': amount,
            'account_type': 'savings',
            'account_number': account_num,
            'transaction_type': 'deposit'
        })
    
    return transactions

def extract_credit_transactions(text, account_num=""):
    """
    Extract transactions from credit card statements
    
    Args:
        text (str): Full text extracted from PDF
        account_num (str): Masked account number for this statement
        
    Returns:
        list: List of transaction dictionaries
    """
    transactions = []
    
    # Clean up extracted PDF text
    text = re.sub(r'\s+', ' ', text)
    
    debug_print("  Trying to extract credit transactions...")
    
    patterns = [
        r'(\d{2}/\d{2})\s+(\d{2}/\d{2})\s+([A-Za-z0-9\*\-\'\s\.\,\(\)#]+?)\s+(\d{1,3}(?:,\d{3})*\.\d{2})',
        r'(\d{1,2}/\d{1,2}/\d{2,4})\s+([A-Za-z0-9\*\-\'\s\.\,\(\)#]+?)\s+(\d{1,3}(?:,\d{3})*\.\d{2})',
        r'(\d{1,2}/\d{1,2})\s+(.+?)\s+(\d{1,3}(?:,\d{3})*\.\d{2})'
    ]
    
    for i, pattern in enumerate(patterns):
        debug_print(f"  Trying pattern {i+1}...")
        matches = list(re.finditer(pattern, text, re.MULTILINE))
        debug_print(f"  Pattern {i+1} found {len(matches)} matches")
        
        if matches and i == 0:
            # Bank of America format with two dates
            for match in matches:
                trans_date = match.group(1)
                post_date = match.group(2)
                description = match.group(3).strip()
                amount = float(match.group(4).replace(',', ''))
                
                description = re.sub(r'\s+\d{4}\s+\d{4}\s*$', '', description)
                description = sanitize_description(description)
                
                if len(description) < 3:
                    continue
                
                transactions.append({
                    'date': post_date,
                    'transaction_date': trans_date,
                    'description': description,
                    'amount': amount,
                    'account_type': 'credit',
                    'account_number': account_num,
                    'transaction_type': 'purchase'
                })
        
        elif matches:
            # Other patterns
            for match in matches:
                if len(match.groups()) == 3:
                    date_str = match.group(1)
                    description = match.group(2).strip()
                    amount = float(match.group(3).replace(',', ''))
                    
                    description = sanitize_description(description)
                    
                    if len(description) < 3:
                        continue
                    
                    transactions.append({
                        'date': date_str,
                        'description': description,
                        'amount': amount,
                        'account_type': 'credit',
                        'account_number': account_num,
                        'transaction_type': 'purchase'
                    })
        
        if transactions:
            debug_print(f"  Found {len(transactions)} transactions with pattern {i+1}")
            break
    
    # Fallback: Line-by-line parsing
    if not transactions:
        debug_print("  Trying line-by-line parsing...")
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            
            if re.search(r'\d+\.\d{2}\s*$', line):
                date_match = re.search(r'^(\d{1,2}/\d{1,2}(?:/\d{2,4})?)', line)
                amount_match = re.search(r'(\d{1,3}(?:,\d{3})*\.\d{2})\s*$', line)
                
                if date_match and amount_match:
                    date_str = date_match.group(1)
                    amount = float(amount_match.group(1).replace(',', ''))
                    
                    desc_start = date_match.end()
                    desc_end = amount_match.start()
                    description = line[desc_start:desc_end].strip()
                    description = sanitize_description(description)
                    
                    if len(description) > 3:
                        transactions.append({
                            'date': date_str,
                            'description': description,
                            'amount': amount,
                            'account_type': 'credit',
                            'account_number': account_num,
                            'transaction_type': 'purchase'
                        })
                        
                        if len(transactions) <= 3:
                            debug_print(f"    Sample: {date_str} | {description} | ${amount}")
    
    debug_print(f"  Final result: {len(transactions)} transactions")
    return transactions

def process_statements(pdf_directory):
    """
    Main processing function - handles all PDFs in specified directory
    
    Args:
        pdf_directory (str): Path to directory containing PDF statements
        
    Returns:
        list: Combined list of all transactions from all processed PDFs
    """
    all_transactions = []
    
    if not os.path.exists(pdf_directory):
        print(f"Error: Directory {pdf_directory} does not exist!")
        return all_transactions
    
    pdf_files = [f for f in os.listdir(pdf_directory) if f.lower().endswith('.pdf')]
    
    if not pdf_files:
        print(f"Error: No PDF files found in {pdf_directory}")
        return all_transactions
    
    print(f"Processing {len(pdf_files)} PDF files...")
    
    for filename in pdf_files:
        file_path = os.path.join(pdf_directory, filename)
        debug_print(f"Processing: {filename}")
        
        text = extract_pdf_text(file_path)
        if not text:
            debug_print(f"  Could not extract text from {filename}")
            continue
        
        debug_print(f"  Extracted {len(text)} characters of text")
        
        # Extract statement period for date context
        statement_start, statement_end = extract_statement_period(text)
        if statement_start and statement_end:
            debug_print(f"  Statement period: {statement_start.strftime('%Y-%m-%d')} to {statement_end.strftime('%Y-%m-%d')}")
        else:
            debug_print("  Warning: Could not extract statement period")
        
        # Determine statement type from filename
        filename_lower = filename.lower()
        debug_print(f"  Filename (lowercase): {filename_lower}")
        
        if 'checking' in filename_lower or 'chk' in filename_lower:
            statement_type = 'checking'
            debug_print(f"  Detected as: {statement_type}")
            account_num = extract_account_number(text, 'checking')
            transactions = extract_checking_transactions(text, account_num)
        elif 'savings' in filename_lower or 'sav' in filename_lower:
            statement_type = 'savings'
            debug_print(f"  Detected as: {statement_type}")
            account_num = extract_account_number(text, 'savings')
            transactions = extract_savings_transactions(text, account_num)
        elif 'credit' in filename_lower:
            statement_type = 'credit'
            debug_print(f"  Detected as: {statement_type}")
            account_num = extract_account_number(text, 'credit')
            debug_print(f"  Account number found: {account_num}")
            transactions = extract_credit_transactions(text, account_num)
        else:
            debug_print(f"  Unknown statement type for {filename}, skipping...")
            continue
        
        if not transactions:
            debug_print("  No transactions found")
            if DEBUG_MODE:
                masked_sample = mask_sensitive_data(text[:500])
                debug_print("  Text sample (masked): " + repr(masked_sample))
        
        # Post-process transactions with proper date context
        for transaction in transactions:
            transaction['date'] = standardize_date(transaction['date'], statement_start, statement_end)
            
            if 'transaction_date' in transaction:
                transaction['transaction_date'] = standardize_date(transaction['transaction_date'], statement_start, statement_end)
            
            transaction['source_file'] = filename
            
            if DEBUG_MODE and statement_start and statement_end:
                transaction['statement_period'] = {
                    'start': statement_start.strftime('%Y-%m-%d'),
                    'end': statement_end.strftime('%Y-%m-%d')
                }
        
        all_transactions.extend(transactions)
        debug_print(f"  Extracted {len(transactions)} transactions")
    
    return all_transactions

def save_to_json(transactions, output_file='financial_transactions.json'):
    """
    Save extracted transactions to JSON file
    
    Args:
        transactions (list): List of transaction dictionaries
        output_file (str): Output filename
    """
    if not transactions:
        print("No transactions to save!")
        return
    
    sorted_transactions = sorted(transactions, key=lambda x: x['date'])
    
    output_data = {
        'metadata': {
            'total_transactions': len(sorted_transactions),
            'date_range': {
                'start': min(t['date'] for t in sorted_transactions),
                'end': max(t['date'] for t in sorted_transactions)
            },
            'generated_at': datetime.now().isoformat(),
            'account_types': list(set(t['account_type'] for t in sorted_transactions)),
            'accounts': list(set(t['account_number'] for t in sorted_transactions if t['account_number'])),
            'security_notice': 'Account numbers are masked showing only last 4 digits. Sensitive data has been sanitized.',
            'data_privacy': 'This file contains financial data. Handle securely and delete when no longer needed.'
        },
        'transactions': sorted_transactions
    }
    
    with open(output_file, 'w', encoding='utf-8') as jsonfile:
        json.dump(output_data, jsonfile, indent=2, ensure_ascii=False)
    
    print(f"Saved {len(transactions)} transactions to {output_file}")

def create_summary(transactions):
    """
    Generate and display summary statistics of extracted transactions
    
    Args:
        transactions (list): List of transaction dictionaries
    """
    if not transactions:
        return
    
    print("\n=== TRANSACTION SUMMARY ===")
    print(f"Total transactions: {len(transactions)}")
    
    dates = [t['date'] for t in transactions]
    print(f"Date range: {min(dates)} to {max(dates)}")
    
    account_types = {}
    transaction_types = {}
    amounts = []
    
    for t in transactions:
        acc_type = t['account_type']
        account_types[acc_type] = account_types.get(acc_type, 0) + 1
        
        trans_type = t.get('transaction_type', 'unknown')
        transaction_types[trans_type] = transaction_types.get(trans_type, 0) + 1
        
        amounts.append(t['amount'])
    
    print("\nBy Account Type:")
    for acc_type, count in account_types.items():
        print(f"  {acc_type}: {count}")
    
    print("\nBy Transaction Type:")
    for trans_type, count in transaction_types.items():
        print(f"  {trans_type}: {count}")
    
    print("\nAmount Statistics:")
    total_amount = sum(amounts)
    avg_amount = total_amount / len(amounts) if amounts else 0
    max_amount = max(amounts) if amounts else 0
    min_amount = min(amounts) if amounts else 0
    
    print(f"Total amount: ${total_amount:,.2f}")
    print(f"Average transaction: ${avg_amount:,.2f}")
    print(f"Largest transaction: ${max_amount:,.2f}")
    print(f"Smallest transaction: ${min_amount:,.2f}")

if __name__ == "__main__":
    """Main execution block"""
    pdf_directory = "."
    output_json = "financial_transactions.json"
    
    transactions = process_statements(pdf_directory)
    
    if transactions:
        save_to_json(transactions, output_json)
        create_summary(transactions)
        print(f"\nJSON file saved as: {output_json}")
    else:
        print("No transactions extracted. Please check your PDF files.")
        if DEBUG_MODE:
            print("\nTroubleshooting:")
            print("- Ensure PDF files contain 'checking', 'savings', or 'credit' in filename")
            print("- Check that PDFs are text-based (not scanned images)")
            print("- Set DEBUG_MODE = True at top of script for detailed output")