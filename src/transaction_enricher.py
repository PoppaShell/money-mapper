#!/usr/bin/env python3
"""
Transaction Enricher - Add categories and merchant names to transactions.

This module enriches parsed transactions with merchant names and categories
using configurable mappings and the Plaid Personal Finance Category taxonomy.
"""

import os
import re
import sys
from datetime import datetime
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple

# Add the src directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import load_config, load_transactions_from_json, save_transactions_to_json, sanitize_description
from config_manager import get_config_manager


def load_enrichment_config(config_dir: str = "config") -> Dict:
    """
    Load all enrichment configuration files using config manager.
    
    Args:
        config_dir: Configuration directory
        
    Returns:
        Dictionary containing all configuration data
    """
    try:
        # Get configuration manager
        config_manager = get_config_manager(config_dir)
        
        # Get file paths from centralized configuration
        enrichment_files = config_manager.get_enrichment_files()
        
        # Load Plaid categories (required)
        plaid_file = enrichment_files['plaid_categories']
        if not os.path.exists(plaid_file):
            print(f"Error: Required file {plaid_file} not found")
            sys.exit(1)
        plaid_categories = load_config(plaid_file)
        
        # Load private mappings (optional)
        private_mappings_file = enrichment_files['private_mappings']
        if os.path.exists(private_mappings_file):
            private_mappings = load_config(private_mappings_file)
        else:
            print(f"Warning: {private_mappings_file} not found. Personal mappings will not be available.")
            private_mappings = {}
        
        # Load public mappings (optional)
        public_mappings_file = enrichment_files['public_mappings']
        if os.path.exists(public_mappings_file):
            public_mappings = load_config(public_mappings_file)
        else:
            print(f"Warning: {public_mappings_file} not found. Public merchant mappings will not be available.")
            public_mappings = {}
        
        return {
            'plaid_categories': plaid_categories,
            'private_mappings': private_mappings,
            'public_mappings': public_mappings
        }
        
    except Exception as e:
        print(f"Error loading enrichment configuration: {e}")
        sys.exit(1)


def process_transaction_enrichment(input_file: str, output_file: str, debug: bool = False) -> None:
    """
    Process transaction enrichment using centralized configuration.
    
    Args:
        input_file: Path to input JSON file with parsed transactions
        output_file: Path to output JSON file for enriched transactions
        debug: Enable debug output
    """
    if debug:
        print("Loading enrichment configuration...")
    
    # Load configuration
    config = load_enrichment_config()
    
    # Load transactions
    transactions = load_transactions_from_json(input_file)
    if not transactions:
        print(f"No transactions found in {input_file}")
        return
    
    if debug:
        print(f"Processing {len(transactions)} transactions...")
    
    # Get fuzzy matching threshold from config manager
    config_manager = get_config_manager()
    fuzzy_threshold = config_manager.get_fuzzy_threshold('enrichment')

    # Enrich each transaction
    enriched_transactions = []
    for i, transaction in enumerate(transactions):
        # Show progress bar (suppressed in debug mode to avoid clutter)
        if not debug:
            from utils import show_progress
            show_progress(i + 1, len(transactions))

        if debug and (i + 1) % 50 == 0:
            print(f"  Processed {i + 1}/{len(transactions)} transactions")

        enriched = enrich_transaction(
            transaction,
            config['private_mappings'],
            config['public_mappings'],
            config['plaid_categories'],
            fuzzy_threshold,
            debug
        )
        enriched_transactions.append(enriched)

    # Print newline after progress bar
    if not debug:
        print()

    # Save enriched transactions
    save_transactions_to_json(enriched_transactions, output_file)

    if debug:
        print(f"Enrichment complete. Results saved to {output_file}")


def enrich_transaction(transaction: Dict, private_mappings: Dict, public_mappings: Dict, 
                      plaid_categories: Dict, fuzzy_threshold: float = 0.7, 
                      debug: bool = False) -> Dict:
    """
    Enrich a single transaction with category and merchant information.
    
    Args:
        transaction: Transaction dictionary
        private_mappings: Private/personal mappings
        public_mappings: Public/merchant mappings
        plaid_categories: Plaid category definitions
        fuzzy_threshold: Threshold for fuzzy matching
        debug: Enable debug output
        
    Returns:
        Enriched transaction dictionary
    """
    # Start with original transaction data
    enriched = transaction.copy()

    # Extract basic info
    description = transaction.get('description', '').strip()
    amount = transaction.get('amount', 0.0)

    # Extract merchant name
    merchant_name = extract_merchant_name(description)
    enriched['merchant_name'] = merchant_name

    # Try to find mapping (priority order: private -> public -> plaid)
    category_result = find_merchant_mapping(
        description, private_mappings, public_mappings, plaid_categories,
        fuzzy_threshold, debug
    )

    # Add categorization results
    enriched.update(category_result)

    # Add metadata
    enriched['enrichment_date'] = transaction.get('processing_date', '')

    # Apply privacy redaction AFTER categorization (so matching still works)
    # Load privacy configuration from settings.toml
    try:
        config_manager = get_config_manager()
        settings_file = config_manager.get_file_path('settings')
        settings_config = load_config(settings_file)
        privacy_config = settings_config.get('privacy', {})

        # Redact the description in the enriched output
        enriched['description'] = sanitize_description(
            description,
            sanitization_patterns=None,  # Legacy patterns not used here
            privacy_config=privacy_config
        )
    except Exception as e:
        if debug:
            print(f"Warning: Could not apply privacy redaction: {e}")
        # If redaction fails, keep original description

    return enriched


def extract_merchant_name(description: str) -> str:
    """
    Extract clean merchant name from transaction description.
    
    Args:
        description: Raw transaction description
        
    Returns:
        Cleaned merchant name
    """
    # Remove common banking prefixes
    cleaned = re.sub(r'^(CHECKCARD|DEBIT\s*CARD|POS|ACH|DES:|REF\s*#?)', '', description, flags=re.IGNORECASE)
    
    # Remove card numbers and dates
    cleaned = re.sub(r'\d{4}\s*\*+\d{4}|\d{2}/\d{2}', '', cleaned)
    
    # Remove reference numbers and codes
    cleaned = re.sub(r'#\d+|\b\d{6,}\b', '', cleaned)
    
    # Remove extra whitespace and normalize
    cleaned = ' '.join(cleaned.split()).strip()
    
    # Take meaningful part (usually first few words)
    words = cleaned.split()
    if len(words) > 4:
        # Keep first 4 words for merchant name
        merchant_name = ' '.join(words[:4])
    else:
        merchant_name = cleaned
    
    return merchant_name.strip()


def find_merchant_mapping(description: str, private_mappings: Dict, public_mappings: Dict,
                         plaid_categories: Dict, fuzzy_threshold: float = 0.7,
                         debug: bool = False) -> Dict:
    """
    Find the best category mapping for a transaction.
    
    Args:
        description: Transaction description
        private_mappings: Private/personal mappings
        public_mappings: Public/merchant mappings  
        plaid_categories: Plaid category definitions
        fuzzy_threshold: Threshold for fuzzy matching
        debug: Enable debug output
        
    Returns:
        Dictionary with categorization results
    """
    cleaned_desc = description.lower().strip()
    merchant_name = extract_merchant_name(description).lower()
    
    # 1. Try private mappings first (highest priority)
    result = apply_custom_mappings(description, merchant_name, private_mappings, 'private_mapping', fuzzy_threshold)
    if result:
        if debug:
            print(f"    Private mapping found: {result['category']}")
        return result
    
    # 2. Try public mappings second
    result = apply_custom_mappings(description, merchant_name, public_mappings, 'public_mapping', fuzzy_threshold)
    if result:
        if debug:
            print(f"    Public mapping found: {result['category']}")
        return result
    
    # 3. Try Plaid keyword matching (fallback)
    result = apply_plaid_keyword_matching(description, merchant_name, plaid_categories)
    if result:
        if debug:
            print(f"    Plaid keyword match: {result['category']}")
        return result
    
    # 4. Default to uncategorized
    if debug:
        print(f"    No category found for: {description}")
    
    return {
        'category': 'UNCATEGORIZED',
        'subcategory': 'UNCATEGORIZED',
        'confidence': 0.1,
        'categorization_method': 'none'
    }


def apply_custom_mappings(description: str, merchant_name: str,
                         mappings: Dict, method_name: str, fuzzy_threshold: float = 0.7) -> Optional[Dict]:
    """
    Apply custom mappings (private or public) to find category.
    
    Args:
        description: Transaction description
        merchant_name: Extracted merchant name
        mappings: Custom mappings dictionary
        method_name: Name of method for tracking
        fuzzy_threshold: Threshold for fuzzy matching
        
    Returns:
        Categorization result or None if no match
    """
    cleaned_desc = description.lower().strip()
    cleaned_merchant = merchant_name.lower().strip()
    
    # Flatten mappings to check all categories
    for category_key, category_data in mappings.items():
        if not isinstance(category_data, dict):
            continue
            
        for subcategory_key, subcategory_data in category_data.items():
            if not isinstance(subcategory_data, dict):
                continue
            
            # Check each merchant pattern in this subcategory
            for pattern, mapping_data in subcategory_data.items():
                if not isinstance(mapping_data, dict):
                    continue
                
                pattern_lower = pattern.lower()
                
                # Method 1: Exact substring match in description
                if pattern_lower in cleaned_desc:
                    return create_mapping_result(mapping_data, method_name, 0.95)
                
                # Method 2: Partial word matching
                pattern_words = pattern_lower.split()
                desc_words = cleaned_desc.split()
                matches = sum(1 for word in pattern_words if word in desc_words)
                if len(pattern_words) > 0 and matches / len(pattern_words) >= 0.6:
                    confidence = 0.85 + (matches / len(pattern_words)) * 0.1
                    return create_mapping_result(mapping_data, method_name, confidence)
                
                # Method 3: Fuzzy matching on merchant name
                if cleaned_merchant and len(pattern_lower) > 2:
                    similarity = fuzzy_match_similarity(pattern_lower, cleaned_merchant)
                    if similarity >= fuzzy_threshold:
                        confidence = min(0.80, similarity)
                        return create_mapping_result(mapping_data, 'fuzzy_match', confidence)
                
                # Method 4: Contains matching
                if (cleaned_merchant and 
                    (cleaned_merchant in pattern_lower or pattern_lower in cleaned_merchant)):
                    return create_mapping_result(mapping_data, method_name, 0.75)
    
    return None


def create_mapping_result(mapping_data: Dict, method: str, confidence: float) -> Dict:
    """
    Create standardized mapping result.
    
    Args:
        mapping_data: Mapping configuration data
        method: Categorization method used
        confidence: Confidence score
        
    Returns:
        Standardized result dictionary
    """
    return {
        'category': mapping_data.get('category', 'UNCATEGORIZED'),
        'subcategory': mapping_data.get('subcategory', 'UNCATEGORIZED'),
        'merchant_name': mapping_data.get('name', ''),
        'confidence': confidence,
        'categorization_method': method
    }


def apply_plaid_keyword_matching(description: str, merchant_name: str, plaid_categories: Dict) -> Optional[Dict]:
    """
    Apply Plaid keyword matching for categorization.
    
    Args:
        description: Transaction description
        merchant_name: Extracted merchant name
        plaid_categories: Plaid category definitions
        
    Returns:
        Categorization result or None if no match
    """
    cleaned_desc = description.lower().strip()
    cleaned_merchant = merchant_name.lower().strip()
    search_text = f"{cleaned_desc} {cleaned_merchant}".strip()
    
    best_match = None
    best_score = 0
    
    # Check each Plaid category
    for category_key, category_data in plaid_categories.items():
        if not isinstance(category_data, dict):
            continue
            
        keywords = category_data.get('keywords', [])
        if not keywords:
            continue
        
        # Count keyword matches
        matches = 0
        for keyword in keywords:
            if keyword.lower() in search_text:
                matches += 1
        
        # Calculate score based on matches
        if matches > 0:
            score = matches / len(keywords)
            if score > best_score:
                best_score = score
                best_match = {
                    'category': category_key.split('.')[0],
                    'subcategory': category_key,
                    'confidence': min(0.70, 0.4 + score * 0.3),
                    'categorization_method': 'plaid_keyword'
                }
    
    return best_match


def fuzzy_match_similarity(text1: str, text2: str) -> float:
    """
    Calculate fuzzy matching similarity between two strings.
    
    Args:
        text1: First string
        text2: Second string
        
    Returns:
        Similarity score between 0.0 and 1.0
    """
    return SequenceMatcher(None, text1, text2).ratio()


def analyze_categorization_accuracy(file_path: str, verbose: bool = False, debug: bool = False) -> None:
    """
    Analyze the accuracy and completeness of transaction categorization.
    
    Args:
        file_path: Path to enriched transactions JSON file
        verbose: Enable verbose output with examples
        debug: Enable debug output with detailed analysis
    """
    # Load transactions
    transactions = load_transactions_from_json(file_path)
    if not transactions:
        print(f"No transactions found in {file_path}")
        return
    
    print(f"\n=== Categorization Analysis ===")
    print(f"Total transactions: {len(transactions)}")
    
    # Basic statistics
    categorized = sum(1 for t in transactions if t.get('category') and t.get('category') != 'UNCATEGORIZED')
    uncategorized = len(transactions) - categorized
    categorization_rate = (categorized / len(transactions)) * 100
    
    print(f"Categorized: {categorized} ({categorization_rate:.1f}%)")
    print(f"Uncategorized: {uncategorized} ({100 - categorization_rate:.1f}%)")
    
    # Confidence distribution
    high_confidence = sum(1 for t in transactions if t.get('confidence', 0) >= 0.8)
    medium_confidence = sum(1 for t in transactions if 0.5 <= t.get('confidence', 0) < 0.8)
    low_confidence = sum(1 for t in transactions if t.get('confidence', 0) < 0.5)
    
    print(f"\nConfidence Distribution:")
    print(f"  High (≥0.8): {high_confidence} ({(high_confidence/len(transactions))*100:.1f}%)")
    print(f"  Medium (0.5-0.8): {medium_confidence} ({(medium_confidence/len(transactions))*100:.1f}%)")
    print(f"  Low (<0.5): {low_confidence} ({(low_confidence/len(transactions))*100:.1f}%)")
    
    # Method distribution
    methods = {}
    for transaction in transactions:
        method = transaction.get('categorization_method', 'unknown')
        methods[method] = methods.get(method, 0) + 1
    
    print(f"\nCategorization Methods:")
    for method, count in sorted(methods.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / len(transactions)) * 100
        print(f"  {method}: {count} ({percentage:.1f}%)")
    
    # Category distribution
    if verbose or debug:
        categories = {}
        for transaction in transactions:
            category = transaction.get('category', 'UNCATEGORIZED')
            categories[category] = categories.get(category, 0) + 1
        
        print(f"\nTop Categories:")
        for category, count in sorted(categories.items(), key=lambda x: x[1], reverse=True)[:10]:
            percentage = (count / len(transactions)) * 100
            print(f"  {category}: {count} ({percentage:.1f}%)")
    
    # Show examples if verbose
    if verbose:
        print(f"\nUncategorized Examples:")
        uncategorized_examples = [t for t in transactions if t.get('category') == 'UNCATEGORIZED'][:5]
        for transaction in uncategorized_examples:
            desc = transaction.get('description', '')[:50]
            amount = transaction.get('amount', 0)
            print(f"  ${amount:8.2f} - {desc}")
        
        print(f"\nHigh Confidence Examples:")
        high_conf_examples = [t for t in transactions if t.get('confidence', 0) >= 0.9][:5]
        for transaction in high_conf_examples:
            desc = transaction.get('description', '')[:30]
            category = transaction.get('category', '')
            confidence = transaction.get('confidence', 0)
            method = transaction.get('categorization_method', '')
            print(f"  {category} ({confidence:.2f}, {method}) - {desc}")
    
    # Debug information
    if debug:
        print(f"\nDebug Information:")
        
        # Method effectiveness
        print(f"\nMethod Effectiveness:")
        for method in methods.keys():
            method_transactions = [t for t in transactions if t.get('categorization_method') == method]
            if method_transactions:
                avg_confidence = sum(t.get('confidence', 0) for t in method_transactions) / len(method_transactions)
                print(f"  {method}: avg confidence {avg_confidence:.3f}")
        
        # Merchant name extraction quality
        print(f"\nMerchant Name Extraction:")
        merchants_with_names = sum(1 for t in transactions if t.get('merchant_name'))
        print(f"  Transactions with merchant names: {merchants_with_names} ({(merchants_with_names/len(transactions))*100:.1f}%)")
        
        # Show some merchant name examples
        print(f"\nMerchant Name Examples:")
        for transaction in transactions[:10]:
            desc = transaction.get('description', '')[:40]
            merchant = transaction.get('merchant_name', 'N/A')
            print(f"  '{desc}' -> '{merchant}'")


def generate_enrichment_report(transactions: List[Dict], output_file: str = None) -> str:
    """
    Generate a detailed enrichment report.
    
    Args:
        transactions: List of enriched transactions
        output_file: Optional file to save report
        
    Returns:
        Report text
    """
    if not transactions:
        return "No transactions to analyze."
    
    report_lines = []
    report_lines.append("=== Transaction Enrichment Report ===")
    report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f"Total Transactions: {len(transactions)}")
    report_lines.append("")
    
    # Summary statistics
    categorized = sum(1 for t in transactions if t.get('category') != 'UNCATEGORIZED')
    report_lines.append(f"Categorization Rate: {(categorized/len(transactions)*100):.1f}%")
    
    # Average confidence by method
    methods = {}
    for transaction in transactions:
        method = transaction.get('categorization_method', 'unknown')
        confidence = transaction.get('confidence', 0)
        if method not in methods:
            methods[method] = []
        methods[method].append(confidence)
    
    report_lines.append("\nMethod Performance:")
    for method, confidences in methods.items():
        avg_conf = sum(confidences) / len(confidences)
        report_lines.append(f"  {method}: {len(confidences)} txns, avg confidence {avg_conf:.3f}")
    
    # Top categories
    categories = {}
    amounts = {}
    for transaction in transactions:
        category = transaction.get('category', 'UNCATEGORIZED')
        amount = abs(float(transaction.get('amount', 0)))
        categories[category] = categories.get(category, 0) + 1
        amounts[category] = amounts.get(category, 0) + amount
    
    report_lines.append("\nTop Categories by Transaction Count:")
    for category, count in sorted(categories.items(), key=lambda x: x[1], reverse=True)[:10]:
        total_amount = amounts.get(category, 0)
        report_lines.append(f"  {category}: {count} transactions, ${total_amount:,.2f}")
    
    report_text = "\n".join(report_lines)
    
    # Save to file if requested
    if output_file:
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report_text)
        except Exception as e:
            print(f"Error saving report to {output_file}: {e}")
    
    return report_text


if __name__ == "__main__":
    """Test the transaction enricher."""
    import sys
    
    if len(sys.argv) != 3:
        print("Usage: python transaction_enricher.py <input_file> <output_file>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    print("Testing transaction enricher...")
    process_transaction_enrichment(input_file, output_file, debug=True)
    print("Enrichment complete!")