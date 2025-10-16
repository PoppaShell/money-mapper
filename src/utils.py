#!/usr/bin/env python3
"""
Utility functions for financial transaction processing.

This module provides helper functions for date handling, text processing,
file operations, and configuration loading that are shared across the
financial parser components.
"""

import json
import os
import re
import tomllib
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union

# Add the src directory to Python path for imports
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config_manager import get_config_manager

try:
    import pypdf
except ImportError:
    print("Error: pypdf is required. Install with: pip install pypdf")
    exit(1)


def load_config(config_file: str) -> Dict:
    """
    Load configuration from TOML file.
    
    Args:
        config_file: Path to TOML configuration file
        
    Returns:
        Dictionary containing configuration data
    """
    try:
        with open(config_file, 'rb') as f:
            return tomllib.load(f)
    except FileNotFoundError:
        print(f"Error: Configuration file '{config_file}' not found")
        exit(1)
    except tomllib.TOMLDecodeError as e:
        print(f"Error: Invalid TOML syntax in '{config_file}': {e}")
        exit(1)
    except Exception as e:
        print(f"Error loading configuration from '{config_file}': {e}")
        exit(1)


def extract_pdf_text(pdf_path: str) -> str:
    """
    Extract text content from PDF file.
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        Extracted text content
    """
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = pypdf.PdfReader(file)
            text = ""
            
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            
            return text.strip()
    
    except Exception as e:
        print(f"Error extracting text from PDF '{pdf_path}': {e}")
        return ""


def standardize_date(date_str: str, statement_period: Optional[Dict] = None) -> str:
    """
    Standardize date format to YYYY-MM-DD.
    
    Args:
        date_str: Date string in various formats
        statement_period: Statement period info for year inference
        
    Returns:
        Standardized date string
    """
    # Remove extra whitespace
    date_str = date_str.strip()
    
    # Handle MM/DD format (need to infer year)
    if re.match(r'^\d{1,2}/\d{1,2}$', date_str):
        month, day = date_str.split('/')
        
        # Try to infer year from statement period
        if statement_period and 'end_year' in statement_period:
            year = statement_period['end_year']
        else:
            # Default to current year
            year = datetime.now().year
        
        return f"{year}-{int(month):02d}-{int(day):02d}"
    
    # Handle MM/DD/YY format
    if re.match(r'^\d{1,2}/\d{1,2}/\d{2}$', date_str):
        month, day, year = date_str.split('/')
        year = int(year)
        
        # Convert 2-digit year to 4-digit
        if year < 50:
            year += 2000
        else:
            year += 1900
        
        return f"{year}-{int(month):02d}-{int(day):02d}"
    
    # Handle MM/DD/YYYY format
    if re.match(r'^\d{1,2}/\d{1,2}/\d{4}$', date_str):
        month, day, year = date_str.split('/')
        return f"{year}-{int(month):02d}-{int(day):02d}"
    
    # Handle YYYY-MM-DD format (already standardized)
    if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        return date_str
    
    # If we can't parse it, return as-is
    print(f"Warning: Could not standardize date format: {date_str}")
    return date_str


def sanitize_description(description: str, sanitization_patterns: List = None,
                        privacy_config: Dict = None, fuzzy_threshold: float = 0.85) -> str:
    """
    Remove sensitive information from transaction descriptions using both
    pattern-based and fuzzy keyword-based redaction.

    This function provides comprehensive privacy protection by:
    1. Applying regex patterns for structured data (account numbers, phone numbers, etc.)
    2. Using fuzzy matching for personal keywords (names, employers, locations, etc.)

    Args:
        description: Original transaction description
        sanitization_patterns: List of legacy patterns (can be dicts or strings)
        privacy_config: Privacy configuration from settings.toml [privacy] section
        fuzzy_threshold: Minimum similarity score for fuzzy keyword matching (0.0-1.0)

    Returns:
        Sanitized description with sensitive information redacted

    Example:
        >>> privacy = {'keywords': {'names': ['John Smith'], 'employers': ['Acme Corp']},
        ...            'patterns': {'account_numbers': [{'pattern': r'\\d{4}', 'replacement': '[ACCT]'}]}}
        >>> sanitize_description("ACME CORP INDN:JOHN SMITH 1234 5678", privacy_config=privacy)
        '[EMPLOYER] INDN:[NAME] [ACCT] [ACCT]'
    """
    from difflib import SequenceMatcher

    sanitized = description

    # Step 1: Apply legacy sanitization patterns (for backwards compatibility)
    if sanitization_patterns:
        for pattern_config in sanitization_patterns:
            # Handle both dictionary format and string format
            if isinstance(pattern_config, dict):
                pattern = pattern_config.get('pattern', '')
                replacement = pattern_config.get('replacement', '[REDACTED]')
            elif isinstance(pattern_config, str):
                # If it's just a string, use it as the pattern with default replacement
                pattern = pattern_config
                replacement = '[REDACTED]'
            else:
                # Skip invalid pattern types
                continue

            try:
                sanitized = re.sub(pattern, replacement, sanitized)
            except re.error:
                # Skip invalid regex patterns
                continue

    # Step 2: Apply privacy configuration if provided
    if privacy_config and privacy_config.get('enable_redaction', True):

        # Get fuzzy threshold from config or use parameter default
        threshold = privacy_config.get('fuzzy_redaction_threshold', fuzzy_threshold)

        # Apply pattern-based redaction from privacy config
        patterns_config = privacy_config.get('patterns', {})

        # Process pattern categories in specific order to avoid conflicts
        # Order matters: specific patterns must be processed before more generic ones
        category_order = [
            'pii_fields',           # Process PII fields first (INDN:, COID:)
            'reference_numbers',    # Then reference/ID numbers
            'account_numbers',      # Then account numbers
            'contact_info',         # Finally contact info (phone, email)
        ]

        # Process ordered categories first
        for category in category_order:
            if category not in patterns_config:
                continue

            pattern_list = patterns_config[category]
            if not isinstance(pattern_list, list):
                continue

            for pattern_config in pattern_list:
                if not isinstance(pattern_config, dict):
                    continue

                pattern = pattern_config.get('pattern', '')
                replacement = pattern_config.get('replacement', '[REDACTED]')

                try:
                    sanitized = re.sub(pattern, replacement, sanitized)
                except re.error:
                    # Skip invalid regex patterns
                    continue

        # Process any remaining categories not in the ordered list
        for pattern_category, pattern_list in patterns_config.items():
            if pattern_category in category_order:
                continue  # Already processed

            if not isinstance(pattern_list, list):
                continue

            for pattern_config in pattern_list:
                if not isinstance(pattern_config, dict):
                    continue

                pattern = pattern_config.get('pattern', '')
                replacement = pattern_config.get('replacement', '[REDACTED]')

                try:
                    sanitized = re.sub(pattern, replacement, sanitized)
                except re.error:
                    # Skip invalid regex patterns
                    continue

        # Apply fuzzy keyword-based redaction
        keywords_config = privacy_config.get('keywords', {})

        # Process names
        for name in keywords_config.get('names', []):
            sanitized = _fuzzy_redact_keyword(sanitized, name, '[NAME]', threshold)

        # Process employers
        for employer in keywords_config.get('employers', []):
            sanitized = _fuzzy_redact_keyword(sanitized, employer, '[EMPLOYER]', threshold)

        # Process locations
        for location in keywords_config.get('locations', []):
            sanitized = _fuzzy_redact_keyword(sanitized, location, '[LOCATION]', threshold)

        # Process custom keywords
        for keyword in keywords_config.get('custom', []):
            sanitized = _fuzzy_redact_keyword(sanitized, keyword, '[REDACTED]', threshold)

    return sanitized.strip()


def _fuzzy_redact_keyword(text: str, keyword: str, replacement: str, threshold: float = 0.85) -> str:
    """
    Redact keyword from text using fuzzy string matching.

    This helper function finds and replaces variations of a keyword that may appear
    in different formats (e.g., "JOHN SMITH", "Smith, John", "J. Smith").

    Args:
        text: Text to search and redact from
        keyword: Keyword to find (case-insensitive)
        replacement: String to replace matches with
        threshold: Minimum similarity score (0.0-1.0) to consider a match

    Returns:
        Text with fuzzy matches replaced

    Algorithm:
        1. Tokenize text into words
        2. For each sliding window matching keyword word count
        3. Calculate fuzzy similarity using SequenceMatcher
        4. Replace windows exceeding threshold with replacement text
    """
    from difflib import SequenceMatcher

    if not keyword or not text:
        return text

    # Normalize keyword for comparison
    keyword_normalized = keyword.lower().strip()
    keyword_words = keyword_normalized.split()
    keyword_word_count = len(keyword_words)

    # Tokenize text while preserving structure
    # Use regex to split on whitespace but keep positions
    words = text.split()

    if len(words) < keyword_word_count:
        return text

    # Sliding window approach to find fuzzy matches
    redacted_text = text
    replacements_made = []  # Track (start_idx, end_idx, original_phrase) to avoid overlaps

    for i in range(len(words) - keyword_word_count + 1):
        # Extract window of words matching keyword length
        window_words = words[i:i + keyword_word_count]
        window_text = ' '.join(window_words)
        window_normalized = window_text.lower().strip()

        # Calculate fuzzy similarity
        similarity = SequenceMatcher(None, keyword_normalized, window_normalized).ratio()

        # If similarity exceeds threshold, mark for replacement
        if similarity >= threshold:
            replacements_made.append((i, i + keyword_word_count, window_text))

    # Apply replacements from right to left to maintain indices
    for start_idx, end_idx, original_phrase in reversed(replacements_made):
        # Reconstruct text with replacement
        before = ' '.join(words[:start_idx])
        after = ' '.join(words[end_idx:])

        # Rebuild with proper spacing
        parts = [p for p in [before, replacement, after] if p]
        redacted_text = ' '.join(parts)

        # Update words list for next iteration
        words = redacted_text.split()

    return redacted_text


def save_transactions_to_json(transactions: List[Dict], output_file: str) -> None:
    """
    Save transactions to JSON file.
    
    Args:
        transactions: List of transaction dictionaries
        output_file: Output file path
    """
    try:
        # Ensure output directory exists
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(transactions, f, indent=2, ensure_ascii=False, default=str)
            
    except Exception as e:
        print(f"Error saving transactions to '{output_file}': {e}")
        raise


def load_transactions_from_json(input_file: str) -> List[Dict]:
    """
    Load transactions from JSON file.
    
    Args:
        input_file: Input file path
        
    Returns:
        List of transaction dictionaries
    """
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: File '{input_file}' not found")
        return []
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in '{input_file}': {e}")
        return []
    except Exception as e:
        print(f"Error loading transactions from '{input_file}': {e}")
        return []


def validate_toml_files(verbose: bool = False) -> bool:
    """
    Validate all TOML configuration files using config manager.
    
    Args:
        verbose: Print detailed validation info
        
    Returns:
        True if all files are valid, False otherwise
    """
    try:
        # Get config manager and file list
        config_manager = get_config_manager()
        config_files = config_manager.get_all_config_files()
        
        if verbose:
            print(f"Validating {len(config_files)} TOML configuration files...")
        
        all_valid = True
        
        for file_path in config_files:
            try:
                if not os.path.exists(file_path):
                    if verbose:
                        print(f"  Warning: {file_path} does not exist (may be optional)")
                    continue
                
                with open(file_path, 'rb') as f:
                    tomllib.load(f)
                
                if verbose:
                    print(f"  Valid: {file_path}")
                    
            except tomllib.TOMLDecodeError as e:
                if verbose:
                    print(f"  Invalid: {file_path}: {e}")
                else:
                    print(f"TOML syntax error in {file_path}: {e}")
                all_valid = False
            except Exception as e:
                if verbose:
                    print(f"  Error: {file_path}: {e}")
                else:
                    print(f"Error reading {file_path}: {e}")
                all_valid = False
        
        return all_valid
        
    except Exception as e:
        print(f"Error during TOML validation: {e}")
        return False


def ensure_directories_exist() -> bool:
    """
    Ensure all required directories exist using config manager.
    
    Returns:
        True if all directories exist or were created successfully
    """
    try:
        config_manager = get_config_manager()
        
        # Get all required directories
        directories_to_check = [
            config_manager.get_directory_path('statements'),
            config_manager.get_directory_path('output'),
            config_manager.get_directory_path('config')
        ]
        
        # Also check backup directory if configured
        try:
            backup_dir = config_manager.get_mapping_processor_files()['backup_directory']
            if backup_dir:
                directories_to_check.append(backup_dir)
        except:
            pass  # Backup directory is optional
        
        all_success = True
        
        for directory in directories_to_check:
            if not os.path.exists(directory):
                try:
                    os.makedirs(directory)
                    print(f"Created directory: {directory}")
                except Exception as e:
                    print(f"Error creating directory {directory}: {e}")
                    all_success = False
            elif not os.path.isdir(directory):
                print(f"Error: {directory} exists but is not a directory")
                all_success = False
        
        return all_success
        
    except Exception as e:
        print(f"Error ensuring directories exist: {e}")
        return False


def clean_merchant_name(description: str) -> str:
    """
    Extract clean merchant name from transaction description.
    
    Args:
        description: Transaction description
        
    Returns:
        Cleaned merchant name
    """
    # Remove common banking prefixes
    cleaned = re.sub(r'^(CHECKCARD|DEBIT CARD|POS|ACH|DES:|REF #)', '', description, flags=re.IGNORECASE)
    
    # Remove card numbers and dates
    cleaned = re.sub(r'\d{4}\s*\*+\d{4}|\d{2}/\d{2}', '', cleaned)
    
    # Remove extra whitespace and normalize
    cleaned = ' '.join(cleaned.split()).strip()
    
    # Take first meaningful part (usually merchant name)
    parts = cleaned.split()
    if parts:
        # Return first 3-4 words as merchant name
        return ' '.join(parts[:4])
    
    return cleaned


def format_amount(amount: Union[float, str]) -> str:
    """
    Format monetary amount for display.
    
    Args:
        amount: Amount to format
        
    Returns:
        Formatted amount string
    """
    try:
        num_amount = float(amount)
        if num_amount >= 0:
            return f"${num_amount:,.2f}"
        else:
            return f"-${abs(num_amount):,.2f}"
    except (ValueError, TypeError):
        return str(amount)


def calculate_confidence_score(method: str, similarity: float = 0.0) -> float:
    """
    Calculate confidence score based on categorization method.
    
    Args:
        method: Categorization method used
        similarity: Similarity score for fuzzy matches
        
    Returns:
        Confidence score between 0.0 and 1.0
    """
    if method == 'private_mapping':
        return 0.95  # Highest confidence for personal mappings
    elif method == 'public_mapping':
        return 0.85  # High confidence for merchant mappings
    elif method == 'fuzzy_match':
        return min(0.80, similarity)  # Based on similarity score
    elif method == 'plaid_keyword':
        return 0.70  # Medium confidence for keyword matching
    elif method == 'plaid_fallback':
        return 0.40  # Lower confidence for fallback categories
    else:
        return 0.20  # Low confidence for unknown methods


def get_processing_stats(transactions: List[Dict]) -> Dict:
    """
    Calculate processing statistics for transactions.
    
    Args:
        transactions: List of processed transactions
        
    Returns:
        Dictionary containing statistics
    """
    if not transactions:
        return {
            'total_transactions': 0,
            'categorized': 0,
            'uncategorized': 0,
            'categorization_rate': 0.0,
            'confidence_distribution': {},
            'method_distribution': {}
        }
    
    total = len(transactions)
    categorized = sum(1 for t in transactions if t.get('category') and t.get('category') != 'UNCATEGORIZED')
    
    # Confidence distribution
    confidence_levels = {'high': 0, 'medium': 0, 'low': 0}
    method_counts = {}
    
    for transaction in transactions:
        confidence = transaction.get('confidence', 0.0)
        method = transaction.get('categorization_method', 'unknown')
        
        # Count confidence levels
        if confidence >= 0.8:
            confidence_levels['high'] += 1
        elif confidence >= 0.5:
            confidence_levels['medium'] += 1
        else:
            confidence_levels['low'] += 1
        
        # Count methods
        method_counts[method] = method_counts.get(method, 0) + 1
    
    return {
        'total_transactions': total,
        'categorized': categorized,
        'uncategorized': total - categorized,
        'categorization_rate': (categorized / total) * 100 if total > 0 else 0.0,
        'confidence_distribution': confidence_levels,
        'method_distribution': method_counts
    }


def normalize_text_for_matching(text: str) -> str:
    """
    Normalize text for consistent matching.
    
    Args:
        text: Text to normalize
        
    Returns:
        Normalized text
    """
    # Convert to lowercase
    text = text.lower()
    
    # Remove extra whitespace
    text = ' '.join(text.split())
    
    # Remove common punctuation
    text = re.sub(r'[^\w\s]', '', text)
    
    # Remove common banking terms
    banking_terms = ['checkcard', 'debit', 'card', 'pos', 'purchase', 'payment']
    for term in banking_terms:
        text = text.replace(term, '')
    
    # Remove extra whitespace again
    text = ' '.join(text.split())
    
    return text.strip()


def fuzzy_match_similarity(text1: str, text2: str) -> float:
    """
    Calculate fuzzy matching similarity between two strings.
    
    Args:
        text1: First string
        text2: Second string
        
    Returns:
        Similarity score between 0.0 and 1.0
    """
    from difflib import SequenceMatcher
    
    # Normalize both strings
    norm1 = normalize_text_for_matching(text1)
    norm2 = normalize_text_for_matching(text2)
    
    # Calculate similarity
    return SequenceMatcher(None, norm1, norm2).ratio()


def validate_transaction_data(transaction: Dict) -> Tuple[bool, List[str]]:
    """
    Validate transaction data structure.
    
    Args:
        transaction: Transaction dictionary
        
    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []
    
    # Check required fields
    required_fields = ['date', 'description', 'amount']
    for field in required_fields:
        if field not in transaction:
            errors.append(f"Missing required field: {field}")
        elif not transaction[field]:
            errors.append(f"Empty required field: {field}")
    
    # Validate date format
    if 'date' in transaction:
        date_str = transaction['date']
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
            errors.append(f"Invalid date format: {date_str} (expected YYYY-MM-DD)")
    
    # Validate amount
    if 'amount' in transaction:
        try:
            float(transaction['amount'])
        except (ValueError, TypeError):
            errors.append(f"Invalid amount format: {transaction['amount']}")
    
    return len(errors) == 0, errors


def backup_file(file_path: str, backup_dir: str = "backups") -> Optional[str]:
    """
    Create a backup copy of a file with timestamp.
    
    Args:
        file_path: Path to file to backup
        backup_dir: Directory to store backup
        
    Returns:
        Path to backup file or None if failed
    """
    if not os.path.exists(file_path):
        return None
    
    try:
        # Ensure backup directory exists
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        # Create backup filename with timestamp
        filename = os.path.basename(file_path)
        name, ext = os.path.splitext(filename)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"{name}_{timestamp}{ext}"
        backup_path = os.path.join(backup_dir, backup_filename)
        
        # Copy file
        import shutil
        shutil.copy2(file_path, backup_path)
        
        return backup_path
        
    except Exception as e:
        print(f"Error creating backup of {file_path}: {e}")
        return None


def merge_transaction_data(base_transaction: Dict, update_data: Dict) -> Dict:
    """
    Merge transaction data with updates.

    Args:
        base_transaction: Original transaction data
        update_data: Data to merge in

    Returns:
        Merged transaction dictionary
    """
    merged = base_transaction.copy()
    merged.update(update_data)

    # Add processing timestamp
    merged['last_updated'] = datetime.now().isoformat()

    return merged


def show_progress(current: int, total: int, bar_length: int = 50) -> None:
    """
    Display a progress bar for long-running operations.

    Args:
        current: Current progress value
        total: Total expected value
        bar_length: Length of progress bar in characters
    """
    if total == 0:
        return

    percent = int((current / total) * 100)
    filled_length = int(bar_length * current / total)
    bar = '█' * filled_length + '░' * (bar_length - filled_length)
    print(f'\r[{bar}] {percent}% ({current}/{total})', end='', flush=True)