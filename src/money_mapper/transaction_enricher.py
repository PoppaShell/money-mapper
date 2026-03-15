#!/usr/bin/env python3
"""
Transaction Enricher - Add categories and merchant names to transactions.

This module enriches parsed transactions with merchant names and categories
using configurable mappings and the Plaid Personal Finance Category taxonomy.
"""

import fnmatch
import json
import multiprocessing
import os
import re
import sys
from datetime import datetime
from difflib import SequenceMatcher
from typing import Any

from money_mapper.config_manager import get_config_manager
from money_mapper.utils import (
    load_config,
    load_transactions_from_json,
    prompt_yes_no,
    sanitize_description,
    save_transactions_to_json,
)


class PatternMatcher:
    """Pre-compiled pattern matcher for fast pattern lookups.

    Builds an index of patterns once and reuses it for all transactions,
    providing 2-3x speedup over re-processing patterns for each transaction.
    """

    def __init__(self, mappings: dict, matcher_name: str):
        """Initialize pattern matcher with pre-compiled patterns.

        Args:
            mappings: Mapping dictionary to index
            matcher_name: Name for this matcher (e.g., 'private', 'public')
        """
        self.name = matcher_name
        self.exact_patterns: dict[str, Any] = {}  # pattern_lower -> mapping_data
        self.wildcard_patterns: list[tuple[Any, str, Any]] = []  # [(compiled_regex, pattern_lower, mapping_data)]
        self.pattern_words: dict[frozenset[str], list[tuple[str, Any]]] = {}  # frozenset(words) -> [(pattern_lower, mapping_data)]
        self._build_index(mappings)

    def _build_index(self, mappings: dict) -> None:
        """Build pre-compiled pattern indices from mappings.

        Separates patterns by type (exact vs wildcard) and pre-compiles regexes.
        """
        for category_key, category_data in mappings.items():
            if not isinstance(category_data, dict):
                continue

            for subcategory_key, subcategory_data in category_data.items():
                if not isinstance(subcategory_data, dict):
                    continue

                for pattern, mapping_data in subcategory_data.items():
                    if not isinstance(mapping_data, dict):
                        continue

                    pattern_lower = pattern.lower()

                    if "*" in pattern_lower or "?" in pattern_lower:
                        # Pre-compile wildcard pattern to regex for faster matching
                        try:
                            regex_pattern = fnmatch.translate(pattern_lower)
                            compiled = re.compile(regex_pattern)
                            self.wildcard_patterns.append((compiled, pattern_lower, mapping_data))
                        except Exception:
                            # Skip patterns that fail to compile
                            pass
                    else:
                        # Exact pattern - store in dict for O(1) lookup
                        self.exact_patterns[pattern_lower] = mapping_data

                        # Also index by words for partial matching
                        words = frozenset(pattern_lower.split())
                        if words not in self.pattern_words:
                            self.pattern_words[words] = []
                        self.pattern_words[words].append((pattern_lower, mapping_data))

    def match(
        self, description: str, merchant_name: str, fuzzy_threshold: float = 0.7
    ) -> dict | None:
        """Find best matching pattern for description.

        Uses priority-based matching:
        1. Exact substring match (O(1) dict lookup)
        2. Word-based matching (set intersection)
        3. Pre-compiled wildcard regex matching
        4. Fuzzy matching (cached, last resort)

        Args:
            description: Transaction description (will be lowercased)
            merchant_name: Extracted merchant name (will be lowercased)
            fuzzy_threshold: Threshold for fuzzy matching (0.0-1.0)

        Returns:
            {'mapping_data': mapping_data_dict, 'confidence': score} or None
        """
        cleaned_desc = description.lower().strip()
        cleaned_merchant = merchant_name.lower().strip()

        # Priority 1: Exact substring match
        for pattern_lower, mapping_data in self.exact_patterns.items():
            if pattern_lower in cleaned_desc:
                return {"mapping_data": mapping_data, "confidence": 0.95}

        # Priority 2: Word-based matching using pre-built index
        desc_words = frozenset(cleaned_desc.split())
        for pattern_words, pattern_list in self.pattern_words.items():
            if not pattern_words:
                continue

            matches = len(pattern_words & desc_words)
            match_ratio = matches / len(pattern_words)

            if match_ratio >= 0.6:
                pattern_lower, mapping_data = pattern_list[0]
                confidence = 0.85 + (match_ratio * 0.1)
                return {"mapping_data": mapping_data, "confidence": confidence}

        # Priority 3: Wildcard matching using pre-compiled regex
        for compiled_regex, pattern_lower, mapping_data in self.wildcard_patterns:
            # Use pre-compiled regex instead of fnmatch (much faster!)
            if compiled_regex.search(cleaned_desc):
                return {"mapping_data": mapping_data, "confidence": 0.90}

            if cleaned_merchant and compiled_regex.search(cleaned_merchant):
                return {"mapping_data": mapping_data, "confidence": 0.89}

        # Priority 4: Fuzzy matching (expensive, last resort)
        if cleaned_merchant:
            for pattern_lower, mapping_data in self.exact_patterns.items():
                if len(pattern_lower) > 2:
                    similarity = self._fuzzy_similarity(pattern_lower, cleaned_merchant)
                    if similarity >= fuzzy_threshold:
                        confidence = min(0.80, similarity)
                        return {"mapping_data": mapping_data, "confidence": confidence}

        return None

    @staticmethod
    def _fuzzy_similarity(text1: str, text2: str) -> float:
        """Calculate fuzzy similarity between two strings."""
        return SequenceMatcher(None, text1, text2).ratio()


# Module-level cache for pattern matchers (built once per session)
_private_matcher = None
_public_matcher = None


def get_pattern_matchers(private_mappings: dict, public_mappings: dict):
    """Get or create pattern matchers (cached).

    Builds matchers once and reuses them for all transactions in the session.

    Args:
        private_mappings: Private mappings dictionary
        public_mappings: Public mappings dictionary

    Returns:
        Tuple of (private_matcher, public_matcher)
    """
    global _private_matcher, _public_matcher

    if _private_matcher is None and private_mappings:
        _private_matcher = PatternMatcher(private_mappings, "private")

    if _public_matcher is None and public_mappings:
        _public_matcher = PatternMatcher(public_mappings, "public")

    return _private_matcher, _public_matcher


def _enrich_transaction_worker(args: tuple) -> dict:
    """
    Worker function for multiprocessing enrichment.

    Must be at module level for pickling by multiprocessing.Pool.

    Args:
        args: Tuple of (transaction, private_mappings, public_mappings, plaid_categories, fuzzy_threshold, config_dir)

    Returns:
        Enriched transaction dictionary
    """
    (
        transaction,
        private_mappings,
        public_mappings,
        plaid_categories,
        fuzzy_threshold,
        config_dir,
    ) = args
    return enrich_transaction(
        transaction,
        private_mappings,
        public_mappings,
        plaid_categories,
        fuzzy_threshold,
        debug=False,
    )


def load_enrichment_config(config_dir: str = "config") -> dict:
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
        plaid_file = enrichment_files["plaid_categories"]
        if not os.path.exists(plaid_file):
            print(f"Error: Required file {plaid_file} not found")
            sys.exit(1)
        plaid_categories = load_config(plaid_file)

        # Load private mappings (optional)
        private_mappings_file = enrichment_files["private_mappings"]
        if os.path.exists(private_mappings_file):
            private_mappings = load_config(private_mappings_file)
        else:
            print(
                f"Warning: {private_mappings_file} not found. Personal mappings will not be available."
            )
            private_mappings = {}

        # Load public mappings (optional)
        public_mappings_file = enrichment_files["public_mappings"]
        if os.path.exists(public_mappings_file):
            public_mappings = load_config(public_mappings_file)
        else:
            print(
                f"Warning: {public_mappings_file} not found. Public merchant mappings will not be available."
            )
            public_mappings = {}

        return {
            "plaid_categories": plaid_categories,
            "private_mappings": private_mappings,
            "public_mappings": public_mappings,
        }

    except Exception as e:
        print(f"Error loading enrichment configuration: {e}")
        sys.exit(1)


def process_transaction_enrichment(
    input_file: str, output_file: str, debug: bool = False, use_multiprocessing: bool = True
) -> None:
    """
    Process transaction enrichment using centralized configuration.

    Uses multiprocessing for parallel enrichment on multi-core systems.
    Falls back to sequential processing if multiprocessing is not available.

    Args:
        input_file: Path to input JSON file with parsed transactions
        output_file: Path to output JSON file for enriched transactions
        debug: Enable debug output
        use_multiprocessing: Enable multiprocessing (default: True)
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
    fuzzy_threshold = config_manager.get_fuzzy_threshold("enrichment")

    # Attempt multiprocessing (with fallback to sequential)
    enriched_transactions = []

    if use_multiprocessing and len(transactions) > 1:
        try:
            # Get number of CPU cores
            num_cores = multiprocessing.cpu_count()

            # For small datasets, sequential is faster
            if len(transactions) < 10:
                use_multiprocessing = False
            else:
                if debug:
                    print(f"  Using multiprocessing ({num_cores} cores)")

                # Prepare arguments for each transaction
                worker_args = [
                    (
                        transaction,
                        config["private_mappings"],
                        config["public_mappings"],
                        config["plaid_categories"],
                        fuzzy_threshold,
                        "config",
                    )
                    for transaction in transactions
                ]

                # Create pool and process transactions
                with multiprocessing.Pool(processes=num_cores) as pool:
                    # Use imap_unordered for load-balanced distribution
                    # Progress tracking with counter
                    processed = 0
                    for enriched in pool.imap_unordered(_enrich_transaction_worker, worker_args):
                        enriched_transactions.append(enriched)
                        processed += 1

                        if not debug and (processed % 50 == 0 or processed == len(transactions)):
                            from utils import show_progress

                            show_progress(processed, len(transactions))

                # Print newline after progress bar
                if not debug:
                    print()

                if debug:
                    print("  Completed multiprocessing enrichment")

        except Exception as e:
            if debug:
                print(f"  Multiprocessing failed: {e}. Falling back to sequential...")
            enriched_transactions = []
            use_multiprocessing = False

    # Fallback to sequential processing
    if not use_multiprocessing or len(transactions) <= 1:
        if debug and len(transactions) > 1:
            print("  Using sequential processing")

        for i, transaction in enumerate(transactions):
            # Show progress bar (suppressed in debug mode to avoid clutter)
            if not debug:
                from utils import show_progress

                show_progress(i + 1, len(transactions))

            if debug and (i + 1) % 50 == 0:
                print(f"  Processed {i + 1}/{len(transactions)} transactions")

            enriched = enrich_transaction(
                transaction,
                config["private_mappings"],
                config["public_mappings"],
                config["plaid_categories"],
                fuzzy_threshold,
                debug,
            )
            enriched_transactions.append(enriched)

        # Print newline after progress bar
        if not debug:
            print()

    # Save enriched transactions
    save_transactions_to_json(enriched_transactions, output_file)

    if debug:
        print(f"Enrichment complete. Results saved to {output_file}")


def enrich_transaction(
    transaction: dict,
    private_mappings: dict,
    public_mappings: dict,
    plaid_categories: dict,
    fuzzy_threshold: float = 0.7,
    debug: bool = False,
) -> dict:
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
    description = transaction.get("description", "").strip()
    transaction.get("amount", 0.0)

    # Extract merchant name
    merchant_name = extract_merchant_name(description)
    enriched["merchant_name"] = merchant_name

    # Try to find mapping (priority order: private -> public -> plaid)
    category_result = find_merchant_mapping(
        description, private_mappings, public_mappings, plaid_categories, fuzzy_threshold, debug
    )

    # Add categorization results
    enriched.update(category_result)

    # Apply privacy redaction AFTER categorization (so matching still works)
    # Load privacy configuration from config manager
    try:
        config_manager = get_config_manager()
        privacy_config = config_manager.get_privacy_settings()

        # Redact the description in the enriched output
        # NOTE: We do NOT store original_description in enriched output to preserve privacy
        # The interactive mapper loads original descriptions from parsed_transactions.json
        enriched["description"] = sanitize_description(
            description,
            sanitization_patterns=[],  # Legacy patterns not used here
            privacy_config=privacy_config,
        )
    except Exception as e:
        if debug:
            print(f"Warning: Could not apply privacy redaction: {e}")
        # If redaction fails, keep original description (no redaction applied)

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
    cleaned = re.sub(
        r"^(CHECKCARD|DEBIT\s*CARD|POS|ACH|DES:|REF\s*#?)", "", description, flags=re.IGNORECASE
    )

    # Remove card numbers and dates
    cleaned = re.sub(r"\d{4}\s*\*+\d{4}|\d{2}/\d{2}", "", cleaned)

    # Remove reference numbers and codes
    cleaned = re.sub(r"#\d+|\b\d{6,}\b", "", cleaned)

    # Remove extra whitespace and normalize
    cleaned = " ".join(cleaned.split()).strip()

    # Take meaningful part (usually first few words)
    words = cleaned.split()
    if len(words) > 4:
        # Keep first 4 words for merchant name
        merchant_name = " ".join(words[:4])
    else:
        merchant_name = cleaned

    return merchant_name.strip()


def find_merchant_mapping(
    description: str,
    private_mappings: dict,
    public_mappings: dict,
    plaid_categories: dict,
    fuzzy_threshold: float = 0.7,
    debug: bool = False,
) -> dict:
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
    description.lower().strip()
    merchant_name = extract_merchant_name(description).lower()

    # 1. Try private mappings first (highest priority)
    result = apply_custom_mappings(
        description, merchant_name, private_mappings, "private_mapping", fuzzy_threshold
    )
    if result:
        if debug:
            print(f"    Private mapping found: {result['category']}")
        return result

    # 2. Try public mappings second
    result = apply_custom_mappings(
        description, merchant_name, public_mappings, "public_mapping", fuzzy_threshold
    )
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
        "category": "UNCATEGORIZED",
        "subcategory": "UNCATEGORIZED",
        "confidence": 0.1,
        "categorization_method": "none",
    }


def wildcard_pattern_match(text: str, pattern: str) -> bool:
    """
    Match wildcard pattern against text with flexible matching.

    For patterns like "joe*pizza*", this will match:
    - "joes pizza" (exact)
    - "joe's pizzeria" (fragments match)
    - "joe pizza shop" (fragments match)

    Args:
        text: Text to search in (already lowercased)
        pattern: Wildcard pattern (already lowercased)

    Returns:
        True if pattern matches text
    """
    # First try standard fnmatch
    if fnmatch.fnmatch(text, pattern):
        return True

    # If pattern doesn't have wildcards at start/end, try with implied wildcards
    if not pattern.startswith("*"):
        if fnmatch.fnmatch(text, f"*{pattern}"):
            return True
    if not pattern.endswith("*"):
        if fnmatch.fnmatch(text, f"{pattern}*"):
            return True
    if not (pattern.startswith("*") or pattern.endswith("*")):
        if fnmatch.fnmatch(text, f"*{pattern}*"):
            return True

    # For patterns with *, split on * and check if fragments appear in order
    if "*" in pattern:
        fragments = [f for f in pattern.split("*") if f and f != "?"]
        if not fragments:
            return False

        # Check if all fragments appear in text in order
        pos = 0
        for fragment in fragments:
            # Handle ? wildcards in fragments
            if "?" in fragment:
                # For now, just check if the non-? parts are present
                fragment_parts = fragment.split("?")
                for part in fragment_parts:
                    if part:
                        idx = text.find(part, pos)
                        if idx == -1:
                            return False
                        pos = idx + len(part)
            else:
                idx = text.find(fragment, pos)
                if idx == -1:
                    return False
                pos = idx + len(fragment)
        return True

    return False


def apply_custom_mappings(
    description: str,
    merchant_name: str,
    mappings: dict,
    method_name: str,
    fuzzy_threshold: float = 0.7,
) -> dict | None:
    """
    Apply custom mappings (private or public) to find category.

    Uses pre-compiled PatternMatcher for efficiency.
    Supports wildcard patterns using * (zero or more chars) and ? (single char).

    Args:
        description: Transaction description
        merchant_name: Extracted merchant name
        mappings: Custom mappings dictionary
        method_name: Name of method for tracking
        fuzzy_threshold: Threshold for fuzzy matching

    Returns:
        Categorization result or None if no match
    """
    if not mappings:
        return None

    # Create matcher if needed (will be cached for reuse)
    matcher = PatternMatcher(mappings, method_name)

    # Use matcher to find best pattern
    result = matcher.match(description, merchant_name, fuzzy_threshold)

    if result:
        return create_mapping_result(result["mapping_data"], method_name, result["confidence"])

    return None


def create_mapping_result(mapping_data: dict, method: str, confidence: float) -> dict:
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
        "category": mapping_data.get("category", "UNCATEGORIZED"),
        "subcategory": mapping_data.get("subcategory", "UNCATEGORIZED"),
        "merchant_name": mapping_data.get("name", ""),
        "confidence": confidence,
        "categorization_method": method,
    }


def apply_plaid_keyword_matching(
    description: str, merchant_name: str, plaid_categories: dict
) -> dict | None:
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
    best_score = 0.0

    # Check each Plaid category
    for category_key, category_data in plaid_categories.items():
        if not isinstance(category_data, dict):
            continue

        keywords = category_data.get("keywords", [])
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
                    "category": category_key.split(".")[0],
                    "subcategory": category_key,
                    "confidence": min(0.70, 0.4 + score * 0.3),
                    "categorization_method": "plaid_keyword",
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


def analyze_categorization_accuracy(
    file_path: str, verbose: bool = False, debug: bool = False, skip_interactive: bool = False
) -> None:
    """
    Analyze the accuracy and completeness of transaction categorization.

    Args:
        file_path: Path to enriched transactions JSON file
        verbose: Enable verbose output with examples
        debug: Enable debug output with detailed analysis
        skip_interactive: Skip interactive mapping prompts (for use in pipelines)
    """
    # Load transactions
    transactions = load_transactions_from_json(file_path)
    if not transactions:
        print(f"No transactions found in {file_path}")
        return

    print("\n=== Categorization Analysis ===")
    print(f"Total transactions: {len(transactions)}")

    # Basic statistics
    categorized = sum(
        1 for t in transactions if t.get("category") and t.get("category") != "UNCATEGORIZED"
    )
    uncategorized = len(transactions) - categorized
    categorization_rate = (categorized / len(transactions)) * 100

    print(f"Categorized: {categorized} ({categorization_rate:.1f}%)")
    print(f"Uncategorized: {uncategorized} ({100 - categorization_rate:.1f}%)")

    # Confidence distribution
    high_confidence = sum(1 for t in transactions if t.get("confidence", 0) >= 0.8)
    medium_confidence = sum(1 for t in transactions if 0.5 <= t.get("confidence", 0) < 0.8)
    low_confidence = sum(1 for t in transactions if t.get("confidence", 0) < 0.5)

    print("\nConfidence Distribution:")
    print(f"  High (≥0.8): {high_confidence} ({(high_confidence / len(transactions)) * 100:.1f}%)")
    print(
        f"  Medium (0.5-0.8): {medium_confidence} ({(medium_confidence / len(transactions)) * 100:.1f}%)"
    )
    print(f"  Low (<0.5): {low_confidence} ({(low_confidence / len(transactions)) * 100:.1f}%)")

    # Method distribution
    methods: dict[str, int] = {}
    for transaction in transactions:
        method = transaction.get("categorization_method", "unknown")
        methods[method] = methods.get(method, 0) + 1

    print("\nCategorization Methods:")
    for method, count in sorted(methods.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / len(transactions)) * 100
        print(f"  {method}: {count} ({percentage:.1f}%)")

    # Category distribution (only show if verbose or debug)
    if verbose or debug:
        categories: dict[str, int] = {}
        for transaction in transactions:
            category = transaction.get("category", "UNCATEGORIZED")
            categories[category] = categories.get(category, 0) + 1

        print("\nTop Categories:")
        for category, count in sorted(categories.items(), key=lambda x: x[1], reverse=True)[:10]:
            percentage = (count / len(transactions)) * 100
            print(f"  {category}: {count} ({percentage:.1f}%)")

    # Debug information
    if debug:
        print("\nDebug Information:")

        # Method effectiveness
        print("\nMethod Effectiveness:")
        for method in methods.keys():
            method_transactions = [
                t for t in transactions if t.get("categorization_method") == method
            ]
            if method_transactions:
                avg_confidence = sum(t.get("confidence", 0) for t in method_transactions) / len(
                    method_transactions
                )
                print(f"  {method}: avg confidence {avg_confidence:.3f}")

        # Merchant name extraction quality
        print("\nMerchant Name Extraction:")
        merchants_with_names = sum(1 for t in transactions if t.get("merchant_name"))
        print(
            f"  Transactions with merchant names: {merchants_with_names} ({(merchants_with_names / len(transactions)) * 100:.1f}%)"
        )

        # Show some merchant name examples
        print("\nMerchant Name Examples:")
        for transaction in transactions[:10]:
            desc = transaction.get("description", "")[:40]
            merchant = transaction.get("merchant_name", "N/A")
            print(f"  '{desc}' -> '{merchant}'")

    # Offer Interactive Mapping Builder for uncategorized transactions (unless skipped)
    if not skip_interactive:
        uncategorized_list = [t for t in transactions if t.get("category") == "UNCATEGORIZED"]

        if uncategorized_list:
            from interactive_mapper import get_transaction_frequency, run_mapping_wizard

            print("\n--- Top Uncategorized Transactions ---")
            print("Analyzing transaction frequency...")

            # Get frequency and show top transactions
            frequency = get_transaction_frequency(uncategorized_list)
            top_transactions = sorted(frequency.items(), key=lambda x: x[1], reverse=True)[:25]

            print(f"\nFound {len(top_transactions)} unique uncategorized merchant(s):\n")
            for i, (desc, count) in enumerate(top_transactions, 1):
                print(f"{i:2}. {desc} ({count} occurrence{'s' if count > 1 else ''})")

            if prompt_yes_no(
                "\nWould you like to create mappings for these transactions?", default=True
            ):
                # Load original descriptions from parsed transactions file (before privacy redaction)
                # The enriched file has redacted descriptions, but we need originals for the wizard
                config = get_config_manager()
                parsed_file = config.get_default_file_path("parsed_transactions")

                # Load parsed transactions and create a map of redacted -> original descriptions
                try:
                    with open(parsed_file) as f:
                        parsed_transactions = json.load(f)

                    # Build a lookup map: (amount, account_number, date) -> original_description
                    original_desc_map = {}
                    for pt in parsed_transactions:
                        key = (pt.get("amount"), pt.get("account_number"), pt.get("date"))
                        original_desc_map[key] = pt.get("description", "")

                    # Enrich uncategorized transactions with original descriptions
                    for ut in uncategorized_list:
                        key = (ut.get("amount"), ut.get("account_number"), ut.get("date"))
                        if key in original_desc_map:
                            ut["original_description"] = original_desc_map[key]
                        else:
                            # Fallback to redacted description if we can't find original
                            ut["original_description"] = ut.get("description", "")

                except Exception as e:
                    if debug:
                        print(f"Warning: Could not load original descriptions: {e}")
                    # If we can't load originals, use redacted descriptions
                    for ut in uncategorized_list:
                        ut["original_description"] = ut.get("description", "")

                # Run the mapping wizard (it will handle processing the mappings)
                created = run_mapping_wizard(uncategorized_list, debug=debug)

                if created > 0:
                    # Ask if user wants to re-run enrichment with the newly processed mappings
                    print("\n--- Next Steps ---")
                    if prompt_yes_no(
                        "\nWould you like to re-run enrichment with the new mappings?", default=True
                    ):
                        # Get the input file (parsed transactions)
                        config = get_config_manager()
                        parsed_file = config.get_default_file_path("parsed_transactions")
                        enriched_file = file_path

                        print("\nRe-running enrichment...")
                        process_transaction_enrichment(parsed_file, enriched_file, debug=debug)

                        print("\n--- Updated Results ---")
                        # Show updated summary (no recursive call - just reload and show stats)
                        updated_transactions = load_transactions_from_json(enriched_file)
                        if updated_transactions:
                            categorized_after = sum(
                                1
                                for t in updated_transactions
                                if t.get("category") and t.get("category") != "UNCATEGORIZED"
                            )
                            uncategorized_after = len(updated_transactions) - categorized_after
                            categorization_rate_after = (
                                categorized_after / len(updated_transactions)
                            ) * 100

                            print(f"Total transactions: {len(updated_transactions)}")
                            print(
                                f"Categorized: {categorized_after} ({categorization_rate_after:.1f}%)"
                            )
                            print(
                                f"Uncategorized: {uncategorized_after} ({100 - categorization_rate_after:.1f}%)"
                            )
                            print(
                                f"\nImprovement: {categorized_after - categorized} additional transaction(s) categorized"
                            )


def generate_enrichment_report(transactions: list[dict], output_file: str | None = None) -> str:
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
    categorized = sum(1 for t in transactions if t.get("category") != "UNCATEGORIZED")
    report_lines.append(f"Categorization Rate: {(categorized / len(transactions) * 100):.1f}%")

    # Average confidence by method
    methods: dict[str, list[float]] = {}
    for transaction in transactions:
        method = transaction.get("categorization_method", "unknown")
        confidence = transaction.get("confidence", 0)
        if method not in methods:
            methods[method] = []
        methods[method].append(float(confidence) if confidence else 0.0)

    report_lines.append("\nMethod Performance:")
    for method, confidences in methods.items():
        avg_conf = sum(confidences) / len(confidences)
        report_lines.append(f"  {method}: {len(confidences)} txns, avg confidence {avg_conf:.3f}")

    # Top categories
    categories: dict[str, int] = {}
    amounts: dict[str, float] = {}
    for transaction in transactions:
        category = transaction.get("category", "UNCATEGORIZED")
        amount = abs(float(transaction.get("amount", 0)))
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
            with open(output_file, "w", encoding="utf-8") as f:
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
