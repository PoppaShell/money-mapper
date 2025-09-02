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
- File permissions automatically set to owner-only (600) for security
- Each transaction includes: date, description, amount, account type, transaction type

SECURITY FEATURES:
==================
- Account numbers masked (shows only last 4 digits: ****1234)
- Transaction descriptions sanitized (removes phone numbers, emails, reference numbers)
- Output file has restrictive permissions (owner read/write only)
- Debug output masks sensitive information
- Security reminders displayed to user

DEPENDENCIES:
=============
Required: pypdf (or PyPDF2), re, json, os, stat, datetime
Optional: pandas (for enhanced summary statistics)

Installation:
pip install pypdf pandas

USAGE:
======
1. Place PDF statements in same directory as script
2. Run: python3 financial_extractor.py
3. Review output in financial_transactions.json
4. Delete files when analysis complete

Last Updated: January 2025
"""

# Import required libraries
import pypdf
import re
import json
import os
import stat
from datetime import datetime
import pandas as pd

def extract_pdf_text(pdf_path):
    """
    Extract text content from PDF file using pypdf or PyPDF2
    
    Args:
        pdf_path (str): Path to the PDF file
        
    Returns:
        str: Extracted text from all pages, or empty string if extraction fails
        
    Notes:
        - Works with both pypdf and PyPDF2 libraries
        - Concatenates text from all pages with newlines
        - Some PDFs may have spacing issues in extracted text
        - Image-based PDFs will return minimal or no text
    """
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = pypdf.PdfReader(file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
        return text
    except Exception as e:
        print(f"Error reading PDF {pdf_path}: {e}")
        return ""

def mask_account_number(account_number):
    """
    Mask account number for security, showing only last 4 digits
    
    Args:
        account_number (str): Full account number (may include spaces/formatting)
        
    Returns:
        str: Masked account number (e.g., "************1234")
        
    Examples:
        "1234567890123456" -> "************3456"
        "1234 5678 9012" -> "********9012"
        "123" -> "***"
    """
    if not account_number:
        return ""
    
    # Remove any spaces or formatting characters
    clean_number = re.sub(r'\s+', '', account_number)
    
    if len(clean_number) >= 4:
        # Show last 4 digits with asterisks for the rest
        masked = '*' * (len(clean_number) - 4) + clean_number[-4:]
        return masked
    else:
        # If less than 4 digits, mask completely for security
        return '*' * len(clean_number)

def mask_sensitive_data(text):
    """
    Mask potentially sensitive information in text for debug output
    
    Args:
        text (str): Raw text that may contain sensitive information
        
    Returns:
        str: Text with sensitive patterns replaced with placeholders
        
    Masks:
        - Account numbers (16, 12, or 9 digit patterns)
        - SSN patterns (XXX-XX-XXXX or 9 consecutive digits)
        - Bank routing numbers (9 digits starting with 0-1)
        
    Used for: Safe debug output without exposing sensitive data
    """
    # Mask potential account numbers in debug output
    text = re.sub(r'\b\d{4}\s*\d{4}\s*\d{4}\s*\d{4}\b', '****-****-****-****', text)
    text = re.sub(r'\b\d{4}\s*\d{4}\s*\d{4}\b', '****-****-****', text)
    
    # Mask potential SSN patterns
    text = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '***-**-****', text)
    text = re.sub(r'\b\d{9}\b', '*********', text)
    
    # Mask potential routing numbers (9 digits starting with 0-1)
    text = re.sub(r'\b[01]\d{8}\b', '*********', text)
    
    return text

def secure_file_permissions(filepath):
    """
    Set restrictive file permissions on output files for security
    
    Args:
        filepath (str): Path to file that needs secure permissions
        
    Sets permissions to 600 (owner read/write only) on Unix-like systems
    Prints warning if permission setting fails (e.g., on Windows)
    
    Security rationale: Financial data should only be accessible to the file owner
    """
    try:
        # Set file permissions to owner read/write only (600)
        os.chmod(filepath, stat.S_IRUSR | stat.S_IWUSR)
        print(f"  Set secure permissions on {filepath}")
    except Exception as e:
        print(f"  Warning: Could not set secure permissions on {filepath}: {e}")

def sanitize_description(description):
    """
    Remove potentially sensitive information from transaction descriptions
    
    Args:
        description (str): Raw transaction description from PDF
        
    Returns:
        str: Cleaned description with sensitive data replaced by placeholders
        
    Sanitization process:
        1. Convert to lowercase for consistency
        2. Replace account numbers with [ACCOUNT]
        3. Replace long reference numbers with [REF#]
        4. Replace phone numbers with [PHONE]
        5. Replace email addresses with [EMAIL]
        6. Clean up extra whitespace
        
    Examples:
        "PAYPAL 555-123-4567 REF#12345678" -> "paypal [PHONE] [REF#]"
        "Transfer to 1234-5678-9012" -> "transfer to [ACCOUNT]"
    """
    # Convert to lowercase first for consistent formatting
    description = description.lower().strip()
    
    # Remove potential account numbers from descriptions
    description = re.sub(r'\b\d{4}\s*\d{4}\s*\d{4}\s*\d{4}\b', '[ACCOUNT]', description)
    description = re.sub(r'\b\d{4}\s*\d{4}\s*\d{4}\b', '[ACCOUNT]', description)
    
    # Remove potential confirmation numbers (8+ consecutive digits)
    description = re.sub(r'\b\d{8,}\b', '[REF#]', description)
    
    # Remove potential phone numbers (various formats)
    description = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE]', description)
    
    # Remove potential email patterns
    description = re.sub(r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b', '[EMAIL]', description)
    
    # Clean up multiple spaces created by replacements
    description = re.sub(r'\s+', ' ', description).strip()
    
    return description

def extract_checking_transactions(text, account_num=""):
    """
    Extract transactions from checking account statements
    
    Args:
        text (str): Full text extracted from PDF
        account_num (str): Masked account number for this statement
        
    Returns:
        list: List of transaction dictionaries with keys:
              - date: Transaction date (MM/DD/YYYY format)
              - description: Sanitized transaction description
              - amount: Transaction amount (negative for withdrawals, positive for deposits)
              - account_type: "checking"
              - account_number: Masked account number
              - transaction_type: "withdrawal" or "deposit"
              
    Regex patterns target Bank of America checking statement format:
        - Deposits: "MM/DD/YYYY DESCRIPTION AMOUNT"
        - Withdrawals: "MM/DD/YYYY DESCRIPTION -AMOUNT"
        
    Note: Some deposits may be filtered out if they appear near withdrawal amounts
          to avoid double-counting entries that show both positive and negative amounts
    """
    transactions = []
    
    # Regex patterns for checking account transactions
    # Matches: date (MM/DD/YYYY) + description + positive amount
    deposit_pattern = r'(\d{2}/\d{2}/\d{2,4})\s+([^-\d]*?)\s+(\d{1,3}(?:,\d{3})*\.\d{2})(?:\s|$)'
    # Matches: date (MM/DD/YYYY) + description + negative amount
    withdrawal_pattern = r'(\d{2}/\d{2}/\d{2,4})\s+([^-\d]*?)\s+-(\d{1,3}(?:,\d{3})*\.\d{2})(?:\s|$)'
    
    # Process withdrawals (negative amounts)
    for match in re.finditer(withdrawal_pattern, text, re.MULTILINE):
        date_str = match.group(1)
        description = match.group(2).strip()
        amount = -float(match.group(3).replace(',', ''))  # Convert to negative
        
        # Clean and sanitize description for security
        description = sanitize_description(description)
        
        transactions.append({
            'date': date_str,
            'description': description,
            'amount': amount,
            'account_type': 'checking',
            'account_number': account_num,
            'transaction_type': 'withdrawal'
        })
    
    # Process deposits (positive amounts)
    for match in re.finditer(deposit_pattern, text, re.MULTILINE):
        date_str = match.group(1)
        description = match.group(2).strip()
        amount = float(match.group(3).replace(',', ''))
        
        # Skip if this amount also appears as a withdrawal nearby (avoid duplicates)
        # This handles cases where statements show both +AMOUNT and -AMOUNT for same transaction
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
        list: List of transaction dictionaries (same format as checking)
        
    Similar to checking account extraction but typically simpler transaction patterns.
    Savings accounts usually have fewer transaction types:
        - Interest payments (deposits)
        - Transfers to/from other accounts
        - Fees (withdrawals)
        
    Uses same regex patterns as checking accounts since Bank of America
    uses consistent formatting across account types.
    """
    transactions = []
    
    # Same patterns as checking - Bank of America uses consistent formatting
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
        
        # Skip if this is part of a withdrawal (same duplicate avoidance as checking)
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
        list: List of transaction dictionaries with additional fields:
              - transaction_date: Original transaction date (for Bank of America format)
              - date: Posting date (primary date used for sorting)
              - All other fields same as checking/savings
              
    Credit card statements are more complex than bank accounts:
        - May have two dates per transaction (transaction date vs. posting date)
        - More varied merchant name formats
        - Reference numbers embedded in descriptions
        - Amounts are positive (purchases) rather than negative
        
    Extraction Strategy:
        1. Try multiple regex patterns of increasing flexibility
        2. Fall back to line-by-line parsing if regex fails
        3. Bank of America format: "MM/DD MM/DD MERCHANT AMOUNT"
        4. Generic formats: "MM/DD MERCHANT AMOUNT" or "MM/DD/YYYY MERCHANT AMOUNT"
        
    Handles PDF text extraction issues:
        - Extra spaces between characters
        - Inconsistent formatting
        - Multi-line merchant names
    """
    transactions = []
    
    # Clean up extracted PDF text - removes excessive whitespace that can break parsing
    text = re.sub(r'\s+', ' ', text)
    
    print("  Trying to extract credit transactions...")
    
    # Multiple regex patterns to handle different credit card statement formats
    # Pattern 1: Bank of America format with transaction and posting dates
    # Pattern 2: Generic format with full date
    # Pattern 3: Generic format with month/day only
    patterns = [
        r'(\d{2}/\d{2})\s+(\d{2}/\d{2})\s+([A-Za-z0-9\*\-\'\s\.\,\(\)#]+?)\s+(\d{1,3}(?:,\d{3})*\.\d{2})',
        r'(\d{1,2}/\d{1,2}/\d{2,4})\s+([A-Za-z0-9\*\-\'\s\.\,\(\)#]+?)\s+(\d{1,3}(?:,\d{3})*\.\d{2})',
        r'(\d{1,2}/\d{1,2})\s+(.+?)\s+(\d{1,3}(?:,\d{3})*\.\d{2})'
    ]
    
    # Try each pattern in order of specificity
    for i, pattern in enumerate(patterns):
        print(f"  Trying pattern {i+1}...")
        matches = list(re.finditer(pattern, text, re.MULTILINE))
        print(f"  Pattern {i+1} found {len(matches)} matches")
        
        if matches and i == 0:
            # Bank of America format with two dates (transaction date and posting date)
            for match in matches:
                trans_date = match.group(1)    # When transaction occurred
                post_date = match.group(2)     # When it posted to account
                description = match.group(3).strip()
                amount = float(match.group(4).replace(',', ''))
                
                # Clean up merchant description
                # Remove trailing reference numbers (common in credit card statements)
                description = re.sub(r'\s+\d{4}\s+\d{4}\s*$', '', description)
                description = sanitize_description(description)
                
                # Skip very short descriptions (likely parsing errors)
                if len(description) < 3:
                    continue
                
                transactions.append({
                    'date': post_date,  # Use posting date as primary date
                    'transaction_date': trans_date,
                    'description': description,
                    'amount': amount,  # Credit card amounts are positive (purchases)
                    'account_type': 'credit',
                    'account_number': account_num,
                    'transaction_type': 'purchase'
                })
        
        elif matches:
            # Handle other patterns (single date formats)
            for match in matches:
                if len(match.groups()) == 3:  # Date, description, amount
                    date_str = match.group(1)
                    description = match.group(2).strip()
                    amount = float(match.group(3).replace(',', ''))
                    
                    description = sanitize_description(description)
                    
                    # Skip very short descriptions
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
        
        # If we found transactions with this pattern, stop trying other patterns
        if transactions:
            print(f"  Found {len(transactions)} transactions with pattern {i+1}")
            break
    
    # Fallback: Line-by-line parsing if regex patterns failed
    # This handles PDFs with unusual formatting or spacing issues
    if not transactions:
        print("  Trying line-by-line parsing...")
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            
            # Look for lines ending with dollar amounts (likely transactions)
            if re.search(r'\d+\.\d{2}\s*$', line):
                # Try to find date at beginning of line
                date_match = re.search(r'^(\d{1,2}/\d{1,2}(?:/\d{2,4})?)', line)
                # Extract dollar amount at end of line
                amount_match = re.search(r'(\d{1,3}(?:,\d{3})*\.\d{2})\s*$', line)
                
                if date_match and amount_match:
                    date_str = date_match.group(1)
                    amount = float(amount_match.group(1).replace(',', ''))
                    
                    # Extract description (everything between date and amount)
                    desc_start = date_match.end()
                    desc_end = amount_match.start()
                    description = line[desc_start:desc_end].strip()
                    description = sanitize_description(description)
                    
                    if len(description) > 3:  # Valid description length
                        transactions.append({
                            'date': date_str,
                            'description': description,
                            'amount': amount,
                            'account_type': 'credit',
                            'account_number': account_num,
                            'transaction_type': 'purchase'
                        })
                        
                        # Show first few transactions found for debugging
                        if len(transactions) <= 3:
                            print(f"    Sample: {date_str} | {description} | ${amount}")
    
    print(f"  Final result: {len(transactions)} transactions")
    return transactions

def standardize_date(date_str):
    """
    Convert various date formats to standardized YYYY-MM-DD format
    
    Args:
        date_str (str): Date in various formats (MM/DD/YY, MM/DD/YYYY, MM/DD)
        
    Returns:
        str: Date in YYYY-MM-DD format, or original string if conversion fails
        
    Handles common date formats found in financial statements:
        - "03/25/24" -> "2024-03-25"
        - "03/25/2024" -> "2024-03-25" 
        - "03/25" -> "2025-03-25" (assumes current year)
        
    Important: 2-digit years are assumed to be 20XX (2000s)
    This assumption may need updating in the future for older statements
    """
    try:
        if '/' in date_str:
            parts = date_str.split('/')
            if len(parts) == 3:
                # Full date with year
                month, day, year = parts
                if len(year) == 2:
                    # Convert 2-digit year to 4-digit (assumes 2000s)
                    year = '20' + year
                return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
            elif len(parts) == 2:
                # Month/day only - assume current year
                month, day = parts
                year = str(datetime.now().year)
                return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
    except:
        # If any conversion fails, return original string
        pass
    return date_str

def extract_account_number(text, statement_type):
    """
    Extract and mask account number from statement text
    
    Args:
        text (str): Full PDF text content
        statement_type (str): "checking", "savings", or "credit"
        
    Returns:
        str: Masked account number showing only last 4 digits
        
    Account number patterns by type:
        - Checking/Savings: "Account # 1234 5678 9012" (12 digits)
        - Credit: "Account # 1234 5678 9012 3456" (16 digits)
        
    Security: Immediately masks the full number after extraction
    """
    # Define regex patterns for different account types
    patterns = {
        'checking': r'Account #\s*(\d{4}\s+\d{4}\s+\d{4})',      # 12-digit pattern
        'savings': r'Account #\s*(\d{4}\s+\d{4}\s+\d{4})',       # 12-digit pattern  
        'credit': r'Account #\s*(\d{4}\s+\d{4}\s+\d{4}\s+\d{4})'  # 16-digit pattern
    }
    
    pattern = patterns.get(statement_type, '')
    if not pattern:
        return ""
    
    match = re.search(pattern, text)
    if match:
        # Extract full number and immediately mask it for security
        full_number = match.group(1).replace(' ', '')
        return mask_account_number(full_number)
    return ""

def process_statements(pdf_directory):
    """
    Main processing function - handles all PDFs in specified directory
    
    Args:
        pdf_directory (str): Path to directory containing PDF statements
        
    Returns:
        list: Combined list of all transactions from all processed PDFs
        
    Processing workflow:
        1. Scan directory for PDF files
        2. For each PDF:
           a. Extract text using pypdf/PyPDF2
           b. Determine statement type from filename
           c. Extract account number and mask it
           d. Run appropriate extraction function
           e. Standardize dates and add metadata
        3. Return combined transaction list
        
    Statement type detection:
        - Files containing "checking" or "chk" -> checking account
        - Files containing "savings" or "sav" -> savings account  
        - Files containing "credit" -> credit card
        - Other files are skipped with warning
        
    Debug output:
        - Shows processing progress
        - Reports character count from PDF extraction
        - Shows masked text samples if no transactions found
        - Helps troubleshoot extraction issues
    """
    all_transactions = []
    
    # Validate directory exists
    if not os.path.exists(pdf_directory):
        print(f"Directory {pdf_directory} does not exist!")
        return all_transactions
    
    # Find all PDF files in directory
    pdf_files = [f for f in os.listdir(pdf_directory) if f.lower().endswith('.pdf')]
    
    if not pdf_files:
        print(f"No PDF files found in {pdf_directory}")
        return all_transactions
    
    # Process each PDF file
    for filename in pdf_files:
        file_path = os.path.join(pdf_directory, filename)
        print(f"Processing: {filename}")
        
        # Step 1: Extract text from PDF
        text = extract_pdf_text(file_path)
        if not text:
            print(f"  Could not extract text from {filename}")
            continue
        
        print(f"  Extracted {len(text)} characters of text")
        
        # Step 2: Determine statement type from filename
        filename_lower = filename.lower()
        print(f"  Filename (lowercase): {filename_lower}")
        
        # Route to appropriate extraction function based on filename
        if 'checking' in filename_lower or 'chk' in filename_lower:
            statement_type = 'checking'
            print(f"  Detected as: {statement_type}")
            account_num = extract_account_number(text, 'checking')
            transactions = extract_checking_transactions(text, account_num)
        elif 'savings' in filename_lower or 'sav' in filename_lower:
            statement_type = 'savings'
            print(f"  Detected as: {statement_type}")
            account_num = extract_account_number(text, 'savings')
            transactions = extract_savings_transactions(text, account_num)
        elif 'credit' in filename_lower:
            statement_type = 'credit'
            print(f"  Detected as: {statement_type}")
            account_num = extract_account_number(text, 'credit')
            print(f"  Account number found: {account_num}")
            transactions = extract_credit_transactions(text, account_num)
        else:
            print(f"  Unknown statement type for {filename}, skipping...")
            continue
        
        # Step 3: Show debug info if no transactions found
        if not transactions:
            print("  Text sample (first 500 chars, sensitive data masked):")
            masked_sample = mask_sensitive_data(text[:500])
            print("  " + repr(masked_sample))
        
        # Step 4: Post-process transactions
        for transaction in transactions:
            # Standardize date format
            transaction['date'] = standardize_date(transaction['date'])
            # Add source file for traceability
            transaction['source_file'] = filename
        
        # Add to master list
        all_transactions.extend(transactions)
        print(f"  Extracted {len(transactions)} transactions")
    
    return all_transactions

def save_to_json(transactions, output_file='financial_transactions.json'):
    """
    Save extracted transactions to JSON file with security features
    
    Args:
        transactions (list): List of transaction dictionaries
        output_file (str): Output filename (default: financial_transactions.json)
        
    JSON Structure:
        {
            "metadata": {
                "total_transactions": int,
                "date_range": {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"},
                "generated_at": "ISO timestamp",
                "account_types": ["checking", "savings", "credit"],
                "accounts": ["****1234", "****5678"],
                "security_notice": "Account numbers masked...",
                "data_privacy": "Handle securely..."
            },
            "transactions": [...]
        }
        
    Security Features:
        - Sets file permissions to owner-only (600)
        - Includes security notices in metadata
        - Reminds user about data handling best practices
        
    The JSON format makes it easy to:
        - Load into Python: json.load()
        - Import to pandas: pd.DataFrame(data['transactions'])
        - Query with JavaScript/Node.js
        - Import to Excel/Google Sheets
    """
    if not transactions:
        print("No transactions to save!")
        return
    
    # Sort transactions chronologically for better usability
    sorted_transactions = sorted(transactions, key=lambda x: x['date'])
    
    # Build comprehensive metadata
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
    
    # Write JSON file with proper formatting
    with open(output_file, 'w', encoding='utf-8') as jsonfile:
        json.dump(output_data, jsonfile, indent=2, ensure_ascii=False)
    
    # Apply secure file permissions (Unix/Linux/macOS)
    secure_file_permissions(output_file)
    
    print(f"Saved {len(transactions)} transactions to {output_file}")
    print("  File permissions set to owner-only access for security")

def create_summary(transactions):
    """
    Generate and display summary statistics of extracted transactions
    
    Args:
        transactions (list): List of transaction dictionaries
        
    Displays:
        - Total transaction count
        - Date range covered
        - Breakdown by account type (checking/savings/credit)
        - Breakdown by transaction type (deposit/withdrawal/purchase)
        - Amount statistics (total, average, min, max)
        
    Used for: Quick validation that extraction worked correctly and
              overview of the financial data for analysis planning
    """
    if not transactions:
        return
    
    print("\n=== TRANSACTION SUMMARY ===")
    print(f"Total transactions: {len(transactions)}")
    
    # Calculate date range manually (works without pandas)
    dates = [t['date'] for t in transactions]
    print(f"Date range: {min(dates)} to {max(dates)}")
    
    # Count transactions by category
    account_types = {}
    transaction_types = {}
    amounts = []
    
    for t in transactions:
        # Count by account type
        acc_type = t['account_type']
        account_types[acc_type] = account_types.get(acc_type, 0) + 1
        
        # Count by transaction type
        trans_type = t.get('transaction_type', 'unknown')
        transaction_types[trans_type] = transaction_types.get(trans_type, 0) + 1
        
        # Collect amounts for statistics
        amounts.append(t['amount'])
    
    # Display breakdowns
    print("\nBy Account Type:")
    for acc_type, count in account_types.items():
        print(f"  {acc_type}: {count}")
    
    print("\nBy Transaction Type:")
    for trans_type, count in transaction_types.items():
        print(f"  {trans_type}: {count}")
    
    # Calculate and display amount statistics
    print("\nAmount Statistics:")
    total_amount = sum(amounts)
    avg_amount = total_amount / len(amounts) if amounts else 0
    max_amount = max(amounts) if amounts else 0
    min_amount = min(amounts) if amounts else 0
    
    print(f"Total amount: ${total_amount:,.2f}")
    print(f"Average transaction: ${avg_amount:,.2f}")
    print(f"Largest transaction: ${max_amount:,.2f}")
    print(f"Smallest transaction: ${min_amount:,.2f}")

# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    """
    Main execution block - runs when script is executed directly
    
    Configuration:
        - pdf_directory: Where to look for PDF files (default: current directory)
        - output_json: Name of output file (default: financial_transactions.json)
        
    Execution Flow:
        1. Display security features and warnings
        2. Process all PDF statements in directory
        3. Save results to JSON with secure permissions
        4. Display summary statistics
        5. Show security reminders
        
    For Production Use:
        - Consider adding command-line argument parsing
        - Add configuration file support
        - Implement logging instead of print statements
        - Add data validation and error recovery
    """
    # Configuration - modify these as needed
    pdf_directory = "."  # Current directory
    output_json = "financial_transactions.json"
    
    # Display startup information
    print("Financial Transaction Extractor")
    print("=" * 40)
    print("Security Features Enabled:")
    print("- Account numbers masked (show last 4 digits only)")
    print("- Sensitive data sanitized from descriptions")
    print("- Secure file permissions on output")
    print("- Debug output masked for security")
    print("=" * 40)
    
    # Main processing
    transactions = process_statements(pdf_directory)
    
    if transactions:
        # Save results
        save_to_json(transactions, output_json)
        
        # Show summary
        create_summary(transactions)
        
        # Final instructions
        print(f"\nJSON file saved as: {output_json}")
        print("SECURITY REMINDER:")
        print("- Output file contains financial data")
        print("- File permissions set to owner-only")
        print("- Delete file when analysis is complete")
        print("- Do not share or commit to version control")
        
    else:
        print("No transactions extracted. Please check your PDF files.")
        print("\nTroubleshooting:")
        print("- Ensure PDF files contain 'checking', 'savings', or 'credit' in filename")
        print("- Check that PDFs are text-based (not scanned images)")
        print("- Review debug output above for extraction issues")

# ============================================================================
# USAGE EXAMPLES AND NEXT STEPS
# ============================================================================

"""
USAGE EXAMPLES:
===============

1. Basic Usage:
   python3 financial_extractor.py

2. Loading Results in Python:
   import json
   with open('financial_transactions.json', 'r') as f:
       data = json.load(f)
   
   transactions = data['transactions']
   metadata = data['metadata']

3. Converting to Pandas DataFrame:
   import pandas as pd
   df = pd.DataFrame(transactions)
   
   # Filter by account type
   credit_txns = df[df['account_type'] == 'credit']
   
   # Group by month
   df['month'] = pd.to_datetime(df['date']).dt.to_period('M')
   monthly_spending = df.groupby('month')['amount'].sum()

4. Budget Analysis Examples:
   # Find top spending categories (would need to categorize descriptions first)
   # Calculate monthly averages
   # Identify unusual spending patterns
   # Track spending trends over time

EXTENDING THE SCRIPT:
=====================

1. Add New Bank Formats:
   - Create new extraction functions for different banks
   - Modify account number patterns in extract_account_number()
   - Update filename detection logic

2. Add Transaction Categorization:
   - Create categorize_transaction() function
   - Use keyword matching or ML for category assignment
   - Add category field to transaction objects

3. Add Data Validation:
   - Check for duplicate transactions
   - Validate date ranges
   - Flag unusual amounts or patterns

4. Add Export Formats:
   - CSV export function
   - Excel export with formatting
   - QIF/OFX formats for financial software

5. Add Configuration:
   - Config file for bank-specific settings
   - Command-line arguments for directories
   - Environment variables for sensitive settings

SECURITY CONSIDERATIONS:
========================

1. Data Storage:
   - Consider encrypting output files
   - Use secure deletion tools when finished
   - Store files on encrypted drives

2. Processing Environment:
   - Run in isolated containers or VMs
   - Use secure, temporary directories
   - Clear memory after processing

3. Code Security:
   - Regular dependency updates
   - Input validation for file paths
   - Secure error handling (no sensitive data in logs)

4. Compliance:
   - Consider data retention policies
   - Log access for audit trails
   - Follow organizational security policies
"""