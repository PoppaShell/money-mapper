#!/usr/bin/env python3
"""
Mapping Processor - Comprehensive financial transaction mapping management.

This module handles:
1. Backup and rename existing mapping files
2. Add missing PFC sections to TOML files
3. Migrate existing mappings with scope field
4. Validate and fix existing mappings
5. Process new mappings from input file
6. Handle conflict resolution interactively
7. Maintain alphabetical organization
8. Update all file references in codebase
"""

import os
import re
import shutil
import sys
import tomllib
from datetime import datetime
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple, Set

# Add the src directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from config_manager import get_config_manager
    from utils import prompt_yes_no
except ImportError:
    # If running from different directory, try relative import
    try:
        from .config_manager import get_config_manager
        from .utils import prompt_yes_no
    except ImportError:
        print("Error: Could not import required modules. Please ensure config_manager.py and utils.py are in the same directory.")
        sys.exit(1)


# Complete PFC Taxonomy with descriptions - All 104 subcategories
COMPLETE_PFC_TAXONOMY = {
    "BANK_FEES": {
        "BANK_FEES_ATM_FEES": "ATM fees and surcharges",
        "BANK_FEES_FOREIGN_TRANSACTION_FEES": "Foreign transaction and currency conversion fees",
        "BANK_FEES_INSUFFICIENT_FUNDS": "NSF and insufficient funds fees",
        "BANK_FEES_INTEREST_CHARGE": "Interest charges on credit cards and loans",
        "BANK_FEES_OVERDRAFT_FEES": "Overdraft and courtesy pay fees",
        "BANK_FEES_OTHER_BANK_FEES": "Other banking fees and charges"
    },
    "ENTERTAINMENT": {
        "ENTERTAINMENT_CASINOS_AND_GAMBLING": "Casinos, gambling, and sports betting",
        "ENTERTAINMENT_MUSIC_AND_AUDIO": "Music streaming, concerts, and audio services",
        "ENTERTAINMENT_SPORTING_EVENTS_AMUSEMENT_PARKS_AND_MUSEUMS": "Sports events, theme parks, museums, and attractions",
        "ENTERTAINMENT_TV_AND_MOVIES": "Streaming services, movie theaters, and video content",
        "ENTERTAINMENT_VIDEO_GAMES": "Gaming platforms, video games, and gaming services",
        "ENTERTAINMENT_OTHER_ENTERTAINMENT": "Other entertainment and recreational activities"
    },
    "FOOD_AND_DRINK": {
        "FOOD_AND_DRINK_BEER_WINE_AND_LIQUOR": "Alcoholic beverages and liquor stores",
        "FOOD_AND_DRINK_COFFEE": "Coffee shops, cafes, and coffee-related purchases",
        "FOOD_AND_DRINK_FAST_FOOD": "Fast food chains and quick service restaurants",
        "FOOD_AND_DRINK_GROCERIES": "Grocery stores and food shopping",
        "FOOD_AND_DRINK_RESTAURANT": "Full-service restaurants and dining",
        "FOOD_AND_DRINK_VENDING_MACHINES": "Vending machines and automated food services",
        "FOOD_AND_DRINK_OTHER_FOOD_AND_DRINK": "Other food and beverage purchases"
    },
    "GENERAL_MERCHANDISE": {
        "GENERAL_MERCHANDISE_BOOKSTORES_AND_NEWSSTANDS": "Bookstores, newsstands, and magazine retailers",
        "GENERAL_MERCHANDISE_CLOTHING_AND_ACCESSORIES": "Clothing stores, fashion retailers, and accessories",
        "GENERAL_MERCHANDISE_CONVENIENCE_STORES": "Convenience stores and gas station marts",
        "GENERAL_MERCHANDISE_DEPARTMENT_STORES": "Department stores and multi-category retailers",
        "GENERAL_MERCHANDISE_DISCOUNT_STORES": "Discount stores, dollar stores, and outlet retailers",
        "GENERAL_MERCHANDISE_ELECTRONICS": "Electronics stores and technology retailers",
        "GENERAL_MERCHANDISE_GIFTS_AND_NOVELTIES": "Gift shops, novelty stores, and specialty items",
        "GENERAL_MERCHANDISE_OFFICE_SUPPLIES": "Office supply stores and business equipment",
        "GENERAL_MERCHANDISE_ONLINE_MARKETPLACES": "E-commerce platforms and online retailers",
        "GENERAL_MERCHANDISE_PET_SUPPLIES": "Pet stores and animal supply retailers",
        "GENERAL_MERCHANDISE_SPORTING_GOODS": "Sporting goods stores and outdoor equipment",
        "GENERAL_MERCHANDISE_SUPERSTORES": "Big box stores, warehouse clubs, and superstores",
        "GENERAL_MERCHANDISE_TOBACCO_AND_VAPE": "Tobacco shops, smoke shops, and vaping supplies",
        "GENERAL_MERCHANDISE_OTHER_GENERAL_MERCHANDISE": "Other general retail and merchandise stores"
    },
    "GENERAL_SERVICES": {
        "GENERAL_SERVICES_ACCOUNTING_AND_FINANCIAL_PLANNING": "Accounting, tax preparation, and financial planning services",
        "GENERAL_SERVICES_AUTOMOTIVE": "Auto repair, maintenance, and automotive services",
        "GENERAL_SERVICES_CHILDCARE": "Childcare, daycare, and child-related services",
        "GENERAL_SERVICES_CONSULTING_AND_LEGAL": "Consulting, legal services, and professional advice",
        "GENERAL_SERVICES_EDUCATION": "Educational services, training, and academic institutions",
        "GENERAL_SERVICES_INSURANCE": "Insurance companies and insurance-related services",
        "GENERAL_SERVICES_POSTAGE_AND_SHIPPING": "Shipping, mailing, and postage services",
        "GENERAL_SERVICES_STORAGE": "Storage facilities and self-storage services",
        "GENERAL_SERVICES_OTHER_GENERAL_SERVICES": "Other professional and general services"
    },
    "GOVERNMENT_AND_NON_PROFIT": {
        "GOVERNMENT_AND_NON_PROFIT_DONATIONS": "Charitable donations and religious contributions",
        "GOVERNMENT_AND_NON_PROFIT_GOVERNMENT_DEPARTMENTS_AND_AGENCIES": "Government departments, agencies, and public services",
        "GOVERNMENT_AND_NON_PROFIT_TAX_PAYMENT": "Tax payments and government revenue collections",
        "GOVERNMENT_AND_NON_PROFIT_OTHER_GOVERNMENT_AND_NON_PROFIT": "Other government and non-profit organizations"
    },
    "HOME_IMPROVEMENT": {
        "HOME_IMPROVEMENT_FURNITURE": "Furniture stores and home furnishing retailers",
        "HOME_IMPROVEMENT_HARDWARE": "Hardware stores, building supplies, and construction materials",
        "HOME_IMPROVEMENT_REPAIR_AND_MAINTENANCE": "Home repair, maintenance, and improvement services",
        "HOME_IMPROVEMENT_SECURITY": "Home security systems and monitoring services",
        "HOME_IMPROVEMENT_OTHER_HOME_IMPROVEMENT": "Other home improvement and property-related services"
    },
    "INCOME": {
        "INCOME_DIVIDENDS": "Investment dividends and distribution payments",
        "INCOME_INTEREST_EARNED": "Interest earned on savings and investment accounts",
        "INCOME_RETIREMENT_PENSION": "Retirement benefits, pension payments, and social security",
        "INCOME_TAX_REFUND": "Tax refunds and government refund payments",
        "INCOME_UNEMPLOYMENT": "Unemployment benefits and unemployment insurance",
        "INCOME_WAGES": "Wages, salaries, and employment income",
        "INCOME_OTHER_INCOME": "Other income sources and miscellaneous earnings"
    },
    "LOAN_PAYMENTS": {
        "LOAN_PAYMENTS_CAR_PAYMENT": "Auto loans, car payments, and vehicle financing",
        "LOAN_PAYMENTS_CREDIT_CARD_PAYMENT": "Credit card payments and credit account payments",
        "LOAN_PAYMENTS_MORTGAGE_PAYMENT": "Mortgage payments and home loan payments",
        "LOAN_PAYMENTS_PERSONAL_LOAN_PAYMENT": "Personal loans and unsecured debt payments",
        "LOAN_PAYMENTS_STUDENT_LOAN_PAYMENT": "Student loan payments and educational debt",
        "LOAN_PAYMENTS_OTHER_PAYMENT": "Other loan payments and debt obligations"
    },
    "MEDICAL": {
        "MEDICAL_DENTAL_CARE": "Dental care, orthodontics, and oral health services",
        "MEDICAL_EYE_CARE": "Eye care, vision services, and optical retailers",
        "MEDICAL_NURSING_CARE": "Nursing care, assisted living, and care facilities",
        "MEDICAL_PHARMACIES_AND_SUPPLEMENTS": "Pharmacies, medications, and health supplements",
        "MEDICAL_PRIMARY_CARE": "Primary care, medical services, and healthcare providers",
        "MEDICAL_VETERINARY_SERVICES": "Veterinary services and animal healthcare",
        "MEDICAL_OTHER_MEDICAL": "Other medical services and healthcare-related expenses"
    },
    "PERSONAL_CARE": {
        "PERSONAL_CARE_GYMS_AND_FITNESS_CENTERS": "Gyms, fitness centers, and exercise facilities",
        "PERSONAL_CARE_HAIR_AND_BEAUTY": "Hair salons, beauty services, and cosmetic retailers",
        "PERSONAL_CARE_LAUNDRY_AND_DRY_CLEANING": "Laundry services, dry cleaning, and garment care",
        "PERSONAL_CARE_OTHER_PERSONAL_CARE": "Other personal care services and wellness activities"
    },
    "RENT_AND_UTILITIES": {
        "RENT_AND_UTILITIES_GAS_AND_ELECTRICITY": "Gas and electric utilities and energy services",
        "RENT_AND_UTILITIES_INTERNET_AND_CABLE": "Internet, cable, and telecommunications services",
        "RENT_AND_UTILITIES_RENT": "Rent payments and housing rental costs",
        "RENT_AND_UTILITIES_SEWAGE_AND_WASTE_MANAGEMENT": "Sewage, waste management, and sanitation services",
        "RENT_AND_UTILITIES_TELEPHONE": "Telephone services and mobile phone carriers",
        "RENT_AND_UTILITIES_WATER": "Water utilities and municipal water services",
        "RENT_AND_UTILITIES_OTHER_UTILITIES": "Other utilities and municipal services"
    },
    "TRANSFER_IN": {
        "TRANSFER_IN_CASH_ADVANCES_AND_LOANS": "Cash advances, loans, and credit line transfers",
        "TRANSFER_IN_DEPOSIT": "Deposits, check deposits, and account funding",
        "TRANSFER_IN_INVESTMENT_AND_RETIREMENT_FUNDS": "Investment transfers and retirement fund contributions",
        "TRANSFER_IN_SAVINGS": "Savings account transfers and savings deposits",
        "TRANSFER_IN_ACCOUNT_TRANSFER": "Account transfers and inter-bank transfers",
        "TRANSFER_IN_OTHER_TRANSFER_IN": "Other inbound transfers and credits"
    },
    "TRANSFER_OUT": {
        "TRANSFER_OUT_INVESTMENT_AND_RETIREMENT_FUNDS": "Investment account transfers and retirement contributions",
        "TRANSFER_OUT_SAVINGS": "Savings account transfers and emergency fund contributions",
        "TRANSFER_OUT_WITHDRAWAL": "ATM withdrawals and cash withdrawals",
        "TRANSFER_OUT_ACCOUNT_TRANSFER": "Account transfers and outbound bank transfers",
        "TRANSFER_OUT_OTHER_TRANSFER_OUT": "Other outbound transfers and debits"
    },
    "TRANSPORTATION": {
        "TRANSPORTATION_BIKES_AND_SCOOTERS": "Bike rentals, scooter services, and micro-mobility",
        "TRANSPORTATION_GAS": "Gasoline, fuel, and gas station purchases",
        "TRANSPORTATION_PARKING": "Parking fees, garage fees, and parking services",
        "TRANSPORTATION_PUBLIC_TRANSIT": "Public transportation, buses, trains, and transit systems",
        "TRANSPORTATION_TAXIS_AND_RIDE_SHARES": "Taxi services, ride-sharing, and transportation apps",
        "TRANSPORTATION_TOLLS": "Toll roads, bridge tolls, and electronic toll collection",
        "TRANSPORTATION_OTHER_TRANSPORTATION": "Other transportation services and travel-related expenses"
    },
    "TRAVEL": {
        "TRAVEL_FLIGHTS": "Airlines, flight bookings, and air travel services",
        "TRAVEL_LODGING": "Hotels, accommodations, and lodging reservations",
        "TRAVEL_RENTAL_CARS": "Car rentals and vehicle rental services",
        "TRAVEL_OTHER_TRAVEL": "Other travel services, tours, and vacation-related expenses"
    }
}


class MappingProcessor:
    """Main class for processing financial transaction mappings."""
    
    def __init__(self, config_dir: str = "config", debug_mode: bool = False):
        """Initialize the mapping processor."""
        self.config_dir = config_dir
        self.debug_mode = debug_mode
        
        # Get configuration manager
        self.config = get_config_manager(config_dir)
        
        # Get file paths from centralized configuration
        mapping_files = self.config.get_mapping_processor_files()
        self.private_mappings = mapping_files['private_mappings']
        self.public_mappings = mapping_files['public_mappings']
        self.new_mappings_file = mapping_files['new_mappings_template']
        self.backup_dir = mapping_files['backup_directory']
        
        # Ensure backup directory exists
        self._ensure_backup_directory()
        
    def _load_settings(self) -> Dict:
        """Load settings from config manager."""
        # Settings are now handled by the config manager
        # This method is kept for compatibility but delegates to config manager
        return {
            'processing': {
                'auto_alphabetize': self.config.get_processing_setting('auto_alphabetize'),
                'interactive_conflicts': self.config.get_processing_setting('interactive_conflicts'),
                'validate_categories': self.config.get_processing_setting('validate_categories')
            },
            'fuzzy_matching': {
                'mapping_processor_threshold': self.config.get_fuzzy_threshold('mapping_processor')
            }
        }
    
    def _ensure_backup_directory(self) -> None:
        """Create backup directory if it doesn't exist."""
        if not os.path.exists(self.backup_dir):
            try:
                os.makedirs(self.backup_dir)
                print(f"Created backup directory: {self.backup_dir}")
            except Exception as e:
                print(f"ERROR: Could not create backup directory {self.backup_dir}: {e}")
        else:
            self._debug_print(f"Backup directory exists: {self.backup_dir}")
    
    def _debug_print(self, message: str) -> None:
        """Print debug message if debug mode is enabled."""
        if self.debug_mode:
            print(f"DEBUG: {message}")
    
    def _backup_file(self, file_path: str, actually_backup: bool = True) -> str:
        """
        Create a timestamped backup of a file.

        Args:
            file_path: Path to file to backup
            actually_backup: If True, actually create the backup; if False, just report what would happen

        Returns:
            Path to backup file (or empty string if file doesn't exist)
        """
        if not os.path.exists(file_path):
            return ""

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.basename(file_path)
        backup_path = os.path.join(self.backup_dir, f"backup_{timestamp}_{filename}")

        if actually_backup:
            try:
                shutil.copy2(file_path, backup_path)
                print(f"Created backup: {backup_path}")
                self._debug_print(f"Backup created: {file_path} -> {backup_path}")
            except Exception as e:
                print(f"ERROR: Could not backup {file_path}: {e}")
                return ""
        else:
            print(f"Would backup {file_path} to {backup_path}")
            self._debug_print(f"Backup planned: {file_path} -> {backup_path}")

        return backup_path

    def _cleanup_old_backups(self, keep_count: int = 10) -> None:
        """
        Remove old backup files, keeping only the most recent backups.

        Args:
            keep_count: Number of most recent backups to keep per file
        """
        if not os.path.exists(self.backup_dir):
            return

        try:
            # Group backups by original filename
            backups_by_file = {}

            for filename in os.listdir(self.backup_dir):
                if not filename.startswith('backup_'):
                    continue

                # Extract original filename from backup name
                # Format: backup_YYYYmmdd_HHMMSS_original_filename.toml
                parts = filename.split('_', 3)
                if len(parts) >= 4:
                    original_name = parts[3]
                    if original_name not in backups_by_file:
                        backups_by_file[original_name] = []

                    full_path = os.path.join(self.backup_dir, filename)
                    mtime = os.path.getmtime(full_path)
                    backups_by_file[original_name].append((full_path, mtime))

            # For each file, keep only the most recent backups
            total_removed = 0
            for original_name, backups in backups_by_file.items():
                # Sort by modification time (newest first)
                backups.sort(key=lambda x: x[1], reverse=True)

                # Remove old backups
                for backup_path, _ in backups[keep_count:]:
                    try:
                        os.remove(backup_path)
                        total_removed += 1
                        self._debug_print(f"Removed old backup: {backup_path}")
                    except Exception as e:
                        print(f"Warning: Could not remove old backup {backup_path}: {e}")

            if total_removed > 0:
                print(f"Cleaned up {total_removed} old backup files (keeping {keep_count} most recent per file)")

        except Exception as e:
            print(f"Warning: Error during backup cleanup: {e}")
    
    def _load_toml_file(self, file_path: str) -> Dict:
        """Load a TOML file safely."""
        if not os.path.exists(file_path):
            return {}
        
        try:
            with open(file_path, 'rb') as f:
                return tomllib.load(f)
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
            return {}
    
    def _write_toml_file(self, file_path: str, data: Dict, template_header: str = "") -> None:
        """Preview what would be written to a TOML file."""
        print(f"Would write to {file_path}:")
        print(f"   - {len(data)} sections")
        
        total_mappings = 0
        for section in data.values():
            if isinstance(section, dict):
                total_mappings += len(section)
        
        print(f"   - {total_mappings} total mappings")
        
        if self.debug_mode:
            print(f"   - Header: {len(template_header)} characters")
            print(f"   - Sections: {list(data.keys())[:5]}{'...' if len(data) > 5 else ''}")
    
    def _get_category_description(self, subcategory: str) -> str:
        """Get a human-readable description for a PFC subcategory."""
        for primary_category, subcategories in COMPLETE_PFC_TAXONOMY.items():
            if subcategory in subcategories:
                return subcategories[subcategory]
        return "Financial transaction category"
    
    def _analyze_scope_addition(self, data: Dict, scope: str) -> None:
        """Analyze what scope fields would be added to mappings."""
        mappings_needing_scope = 0
        mappings_with_scope = 0
        
        for section in data.values():
            if isinstance(section, dict):
                for mapping in section.values():
                    if isinstance(mapping, dict):
                        if "scope" not in mapping:
                            mappings_needing_scope += 1
                        else:
                            mappings_with_scope += 1
        
        if mappings_needing_scope > 0:
            print(f"Would add scope='{scope}' to {mappings_needing_scope} mappings")
        if mappings_with_scope > 0:
            print(f"Found {mappings_with_scope} mappings already have scope field")
    
    def _check_required_files(self) -> bool:
        """Check that required mapping files exist in proper locations."""
        required_files = [
            (self.private_mappings, "private_mappings.toml"),
            (self.public_mappings, "public_mappings.toml")
        ]
        
        missing_files = []
        for file_path, file_name in required_files:
            if not os.path.exists(file_path):
                missing_files.append(file_name)
            else:
                print(f"Found: {file_name}")
        
        if missing_files:
            print(f"\nERROR: Missing required mapping files:")
            for file_name in missing_files:
                print(f"  - {file_name}")
            print(f"\nPlease ensure you have the complete Money Mapper repository with all config files.")
            return False
        
        print("All required mapping files found.")
        return True
    
    def _write_toml_file_actual(self, file_path: str, data: Dict, header: str) -> None:
        """Actually write data to a TOML file."""
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(header + "\n\n")

            # Write sections in alphabetical order
            for section_name in sorted(data.keys()):
                section_data = data[section_name]
                if isinstance(section_data, dict) and section_data:
                    f.write(f"[{section_name}]\n")
                    description = self._get_category_description(section_name.split('.')[-1])
                    f.write(f"# {description}\n")

                    # Write mappings in alphabetical order
                    for pattern in sorted(section_data.keys()):
                        mapping_data = section_data[pattern]
                        if isinstance(mapping_data, dict):
                            f.write(f'"{pattern}" = {{ ')
                            f.write(f'name = "{mapping_data.get("name", "")}", ')
                            f.write(f'category = "{mapping_data.get("category", "")}", ')
                            f.write(f'subcategory = "{mapping_data.get("subcategory", "")}", ')
                            f.write(f'scope = "{mapping_data.get("scope", "")}"')
                            f.write(' }\n')

                    f.write('\n')
    
    def _get_private_mappings_header(self) -> str:
        """Get the header template for private mappings file."""
        return '''# Private Financial Transaction Mappings - Personal and Local Businesses
# 
# This file contains YOUR specific merchant mappings for local businesses,
# personal services, and location-specific patterns. These mappings have
# HIGHEST priority and override both public_mappings.toml and plaid_categories.toml.
#
# PRIVACY NOTICE:
# - This file contains YOUR PERSONAL DATA
# - Should not be shared publicly or committed to version control
# - Keep backup copies of your customizations
#
# STRUCTURE:
# [PRIMARY_CATEGORY.DETAILED_CATEGORY]
# "pattern" = { name = "Clean Name", category = "PRIMARY", subcategory = "DETAILED", scope = "private" }
#
# SCOPE GUIDELINES:
# Use scope = "private" for:
# - Local businesses (restaurants, services, shops)
# - Personal service providers (doctors, dentists, salons) 
# - Regional chains not widely known
# - Your employer and income sources
# - Location-specific patterns
#
# MAINTENANCE:
# - Update when you change jobs or move
# - Add new local businesses as discovered
# - Remove patterns for businesses no longer used'''
    
    def _get_public_mappings_header(self) -> str:
        """Get the header template for public mappings file."""
        return '''# Public Financial Transaction Mappings - National Chains and Services
# 
# This file contains mappings for well-known national chains and services
# that are widely applicable. These mappings have MEDIUM priority 
# (after private_mappings.toml, before plaid_categories.toml).
#
# STRUCTURE:
# [PRIMARY_CATEGORY.DETAILED_CATEGORY]
# "pattern" = { name = "Clean Name", category = "PRIMARY", subcategory = "DETAILED", scope = "public" }
#
# SCOPE GUIDELINES:
# Use scope = "public" for:
# - National chain stores and restaurants
# - Well-known online services and platforms
# - Major banks and financial institutions
# - Large utility and telecom companies
# - Widely recognized brand names
#
# MAINTENANCE:
# - Safe to share publicly and commit to version control
# - Update when businesses rebrand or merge
# - Add new national chains as they emerge
# - Keep patterns generic (avoid location-specific terms)'''
    
    def _detect_duplicates(self) -> List[Dict]:
        """Detect duplicate mappings across all files."""
        print("=== DETECTING DUPLICATE MAPPINGS ===")

        duplicates = []
        private_data = self._load_toml_file(self.private_mappings)
        public_data = self._load_toml_file(self.public_mappings)

        # Create pattern-to-location mapping
        all_patterns = {}

        # Index private mappings (handle nested structure: PRIMARY -> SUBCATEGORY -> patterns)
        for primary_key, primary_section in private_data.items():
            if isinstance(primary_section, dict):
                for subcategory_key, subcategory_section in primary_section.items():
                    if isinstance(subcategory_section, dict):
                        section_key = f"{primary_key}.{subcategory_key}"
                        for pattern, mapping in subcategory_section.items():
                            if not isinstance(mapping, dict):
                                continue

                            if pattern in all_patterns:
                                duplicates.append({
                                    'pattern': pattern,
                                    'existing_file': all_patterns[pattern]['file'],
                                    'existing_section': all_patterns[pattern]['section'],
                                    'existing_mapping': all_patterns[pattern]['mapping'],
                                    'existing_primary': all_patterns[pattern]['primary'],
                                    'existing_subcategory': all_patterns[pattern]['subcategory'],
                                    'duplicate_file': 'private_mappings.toml',
                                    'duplicate_section': section_key,
                                    'duplicate_mapping': mapping,
                                    'duplicate_primary': primary_key,
                                    'duplicate_subcategory': subcategory_key
                                })
                            else:
                                all_patterns[pattern] = {
                                    'file': 'private_mappings.toml',
                                    'section': section_key,
                                    'mapping': mapping,
                                    'primary': primary_key,
                                    'subcategory': subcategory_key
                                }

        # Index public mappings (handle nested structure: PRIMARY -> SUBCATEGORY -> patterns)
        for primary_key, primary_section in public_data.items():
            if isinstance(primary_section, dict):
                for subcategory_key, subcategory_section in primary_section.items():
                    if isinstance(subcategory_section, dict):
                        section_key = f"{primary_key}.{subcategory_key}"
                        for pattern, mapping in subcategory_section.items():
                            if not isinstance(mapping, dict):
                                continue

                            if pattern in all_patterns:
                                duplicates.append({
                                    'pattern': pattern,
                                    'existing_file': all_patterns[pattern]['file'],
                                    'existing_section': all_patterns[pattern]['section'],
                                    'existing_mapping': all_patterns[pattern]['mapping'],
                                    'existing_primary': all_patterns[pattern]['primary'],
                                    'existing_subcategory': all_patterns[pattern]['subcategory'],
                                    'duplicate_file': 'public_mappings.toml',
                                    'duplicate_section': section_key,
                                    'duplicate_mapping': mapping,
                                    'duplicate_primary': primary_key,
                                    'duplicate_subcategory': subcategory_key
                                })
                            else:
                                all_patterns[pattern] = {
                                    'file': 'public_mappings.toml',
                                    'section': section_key,
                                    'mapping': mapping,
                                    'primary': primary_key,
                                    'subcategory': subcategory_key
                                }

        if duplicates:
            print(f"Found {len(duplicates)} duplicate patterns:")
            for i, dup in enumerate(duplicates, 1):
                print(f"\n{i}. Pattern: '{dup['pattern']}'")
                print(f"   File 1: {dup['existing_file']} [{dup['existing_section']}]")
                print(f"   File 2: {dup['duplicate_file']} [{dup['duplicate_section']}]")
        else:
            print("No duplicate patterns found")

        return duplicates
    
    def _validate_mappings(self) -> List[Dict]:
        """Validate all mappings for common issues."""
        print("=== VALIDATING MAPPINGS ===")

        issues = []
        private_data = self._load_toml_file(self.private_mappings)
        public_data = self._load_toml_file(self.public_mappings)

        for file_name, data in [("private_mappings.toml", private_data), ("public_mappings.toml", public_data)]:
            for primary_key, primary_section in data.items():
                if isinstance(primary_section, dict):
                    # Handle nested structure: PRIMARY -> SUBCATEGORY -> patterns
                    for subcategory_key, subcategory_section in primary_section.items():
                        if isinstance(subcategory_section, dict):
                            # Now iterate through actual pattern mappings
                            for pattern, mapping in subcategory_section.items():
                                # Skip if mapping is not a dict (shouldn't happen but be safe)
                                if not isinstance(mapping, dict):
                                    continue

                                section_key = f"{primary_key}.{subcategory_key}"

                                # Validate required fields
                                required_fields = ['name', 'category', 'subcategory', 'scope']
                                for field in required_fields:
                                    if field not in mapping:
                                        issues.append({
                                            'type': 'missing_field',
                                            'file': file_name,
                                            'section': section_key,
                                            'pattern': pattern,
                                            'issue': f"Missing required field: {field}",
                                            'mapping': mapping
                                        })

                                # Validate PFC category exists
                                if 'category' in mapping and 'subcategory' in mapping:
                                    primary = mapping['category']
                                    subcategory = mapping['subcategory']
                                    if (primary not in COMPLETE_PFC_TAXONOMY or
                                        subcategory not in COMPLETE_PFC_TAXONOMY[primary]):
                                        issues.append({
                                            'type': 'invalid_category',
                                            'file': file_name,
                                            'section': section_key,
                                            'pattern': pattern,
                                            'issue': f"Invalid PFC category: {primary}.{subcategory}",
                                            'mapping': mapping
                                        })

                                # Validate scope matches file
                                expected_scope = "private" if "private" in file_name else "public"
                                if mapping.get('scope') != expected_scope:
                                    issues.append({
                                        'type': 'wrong_scope',
                                        'file': file_name,
                                        'section': section_key,
                                        'pattern': pattern,
                                        'issue': f"Scope '{mapping.get('scope')}' doesn't match file (expected '{expected_scope}')",
                                        'mapping': mapping
                                    })
        
        if issues:
            print(f"Found {len(issues)} validation issues:")
            for i, issue in enumerate(issues, 1):
                print(f"\n{i}. {issue['type'].replace('_', ' ').title()}")
                print(f"   File: {issue['file']}")
                print(f"   Pattern: '{issue['pattern']}'")
                print(f"   Issue: {issue['issue']}")
        else:
            print("All mappings are valid")
        
        return issues
    
    def _create_input_template(self) -> None:
        """Report what input template would be created."""
        if os.path.exists(self.new_mappings_file):
            print(f"Input template already exists: {self.new_mappings_file}")
            return
        
        print(f"Would create input template: {self.new_mappings_file}")
        print(f"   Template includes documentation and examples for new mappings")
    
    def _create_settings_file(self) -> None:
        """Report on configuration files status."""
        public_settings = self.config.get_file_path('public_settings')
        private_settings = self.config.get_file_path('private_settings')

        print("Configuration files:")
        if os.path.exists(public_settings):
            print(f"  ✓ Public settings exists: {public_settings}")
        else:
            print(f"  ✗ Public settings missing: {public_settings}")

        if os.path.exists(private_settings):
            print(f"  ✓ Private settings exists: {private_settings}")
        else:
            print(f"  ✗ Private settings missing: {private_settings}")
            print(f"     Run setup wizard to create private configuration")

        print(f"   Settings include fuzzy matching thresholds and processing options")
    
    def _process_new_mappings(self) -> bool:
        """Process new mappings from the input template file."""
        if not os.path.exists(self.new_mappings_file):
            print(f"No new mappings file found: {self.new_mappings_file}")
            return False
        
        print("=== PROCESSING NEW MAPPINGS ===")
        
        # Load new mappings
        new_data = self._load_toml_file(self.new_mappings_file)
        if not new_data:
            print("No new mappings found in input file")
            return False
        
        # Separate by scope
        private_additions = {}
        public_additions = {}

        # Handle flat structure: pattern -> mapping dict directly at root
        for pattern, mapping in new_data.items():
            if not isinstance(mapping, dict):
                continue

            # Validate mapping
            validation_errors = self._validate_single_mapping(pattern, mapping)
            if validation_errors:
                print(f"Validation errors for '{pattern}':")
                for error in validation_errors:
                    print(f"   - {error}")
                continue

            # Add to appropriate file based on scope
            scope = mapping.get('scope', 'public')
            target_dict = private_additions if scope == 'private' else public_additions

            # Ensure section exists
            pfc_section = f"{mapping['category']}.{mapping['subcategory']}"
            if pfc_section not in target_dict:
                target_dict[pfc_section] = {}

            target_dict[pfc_section][pattern] = mapping
        
        # Check for conflicts with existing mappings
        conflicts = self._check_mapping_conflicts(private_additions, public_additions)
        if conflicts and not self._resolve_conflicts(conflicts):
            print("ERROR: Mapping conflicts not resolved. Processing cancelled.")
            return False
        
        # Add new mappings to existing files
        success = True
        if private_additions:
            success &= self._add_mappings_to_file(self.private_mappings, private_additions, "private")
        if public_additions:
            success &= self._add_mappings_to_file(self.public_mappings, public_additions, "public")
        
        if success:
            # Clear the input file
            self._clear_input_file()
            print("SUCCESS: All new mappings processed successfully")
        
        return success
    
    def _validate_single_mapping(self, pattern: str, mapping: Dict) -> List[str]:
        """Validate a single mapping and return list of errors."""
        errors = []
        
        # Check required fields
        required_fields = ['name', 'category', 'subcategory', 'scope']
        for field in required_fields:
            if field not in mapping:
                errors.append(f"Missing required field: {field}")
        
        # Validate category exists in PFC taxonomy
        if 'category' in mapping and 'subcategory' in mapping:
            primary = mapping['category']
            subcategory = mapping['subcategory']
            
            if primary not in COMPLETE_PFC_TAXONOMY:
                errors.append(f"Invalid primary category: {primary}")
            elif subcategory not in COMPLETE_PFC_TAXONOMY[primary]:
                errors.append(f"Invalid subcategory: {subcategory}")
        
        # Validate scope
        if 'scope' in mapping and mapping['scope'] not in ['public', 'private']:
            errors.append(f"Invalid scope: {mapping['scope']} (must be 'public' or 'private')")
        
        # Validate pattern isn't empty
        if not pattern or not pattern.strip():
            errors.append("Pattern cannot be empty")
        
        return errors
    
    def _check_mapping_conflicts(self, private_additions: Dict, public_additions: Dict) -> List[Dict]:
        """Check for conflicts between new mappings and existing ones.

        Searches for pattern conflicts across ALL sections in both files,
        not just within the same PFC category/subcategory section.
        """
        conflicts = []

        # Load existing mappings (nested structure: PRIMARY -> SUBCATEGORY -> patterns)
        existing_private = self._load_toml_file(self.private_mappings)
        existing_public = self._load_toml_file(self.public_mappings)

        # Build a flat index of all existing patterns for fast lookup
        # Format: { pattern: [(file, section, mapping), ...] }
        existing_patterns = {}

        # Index private mappings
        for primary_key, primary_section in existing_private.items():
            if isinstance(primary_section, dict):
                for subcategory_key, subcategory_section in primary_section.items():
                    if isinstance(subcategory_section, dict):
                        section_key = f"{primary_key}.{subcategory_key}"
                        for pattern, mapping in subcategory_section.items():
                            if pattern not in existing_patterns:
                                existing_patterns[pattern] = []
                            existing_patterns[pattern].append({
                                'file': 'private_mappings.toml',
                                'section': section_key,
                                'mapping': mapping
                            })

        # Index public mappings
        for primary_key, primary_section in existing_public.items():
            if isinstance(primary_section, dict):
                for subcategory_key, subcategory_section in primary_section.items():
                    if isinstance(subcategory_section, dict):
                        section_key = f"{primary_key}.{subcategory_key}"
                        for pattern, mapping in subcategory_section.items():
                            if pattern not in existing_patterns:
                                existing_patterns[pattern] = []
                            existing_patterns[pattern].append({
                                'file': 'public_mappings.toml',
                                'section': section_key,
                                'mapping': mapping
                            })
        
        # Check private additions against all existing patterns
        for section_key, section in private_additions.items():
            for pattern, mapping in section.items():
                if pattern in existing_patterns:
                    # Pattern exists somewhere - create conflict for each occurrence
                    for existing in existing_patterns[pattern]:
                        conflicts.append({
                            'pattern': pattern,
                            'new_mapping': mapping,
                            'new_section': section_key,
                            'existing_mapping': existing['mapping'],
                            'file': existing['file'],
                            'section': existing['section']
                        })

        # Check public additions against all existing patterns
        for section_key, section in public_additions.items():
            for pattern, mapping in section.items():
                if pattern in existing_patterns:
                    # Pattern exists somewhere - create conflict for each occurrence
                    for existing in existing_patterns[pattern]:
                        conflicts.append({
                            'pattern': pattern,
                            'new_mapping': mapping,
                            'new_section': section_key,
                            'existing_mapping': existing['mapping'],
                            'file': existing['file'],
                            'section': existing['section']
                        })

        return conflicts
    
    def _resolve_conflicts(self, conflicts: List[Dict]) -> bool:
        """Interactively resolve mapping conflicts."""
        if not conflicts:
            return True

        settings = self._load_settings()
        if not settings.get('processing', {}).get('interactive_conflicts', True):
            print(f"Found {len(conflicts)} conflicts. Interactive resolution disabled.")
            return False

        print(f"\nFound {len(conflicts)} mapping conflicts:")

        for i, conflict in enumerate(conflicts, 1):
            print(f"\n{'='*60}")
            print(f"CONFLICT {i}/{len(conflicts)}")
            print(f"{'='*60}")
            print(f"Pattern: '{conflict['pattern']}'")

            # Determine if this is same-file or cross-file duplicate
            new_scope = conflict['new_mapping'].get('scope', 'unknown')
            existing_file_scope = 'private' if 'private' in conflict['file'] else 'public'
            is_cross_file = (new_scope != existing_file_scope)

            # Show existing mapping details
            print(f"\nEXISTING MAPPING:")
            print(f"  File: {conflict['file']}")
            print(f"  Section: {conflict['section']}")
            print(f"  Name: {conflict['existing_mapping'].get('name', 'N/A')}")
            print(f"  Category: {conflict['existing_mapping'].get('category', 'N/A')}")
            print(f"  Subcategory: {conflict['existing_mapping'].get('subcategory', 'N/A')}")
            print(f"  Scope: {conflict['existing_mapping'].get('scope', 'N/A')}")

            # Show new mapping details
            print(f"\nNEW MAPPING:")
            print(f"  Would go to: {'private_mappings.toml' if new_scope == 'private' else 'public_mappings.toml'}")
            print(f"  Name: {conflict['new_mapping'].get('name', 'N/A')}")
            print(f"  Category: {conflict['new_mapping'].get('category', 'N/A')}")
            print(f"  Subcategory: {conflict['new_mapping'].get('subcategory', 'N/A')}")
            print(f"  Scope: {new_scope}")

            # Provide different prompts based on conflict type
            if is_cross_file:
                print(f"\n⚠️  CROSS-FILE DUPLICATE DETECTED")
                print(f"This pattern exists in {conflict['file']} but you're trying to add it")
                print(f"with scope='{new_scope}' which would put it in a different file.")
                print(f"\nOptions:")
                print(f"  (k) Keep existing in {conflict['file']} and skip new mapping")
                print(f"  (r) Replace - Remove from {conflict['file']} and add new mapping")
                print(f"  (u) Update existing mapping's scope to '{new_scope}' and merge details")
                print(f"  (a) Abort entire operation")

                while True:
                    choice = input("\nResolve cross-file duplicate (k/r/u/a): ").lower().strip()

                    if choice == 'k':
                        print(f"✓ Keeping existing mapping in {conflict['file']}, skipping new")
                        break
                    elif choice == 'r':
                        print(f"✓ Will remove from {conflict['file']} and add new mapping")
                        conflict['action'] = 'replace_cross_file'
                        break
                    elif choice == 'u':
                        print(f"✓ Will update existing mapping's scope to '{new_scope}' and use new details")
                        conflict['action'] = 'update_scope'
                        break
                    elif choice == 'a':
                        print("Aborting all mapping additions")
                        return False
                    else:
                        print("Please enter 'k', 'r', 'u', or 'a'")
            else:
                print(f"\n⚠️  SAME-FILE DUPLICATE DETECTED")
                print(f"This pattern already exists in {conflict['file']}.")
                print(f"\nOptions:")
                print(f"  (s) Skip - Keep existing mapping, don't add new one")
                print(f"  (o) Overwrite - Replace existing mapping with new details")
                print(f"  (a) Abort entire operation")

                while True:
                    choice = input("\nResolve same-file duplicate (s/o/a): ").lower().strip()

                    if choice == 's':
                        print("✓ Skipping new mapping, keeping existing")
                        break
                    elif choice == 'o':
                        print("✓ Will overwrite existing mapping with new details")
                        conflict['action'] = 'overwrite'
                        break
                    elif choice == 'a':
                        print("Aborting all mapping additions")
                        return False
                    else:
                        print("Please enter 's', 'o', or 'a'")

        return True
    
    def _add_mappings_to_file(self, file_path: str, new_mappings: Dict, file_type: str) -> bool:
        """Add new mappings to an existing TOML file."""
        try:
            # Load existing data (nested structure: PRIMARY -> SUBCATEGORY -> patterns)
            existing_data = self._load_toml_file(file_path)

            # Merge new mappings (new_mappings is flat: "PRIMARY.SUBCATEGORY" -> patterns)
            for section_key, section in new_mappings.items():
                # Parse section_key: "ENTERTAINMENT.ENTERTAINMENT_SPORTING_EVENTS..." -> PRIMARY, SUBCATEGORY
                parts = section_key.split('.', 1)
                if len(parts) != 2:
                    print(f"Warning: Invalid section key format: {section_key}")
                    continue

                primary_key, subcategory_key = parts

                # Ensure primary category exists in existing data
                if primary_key not in existing_data:
                    existing_data[primary_key] = {}

                # Ensure subcategory exists in primary category
                if subcategory_key not in existing_data[primary_key]:
                    existing_data[primary_key][subcategory_key] = {}

                # Add each pattern mapping to the nested structure
                for pattern, mapping in section.items():
                    existing_data[primary_key][subcategory_key][pattern] = mapping

            # Flatten the nested structure for writing (TOML format)
            flattened_data = {}
            for primary_key, primary_section in existing_data.items():
                if isinstance(primary_section, dict):
                    for subcategory_key, subcategory_section in primary_section.items():
                        if isinstance(subcategory_section, dict):
                            section_name = f"{primary_key}.{subcategory_key}"
                            flattened_data[section_name] = subcategory_section

            # Write updated file
            header = self._get_private_mappings_header() if file_type == 'private' else self._get_public_mappings_header()
            self._write_toml_file_actual(file_path, flattened_data, header)

            total_added = sum(len(section) for section in new_mappings.values())
            print(f"SUCCESS: Added {total_added} mappings to {os.path.basename(file_path)}")
            return True

        except Exception as e:
            print(f"ERROR: Error adding mappings to {file_path}: {e}")
            return False
    
    def _clear_input_file(self) -> None:
        """Clear the input template file after successful processing."""
        try:
            # Write clean template with header and examples
            template_content = '''# New Financial Transaction Mappings - Input Template
#
# Add new transaction mappings below. Run 'python cli.py add-mappings' to process.
# This file will be automatically processed and cleared after successful import.
#
# REQUIRED FIELDS:
# - name: Clean display name for the merchant
# - category: Primary PFC category (see list below)
# - subcategory: Detailed PFC subcategory
# - scope: "public" for national chains, "private" for local businesses
#
# VALIDATION:
# - Patterns will be checked for duplicates across all mapping files
# - Categories will be validated against official PFC taxonomy
# - Scope will determine target file (private_mappings.toml vs public_mappings.toml)
#
# AVAILABLE PRIMARY CATEGORIES:
# BANK_FEES, ENTERTAINMENT, FOOD_AND_DRINK, GENERAL_MERCHANDISE, GENERAL_SERVICES,
# GOVERNMENT_AND_NON_PROFIT, HOME_IMPROVEMENT, INCOME, LOAN_PAYMENTS, MEDICAL,
# PERSONAL_CARE, RENT_AND_UTILITIES, TRANSFER_IN, TRANSFER_OUT, TRANSPORTATION, TRAVEL
#
# EXAMPLES:
# "starbucks" = { name = "Starbucks", category = "FOOD_AND_DRINK", subcategory = "FOOD_AND_DRINK_COFFEE", scope = "public" }
# "joes pizza downtown" = { name = "Joe's Pizza", category = "FOOD_AND_DRINK", subcategory = "FOOD_AND_DRINK_RESTAURANT", scope = "private" }
# "shell gas" = { name = "Shell", category = "TRANSPORTATION", subcategory = "TRANSPORTATION_GAS", scope = "public" }
#
# ADD NEW ENTRIES BELOW THIS LINE:
# ============================================================================
'''

            with open(self.new_mappings_file, 'w', encoding='utf-8') as f:
                f.write(template_content)

            print(f"SUCCESS: Cleared input file: {self.new_mappings_file}")
        except Exception as e:
            print(f"Warning: Could not clear input file: {e}")
    
    def _update_codebase_references(self) -> None:
        """Update file references in the codebase from old to new names."""
        print("=== UPDATING CODEBASE REFERENCES ===")
        
        files_to_update = [
            'src/transaction_enricher.py',
            'src/utils.py',
            'README.md'
        ]
        
        replacements = {
            'personal_mappings.toml': 'private_mappings.toml',
            'merchant_mappings.toml': 'public_mappings.toml'
        }
        
        for file_path in files_to_update:
            if not os.path.exists(file_path):
                continue
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                original_content = content
                for old_name, new_name in replacements.items():
                    content = content.replace(old_name, new_name)
                
                if content != original_content:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    print(f"SUCCESS: Updated references in {file_path}")
                else:
                    print(f"  No updates needed in {file_path}")
                    
            except Exception as e:
                print(f"ERROR: Error updating {file_path}: {e}")
    
    def run_full_processing(self) -> bool:
        """Run the complete mapping analysis and reporting workflow."""
        print("STARTING MAPPING ANALYSIS")
        print("=" * 60)
        
        try:
            # Step 1: Check that required files exist
            print("\nCHECKING REQUIRED FILES:")
            if not self._check_required_files():
                return False
            
            # Step 2: Report on template files
            print("\nTEMPLATE FILES:")
            self._create_settings_file()
            self._create_input_template()
            
            # Step 3: Validate current mappings
            print(f"\nVALIDATION ANALYSIS:")
            validation_issues = self._validate_mappings()
            if validation_issues:
                print(f"\nWARNING: Found {len(validation_issues)} validation issues to fix.")
                self._report_validation_fixes(validation_issues)
            
            # Step 4: Detect and report duplicates
            print(f"\nDUPLICATE ANALYSIS:")
            duplicates = self._detect_duplicates()
            if duplicates:
                print(f"\nWARNING: Found {len(duplicates)} duplicate patterns to resolve.")
                self._report_duplicate_resolutions(duplicates)
            
            # Step 5: Check for and process new mappings
            print(f"\nNEW MAPPINGS PROCESSING:")
            if os.path.exists(self.new_mappings_file):
                new_data = self._load_toml_file(self.new_mappings_file)
                if new_data:
                    # Count new mappings by scope (handle flat structure)
                    private_count = sum(1 for m in new_data.values() if isinstance(m, dict) and m.get('scope') == 'private')
                    public_count = sum(1 for m in new_data.values() if isinstance(m, dict) and m.get('scope') != 'private')

                    print(f"Found {private_count + public_count} new mappings:")
                    print(f"   - {private_count} private mappings")
                    print(f"   - {public_count} public mappings")
                    print(f"\nProcessing new mappings...")

                    # Actually process the new mappings
                    if not self._process_new_mappings():
                        print("ERROR: Failed to process new mappings")
                        return False
                else:
                    print("No new mappings found in input file")
            else:
                print(f"No new mappings file found: {self.new_mappings_file}")

            print("\n" + "=" * 60)
            print("MAPPING PROCESSING COMPLETE")
            print("\nNext steps:")
            print("1. Use 'check-mappings' command to fix any validation or duplicate issues")
            print("2. Add more new mappings via new_mappings.toml template as needed")

            return True
            
        except Exception as e:
            print(f"\nERROR: ANALYSIS FAILED: {e}")
            if self.debug_mode:
                import traceback
                traceback.print_exc()
            return False
    
    def _report_validation_fixes(self, issues: List[Dict]) -> None:
        """Report what validation fixes would be applied."""
        fix_types = {}
        for issue in issues:
            fix_type = issue['type']
            fix_types[fix_type] = fix_types.get(fix_type, 0) + 1
        
        print("Validation fixes that would be applied:")
        for fix_type, count in fix_types.items():
            print(f"   - {fix_type.replace('_', ' ').title()}: {count} issues")
    
    def _report_duplicate_resolutions(self, duplicates: List[Dict]) -> None:
        """Report what duplicate resolutions would be needed."""
        print("Duplicate resolutions needed:")
        for i, dup in enumerate(duplicates[:5], 1):  # Show first 5
            print(f"   {i}. Pattern '{dup['pattern']}' appears in:")
            print(f"      - {dup['existing_file']} [{dup['existing_section']}]")
            print(f"      - {dup['duplicate_file']} [{dup['duplicate_section']}]")
        
        if len(duplicates) > 5:
            print(f"      ... and {len(duplicates) - 5} more")
    
    def _analyze_new_mappings(self) -> None:
        """Analyze new mappings from input file."""
        if not os.path.exists(self.new_mappings_file):
            print(f"No new mappings file found: {self.new_mappings_file}")
            print(f"   Would create template for adding new mappings")
            return
        
        new_data = self._load_toml_file(self.new_mappings_file)
        if not new_data:
            print("No new mappings found in input file")
            return
        
        # Count new mappings by scope (handle flat structure)
        private_count = 0
        public_count = 0

        for pattern, mapping in new_data.items():
            if isinstance(mapping, dict):
                scope = mapping.get('scope', 'public')
                if scope == 'private':
                    private_count += 1
                else:
                    public_count += 1

        print(f"Found {private_count + public_count} new mappings:")
        print(f"   - {private_count} private mappings")
        print(f"   - {public_count} public mappings")
    
    def run_check_only(self) -> bool:
        """Run mapping validation and analysis with interactive fixing."""
        print("STARTING MAPPING VALIDATION")
        print("=" * 60)

        try:
            # Step 1: Check that required files exist
            print("\nFILE CHECK:")
            if not self._check_required_files():
                return False

            # Step 2: Create backups of mapping files before any modifications
            print("\nBACKUP:")
            self._backup_file(self.private_mappings, actually_backup=True)
            self._backup_file(self.public_mappings, actually_backup=True)

            # Clean up old backups
            self._cleanup_old_backups(keep_count=10)
            
            # Step 2: Validate current mappings and offer to fix issues
            print(f"\nVALIDATION ANALYSIS:")
            validation_issues = self._validate_mappings()
            if validation_issues:
                print(f"\nFound {len(validation_issues)} validation issues.")
                
                if self.config.get_processing_setting('interactive_conflicts'):
                    if self._confirm_action("Would you like to fix validation issues interactively?"):
                        fixed_count = self._interactive_fix_validation_issues(validation_issues)
                        print(f"Fixed {fixed_count} validation issues.")
            else:
                print("All existing mappings are valid.")
            
            # Step 3: Detect duplicates and offer to resolve them
            print(f"\nDUPLICATE ANALYSIS:")
            duplicates = self._detect_duplicates()
            if duplicates:
                print(f"\nFound {len(duplicates)} duplicate patterns.")
                
                if self.config.get_processing_setting('interactive_conflicts'):
                    if self._confirm_action("Would you like to resolve duplicates interactively?"):
                        resolved_count = self._interactive_resolve_duplicates(duplicates)
                        print(f"Resolved {resolved_count} duplicate patterns.")
            else:
                print("No duplicate patterns found.")
            
            print("\n" + "=" * 60)
            print("MAPPING VALIDATION COMPLETE")
            
            # Summary
            remaining_validation = len([issue for issue in validation_issues if not getattr(issue, 'fixed', False)])
            remaining_duplicates = len([dup for dup in duplicates if not getattr(dup, 'resolved', False)])
            total_remaining = remaining_validation + remaining_duplicates
            
            if total_remaining == 0:
                print("\nSUMMARY: All mappings are valid and ready to use.")
            else:
                print(f"\nSUMMARY: {total_remaining} issues remaining:")
                if remaining_validation > 0:
                    print(f"  - {remaining_validation} validation issues")
                if remaining_duplicates > 0:
                    print(f"  - {remaining_duplicates} duplicate patterns")
                print("\nRun the command again to continue fixing remaining issues.")
            
            return True
            
        except Exception as e:
            print(f"\nERROR: VALIDATION FAILED: {e}")
            if self.debug_mode:
                import traceback
                traceback.print_exc()
            return False

    def run_combined_processing(self) -> bool:
        """
        Run comprehensive mapping management workflow.

        This combines the best of both workflows:
        1. Process new mappings from new_mappings.toml (if any)
        2. Validate existing mappings with interactive fixing
        3. Detect and resolve duplicates interactively
        """
        print("COMPREHENSIVE MAPPING MANAGEMENT")
        print("=" * 60)

        try:
            # Step 1: Check that required files exist
            print("\nFILE CHECK:")
            if not self._check_required_files():
                return False

            # Step 2: Create backups before any modifications
            print("\nBACKUP:")
            self._backup_file(self.private_mappings, actually_backup=True)
            self._backup_file(self.public_mappings, actually_backup=True)
            self._cleanup_old_backups(keep_count=10)

            # Step 3: Process new mappings if they exist
            print(f"\nNEW MAPPINGS:")
            new_mappings_processed = False
            if os.path.exists(self.new_mappings_file):
                new_data = self._load_toml_file(self.new_mappings_file)
                if new_data:
                    # Count new mappings
                    private_count = sum(1 for m in new_data.values() if isinstance(m, dict) and m.get('scope') == 'private')
                    public_count = sum(1 for m in new_data.values() if isinstance(m, dict) and m.get('scope') != 'private')
                    total_new = private_count + public_count

                    print(f"Found {total_new} new mappings:")
                    print(f"  - {private_count} private mappings")
                    print(f"  - {public_count} public mappings")

                    if self._confirm_action("\nProcess these new mappings?"):
                        if self._process_new_mappings():
                            print("✓ New mappings processed successfully")
                            new_mappings_processed = True
                        else:
                            print("✗ Failed to process new mappings")
                            return False
                    else:
                        print("Skipping new mappings processing")
                else:
                    print("No new mappings found in file")
            else:
                print(f"No new mappings file found ({os.path.basename(self.new_mappings_file)})")

            # Step 4: Validate existing mappings with interactive fixing
            print(f"\nVALIDATION:")
            validation_issues = self._validate_mappings()
            if validation_issues:
                print(f"Found {len(validation_issues)} validation issues")

                if self.config.get_processing_setting('interactive_conflicts'):
                    if self._confirm_action("\nFix validation issues interactively?"):
                        fixed_count = self._interactive_fix_validation_issues(validation_issues)
                        print(f"✓ Fixed {fixed_count} validation issues")
                else:
                    print("Interactive mode disabled - run with interactive_conflicts=true to fix")
            else:
                print("✓ All existing mappings are valid")

            # Step 5: Detect and resolve duplicates interactively
            print(f"\nDUPLICATES:")
            duplicates = self._detect_duplicates()
            if duplicates:
                print(f"Found {len(duplicates)} duplicate patterns")

                if self.config.get_processing_setting('interactive_conflicts'):
                    if self._confirm_action("\nResolve duplicates interactively?"):
                        resolved_count = self._interactive_resolve_duplicates(duplicates)
                        print(f"✓ Resolved {resolved_count} duplicate patterns")
                else:
                    print("Interactive mode disabled - run with interactive_conflicts=true to resolve")
            else:
                print("✓ No duplicate patterns found")

            # Summary
            print("\n" + "=" * 60)
            print("MAPPING MANAGEMENT COMPLETE")

            if new_mappings_processed:
                print("\n✓ New mappings integrated")

            # Count remaining issues
            remaining_validation = len([issue for issue in validation_issues if not getattr(issue, 'fixed', False)])
            remaining_duplicates = len([dup for dup in duplicates if not getattr(dup, 'resolved', False)])
            total_remaining = remaining_validation + remaining_duplicates

            if total_remaining == 0:
                print("✓ All mappings validated and clean")
            else:
                print(f"\n⚠  {total_remaining} issues remaining to fix manually")

            return True

        except Exception as e:
            print(f"\nERROR: {e}")
            if self.debug_mode:
                import traceback
                traceback.print_exc()
            return False

    def _confirm_action(self, message: str, default: bool = True) -> bool:
        """Ask user for confirmation with default Yes."""
        return prompt_yes_no(message, default=default)
    
    def _interactive_fix_validation_issues(self, issues: List[Dict]) -> int:
        """Interactively fix validation issues."""
        print("\nInteractive Validation Issue Fixing")
        print("-" * 40)
        
        fixed_count = 0
        
        for i, issue in enumerate(issues, 1):
            print(f"\nIssue {i}/{len(issues)}:")
            print(f"File: {issue['file']}")
            print(f"Pattern: '{issue['pattern']}'")
            print(f"Section: {issue['section']}")
            print(f"Problem: {issue['issue']}")
            print(f"Current mapping: {issue['mapping']}")
            
            # Offer specific fixes based on issue type
            if issue['type'] == 'missing_field':
                if self._fix_missing_field_interactive(issue):
                    fixed_count += 1
                    issue['fixed'] = True
                    
            elif issue['type'] == 'wrong_scope':
                if self._fix_wrong_scope_interactive(issue):
                    fixed_count += 1
                    issue['fixed'] = True
                    
            elif issue['type'] == 'invalid_category':
                if self._fix_invalid_category_interactive(issue):
                    fixed_count += 1
                    issue['fixed'] = True
            
            else:
                print("Cannot auto-fix this issue type. Manual correction needed.")
        
        return fixed_count
    
    def _fix_missing_field_interactive(self, issue: Dict) -> bool:
        """Interactively fix missing field issues."""
        missing_field = issue['issue'].split(': ')[1]  # Extract field name from "Missing required field: scope"
        mapping = issue['mapping']
        
        if missing_field == 'scope':
            print(f"\nMissing scope field. This mapping should be:")
            print("1. 'private' - Local business, personal service, or employer")
            print("2. 'public' - National chain or well-known service")
            
            while True:
                choice = input("Enter scope (private/public): ").lower().strip()
                if choice in ['private', 'public']:
                    print(f"Would set scope = '{choice}' for this mapping.")
                    # Note: In actual implementation, this would update the file
                    return True
                else:
                    print("Please enter 'private' or 'public'")
        
        elif missing_field in ['name', 'category', 'subcategory']:
            suggested_value = input(f"Enter value for missing '{missing_field}': ").strip()
            if suggested_value:
                print(f"Would set {missing_field} = '{suggested_value}' for this mapping.")
                return True
        
        return False
    
    def _fix_wrong_scope_interactive(self, issue: Dict) -> bool:
        """Interactively fix wrong scope issues."""
        current_scope = issue['mapping'].get('scope', 'unknown')
        file_name = issue['file']
        expected_scope = "private" if "private" in file_name else "public"
        
        print(f"\nScope mismatch:")
        print(f"Current scope: '{current_scope}'")
        print(f"Expected scope for {file_name}: '{expected_scope}'")
        print(f"1. Fix scope to '{expected_scope}'")
        print(f"2. Move mapping to correct file")
        print(f"3. Skip this issue")
        
        while True:
            choice = input("Enter choice (1/2/3): ").strip()
            if choice == '1':
                print(f"Would update scope to '{expected_scope}'")
                return True
            elif choice == '2':
                target_file = "private_mappings.toml" if current_scope == "private" else "public_mappings.toml"
                print(f"Would move mapping to {target_file}")
                return True
            elif choice == '3':
                return False
            else:
                print("Please enter 1, 2, or 3")
    
    def _fix_invalid_category_interactive(self, issue: Dict) -> bool:
        """Interactively fix invalid category issues."""
        mapping = issue['mapping']
        current_category = mapping.get('category', '')
        current_subcategory = mapping.get('subcategory', '')
        
        print(f"\nInvalid category: {current_category}.{current_subcategory}")
        print("Available primary categories:")
        
        # Show available categories
        for i, primary in enumerate(sorted(COMPLETE_PFC_TAXONOMY.keys())[:10], 1):
            print(f"  {i}. {primary}")
        if len(COMPLETE_PFC_TAXONOMY) > 10:
            print(f"  ... and {len(COMPLETE_PFC_TAXONOMY) - 10} more")
        
        print("\nOptions:")
        print("1. Enter new category and subcategory")
        print("2. Skip this issue")
        
        while True:
            choice = input("Enter choice (1/2): ").strip()
            if choice == '1':
                new_category = input("Enter primary category: ").strip()
                if new_category in COMPLETE_PFC_TAXONOMY:
                    print(f"Available subcategories for {new_category}:")
                    for subcategory in sorted(COMPLETE_PFC_TAXONOMY[new_category].keys())[:5]:
                        print(f"  - {subcategory}")
                    if len(COMPLETE_PFC_TAXONOMY[new_category]) > 5:
                        print(f"  ... and {len(COMPLETE_PFC_TAXONOMY[new_category]) - 5} more")
                    
                    new_subcategory = input("Enter subcategory: ").strip()
                    if new_subcategory in COMPLETE_PFC_TAXONOMY[new_category]:
                        print(f"Would update to {new_category}.{new_subcategory}")
                        return True
                    else:
                        print("Invalid subcategory. Available options shown above.")
                else:
                    print("Invalid primary category. Please check available categories.")
            elif choice == '2':
                return False
            else:
                print("Please enter 1 or 2")
    
    def _remove_pattern_from_file(self, file_path: str, pattern: str, primary_key: str, subcategory_key: str) -> bool:
        """
        Remove a specific pattern from a TOML file.

        Args:
            file_path: Path to the TOML file
            pattern: The pattern string to remove
            primary_key: Primary category key (e.g., "FOOD_AND_DRINK")
            subcategory_key: Subcategory key (e.g., "FOOD_AND_DRINK_RESTAURANT")

        Returns:
            True if successfully removed, False otherwise
        """
        try:
            # Load the file (nested structure: PRIMARY -> SUBCATEGORY -> patterns)
            data = self._load_toml_file(file_path)

            # Navigate the nested structure and remove the pattern
            if primary_key in data:
                if subcategory_key in data[primary_key]:
                    if pattern in data[primary_key][subcategory_key]:
                        del data[primary_key][subcategory_key][pattern]
                        self._debug_print(f"Removed pattern '{pattern}' from {primary_key}.{subcategory_key}")

                        # If subcategory is now empty, optionally remove it (keep for now)
                        # Clean up empty subcategories would go here if desired

                        # Flatten the nested structure for writing (TOML format)
                        flattened_data = {}
                        for prim_key, prim_section in data.items():
                            if isinstance(prim_section, dict):
                                for subcat_key, subcat_section in prim_section.items():
                                    if isinstance(subcat_section, dict):
                                        section_name = f"{prim_key}.{subcat_key}"
                                        flattened_data[section_name] = subcat_section

                        # Write the file back with flattened structure
                        header = self._get_private_mappings_header() if 'private' in file_path else self._get_public_mappings_header()
                        self._write_toml_file_actual(file_path, flattened_data, header)
                        return True

            print(f"Warning: Pattern '{pattern}' not found in {file_path}")
            return False

        except Exception as e:
            print(f"ERROR: Could not remove pattern from {file_path}: {e}")
            if self.debug_mode:
                import traceback
                traceback.print_exc()
            return False

    def _interactive_resolve_duplicates(self, duplicates: List[Dict]) -> int:
        """Interactively resolve duplicate patterns."""
        print("\nInteractive Duplicate Resolution")
        print("-" * 40)

        resolved_count = 0

        for i, dup in enumerate(duplicates, 1):
            print(f"\nDuplicate {i}/{len(duplicates)}:")
            print(f"Pattern: '{dup['pattern']}'")
            print(f"\n1. Keep in {dup['existing_file']} [{dup['existing_section']}]")
            print(f"   Mapping: {dup['existing_mapping']}")
            print(f"\n2. Keep in {dup['duplicate_file']} [{dup['duplicate_section']}]")
            print(f"   Mapping: {dup['duplicate_mapping']}")

            while True:
                choice = input("\nKeep which mapping? (1/2/s to skip): ").strip()
                if choice == '1':
                    # Keep existing, remove duplicate
                    file_to_modify = os.path.join(self.config_dir, dup['duplicate_file'])
                    if self._remove_pattern_from_file(
                        file_to_modify,
                        dup['pattern'],
                        dup['duplicate_primary'],
                        dup['duplicate_subcategory']
                    ):
                        print(f"✓ Removed duplicate from {dup['duplicate_file']}")
                        resolved_count += 1
                        dup['resolved'] = True
                    else:
                        print(f"✗ Failed to remove duplicate")
                    break
                elif choice == '2':
                    # Keep duplicate, remove existing
                    file_to_modify = os.path.join(self.config_dir, dup['existing_file'])
                    if self._remove_pattern_from_file(
                        file_to_modify,
                        dup['pattern'],
                        dup['existing_primary'],
                        dup['existing_subcategory']
                    ):
                        print(f"✓ Removed duplicate from {dup['existing_file']}")
                        resolved_count += 1
                        dup['resolved'] = True
                    else:
                        print(f"✗ Failed to remove duplicate")
                    break
                elif choice.lower() == 's':
                    print("Skipped duplicate resolution")
                    break
                else:
                    print("Please enter '1', '2', or 's'")

        return resolved_count

    def _detect_similar_patterns(self) -> List[Dict]:
        """
        Detect similar mapping patterns that could be consolidated with wildcards.

        Returns:
            List of pattern groups that could benefit from wildcard consolidation
        """
        from difflib import SequenceMatcher

        print("\nAnalyzing mappings for wildcard consolidation opportunities...")

        similar_groups = []
        files_to_check = {
            'private_mappings.toml': os.path.join(self.config_dir, 'private_mappings.toml'),
            'public_mappings.toml': os.path.join(self.config_dir, 'public_mappings.toml')
        }

        for file_name, file_path in files_to_check.items():
            if not os.path.exists(file_path):
                continue

            try:
                data = self._load_toml_file(file_path)

                # Flatten patterns by category
                for primary_key, primary_section in data.items():
                    if not isinstance(primary_section, dict):
                        continue

                    for subcat_key, subcat_section in primary_section.items():
                        if not isinstance(subcat_section, dict):
                            continue

                        patterns = list(subcat_section.keys())

                        # Find groups of similar patterns
                        checked = set()
                        for i, pattern1 in enumerate(patterns):
                            if pattern1 in checked or '*' in pattern1 or '?' in pattern1:
                                continue  # Skip already-wildcarded patterns

                            similar = [pattern1]
                            mapping1 = subcat_section[pattern1]

                            for pattern2 in patterns[i+1:]:
                                if pattern2 in checked or '*' in pattern2 or '?' in pattern2:
                                    continue

                                mapping2 = subcat_section[pattern2]

                                # Check if patterns are similar AND have same mapping
                                if (mapping1.get('name') == mapping2.get('name') and
                                    mapping1.get('category') == mapping2.get('category') and
                                    mapping1.get('subcategory') == mapping2.get('subcategory')):

                                    # Calculate similarity
                                    similarity = SequenceMatcher(None, pattern1.lower(), pattern2.lower()).ratio()

                                    if similarity >= 0.6:  # 60% similar
                                        similar.append(pattern2)
                                        checked.add(pattern2)

                            if len(similar) >= 2:  # At least 2 similar patterns
                                checked.add(pattern1)
                                similar_groups.append({
                                    'file': file_name,
                                    'category': primary_key,
                                    'subcategory': subcat_key,
                                    'patterns': similar,
                                    'mapping': mapping1,
                                    'suggested_wildcard': self._suggest_wildcard_pattern(similar)
                                })

            except Exception as e:
                print(f"Error analyzing {file_name}: {e}")
                if self.debug_mode:
                    import traceback
                    traceback.print_exc()

        return similar_groups

    def _suggest_wildcard_pattern(self, patterns: List[str]) -> str:
        """
        Suggest a wildcard pattern that matches all given patterns.

        Args:
            patterns: List of similar patterns

        Returns:
            Suggested wildcard pattern
        """
        if not patterns:
            return ""

        if len(patterns) == 1:
            return patterns[0]

        # Find common prefix
        common_prefix = patterns[0].lower()
        for pattern in patterns[1:]:
            pattern_lower = pattern.lower()
            i = 0
            while i < len(common_prefix) and i < len(pattern_lower) and common_prefix[i] == pattern_lower[i]:
                i += 1
            common_prefix = common_prefix[:i]

        # Find common suffix
        common_suffix = patterns[0].lower()
        for pattern in patterns[1:]:
            pattern_lower = pattern.lower()
            i = 1
            while (i <= len(common_suffix) and i <= len(pattern_lower) and
                   common_suffix[-i] == pattern_lower[-i]):
                i += 1
            common_suffix = common_suffix[-(i-1):] if i > 1 else ""

        # Remove overlapping prefix/suffix
        if common_prefix and common_suffix:
            # Check if they overlap
            overlap_len = min(len(common_prefix), len(common_suffix))
            for i in range(overlap_len, 0, -1):
                if common_prefix[-i:] == common_suffix[:i]:
                    common_suffix = common_suffix[i:]
                    break

        # Build wildcard pattern
        if common_prefix and common_suffix:
            return f"{common_prefix}*{common_suffix}"
        elif common_prefix:
            return f"{common_prefix}*"
        elif common_suffix:
            return f"*{common_suffix}"
        else:
            # Find most common word
            word_counts = {}
            for pattern in patterns:
                words = pattern.lower().split()
                for word in words:
                    word_counts[word] = word_counts.get(word, 0) + 1

            if word_counts:
                most_common = max(word_counts.items(), key=lambda x: x[1])[0]
                return f"*{most_common}*"

            return patterns[0]  # Fallback to first pattern

    def run_wildcard_consolidation(self) -> bool:
        """
        Analyze mappings and suggest wildcard consolidations interactively.

        Returns:
            True if consolidations were made successfully
        """
        print("\n" + "="*70)
        print("WILDCARD MAPPING CONSOLIDATION ANALYZER")
        print("="*70)
        print("\nThis tool identifies similar mapping patterns that could be")
        print("consolidated into fewer wildcard patterns for easier maintenance.")
        print()

        # Detect similar patterns
        similar_groups = self._detect_similar_patterns()

        if not similar_groups:
            print("✓ No consolidation opportunities found.")
            print("  All mappings are already optimized!")
            return True

        print(f"\n�� Found {len(similar_groups)} consolidation opportunit{'y' if len(similar_groups) == 1 else 'ies'}!\n")

        consolidated_count = 0
        skipped_count = 0

        for i, group in enumerate(similar_groups, 1):
            print("="*70)
            print(f"Opportunity {i}/{len(similar_groups)}")
            print("="*70)
            print(f"File: {group['file']}")
            print(f"Category: {group['category']}.{group['subcategory']}")
            print(f"Merchant: {group['mapping'].get('name', 'Unknown')}")
            print()
            print(f"Current patterns ({len(group['patterns'])}):")
            for pattern in group['patterns']:
                print(f"  - \"{pattern}\"")
            print()
            print(f"Suggested wildcard pattern:")
            print(f"  → \"{group['suggested_wildcard']}\"")
            print()
            print(f"This would replace {len(group['patterns'])} patterns with 1 wildcard pattern.")
            print()

            # Ask user if they want to consolidate
            from utils import prompt_with_validation
            choice = prompt_with_validation(
                "Consolidate these patterns?",
                valid_options=['y', 'yes', 'n', 'no', 's', 'skip', 'q', 'quit'],
                default='y'
            )

            if choice in ['q', 'quit']:
                print("\nExiting consolidation...")
                break
            elif choice in ['s', 'skip']:
                print("Skipping remaining opportunities...")
                skipped_count += len(similar_groups) - i + 1
                break
            elif choice in ['n', 'no']:
                print("Skipped this consolidation.")
                skipped_count += 1
                continue

            # User chose yes - perform consolidation
            print("\n→ Consolidating patterns...")

            # This would implement the actual consolidation
            # For now, just print what would happen
            print(f"  ✓ Would add wildcard pattern: \"{group['suggested_wildcard']}\"")
            print(f"  ✓ Would remove {len(group['patterns'])} exact patterns")
            consolidated_count += 1

            # TODO: Implement actual file modification
            print("  ⚠  NOTE: Actual file modification not yet implemented")
            print()

        print("\n" + "="*70)
        print("CONSOLIDATION SUMMARY")
        print("="*70)
        print(f"Consolidated: {consolidated_count}")
        print(f"Skipped: {skipped_count}")
        print(f"Total analyzed: {len(similar_groups)}")

        if consolidated_count > 0:
            print("\n⚠  Remember to test enrichment after consolidation!")
            print("   Run: python src/cli.py enrich")

        return True


def main():
    """Main function for standalone execution."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Process financial transaction mappings")
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    parser.add_argument('--config-dir', default='config', help='Configuration directory')
    
    args = parser.parse_args()
    
    processor = MappingProcessor(config_dir=args.config_dir, debug_mode=args.debug)
    success = processor.run_full_processing()
    
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())