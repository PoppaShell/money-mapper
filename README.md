# Financial Transaction Parser & Enricher

A Python tool for extracting and categorizing financial transactions from bank statements. Automatically detects statement types (checking, savings, credit), extracts transaction data, and enriches with merchant names and categories using the Plaid Personal Finance Category (PFC) taxonomy.

## Features

- **Multi-format Support**: Handles checking, savings, and credit card statements
- **Automatic Detection**: Intelligently identifies statement types
- **Transaction Extraction**: Parses transaction data with proper date handling
- **Merchant Recognition**: Extracts clean merchant names from descriptions
- **Smart Categorization**: Uses Plaid PFC taxonomy + custom mappings
- **Configurable**: TOML-based configuration for easy customization
- **Privacy-Aware**: Sanitizes account numbers and sensitive data
- **CLI Interface**: Simple command-line tools for batch processing

## Installation

### Requirements
- Python 3.11+ (for built-in TOML support)
- For Python < 3.11: Install `tomli` package

### Setup
```bash
# Clone or download the project
cd financial_parser

# Install dependencies
pip install -r requirements.txt

# Verify installation
python cli.py --help
```

## Quick Start

### Interactive Mode (Recommended)
```bash
python cli.py
```
Choose from menu options for guided processing.

### Command Line Usage
```bash
# Parse PDF statements
python cli.py parse --dir ./statements

# Enrich with categories
python cli.py enrich --input financial_transactions.json

# Complete pipeline
python cli.py pipeline --dir ./statements

# Analyze accuracy
python cli.py analyze --file enriched_transactions.json
```

## Configuration

### Personal Mappings Setup

1. **Edit** `config/personal_mappings.toml` with your specific data
2. **Add** your income sources, banks, merchants, etc.
3. **Use** the commented template examples as guides
4. **Remove** personal data before sharing publicly

### Adding Custom Merchants

Add entries to `config/merchant_mappings.toml`:
```toml
[local_businesses]
"your merchant" = { 
    name = "Your Merchant Name", 
    category = "FOOD_AND_DRINK", 
    subcategory = "FOOD_AND_DRINK_RESTAURANTS" 
}
```

## File Structure

```
financial_parser/
├── cli.py                      # Command-line interface
├── statement_parser.py         # PDF parsing logic
├── transaction_enricher.py     # Categorization logic
├── utils.py                    # Shared utilities
├── config/
│   ├── statement_patterns.toml # PDF parsing patterns
│   ├── plaid_categories.toml   # Official Plaid taxonomy
│   ├── merchant_mappings.toml  # Public merchant mappings
│   └── personal_mappings.toml  # Your private mappings
├── requirements.txt
└── README.md
```

## Output Format

### Raw Transactions (`output/financial_transactions.json`)
```json
{
  "transaction_date": "2025-01-15",
  "description": "walmart supercenter",
  "amount": -45.67,
  "account_type": "checking",
  "account_number": "********1234",
  "transaction_type": "withdrawal",
  "source_file": "checking_2025-01-15.pdf"
}
```

### Enriched Transactions (`output/enriched_transactions.json`)
```json
{
  "transaction_date": "2025-01-15",
  "description": "walmart supercenter",
  "amount": -45.67,
  "account_type": "checking",
  "account_number": "********1234",
  "transaction_type": "withdrawal",
  "source_file": "checking_2025-01-15.pdf",
  "merchant_name": "Walmart",
  "primary_category": "FOOD_AND_DRINK",
  "detailed_category": "FOOD_AND_DRINK_GROCERIES",
  "confidence": 0.95,
  "categorization_method": "custom_mapping",
  "original_amount": -45.67
}
```

## Supported Statement Types

### Bank Statement Formats
- **Checking Accounts**: Enhanced parsing for multi-line descriptions
- **Savings Accounts**: Interest and transfer tracking
- **Credit Cards**: Dual-date support (posting + transaction dates)

### Date Handling
- Automatically determines correct years for partial dates
- Handles cross-year statement periods
- Standardizes to ISO format (YYYY-MM-DD)

## Category System

Uses the [Plaid Personal Finance Category (PFC) taxonomy](https://plaid.com/docs/api/products/transactions/#transaction-object):

- **Primary Categories**: FOOD_AND_DRINK, TRANSPORTATION, MEDICAL, etc.
- **Detailed Categories**: FOOD_AND_DRINK_GROCERIES, TRANSPORTATION_GAS, etc.
- **Custom Mappings**: Override with your specific merchants and patterns

## Privacy & Security

- **Account Masking**: Shows only last 4 digits
- **Data Sanitization**: Removes phone numbers, reference codes
- **Local Processing**: All data stays on your machine
- **Configurable**: Easy to remove personal data before sharing

## Development

### Code Standards
- **PEP 8 Compliant**: Follows Python style guidelines
- **Well Documented**: Comprehensive docstrings and comments
- **Modular Design**: Simple functions, minimal dependencies
- **Error Handling**: Graceful failure and user feedback

### Extending the Parser

1. **New Statement Types**: Add patterns to `config/statement_patterns.toml`
2. **New Categories**: Extend `config/plaid_categories.toml`
3. **Custom Logic**: Modify parsing functions in `statement_parser.py`

## Troubleshooting

### Common Issues

**No transactions found**:
- Check PDF file format and bank compatibility
- Enable debug mode: `--debug` flag in src/ directory
- Verify statement text extraction

**Low categorization confidence**:
- Add custom mappings for frequent merchants
- Run analysis: `cd src && python cli.py analyze`
- Review and update patterns

**Configuration errors**:
- Validate TOML syntax
- Check file paths and permissions
- Review error messages for specific issues

### Debug Mode
```bash
cd src
python cli.py parse --debug --dir ../statements
```
Provides detailed output for troubleshooting parsing issues.

## Contributing

1. **Follow PEP 8** coding standards
2. **Add comprehensive comments** for maintainability
3. **Test with various statement formats**
4. **Update documentation** for new features

## License

This project is provided as-is for personal financial management. Please ensure compliance with your bank's terms of service when processing statements.