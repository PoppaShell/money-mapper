#!/usr/bin/env python3
"""
Transaction Enricher - Add merchant names and categories to transactions.

This module enriches parsed financial transactions by:
1. Extracting clean merchant names from transaction descriptions
2. Categorizing transactions using Plaid Personal Finance Category taxonomy
3. Applying custom merchant mappings for improved accuracy
4. Adding confidence scores and categorization methods
"""

import re
from typing import Dict, List, Optional, Tuple
from difflib import SequenceMatcher

from utils import (
    load_config, load_transactions_from_json, save_transactions_to_json,
    clean_business_name, fuzzy_match, show_progress
)


def extract_merchant_name(description: str) -> str:
    """
    Extract clean merchant name from transaction description.
    
    Handles various banking description formats and removes
    transaction codes, reference numbers, and location information.
    
    Args:
        description: Raw transaction description
        
    Returns:
        Cleaned merchant name
    """
    if not description:
        return ""
    
    # Convert to lowercase for processing
    cleaned = description.lower().strip()
    
    # Remove common prefixes and suffixes
    prefixes_to_remove = ['checkcard', 'pos', 'purchase', 'tst*', 'sq *', 'pp*']
    for prefix in prefixes_to_remove:
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):].strip()
    
    # Banking-specific patterns for better merchant extraction
    banking_patterns = [
        # Standard checkcard pattern: "checkcard 0125 merchant name location"
        (r'checkcard\s+\d{4}\s+([^#\d]*?)(?:\s+[a-z]{2}\s*#|\s+\d{3,}|\s+[a-z]{2}$|$)', r'\1'),
        # POS pattern: "pos purchase merchant name"
        (r'pos\s+purchase\s+([^#\d]*?)(?:\s+#|\s+\d{3,}|\s+[a-z]{2}$|$)', r'\1'),
        # Direct merchant: "merchant name des:description"
        (r'^([^#\d]*?)\s+des:', r'\1'),
        # Square payments: "sq * merchant name"
        (r'sq\s*\*\s*([^#\d]*?)(?:\s+#|\s+\d{3,}|$)', r'\1'),
        # PayPal: "paypal * merchant name"
        (r'paypal\s*\*\s*([^#\d]*?)(?:\s+#|\s+\d{3,}|$)', r'\1'),
        # TST pattern: "tst* merchant name"
        (r'tst\*\s*([^#\d]*?)(?:\s+#|\s+\d{3,}|$)', r'\1'),
        # Remove trailing reference numbers
        (r'^(.*?)\s+(?:id:|ref#|conf#|#)\s*[0-9#]+.*$', r'\1'),
        # Remove trailing phone numbers
        (r'^(.*?)\s+\d{3}[-.]?\d{3}[-.]?\d{4}.*$', r'\1'),
        # Remove dates and times
        (r'^(.*?)\s+\d{1,2}/\d{1,2}(?:/\d{2,4})?\s*.*$', r'\1'),
        # Remove trailing numbers and location codes
        (r'^(.*?)\s+(?:\d{5,}|\d{3,4}\s+[a-z]{2}).*$', r'\1'),
        # Remove "des:" and everything after
        (r'^(.*?)\s+des:.*$', r'\1'),
        # Clean up common suffixes
        (r'^(.*?)\s+(?:llc|inc|corp|co|ltd)(?:\s|$)', r'\1'),
    ]
    
    for pattern, replacement in banking_patterns:
        match = re.search(pattern, cleaned, re.IGNORECASE)
        if match:
            extracted = match.group(1).strip()
            if len(extracted) > 2:
                extracted = extracted.replace('  ', ' ')
                extracted = re.sub(r'\s+', ' ', extracted)
                extracted = extracted.strip()
                return clean_business_name(extracted)
    
    # General patterns for merchant extraction
    patterns = [
        r'^([a-zA-Z\s&\'.-]+?)(?:\s+#\d+|\s+\d{3,}|\s+[a-z]{2}$)',
        r'^([a-zA-Z\s&\'.-]+)',
    ]
    
    for pattern in patterns:
        match = re.match(pattern, cleaned)
        if match:
            name = match.group(1).strip()
            if len(name) > 2:
                return clean_business_name(name)
    
    return clean_business_name(cleaned)


def categorize_with_plaid_taxonomy(description: str, merchant_name: str, 
                                  amount: float, transaction_type: str,
                                  plaid_config: Dict) -> Dict:
    """
    Categorize transaction using Plaid Personal Finance Category taxonomy.
    
    Args:
        description: Transaction description
        merchant_name: Extracted merchant name
        amount: Transaction amount
        transaction_type: Type of transaction
        plaid_config: Plaid categories configuration
        
    Returns:
        Dictionary with category information and confidence score
    """
    cleaned_desc = description.lower()
    
    # Special case: Handle transfer directions for checking/savings
    if any(transfer in cleaned_desc for transfer in ['transfer', 'online banking']):
        if transaction_type.lower() in ['withdrawal', 'debit']:
            return {
                'primary_category': 'TRANSFER_OUT',
                'detailed_category': 'TRANSFER_OUT_ACCOUNT_TRANSFER',
                'confidence': 0.95,
                'method': 'transfer_direction'
            }
        else:
            return {
                'primary_category': 'TRANSFER_IN',
                'detailed_category': 'TRANSFER_IN_ACCOUNT_TRANSFER',
                'confidence': 0.95,
                'method': 'transfer_direction'
            }
    
    # Special case: Bank fees and charges
    fee_indicators = ['overdraft', 'nsf', 'maintenance fee', 'service charge', 
                     'foreign transaction', 'late fee', 'atm fee']
    if any(fee in cleaned_desc for fee in fee_indicators):
        return {
            'primary_category': 'BANK_FEES',
            'detailed_category': 'BANK_FEES_OTHER_BANK_FEES',
            'confidence': 0.95,
            'method': 'special_case_bank_fees'
        }
    
    # Special case: Cash rewards and refunds should be income
    reward_indicators = ['cash reward', 'cashback', 'refund', 'interest earned']
    if any(reward in cleaned_desc for reward in reward_indicators):
        if 'interest earned' in cleaned_desc:
            return {
                'primary_category': 'INCOME',
                'detailed_category': 'INCOME_INTEREST_EARNED',
                'confidence': 0.95,
                'method': 'special_case_interest'
            }
        else:
            return {
                'primary_category': 'INCOME',
                'detailed_category': 'INCOME_OTHER_INCOME',
                'confidence': 0.95,
                'method': 'special_case_income'
            }
    
    # Check Plaid categories for matches
    best_match = None
    highest_confidence = 0.0
    
    for primary_category, subcategories in plaid_config.items():
        # Skip transfer categories as we handled those above
        if primary_category in ['TRANSFER_IN', 'TRANSFER_OUT']:
            continue
            
        for subcategory, keywords in subcategories.items():
            for keyword in keywords:
                # Exact keyword match in description
                if keyword in cleaned_desc:
                    confidence = 0.9
                    if confidence > highest_confidence:
                        best_match = {
                            'primary_category': primary_category,
                            'detailed_category': subcategory,
                            'confidence': confidence,
                            'method': 'exact_keyword'
                        }
                        highest_confidence = confidence
                
                # Fuzzy match on merchant name
                if fuzzy_match(keyword, merchant_name.lower(), 0.7):
                    confidence = 0.8
                    if confidence > highest_confidence:
                        best_match = {
                            'primary_category': primary_category,
                            'detailed_category': subcategory,
                            'confidence': confidence,
                            'method': 'fuzzy_merchant'
                        }
                        highest_confidence = confidence
    
    # Default fallback
    if not best_match or highest_confidence < 0.5:
        return {
            'primary_category': 'OTHER',
            'detailed_category': 'OTHER_OTHER',
            'confidence': 0.1,
            'method': 'default'
        }
    
    return best_match


def apply_custom_mappings(description: str, merchant_name: str,
                         custom_mappings: Dict) -> Optional[Dict]:
    """
    Apply custom merchant mappings for improved categorization accuracy.
    
    Args:
        description: Transaction description
        merchant_name: Extracted merchant name
        custom_mappings: Custom mappings from config files
        
    Returns:
        Category information if match found, None otherwise
    """
    cleaned_desc = description.lower()
    cleaned_merchant = merchant_name.lower()
    
    # Check all mapping sections
    for section_name, mappings in custom_mappings.items():
        if section_name.endswith('_examples'):
            continue  # Skip template examples
            
        for pattern, mapping in mappings.items():
            pattern_lower = pattern.lower()
            
            # Check for exact match in description
            if pattern_lower in cleaned_desc:
                return {
                    'primary_category': mapping['category'],
                    'detailed_category': mapping['subcategory'], 
                    'confidence': 0.95,
                    'method': 'custom_mapping',
                    'merchant_override': mapping.get('name', merchant_name)
                }
            
            # Check for fuzzy match on merchant name
            if fuzzy_match(pattern_lower, cleaned_merchant, 0.8):
                return {
                    'primary_category': mapping['category'],
                    'detailed_category': mapping['subcategory'],
                    'confidence': 0.90,
                    'method': 'custom_fuzzy',
                    'merchant_override': mapping.get('name', merchant_name)
                }
    
    return None


def enrich_single_transaction(transaction: Dict, plaid_config: Dict, 
                            merchant_config: Dict, personal_config: Dict) -> Dict:
    """
    Enrich a single transaction with merchant name and category information.
    
    Args:
        transaction: Original transaction dictionary
        plaid_config: Plaid taxonomy configuration
        merchant_config: Public merchant mappings
        personal_config: Personal merchant mappings
        
    Returns:
        Enriched transaction dictionary
    """
    description = transaction.get('description', '')
    account_type = transaction.get('account_type', '').lower()
    amount = transaction.get('amount', 0)
    transaction_type = transaction.get('transaction_type', '')
    
    # For credit cards, make amounts negative for expenses
    if account_type == 'credit':
        amount = -amount
    
    # Extract merchant name
    merchant_name = extract_merchant_name(description)
    
    # Try custom mappings first (personal, then public)
    category_info = None
    
    # Check personal mappings first
    if personal_config:
        category_info = apply_custom_mappings(description, merchant_name, personal_config)
    
    # If no personal match, try public merchant mappings
    if not category_info and merchant_config:
        category_info = apply_custom_mappings(description, merchant_name, merchant_config)
    
    # If no custom mapping, use Plaid taxonomy
    if not category_info:
        category_info = categorize_with_plaid_taxonomy(
            description, merchant_name, amount, transaction_type, plaid_config
        )
    
    # Apply merchant name override if specified
    if 'merchant_override' in category_info:
        merchant_name = category_info['merchant_override']
        del category_info['merchant_override']
    
    # Create enriched transaction
    enriched = transaction.copy()
    enriched.update({
        'merchant_name': merchant_name,
        'primary_category': category_info['primary_category'],
        'detailed_category': category_info['detailed_category'],
        'confidence': category_info['confidence'],
        'categorization_method': category_info['method'],
        'amount': amount,
        'original_amount': transaction.get('amount', 0)
    })
    
    return enriched


def process_transaction_enrichment(input_file: str = "output/financial_transactions.json",
                                 output_file: str = "output/enriched_transactions.json") -> None:
    """
    Process all transactions and enrich with merchant names and categories.
    
    Main function that coordinates the enrichment process:
    1. Load configuration files
    2. Load transactions from JSON
    3. Enrich each transaction
    4. Save enriched results
    5. Display summary statistics
    
    Args:
        input_file: Path to input transactions JSON file
        output_file: Path to output enriched transactions JSON file
    """
    print(f"Loading transactions from {input_file}...")
    
    # Load transactions
    try:
        transactions = load_transactions_from_json(input_file)
    except Exception as e:
        print(f"Error loading transactions: {e}")
        return
    
    if not transactions:
        print("No transactions found to process")
        return
    
    # Load configuration files
    try:
        plaid_config = load_config('config/plaid_categories.toml')
        merchant_config = load_config('config/merchant_mappings.toml')
        try:
            personal_config = load_config('config/personal_mappings.toml')
        except FileNotFoundError:
            print("Note: Personal mappings not found, using public mappings only")
            personal_config = {}
    except Exception as e:
        print(f"Error loading configuration: {e}")
        return
    
    total_transactions = len(transactions)
    print(f"Processing {total_transactions} transactions...")
    
    enriched_transactions = []
    
    # Process each transaction with progress bar
    for i, transaction in enumerate(transactions):
        try:
            enriched = enrich_single_transaction(
                transaction, plaid_config, merchant_config, personal_config
            )
            enriched_transactions.append(enriched)
        except Exception as e:
            print(f"\nWarning: Error processing transaction {i+1}: {e}")
            print(f"Transaction data: {transaction}")
            # Add original transaction without enrichment
            enriched_transactions.append(transaction)
            continue
        
        # Show progress
        show_progress(i + 1, total_transactions)
    
    print()  # New line after progress bar
    
    # Save enriched transactions
    print(f"Saving enriched transactions to {output_file}...")
    save_transactions_to_json(enriched_transactions, output_file)
    
    # Calculate and display summary statistics
    category_counts = {}
    confidence_total = 0
    method_counts = {}
    
    for transaction in enriched_transactions:
        category = transaction.get('primary_category', 'UNKNOWN')
        category_counts[category] = category_counts.get(category, 0) + 1
        
        confidence = transaction.get('confidence', 0)
        confidence_total += confidence
        
        method = transaction.get('categorization_method', 'unknown')
        method_counts[method] = method_counts.get(method, 0) + 1
    
    avg_confidence = confidence_total / len(enriched_transactions) if enriched_transactions else 0
    
    print(f"\nEnrichment Complete!")
    print(f"Average confidence: {avg_confidence:.2f}")
    print(f"Categories found: {len(category_counts)}")
    
    print("\nTop categories:")
    for category, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
        percentage = (count / total_transactions) * 100
        print(f"  {category}: {count} transactions ({percentage:.1f}%)")
    
    print("\nCategorization methods:")
    for method, count in sorted(method_counts.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / total_transactions) * 100
        print(f"  {method}: {count} transactions ({percentage:.1f}%)")


def categorize_transaction(description: str, amount: float = 0, 
                          transaction_type: str = "") -> Dict:
    """
    Legacy function for backward compatibility.
    
    Categorizes a single transaction using Plaid PFC taxonomy.
    This function maintains compatibility with existing code.
    
    Args:
        description: Transaction description
        amount: Transaction amount (optional)
        transaction_type: Transaction type (optional)
        
    Returns:
        Dictionary with category information
    """
    try:
        plaid_config = load_config('config/plaid_categories.toml')
        merchant_name = extract_merchant_name(description)
        return categorize_with_plaid_taxonomy(
            description, merchant_name, amount, transaction_type, plaid_config
        )
    except Exception as e:
        print(f"Error in categorize_transaction: {e}")
        return {
            'primary_category': 'OTHER',
            'detailed_category': 'OTHER_OTHER',
            'confidence': 0.1,
            'method': 'error'
        }


def analyze_categorization_accuracy(enriched_file: str = "output/enriched_transactions.json") -> None:
    """
    Analyze categorization accuracy and provide insights for improvement.
    
    Args:
        enriched_file: Path to enriched transactions JSON file
    """
    try:
        transactions = load_transactions_from_json(enriched_file)
    except Exception as e:
        print(f"Error loading enriched transactions: {e}")
        return
    
    if not transactions:
        print("No enriched transactions found")
        return
    
    print(f"Analyzing {len(transactions)} enriched transactions...")
    
    # Confidence distribution
    confidence_ranges = {
        'High (0.9-1.0)': 0,
        'Medium (0.7-0.9)': 0,
        'Low (0.5-0.7)': 0,
        'Very Low (0.0-0.5)': 0
    }
    
    low_confidence_transactions = []
    
    for transaction in transactions:
        confidence = transaction.get('confidence', 0)
        
        if confidence >= 0.9:
            confidence_ranges['High (0.9-1.0)'] += 1
        elif confidence >= 0.7:
            confidence_ranges['Medium (0.7-0.9)'] += 1
        elif confidence >= 0.5:
            confidence_ranges['Low (0.5-0.7)'] += 1
        else:
            confidence_ranges['Very Low (0.0-0.5)'] += 1
            low_confidence_transactions.append(transaction)
    
    print("\nConfidence Distribution:")
    for range_name, count in confidence_ranges.items():
        percentage = (count / len(transactions)) * 100
        print(f"  {range_name}: {count} transactions ({percentage:.1f}%)")
    
    # Show low confidence transactions for review
    if low_confidence_transactions:
        print(f"\nLow confidence transactions (showing first 10):")
        for i, transaction in enumerate(low_confidence_transactions[:10]):
            print(f"  {i+1}. {transaction.get('description', 'N/A')[:50]}...")
            print(f"     Merchant: {transaction.get('merchant_name', 'N/A')}")
            print(f"     Category: {transaction.get('primary_category', 'N/A')}")
            print(f"     Confidence: {transaction.get('confidence', 0):.2f}")
            print()
    
    # Suggest improvements
    print("Suggestions for improvement:")
    if confidence_ranges['Very Low (0.0-0.5)'] > 0:
        print(f"  - Add custom mappings for {confidence_ranges['Very Low (0.0-0.5)']} low-confidence transactions")
    if confidence_ranges['Low (0.5-0.7)'] > 0:
        print(f"  - Review and refine {confidence_ranges['Low (0.5-0.7)']} medium-low confidence transactions")
    
    print(f"  - Overall accuracy: {(confidence_ranges['High (0.9-1.0)'] + confidence_ranges['Medium (0.7-0.9)']) / len(transactions) * 100:.1f}%")


if __name__ == "__main__":
    # Simple command line usage
    import sys
    
    from utils import ensure_directories_exist
    ensure_directories_exist()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "analyze":
            # Run analysis mode
            analyze_categorization_accuracy()
        else:
            # Custom input/output files
            input_file = sys.argv[1]
            output_file = sys.argv[2] if len(sys.argv) > 2 else "output/enriched_transactions.json"
            process_transaction_enrichment(input_file, output_file)
    else:
        # Default processing
        process_transaction_enrichment()