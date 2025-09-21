#!/usr/bin/env python3
"""
Bank Statement Parser - Extract transactions from PDF statements.

This module parses Bank of America PDF statements (checking, savings, credit) 
and extracts transaction data into structured format. Supports automatic
statement type detection and handles multiple date formats.
"""

import os
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from utils import (
    load_config, extract_pdf_text, sanitize_description, standardize_date,
    extract_statement_period, mask_account_number, debug_print, get_pdf_files
)


def detect_statement_type(text: str, detection_config: Dict) -> Optional[str]:
    """
    Detect statement type (checking, savings, credit) based on text content.
    
    Uses scoring system with indicators and strong indicators to determine
    the most likely statement type from the PDF content.
    
    Args:
        text: Full text content from PDF
        detection_config: Detection configuration from TOML file
        
    Returns:
        Statement type string ('checking', 'savings', 'credit') or None
    """
    text_lower = text.lower()
    scores = {}
    
    # Calculate scores for each statement type
    for statement_type, config in detection_config.items():
        score = 0
        
        # Check regular indicators
        for indicator in config['indicators']:
            if indicator in text_lower:
                score += config['weight']
        
        # Check strong indicators with higher weights
        for indicator, weight in config['strong_indicators'].items():
            if indicator in text_lower:
                score += weight
                debug_print(f"  Found '{indicator}' - strong {statement_type} indicator")
        
        scores[statement_type] = score
    
    debug_print(f"  Detection scores - {scores}")
    
    # Return type with highest score
    if scores:
        max_score = max(scores.values())
        if max_score > 0:
            return max(scores, key=scores.get)
    
    return None


def extract_account_number(text: str, statement_type: str, patterns: Dict) -> str:
    """
    Extract and mask account number from statement text.
    
    Args:
        text: Full text content from PDF
        statement_type: Type of statement (checking, savings, credit)
        patterns: Account number regex patterns from config
        
    Returns:
        Masked account number string
    """
    pattern = patterns.get(statement_type, '')
    if pattern:
        match = re.search(pattern, text)
        if match:
            full_number = match.group(1).replace(' ', '')
            return mask_account_number(full_number)
    return ""


def extract_checking_transactions(text: str, account_num: str, 
                                 patterns: Dict, sanitization_patterns: List) -> List[Dict]:
    """
    Extract transactions from checking account statements.
    
    Parses both deposits and withdrawals sections using enhanced patterns
    that handle multi-line transaction descriptions.
    
    Args:
        text: Full text content from PDF
        account_num: Masked account number
        patterns: Transaction section patterns from config
        sanitization_patterns: Text sanitization patterns from config
        
    Returns:
        List of transaction dictionaries
    """
    transactions = []
    debug_print("  === PARSING CHECKING TRANSACTIONS ===")
    
    # Extract deposits section
    deposits_pattern = patterns['deposits']
    deposits_match = re.search(deposits_pattern, text, re.DOTALL | re.IGNORECASE)
    
    if deposits_match:
        deposits_section = deposits_match.group(0)
        debug_print(f"  Found deposits section: {len(deposits_section)} characters")
        
        # Split by date patterns
        parts = re.split(r'(\d{2}/\d{2}/\d{2,4})', deposits_section)
        debug_print(f"  Split deposits into {len(parts)} parts")
        
        # Process each date + content pair
        for i in range(1, len(parts), 2):
            if i + 1 < len(parts):
                date_str = parts[i].strip()
                content = parts[i + 1]
                
                # Find amount at end of content
                amount_match = re.search(r'(\d{1,3}(?:,\d{3})*\.\d{2})(?=\s*(?:\d{2}/\d{2}|Total|$))', content)
                
                if amount_match:
                    amount_str = amount_match.group(1)
                    description = content[:amount_match.start()].strip()
                    description = re.sub(r'\s+', ' ', description)
                    description = sanitize_description(description, sanitization_patterns)
                    
                    if description:
                        try:
                            amount = float(amount_str.replace(',', ''))
                            transactions.append({
                                'transaction_date': date_str,
                                'description': description,
                                'amount': amount,
                                'account_type': 'checking',
                                'account_number': account_num,
                                'transaction_type': 'deposit'
                            })
                            debug_print(f"    ✓ DEPOSIT: {date_str} | {description[:40]}... | ${amount}")
                        except ValueError as e:
                            debug_print(f"    ✗ Amount parse error: {e}")
    else:
        debug_print("  ✗ No deposits section found")
    
    # Extract withdrawals section
    withdrawals_pattern = patterns['withdrawals']
    withdrawals_match = re.search(withdrawals_pattern, text, re.DOTALL | re.IGNORECASE)
    
    if withdrawals_match:
        withdrawals_section = withdrawals_match.group(0)
        debug_print(f"  Found withdrawals section: {len(withdrawals_section)} characters")
        
        # Split by date patterns
        parts = re.split(r'(\d{2}/\d{2}/\d{2,4})', withdrawals_section)
        debug_print(f"  Split withdrawals into {len(parts)} parts")
        
        # Process each date + content pair
        for i in range(1, len(parts), 2):
            if i + 1 < len(parts):
                date_str = parts[i].strip()
                content = parts[i + 1]
                
                # Find amount at end of content
                amount_match = re.search(r'(\d{1,3}(?:,\d{3})*\.\d{2})(?=\s*(?:\d{2}/\d{2}|Total|$))', content)
                
                if amount_match:
                    amount_str = amount_match.group(1)
                    description = content[:amount_match.start()].strip()
                    description = re.sub(r'\s+', ' ', description)
                    description = sanitize_description(description, sanitization_patterns)
                    
                    if description:
                        try:
                            amount = -float(amount_str.replace(',', ''))
                            transactions.append({
                                'transaction_date': date_str,
                                'description': description,
                                'amount': amount,
                                'account_type': 'checking',
                                'account_number': account_num,
                                'transaction_type': 'withdrawal'
                            })
                            debug_print(f"    ✓ WITHDRAWAL: {date_str} | {description[:40]}... | ${amount}")
                        except ValueError as e:
                            debug_print(f"    ✗ Amount parse error: {e}")
    else:
        debug_print("  ✗ No withdrawals section found")
    
    debug_print(f"  === TOTAL CHECKING TRANSACTIONS: {len(transactions)} ===")
    return transactions


def extract_savings_transactions(text: str, account_num: str, 
                                patterns: Dict, sanitization_patterns: List) -> List[Dict]:
    """
    Extract transactions from savings account statements.
    
    Uses the same proven method as checking transactions but adapted
    for savings account statement structure.
    
    Args:
        text: Full text content from PDF
        account_num: Masked account number
        patterns: Transaction section patterns from config
        sanitization_patterns: Text sanitization patterns from config
        
    Returns:
        List of transaction dictionaries
    """
    transactions = []
    debug_print("  === PARSING SAVINGS TRANSACTIONS ===")
    
    # Extract deposits section (same as checking)
    deposits_pattern = patterns['deposits']
    deposits_match = re.search(deposits_pattern, text, re.DOTALL | re.IGNORECASE)
    
    if deposits_match:
        deposits_section = deposits_match.group(0)
        debug_print(f"  Found deposits section: {len(deposits_section)} characters")
        
        # Split by date patterns (same approach as checking)
        parts = re.split(r'(\d{2}/\d{2}/\d{2,4})', deposits_section)
        debug_print(f"  Split deposits into {len(parts)} parts")
        
        # Process each date + content pair (same as checking)
        for i in range(1, len(parts), 2):
            if i + 1 < len(parts):
                date_str = parts[i].strip()
                content = parts[i + 1]
                
                # Find amount at end (same as checking)
                amount_match = re.search(r'(\d{1,3}(?:,\d{3})*\.\d{2})(?=\s*(?:\d{2}/\d{2}|Total|$))', content)
                
                if amount_match:
                    amount_str = amount_match.group(1)
                    description = content[:amount_match.start()].strip()
                    description = re.sub(r'\s+', ' ', description)
                    description = sanitize_description(description, sanitization_patterns)
                    
                    if description:
                        try:
                            amount = float(amount_str.replace(',', ''))
                            transactions.append({
                                'transaction_date': date_str,
                                'description': description,
                                'amount': amount,
                                'account_type': 'savings',
                                'account_number': account_num,
                                'transaction_type': 'deposit'
                            })
                            debug_print(f"    ✓ DEPOSIT: {date_str} | {description[:40]}... | ${amount}")
                        except ValueError as e:
                            debug_print(f"    ✗ Amount parse error: {e}")
    else:
        debug_print("  ✗ No deposits section found")
    
    # Extract withdrawals section
    withdrawals_pattern = patterns['withdrawals']
    withdrawals_match = re.search(withdrawals_pattern, text, re.DOTALL | re.IGNORECASE)
    
    if withdrawals_match:
        withdrawals_section = withdrawals_match.group(0)
        debug_print(f"  Found withdrawals section: {len(withdrawals_section)} characters")
        
        # Split by date patterns
        parts = re.split(r'(\d{2}/\d{2}/\d{2,4})', withdrawals_section)
        debug_print(f"  Split withdrawals into {len(parts)} parts")
        
        # Process each date + content pair
        for i in range(1, len(parts), 2):
            if i + 1 < len(parts):
                date_str = parts[i].strip()
                content = parts[i + 1]
                
                # Find amount at end
                amount_match = re.search(r'(\d{1,3}(?:,\d{3})*\.\d{2})(?=\s*(?:\d{2}/\d{2}|Total|$))', content)
                
                if amount_match:
                    amount_str = amount_match.group(1)
                    description = content[:amount_match.start()].strip()
                    description = re.sub(r'\s+', ' ', description)
                    description = sanitize_description(description, sanitization_patterns)
                    
                    if description:
                        try:
                            amount = -float(amount_str.replace(',', ''))
                            transactions.append({
                                'transaction_date': date_str,
                                'description': description,
                                'amount': amount,
                                'account_type': 'savings',
                                'account_number': account_num,
                                'transaction_type': 'withdrawal'
                            })
                            debug_print(f"    ✓ WITHDRAWAL: {date_str} | {description[:40]}... | ${amount}")
                        except ValueError as e:
                            debug_print(f"    ✗ Amount parse error: {e}")
    else:
        debug_print("  ✗ No withdrawals section found")
    
    debug_print(f"  === TOTAL SAVINGS TRANSACTIONS: {len(transactions)} ===")
    return transactions


def extract_credit_transactions(text: str, account_num: str, 
                               patterns: List, sanitization_patterns: List) -> List[Dict]:
    """
    Extract transactions from credit card statements.
    
    Credit card statements have different format with posting_date and 
    transaction_date fields. This function preserves both dates.
    
    Args:
        text: Full text content from PDF
        account_num: Masked account number
        patterns: List of regex patterns for credit transactions
        sanitization_patterns: Text sanitization patterns from config
        
    Returns:
        List of transaction dictionaries
    """
    transactions = []
    text = re.sub(r'\s+', ' ', text)
    debug_print("  === PARSING CREDIT TRANSACTIONS ===")
    
    for pattern in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            try:
                if len(match) == 4:
                    # Pattern with posting and transaction dates
                    posting_date, transaction_date, description, amount_str = match
                    
                    # Clean description and amount
                    description = description.strip()
                    description = sanitize_description(description, sanitization_patterns)
                    amount = float(amount_str.replace(',', ''))
                    
                    if description and amount > 0:
                        transactions.append({
                            'posting_date': posting_date,
                            'transaction_date': transaction_date,
                            'description': description,
                            'amount': amount,
                            'account_type': 'credit',
                            'account_number': account_num,
                            'transaction_type': 'purchase'
                        })
                        debug_print(f"    ✓ CREDIT: {posting_date}/{transaction_date} | {description[:40]}... | ${amount}")
                
                elif len(match) == 3:
                    # Pattern with single date
                    date_str, description, amount_str = match
                    
                    # Clean description and amount
                    description = description.strip()
                    description = sanitize_description(description, sanitization_patterns)
                    amount = float(amount_str.replace(',', ''))
                    
                    if description and amount > 0:
                        transactions.append({
                            'transaction_date': date_str,
                            'description': description,
                            'amount': amount,
                            'account_type': 'credit',
                            'account_number': account_num,
                            'transaction_type': 'purchase'
                        })
                        debug_print(f"    ✓ CREDIT: {date_str} | {description[:40]}... | ${amount}")
                        
            except (ValueError, IndexError) as e:
                debug_print(f"    ✗ Credit transaction parse error: {e}")
                continue
    
    debug_print(f"  === TOTAL CREDIT TRANSACTIONS: {len(transactions)} ===")
    return transactions


def process_pdf_statements(pdf_directory: str = "statements", debug_mode: bool = False) -> List[Dict]:
    """
    Process all PDF statements in directory and extract transactions.
    
    Main function that orchestrates the entire statement processing workflow:
    1. Load configuration files
    2. Find and process PDF files
    3. Detect statement types
    4. Extract transactions
    5. Standardize dates and add metadata
    
    Args:
        pdf_directory: Directory containing PDF statement files
        debug_mode: Enable detailed debug output
        
    Returns:
        List of all extracted transactions across all statements
    """
    # Load configuration
    try:
        patterns_config = load_config('config/statement_patterns.toml')
    except Exception as e:
        print(f"Failed to load configuration: {e}")
        return []
    
    all_transactions = []
    
    # Get PDF files
    pdf_files = get_pdf_files(pdf_directory)
    if not pdf_files:
        print(f"No PDF files found in {pdf_directory}")
        return []
    
    print(f"Processing {len(pdf_files)} PDF files...")
    
    for file_path in pdf_files:
        filename = os.path.basename(file_path)
        debug_print(f"Processing: {filename}", debug_mode)
        
        # Extract text from PDF
        text = extract_pdf_text(file_path)
        if not text:
            debug_print(f"  Could not extract text from {filename}", debug_mode)
            continue
        
        debug_print(f"  Extracted {len(text)} characters of text", debug_mode)
        
        # Extract statement period
        statement_start, statement_end = extract_statement_period(
            text, 
            patterns_config['statement_period']['patterns'],
            patterns_config['statement_period']['month_names']
        )
        
        if statement_start and statement_end:
            debug_print(f"  Statement period: {statement_start.strftime('%Y-%m-%d')} to {statement_end.strftime('%Y-%m-%d')}", debug_mode)
        
        # Detect statement type
        statement_type = detect_statement_type(text, patterns_config['detection'])
        if not statement_type:
            debug_print(f"  Could not detect statement type for {filename}, skipping...", debug_mode)
            continue
        
        debug_print(f"  Detected statement type: {statement_type}", debug_mode)
        
        # Extract account number
        account_num = extract_account_number(text, statement_type, patterns_config['account_patterns'])
        debug_print(f"  Account number: {account_num}", debug_mode)
        
        # Extract transactions based on statement type
        if statement_type == 'checking':
            transactions = extract_checking_transactions(
                text, account_num, 
                patterns_config['transaction_sections']['checking'],
                patterns_config['text_sanitization']['patterns']
            )
        elif statement_type == 'savings':
            transactions = extract_savings_transactions(
                text, account_num,
                patterns_config['transaction_sections']['savings'],
                patterns_config['text_sanitization']['patterns']
            )
        elif statement_type == 'credit':
            transactions = extract_credit_transactions(
                text, account_num,
                patterns_config['transaction_sections']['credit']['patterns'],
                patterns_config['text_sanitization']['patterns']
            )
        else:
            debug_print(f"  Unknown statement type: {statement_type}, skipping...", debug_mode)
            continue
        
        if not transactions:
            debug_print("  No transactions found", debug_mode)
        
        # Standardize dates and add metadata
        for transaction in transactions:
            if 'transaction_date' in transaction:
                transaction['transaction_date'] = standardize_date(
                    transaction['transaction_date'], statement_start, statement_end
                )
            if 'posting_date' in transaction:
                transaction['posting_date'] = standardize_date(
                    transaction['posting_date'], statement_start, statement_end
                )
            
            transaction['source_file'] = filename
        
        all_transactions.extend(transactions)
        debug_print(f"  Extracted {len(transactions)} transactions", debug_mode)
    
    return all_transactions


if __name__ == "__main__":
    # Simple command line usage
    import sys
    
    directory = sys.argv[1] if len(sys.argv) > 1 else "statements"
    debug = "--debug" in sys.argv
    
    from utils import ensure_directories_exist
    ensure_directories_exist()
    
    transactions = process_pdf_statements(directory, debug)
    
    if transactions:
        from utils import save_transactions_to_json
        save_transactions_to_json(transactions, "output/financial_transactions.json")
        print(f"Successfully processed {len(transactions)} transactions")
    else:
        print("No transactions found")