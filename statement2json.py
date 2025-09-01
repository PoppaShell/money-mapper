import pypdf
import re
import json
import os
from datetime import datetime
import pandas as pd

def extract_pdf_text(pdf_path):
    """Extract text from PDF file"""
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

def extract_checking_transactions(text, account_num=""):
    """Extract transactions from checking account statements"""
    transactions = []
    
    # Pattern for checking transactions (Date, Description, Amount)
    # Looking for patterns like: 07/22/24 PAYPAL DES:INST XFER... -5.99
    deposit_pattern = r'(\d{2}/\d{2}/\d{2,4})\s+([^-\d]*?)\s+(\d{1,3}(?:,\d{3})*\.\d{2})(?:\s|$)'
    withdrawal_pattern = r'(\d{2}/\d{2}/\d{2,4})\s+([^-\d]*?)\s+-(\d{1,3}(?:,\d{3})*\.\d{2})(?:\s|$)'
    
    # Find all withdrawals (negative amounts)
    for match in re.finditer(withdrawal_pattern, text, re.MULTILINE):
        date_str = match.group(1)
        description = match.group(2).strip()
        amount = -float(match.group(3).replace(',', ''))
        
        # Clean up description and convert to lowercase
        description = re.sub(r'\s+', ' ', description).lower().strip()
        
        transactions.append({
            'date': date_str,
            'description': description,
            'amount': amount,
            'account_type': 'checking',
            'account_number': account_num,
            'transaction_type': 'withdrawal'
        })
    
    # Find all deposits (positive amounts)
    for match in re.finditer(deposit_pattern, text, re.MULTILINE):
        date_str = match.group(1)
        description = match.group(2).strip()
        amount = float(match.group(3).replace(',', ''))
        
        # Skip if this looks like it's part of a withdrawal line
        line = match.group(0)
        if '-' + match.group(3) in text[max(0, match.start()-50):match.end()+50]:
            continue
            
        description = re.sub(r'\s+', ' ', description).lower().strip()
        
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
    """Extract transactions from savings account statements"""
    transactions = []
    
    # Pattern for savings transactions
    withdrawal_pattern = r'(\d{2}/\d{2}/\d{2,4})\s+([^-\d]*?)\s+-(\d{1,3}(?:,\d{3})*\.\d{2})(?:\s|$)'
    deposit_pattern = r'(\d{2}/\d{2}/\d{2,4})\s+([^-\d]*?)\s+(\d{1,3}(?:,\d{3})*\.\d{2})(?:\s|$)'
    
    # Find withdrawals
    for match in re.finditer(withdrawal_pattern, text, re.MULTILINE):
        date_str = match.group(1)
        description = match.group(2).strip()
        amount = -float(match.group(3).replace(',', ''))
        
        description = re.sub(r'\s+', ' ', description).lower().strip()
        
        transactions.append({
            'date': date_str,
            'description': description,
            'amount': amount,
            'account_type': 'savings',
            'account_number': account_num,
            'transaction_type': 'withdrawal'
        })
    
    # Find deposits
    for match in re.finditer(deposit_pattern, text, re.MULTILINE):
        date_str = match.group(1)
        description = match.group(2).strip()
        amount = float(match.group(3).replace(',', ''))
        
        # Skip if this is part of a withdrawal
        line = match.group(0)
        if '-' + match.group(3) in text[max(0, match.start()-50):match.end()+50]:
            continue
            
        description = re.sub(r'\s+', ' ', description).lower().strip()
        
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
    """Extract transactions from credit card statements"""
    transactions = []
    
    # Pattern for credit card transactions (Date, Post Date, Description, Amount)
    # Looking for patterns like: 03/22 03/25 HAMBURGER AND 183BRYAN TX 3126 1727 42.59
    credit_pattern = r'(\d{2}/\d{2})\s+(\d{2}/\d{2})\s+([^-\d]*?)\s+(\d{1,3}(?:,\d{3})*\.\d{2})(?:\s|$)'
    
    for match in re.finditer(credit_pattern, text, re.MULTILINE):
        trans_date = match.group(1)
        post_date = match.group(2)
        description = match.group(3).strip()
        amount = float(match.group(4).replace(',', ''))
        
        # Clean up description - remove reference numbers at the end and convert to lowercase
        description = re.sub(r'\s+\d{4}\s+\d{4}\s*$', '', description)
        description = re.sub(r'\s+', ' ', description).lower().strip()
        
        transactions.append({
            'date': post_date,  # Use post date as primary date
            'transaction_date': trans_date,
            'description': description,
            'amount': amount,  # Credit card purchases are positive in statements
            'account_type': 'credit',
            'account_number': account_num,
            'transaction_type': 'purchase'
        })
    
    return transactions

def standardize_date(date_str):
    """Standardize date format to YYYY-MM-DD"""
    try:
        # Handle MM/DD/YY and MM/DD/YYYY formats
        if '/' in date_str:
            parts = date_str.split('/')
            if len(parts) == 3:
                month, day, year = parts
                if len(year) == 2:
                    # Convert 2-digit year to 4-digit (assuming 2000s for now)
                    year = '20' + year
                return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
    except:
        pass
    return date_str

def extract_account_number(text, statement_type):
    """Extract account number from statement"""
    patterns = {
        'checking': r'Account #\s*(\d{4}\s+\d{4}\s+\d{4})',
        'savings': r'Account #\s*(\d{4}\s+\d{4}\s+\d{4})',
        'credit': r'Account #\s*(\d{4}\s+\d{4}\s+\d{4}\s+\d{4})'
    }
    
    pattern = patterns.get(statement_type, '')
    if not pattern:
        return ""
    
    match = re.search(pattern, text)
    return match.group(1).replace(' ', '') if match else ""

def process_statements(pdf_directory):
    """Process all PDF statements in directory"""
    all_transactions = []
    
    if not os.path.exists(pdf_directory):
        print(f"Directory {pdf_directory} does not exist!")
        return all_transactions
    
    pdf_files = [f for f in os.listdir(pdf_directory) if f.lower().endswith('.pdf')]
    
    if not pdf_files:
        print(f"No PDF files found in {pdf_directory}")
        return all_transactions
    
    for filename in pdf_files:
        file_path = os.path.join(pdf_directory, filename)
        print(f"Processing: {filename}")
        
        # Extract text from PDF
        text = extract_pdf_text(file_path)
        if not text:
            continue
        
        # Determine statement type from filename
        filename_lower = filename.lower()
        if 'checking' in filename_lower or 'chk' in filename_lower:
            statement_type = 'checking'
            account_num = extract_account_number(text, 'checking')
            transactions = extract_checking_transactions(text, account_num)
        elif 'savings' in filename_lower or 'sav' in filename_lower:
            statement_type = 'savings'
            account_num = extract_account_number(text, 'savings')
            transactions = extract_savings_transactions(text, account_num)
        elif 'credit' in filename_lower:
            statement_type = 'credit'
            account_num = extract_account_number(text, 'credit')
            transactions = extract_credit_transactions(text, account_num)
        else:
            print(f"  Unknown statement type for {filename}, skipping...")
            continue
        
        # Standardize dates
        for transaction in transactions:
            transaction['date'] = standardize_date(transaction['date'])
            transaction['source_file'] = filename
        
        all_transactions.extend(transactions)
        print(f"  Extracted {len(transactions)} transactions")
    
    return all_transactions

def save_to_json(transactions, output_file='financial_transactions.json'):
    """Save transactions to JSON file"""
    if not transactions:
        print("No transactions to save!")
        return
    
    # Sort transactions by date
    sorted_transactions = sorted(transactions, key=lambda x: x['date'])
    
    # Create output structure
    output_data = {
        'metadata': {
            'total_transactions': len(sorted_transactions),
            'date_range': {
                'start': min(t['date'] for t in sorted_transactions),
                'end': max(t['date'] for t in sorted_transactions)
            },
            'generated_at': datetime.now().isoformat(),
            'account_types': list(set(t['account_type'] for t in sorted_transactions)),
            'accounts': list(set(t['account_number'] for t in sorted_transactions if t['account_number']))
        },
        'transactions': sorted_transactions
    }
    
    with open(output_file, 'w', encoding='utf-8') as jsonfile:
        json.dump(output_data, jsonfile, indent=2, ensure_ascii=False)
    
    print(f"Saved {len(transactions)} transactions to {output_file}")

def save_to_csv(transactions, output_file='financial_transactions.csv'):
    """Save transactions to CSV file (legacy function, kept for compatibility)"""
    if not transactions:
        print("No transactions to save!")
        return
    
    # Define column order
    columns = [
        'date', 'description', 'amount', 'account_type', 
        'account_number', 'transaction_type', 'source_file'
    ]
    
    # Add credit card specific columns if they exist
    if any('transaction_date' in t for t in transactions):
        columns.insert(1, 'transaction_date')
    
    import csv
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=columns)
        writer.writeheader()
        
        # Sort transactions by date
        sorted_transactions = sorted(transactions, key=lambda x: x['date'])
        
        for transaction in sorted_transactions:
            # Only write columns that exist for this transaction
            row = {k: transaction.get(k, '') for k in columns}
            writer.writerow(row)
    
    print(f"Saved {len(transactions)} transactions to {output_file}")

def create_summary(transactions):
    """Create a summary of extracted transactions"""
    if not transactions:
        return
    
    df = pd.DataFrame(transactions)
    
    print("\n=== TRANSACTION SUMMARY ===")
    print(f"Total transactions: {len(transactions)}")
    print(f"Date range: {df['date'].min()} to {df['date'].max()}")
    
    print("\nBy Account Type:")
    print(df['account_type'].value_counts())
    
    print("\nBy Transaction Type:")
    if 'transaction_type' in df.columns:
        print(df['transaction_type'].value_counts())
    
    print("\nAmount Statistics:")
    print(f"Total amount: ${df['amount'].sum():,.2f}")
    print(f"Average transaction: ${df['amount'].mean():,.2f}")
    print(f"Largest transaction: ${df['amount'].max():,.2f}")
    print(f"Smallest transaction: ${df['amount'].min():,.2f}")

# Main execution
if __name__ == "__main__":
    # Directory containing PDF statements
    pdf_directory = "."  # Current directory, change as needed
    output_json = "financial_transactions.json"
    
    print("Financial Transaction Extractor")
    print("=" * 40)
    
    # Process all statements
    transactions = process_statements(pdf_directory)
    
    if transactions:
        # Save to JSON (primary format)
        save_to_json(transactions, output_json)
        
        # Create summary
        create_summary(transactions)
        
        print(f"\nJSON file saved as: {output_json}")
        print("You can now use this data for budgeting analysis!")
        
        # Optionally save CSV as well (uncomment if needed)
        # save_to_csv(transactions, "financial_transactions.csv")
        
    else:
        print("No transactions extracted. Please check your PDF files.")