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

try:
    import pypdf
except ImportError:
    print("Error: pypdf is required. Install with: pip install pypdf")
    exit(1)


def load_config(config_file: str) -> Dict:
    """
    Load configuration from TOML file.
    
    Args:
        config_file: Path to the TOML configuration file
        
    Returns:
        Dictionary containing configuration data
        
    Raises:
        FileNotFoundError: If config file doesn't exist
        tomllib.TOMLDecodeError: If config file has invalid TOML syntax
    """
    try:
        with open(config_file, 'rb') as f:
            return tomllib.load(f)
    except FileNotFoundError:
        print(f"Error: Configuration file '{config_file}' not found")
        raise
    except tomllib.TOMLDecodeError as e:
        print(f"Error: Invalid TOML syntax in '{config_file}': {e}")
        raise


def extract_pdf_text(pdf_path: str) -> str:
    """
    Extract text content from PDF file.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Extracted text content as string, empty string if extraction fails
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


def sanitize_description(description: str, patterns: List[Dict]) -> str:
    """
    Clean and sanitize transaction description by removing sensitive information.
    
    Args:
        description: Original transaction description
        patterns: List of regex patterns and replacements from config
        
    Returns:
        Sanitized description with sensitive data masked
    """
    if not description:
        return ""
        
    description = description.lower().strip()
    
    # Apply sanitization patterns from config
    for pattern_config in patterns:
        pattern = pattern_config['pattern']
        replacement = pattern_config['replacement']
        description = re.sub(pattern, replacement, description)
    
    return description.strip()


def standardize_date(date_str: str, 
                    statement_start: Optional[datetime] = None, 
                    statement_end: Optional[datetime] = None) -> str:
    """
    Convert various date formats to standardized YYYY-MM-DD format.
    
    Uses statement period context to determine correct year for partial dates.
    
    Args:
        date_str: Date string in various formats (MM/DD, MM/DD/YY, MM/DD/YYYY)
        statement_start: Start date of statement period for context
        statement_end: End date of statement period for context
        
    Returns:
        Standardized date string in YYYY-MM-DD format
    """
    try:
        if '/' in date_str:
            parts = date_str.split('/')
            
            if len(parts) == 3:
                # Full date: MM/DD/YYYY or MM/DD/YY
                month, day, year = parts
                if len(year) == 2:
                    year = '20' + year
                return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
            
            elif len(parts) == 2 and statement_start and statement_end:
                # Partial date: MM/DD - need to determine year from statement context
                month, day = int(parts[0]), int(parts[1])
                
                # For cross-year periods (like credit card statements)
                if statement_start.year != statement_end.year:
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
                    
                    # Use logic based on month proximity to statement dates
                    if abs(month - statement_start.month) <= abs(month - statement_end.month):
                        return f"{statement_start.year}-{month:02d}-{day:02d}"
                    else:
                        return f"{statement_end.year}-{month:02d}-{day:02d}"
                
                else:
                    # Same year period - use statement year
                    try:
                        candidate_date = datetime(statement_start.year, month, day)
                        if statement_start <= candidate_date <= statement_end:
                            return f"{statement_start.year}-{month:02d}-{day:02d}"
                        else:
                            # Date might be slightly outside range, still use statement year
                            return f"{statement_start.year}-{month:02d}-{day:02d}"
                    except ValueError:
                        # Invalid date (e.g., Feb 30), use statement year anyway
                        return f"{statement_start.year}-{month:02d}-{day:02d}"
            
            elif len(parts) == 2:
                # No statement context available - use current year as fallback
                month, day = parts
                year = str(datetime.now().year)
                return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                
    except Exception as e:
        print(f"Date parsing error for '{date_str}': {e}")
    
    # Return original if parsing fails
    return date_str


def extract_statement_period(text: str, patterns: List[str], 
                           month_names: Dict[str, int]) -> Tuple[Optional[datetime], Optional[datetime]]:
    """
    Extract statement period start and end dates from PDF text.
    
    Args:
        text: Full text content from PDF
        patterns: List of regex patterns for finding date ranges
        month_names: Mapping of month names to numbers
        
    Returns:
        Tuple of (start_date, end_date) or (None, None) if not found
    """
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                groups = match.groups()
                if len(groups) == 6:
                    start_month = month_names.get(groups[0].lower())
                    start_day = int(groups[1])
                    start_year = int(groups[2])
                    end_month = month_names.get(groups[3].lower())
                    end_day = int(groups[4])
                    end_year = int(groups[5])
                    
                    start_date = datetime(start_year, start_month, start_day)
                    end_date = datetime(end_year, end_month, end_day)
                    
                    # Validate dates are reasonable
                    if (start_date.year >= 2020 and end_date.year <= 2030 and 
                        start_date <= end_date):
                        return start_date, end_date
            except (ValueError, KeyError, TypeError):
                continue
    
    return None, None


def mask_account_number(account_number: str) -> str:
    """
    Mask account number showing only last 4 digits.
    
    Args:
        account_number: Full account number string
        
    Returns:
        Masked account number (e.g., "************1234")
    """
    if not account_number:
        return ""
        
    clean_number = re.sub(r'\s+', '', account_number)
    if len(clean_number) >= 4:
        return '*' * (len(clean_number) - 4) + clean_number[-4:]
    else:
        return '*' * len(clean_number)


def save_transactions_to_json(transactions: List[Dict], output_file: str) -> None:
    """
    Save transaction list to JSON file with proper formatting.
    
    Args:
        transactions: List of transaction dictionaries
        output_file: Path to output JSON file
    """
    if not transactions:
        print("No transactions to save!")
        return
    
    # Ensure output directory exists
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    try:
        with open(output_file, 'w') as f:
            json.dump(transactions, f, indent=2)
        print(f"Successfully saved {len(transactions)} transactions to {output_file}")
    except Exception as e:
        print(f"Error saving transactions to {output_file}: {e}")


def load_transactions_from_json(input_file: str) -> List[Dict]:
    """
    Load transactions from JSON file.
    
    Args:
        input_file: Path to input JSON file
        
    Returns:
        List of transaction dictionaries
        
    Raises:
        FileNotFoundError: If input file doesn't exist
        json.JSONDecodeError: If file has invalid JSON
    """
    try:
        with open(input_file, 'r') as f:
            data = json.load(f)
        
        # Handle different JSON structures
        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and 'transactions' in data:
            return data['transactions']
        else:
            print(f"Error: Unexpected JSON structure in {input_file}")
            return []
            
    except FileNotFoundError:
        print(f"Error: Could not find {input_file}")
        raise
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {input_file}: {e}")
        raise


def fuzzy_match(text1: str, text2: str, threshold: float = 0.6) -> bool:
    """
    Simple fuzzy string matching using sequence similarity.
    
    Args:
        text1: First string to compare
        text2: Second string to compare  
        threshold: Minimum similarity ratio (0.0 to 1.0)
        
    Returns:
        True if strings are similar enough, False otherwise
    """
    from difflib import SequenceMatcher
    return SequenceMatcher(None, text1, text2).ratio() >= threshold


def clean_business_name(name: str) -> str:
    """
    Clean business name by removing location indicators and standardizing format.
    
    Args:
        name: Raw business name from transaction description
        
    Returns:
        Cleaned business name
    """
    if not name:
        return ""
    
    # Remove common location indicators
    location_patterns = [
        r'\s+f\d+.*$',           # McDonald's franchise numbers
        r'\s+#\d+.*$',           # Store numbers
        r'\s+\d{5}.*$',          # Zip codes
        r'\s+(inside|outside)\s+.*$',  # Location descriptors
        r'\s+[a-z]{2}$',         # State abbreviations
        r'\s+express\s+lane\s*.*$',    # Express lane
        r'\s+rf[x-]+.*$'         # RFX prefixes
    ]
    
    # Common city names to remove
    cities = [
        'las vegas', 'fort worth', 'scottsdale', 'denton', 'prosper', 'aubrey', 
        'frisco', 'plano', 'celina', 'dallas', 'chicago', 'tallahassee', 
        'williamstown', 'petersburg', 'dry ridge', 'milton', 'lake city', 
        'fontaineb', 'chandler', 'crossroads', 'cross roads', 'kenedy', 
        'bentonville', 'little elm'
    ]
    
    cleaned_name = name
    
    # Remove location patterns
    for pattern in location_patterns:
        cleaned_name = re.sub(pattern, '', cleaned_name, flags=re.IGNORECASE)
    
    # Remove city names
    for city in cities:
        city_pattern = r'\s+' + re.escape(city) + r'\s*.*$'
        cleaned_name = re.sub(city_pattern, '', cleaned_name, flags=re.IGNORECASE)
    
    # Clean up whitespace and return title case
    cleaned_name = ' '.join(cleaned_name.split())
    return cleaned_name.title() if cleaned_name else name


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


def debug_print(message: str, debug_mode: bool = False) -> None:
    """
    Print debug message if debug mode is enabled.
    
    Args:
        message: Debug message to print
        debug_mode: Whether debug mode is enabled
    """
    if debug_mode:
        print(message)


def get_pdf_files(directory: str) -> List[str]:
    """
    Get list of PDF files in specified directory.
    
    Args:
        directory: Directory path to search for PDF files
        
    Returns:
        List of PDF file paths
    """
    try:
        pdf_files = [
            os.path.join(directory, f) 
            for f in os.listdir(directory) 
            if f.lower().endswith('.pdf')
        ]
        return sorted(pdf_files)
    except FileNotFoundError:
        print(f"Error: Directory '{directory}' not found")
        return []
    except PermissionError:
        print(f"Error: Permission denied accessing directory '{directory}'")
        return []


def ensure_directories_exist():
    """
    Create standard project directories if they don't exist.
    """
    directories = ['statements', 'output', 'config']
    
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"Created directory: {directory}")