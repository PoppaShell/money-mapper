#!/usr/bin/env python3
"""
Statement Parser - PDF Bank Statement Processing.

This module parses PDF bank statements and extracts transaction information
using configurable patterns and rules defined in statement_patterns.toml.
"""

import os
import re
import sys
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Add the src directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import extract_pdf_text, standardize_date, sanitize_description, load_config
from config_manager import get_config_manager


def load_statement_patterns(config_dir: str = "config") -> Dict:
    """
    Load statement parsing patterns from centralized configuration.

    Args:
        config_dir: Configuration directory

    Returns:
        Dictionary containing statement patterns
    """
    try:
        config_manager = get_config_manager(config_dir)
        patterns_file = config_manager.get_file_path('statement_patterns')
        return load_config(patterns_file)
    except Exception as e:
        print(f"Error loading statement patterns: {e}")
        sys.exit(1)


def normalize_whitespace(text: str) -> str:
    """
    Normalize whitespace in text by replacing multiple consecutive spaces with a single space.

    Args:
        text: Text to normalize

    Returns:
        Text with normalized whitespace
    """
    # Replace multiple spaces with single space
    normalized = re.sub(r'\s+', ' ', text)
    # Strip leading/trailing whitespace
    return normalized.strip()


def process_pdf_statements(directory: str, debug: bool = False) -> List[Dict]:
    """
    Process all PDF files in a directory and extract transactions.
    
    Args:
        directory: Directory containing PDF files
        debug: Enable debug output
        
    Returns:
        List of transaction dictionaries
    """
    # Load configuration using config manager
    config = load_statement_patterns()
    
    if debug:
        print("\n=== Statement Parser Debug Mode ===")
        print(f"Configuration loaded successfully")
        print(f"Available statement types: {list(config.get('detection', {}).keys())}")
    
    # Get PDF files
    pdf_files = []
    try:
        pdf_files = [
            os.path.join(directory, f) 
            for f in os.listdir(directory) 
            if f.lower().endswith('.pdf')
        ]
        pdf_files.sort()  # Process in consistent order
    except FileNotFoundError:
        print(f"Error: Directory '{directory}' not found")
        return []
    except PermissionError:
        print(f"Error: Permission denied accessing directory '{directory}'")
        return []
    
    if not pdf_files:
        print(f"No PDF files found in '{directory}'")
        return []
    
    print(f"Found {len(pdf_files)} PDF files to process")

    all_transactions = []

    for i, pdf_file in enumerate(pdf_files, 1):
        # Show progress bar (suppressed in debug mode to avoid clutter)
        if not debug:
            from utils import show_progress
            show_progress(i, len(pdf_files))

        if debug:
            print(f"\n{'='*60}")
            print(f"Processing file {i}/{len(pdf_files)}: {os.path.basename(pdf_file)}")
            print(f"{'='*60}")

        try:
            # Extract text from PDF
            text = extract_pdf_text(pdf_file)
            
            if debug:
                print(f"Text extraction:")
                print(f"  Total characters extracted: {len(text)}")
                print(f"  Total lines: {len(text.splitlines())}")
                if text:
                    print(f"  First 300 characters:")
                    print(f"  {repr(text[:300])}")
                else:
                    print(f"  WARNING: No text extracted!")
            
            if not text:
                print(f"Warning: Could not extract text from {pdf_file}")
                continue
            
            # Parse transactions from text
            transactions = parse_statement_text(text, config, debug)
            
            # Add file metadata to each transaction
            for transaction in transactions:
                transaction['source_file'] = os.path.basename(pdf_file)
            
            all_transactions.extend(transactions)
            
            if debug:
                print(f"\nResult: Extracted {len(transactions)} transactions from this file")

        except Exception as e:
            print(f"Error processing {pdf_file}: {e}")
            if debug:
                import traceback
                traceback.print_exc()
            continue

    # Print newline after progress bar
    if not debug:
        print()

    print(f"\nTotal transactions extracted: {len(all_transactions)}")
    return all_transactions


def parse_statement_text(text: str, config: Dict, debug: bool = False) -> List[Dict]:
    """
    Parse transaction data from statement text using configuration patterns.
    
    Args:
        text: Raw text extracted from PDF
        config: Statement parsing configuration
        debug: Enable debug output
        
    Returns:
        List of transaction dictionaries
    """
    if debug:
        print(f"\n--- Starting Transaction Parsing ---")
    
    # Step 1: Detect statement type
    statement_type = detect_statement_type(text, config.get('detection', {}), debug)
    
    if not statement_type:
        if debug:
            print(f"ERROR: Could not detect statement type")
            print(f"This means none of the detection patterns matched the PDF text")
            print(f"Check your statement_patterns.toml [detection] section")
        return []
    
    if debug:
        print(f"\nSUCCESS: Detected statement type: {statement_type}")

    # Step 2: Extract statement period (for year information)
    period_config = config.get('period_patterns', {})
    statement_period = extract_statement_period(text, period_config)
    if debug and statement_period:
        print(f"Statement period: {statement_period}")

    # Step 2.5: Extract account number
    account_patterns = config.get('account_patterns', {})
    account_number = extract_account_number(text, account_patterns, debug)
    masked_account = None
    if account_number:
        masked_account = mask_account_number(account_number)
        if debug:
            print(f"Account number extracted and masked: {masked_account}")

    # Step 3: Extract transactions based on statement type
    transaction_patterns = config.get('transaction_sections', {})
    if statement_type not in transaction_patterns:
        if debug:
            print(f"ERROR: No transaction patterns configured for '{statement_type}'")
            print(f"Available patterns: {list(transaction_patterns.keys())}")
        return []
    
    patterns = transaction_patterns[statement_type]
    if debug:
        print(f"\nTransaction extraction patterns for '{statement_type}':")
        print(f"  Available sections: {list(patterns.keys())}")
    
    transactions = []

    if statement_type == 'credit':
        transactions = extract_credit_transactions(text, patterns, debug, statement_period)
    elif statement_type in ['checking', 'savings']:
        transactions = extract_banking_transactions(text, patterns, debug)
    else:
        if debug:
            print(f"ERROR: Unknown statement type '{statement_type}'")
    
    # Step 4: Add metadata (no redaction at parse time - that happens during enrichment)
    for transaction in transactions:
        # Add account type to identify which statement this came from
        transaction['account_type'] = statement_type

        # Add masked account number if available
        # For credit cards: use account_suffix (from transaction line) instead of account_number (from header)
        # For checking/savings: use account_number (they don't have per-transaction suffix)
        if masked_account and statement_type != 'credit':
            transaction['account_number'] = masked_account

        # Standardize date format
        if 'date' in transaction:
            transaction['date'] = standardize_date(transaction['date'])
    
    if debug:
        print(f"\n--- Parsing Complete ---")
        print(f"Total transactions extracted: {len(transactions)}")
        if transactions:
            print(f"\nFirst transaction example:")
            first = transactions[0]
            print(f"  Date: {first.get('date')}")
            print(f"  Description: {first.get('description')[:50]}...")
            print(f"  Amount: ${first.get('amount')}")
    
    return transactions


def detect_statement_type(text: str, detection_config: Dict, debug: bool = False) -> Optional[str]:
    """
    Detect the type of bank statement based on indicators.
    
    Args:
        text: PDF text content
        detection_config: Detection configuration
        debug: Enable debug output
        
    Returns:
        Statement type or None if not detected
    """
    if debug:
        print(f"\n--- Statement Type Detection ---")
        print(f"Checking {len(detection_config)} statement types")
    
    text_lower = text.lower()
    scores = {}
    
    for statement_type, config in detection_config.items():
        if debug:
            print(f"\nChecking: {statement_type}")
        
        score = 0
        found_indicators = []
        
        # Check regular indicators
        indicators = config.get('indicators', [])
        if debug:
            print(f"  Regular indicators ({len(indicators)} total):")
        
        for indicator in indicators:
            if indicator.lower() in text_lower:
                weight = config.get('weight', 1)
                score += weight
                found_indicators.append(f"{indicator} (+{weight})")
                if debug:
                    print(f"    FOUND: '{indicator}' (weight: {weight})")
            elif debug:
                print(f"    missing: '{indicator}'")
        
        # Check strong indicators
        strong_indicators = config.get('strong_indicators', {})
        if debug:
            print(f"  Strong indicators ({len(strong_indicators)} total):")
        
        for indicator, weight in strong_indicators.items():
            if indicator.lower() in text_lower:
                score += weight
                found_indicators.append(f"{indicator} (+{weight})")
                if debug:
                    print(f"    FOUND: '{indicator}' (weight: {weight})")
            elif debug:
                print(f"    missing: '{indicator}'")
        
        scores[statement_type] = score
        
        if debug:
            threshold = config.get('threshold', 1)
            print(f"  Score: {score} (threshold: {threshold})")
            if found_indicators:
                print(f"  Found: {', '.join(found_indicators)}")
    
    # Return type with highest score (minimum threshold)
    if scores:
        best_type = max(scores, key=scores.get)
        best_score = scores[best_type]
        threshold = detection_config.get(best_type, {}).get('threshold', 1)
        
        if debug:
            print(f"\n--- Detection Results ---")
            print(f"All scores: {scores}")
            print(f"Best match: {best_type} (score: {best_score}, threshold: {threshold})")
        
        if best_score >= threshold:
            if debug:
                print(f"SUCCESS: Statement type detected as '{best_type}'")
            return best_type
        else:
            if debug:
                print(f"FAILED: Best score ({best_score}) below threshold ({threshold})")
    
    if debug:
        print(f"FAILED: No statement type detected")
    
    return None


def determine_transaction_year(month: int, statement_period: Optional[Dict]) -> int:
    """
    Determine the year for a transaction based on its month and the statement period.

    For statements spanning year boundaries (e.g., Dec 2024 - Jan 2025):
    - Transactions in months > statement end month are from previous year
    - Otherwise use statement end year

    Args:
        month: Transaction month (1-12)
        statement_period: Statement period dict with end_month and end_year

    Returns:
        Year for the transaction
    """
    if not statement_period or 'end_year' not in statement_period:
        # Fallback to current year if no statement period
        return datetime.now().year

    end_year = statement_period['end_year']
    end_month_str = statement_period.get('end_month', '')

    # Convert end month to number (handle month names)
    month_map = {'01': 1, '02': 2, '03': 3, '04': 4, '05': 5, '06': 6,
                 '07': 7, '08': 8, '09': 9, '10': 10, '11': 11, '12': 12,
                 'january': 1, 'february': 2, 'march': 3, 'april': 4,
                 'may': 5, 'june': 6, 'july': 7, 'august': 8,
                 'september': 9, 'october': 10, 'november': 11, 'december': 12}

    end_month = month_map.get(end_month_str.lower(), month_map.get(end_month_str, 12))

    # If transaction month > end month, it's from previous year
    # Example: End month = Jan (1), transaction month = Dec (12) → previous year
    if month > end_month:
        return end_year - 1
    else:
        return end_year


def extract_credit_transactions(text: str, patterns: Dict, debug: bool = False, statement_period: Optional[Dict] = None) -> List[Dict]:
    """
    Extract transactions from credit card statements.

    Args:
        text: Statement text
        patterns: Transaction patterns
        debug: Debug mode
        statement_period: Statement period with start/end dates and years

    Returns:
        List of transaction dictionaries
    """
    transactions = []

    if debug:
        print(f"\n--- Credit Card Transaction Extraction ---")
    
    # Get credit card patterns
    credit_patterns = patterns.get('patterns', [])
    if not credit_patterns:
        if debug:
            print("  ERROR: No credit card patterns configured")
        return []
    
    if debug:
        print(f"  Testing {len(credit_patterns)} credit card patterns...")
    
    for pattern_idx, pattern in enumerate(credit_patterns):
        try:
            matches = re.findall(pattern, text, re.MULTILINE)
            if debug:
                print(f"  Pattern {pattern_idx + 1}: {len(matches)} matches")
                if matches and len(matches) > 0:
                    print(f"    First match groups: {matches[0]}")
                    print(f"    Number of groups: {len(matches[0]) if matches else 0}")
            
            for match in matches:
                try:
                    # Credit card patterns can have different formats
                    # Formats:
                    #   3 groups: (date, description, amount) - Single date fallback
                    #   4 groups: (trans_date, post_date, description, amount) - Two dates without ref numbers
                    #   6 groups: (trans_date, post_date, description, ref#, acct#, amount) - Full BoA format
                    if len(match) == 3:
                        # Format: (date, description, amount)
                        # Single date - use for both transaction and posting date
                        date, description, amount_str = match
                        transaction_date = date
                        posting_date = None  # No separate posting date
                        reference_number = None
                        account_suffix = None
                    elif len(match) == 4:
                        # Format: (trans_date, post_date, description, amount)
                        transaction_date = match[0]  # When purchase was made
                        posting_date = match[1]      # When it posted to account
                        description = match[2]
                        amount_str = match[3]
                        reference_number = None
                        account_suffix = None
                    elif len(match) == 6:
                        # Format: (trans_date, post_date, description, ref#, acct#, amount)
                        # Full BoA credit card format with reference numbers
                        transaction_date = match[0]  # When purchase was made
                        posting_date = match[1]      # When it posted to account
                        description = match[2]       # Clean description (no ref numbers)
                        reference_number = match[3]  # 4-digit reference number
                        account_suffix = match[4]    # Last 4 digits of card
                        amount_str = match[5]        # Transaction amount
                    else:
                        if debug:
                            print(f"    WARNING: Unexpected match format with {len(match)} groups: {match}")
                        continue

                    # Parse amount
                    amount = float(amount_str.replace(',', ''))

                    # Credit card logic:
                    # - Positive amounts in PDF = Purchases (money spent) → make negative
                    # - Negative amounts in PDF = Payments/Credits (money received) → make positive
                    amount = -amount  # Flip the sign

                    # Determine year for transaction_date and posting_date
                    # Extract month from MM/DD format
                    trans_month = int(transaction_date.strip().split('/')[0])
                    trans_year = determine_transaction_year(trans_month, statement_period)

                    transaction = {
                        'date': transaction_date.strip(),
                        'description': normalize_whitespace(description),
                        'amount': amount,
                        'transaction_date': f"{transaction_date.strip()}/{trans_year}"  # MM/DD/YYYY
                    }

                    # Add posting_date if available (credit cards with dual dates)
                    if posting_date:
                        post_month = int(posting_date.strip().split('/')[0])
                        post_year = determine_transaction_year(post_month, statement_period)
                        transaction['posting_date'] = f"{posting_date.strip()}/{post_year}"  # MM/DD/YYYY

                    # Add reference numbers if captured (BoA format)
                    # These are kept separate from description and not displayed by default
                    if reference_number:
                        transaction['reference_number'] = reference_number
                    if account_suffix:
                        transaction['account_suffix'] = account_suffix

                    transactions.append(transaction)
                    
                except (ValueError, IndexError) as e:
                    if debug:
                        print(f"    ERROR parsing transaction: {e}")
                        print(f"    Match data: {match}")
                    continue
                    
        except re.error as e:
            if debug:
                print(f"  ERROR: Invalid regex pattern {pattern_idx + 1}: {e}")
            continue
    
    if debug:
        print(f"  Total credit transactions extracted: {len(transactions)}")
    
    return transactions


def extract_banking_transactions(text: str, patterns: Dict, debug: bool = False) -> List[Dict]:
    """Extract transactions from checking/savings statements."""
    transactions = []
    
    if debug:
        print(f"\n--- Banking Transaction Extraction ---")
        print(f"Available sections: {list(patterns.keys())}")
    
    # Extract deposits
    if 'deposits' in patterns:
        if debug:
            print(f"\nExtracting deposits...")
        deposits = extract_section_transactions(
            text, patterns['deposits'], 'deposit', debug
        )
        transactions.extend(deposits)
        if debug:
            print(f"  Found {len(deposits)} deposits")
    
    # Extract withdrawals
    if 'withdrawals' in patterns:
        if debug:
            print(f"\nExtracting withdrawals...")
        withdrawals = extract_section_transactions(
            text, patterns['withdrawals'], 'withdrawal', debug
        )
        transactions.extend(withdrawals)
        if debug:
            print(f"  Found {len(withdrawals)} withdrawals")
    
    return transactions


def extract_section_transactions(text: str, section_pattern: str, transaction_type: str, debug: bool = False) -> List[Dict]:
    """Extract transactions from a specific section of the statement."""
    transactions = []
    
    if debug:
        print(f"  Looking for {transaction_type} section...")
        print(f"  Section pattern: {section_pattern[:100]}...")
    
    try:
        # Find the section
        section_match = re.search(section_pattern, text, re.DOTALL | re.IGNORECASE)
        if not section_match:
            if debug:
                print(f"  WARNING: No {transaction_type} section found")
                print(f"  The section pattern did not match any part of the PDF text")
            return []
        
        section_text = section_match.group(0)
        if debug:
            print(f"  SUCCESS: Found {transaction_type} section ({len(section_text)} characters)")
            print(f"  Section preview: {section_text[:200]}")
        
        # Common transaction patterns for banking statements
        transaction_patterns = [
            # Bank of America checking format: Date+Description+Amount (no spaces between description and amount)
            r'(\d{1,2}/\d{1,2}/\d{2})(.*?)(-?\d{1,3}(?:,\d{3})*\.\d{2})',  # MM/DD/YY Description Amount (concatenated)
            # Standard format with spacing
            r'(\d{1,2}/\d{1,2})\s+(.+?)\s+(\d{1,3}(?:,\d{3})*\.\d{2})',  # MM/DD Description Amount
            r'(\d{1,2}/\d{1,2}/\d{2,4})\s+(.+?)\s+(\d{1,3}(?:,\d{3})*\.\d{2})',  # MM/DD/YYYY Description Amount
        ]
        
        if debug:
            print(f"  Trying {len(transaction_patterns)} transaction patterns...")
        
        for idx, pattern in enumerate(transaction_patterns):
            matches = re.findall(pattern, section_text, re.MULTILINE)
            if debug:
                print(f"  Pattern {idx + 1}: {len(matches)} matches")
            
            if matches and debug:
                print(f"    First match example: {matches[0]}")
            
            for match in matches:
                if len(match) >= 3:
                    try:
                        # Parse amount (remove commas and minus sign for parsing)
                        amount_str = match[2].replace(',', '').replace('-', '')
                        amount = float(amount_str)

                        # Apply sign based on transaction type
                        # Deposits are positive, withdrawals are negative
                        if transaction_type == 'withdrawal':
                            amount = -amount

                        transaction = {
                            'date': match[0],
                            'description': normalize_whitespace(match[1]),
                            'amount': amount
                        }
                        transactions.append(transaction)
                    except ValueError as e:
                        if debug:
                            print(f"    ERROR parsing amount '{match[2]}': {e}")
        
    except (re.error, ValueError, IndexError) as e:
        if debug:
            print(f"  ERROR extracting {transaction_type} transactions: {e}")
            import traceback
            traceback.print_exc()
    
    return transactions


def extract_statement_period(text: str, period_config: Dict, debug: bool = False) -> Optional[Dict]:
    """Extract statement period dates."""
    patterns = period_config.get('patterns', [])
    month_names = period_config.get('month_names', {})
    
    for pattern in patterns:
        try:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                groups = match.groups()
                if len(groups) >= 6:  # Start month, day, year, end month, day, year
                    return {
                        'start_month': groups[0],
                        'start_day': int(groups[1]),
                        'start_year': int(groups[2]),
                        'end_month': groups[3],
                        'end_day': int(groups[4]),
                        'end_year': int(groups[5])
                    }
        except (re.error, ValueError, IndexError):
            continue
    
    return None


def extract_account_number(text: str, account_patterns: Dict, debug: bool = False) -> Optional[str]:
    """
    Extract account number from statement text.
    
    Args:
        text: PDF text content
        account_patterns: Account number patterns
        debug: Enable debug output
        
    Returns:
        Account number or None if not found
    """
    for statement_type, pattern in account_patterns.items():
        try:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if debug:
                    print(f"    Found account number for {statement_type}")
                return match.group(1) if match.groups() else match.group(0)
        except re.error:
            continue
    
    return None


def mask_account_number(account_number: str) -> str:
    """
    Mask account number to show only last 4 digits.

    Args:
        account_number: Full account number (may contain spaces or dashes)

    Returns:
        Masked account number (e.g., "****1234")

    Examples:
        "1234 5678 9012 3456" -> "****3456"
        "1234-5678-9012" -> "****9012"
        "123456789012" -> "****9012"
    """
    # Remove spaces, dashes, and other non-digit characters
    digits_only = ''.join(c for c in account_number if c.isdigit())

    # Show last 4 digits only
    if len(digits_only) >= 4:
        return '****' + digits_only[-4:]
    else:
        # If less than 4 digits, mask what we have
        return '****' + digits_only


def validate_transaction(transaction: Dict) -> bool:
    """
    Validate that a transaction has required fields.
    
    Args:
        transaction: Transaction dictionary
        
    Returns:
        True if valid, False otherwise
    """
    required_fields = ['date', 'description', 'amount']
    
    for field in required_fields:
        if field not in transaction or not transaction[field]:
            return False
    
    # Validate amount is numeric
    try:
        float(transaction['amount'])
    except (ValueError, TypeError):
        return False
    
    return True


def sort_transactions_by_date(transactions: List[Dict]) -> List[Dict]:
    """
    Sort transactions by date.
    
    Args:
        transactions: List of transaction dictionaries
        
    Returns:
        Sorted list of transactions
    """
    def date_key(transaction):
        try:
            date_str = transaction.get('date', '')
            # Handle different date formats
            if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
                return datetime.strptime(date_str, '%Y-%m-%d')
            elif re.match(r'^\d{1,2}/\d{1,2}/\d{4}$', date_str):
                return datetime.strptime(date_str, '%m/%d/%Y')
            elif re.match(r'^\d{1,2}/\d{1,2}$', date_str):
                # Default to current year for MM/DD format
                year = datetime.now().year
                return datetime.strptime(f"{date_str}/{year}", '%m/%d/%Y')
            else:
                return datetime.min  # Sort unknown dates first
        except ValueError:
            return datetime.min
    
    return sorted(transactions, key=date_key)