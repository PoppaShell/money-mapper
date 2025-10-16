# Money Mapper - Financial Transaction Parser & Enricher

A Python tool for extracting and categorizing financial transactions from bank statements. Automatically detects statement types (checking, savings, credit), extracts transaction data, and enriches with merchant names and categories using the Plaid Personal Finance Category (PFC) taxonomy.

## Features

- **Multi-format Support**: Handles checking, savings, and credit card statements
- **Automatic Detection**: Intelligently identifies statement types
- **Transaction Extraction**: Parses transaction data with proper date handling
- **Merchant Recognition**: Extracts clean merchant names from descriptions
- **Smart Categorization**: Uses Plaid PFC taxonomy + custom mappings
- **Configurable**: TOML-based configuration system via `settings.toml`
- **Privacy-Aware**: Sanitizes account numbers and sensitive data automatically
- **Progress Tracking**: Visual progress bars for long-running operations
- **Mapping Management**: Interactive tools for managing merchant categorizations
- **CLI Interface**: Simple command-line and interactive menu modes

## Installation

### Requirements
- Python 3.11+ (for built-in TOML support)
- For Python < 3.11: Install `tomli` package

### Setup
```bash
# Clone the repository
git clone https://github.com/PoppaShell/money-mapper.git
cd money-mapper

# Install dependencies
pip install -r requirements.txt

# Verify installation
python src/cli.py --help
```

## Quick Start

### Interactive Mode (Recommended)
```bash
python src/cli.py
```

You'll see a menu with options:
```
1. Extract transactions from PDFs
2. Categorize transactions
3. Extract & categorize (full process)
4. Review categorization results
5. Check configuration files
6. Manage merchant mappings
7. Exit
```

Choose an option and follow the prompts - no need to remember commands!

### Command Line Usage
```bash
# Parse PDF statements
python src/cli.py parse --dir statements

# Enrich with categories
python src/cli.py enrich --input output/financial_transactions.json

# Complete pipeline
python src/cli.py pipeline --dir statements

# Analyze accuracy
python src/cli.py analyze --file output/enriched_transactions.json

# Manage mappings
python src/cli.py add-mappings
```

### Advanced Options
```bash
# Enable verbose output
python src/cli.py analyze --verbose

# Enable debug mode for troubleshooting
python src/cli.py parse --debug --dir statements
python src/cli.py enrich --debug --input output/financial_transactions.json
```

## Configuration

### Initial Setup

The project includes template configuration files. On first run:

1. **Review** `config/settings.toml` - Main configuration file
2. **Customize** `config/private_mappings.toml` - Add your local merchants and personal mappings
3. **Review** `config/public_mappings.toml` - Pre-configured with 580+ national chain mappings
4. **Configure Privacy** - Add personal info to redact in `settings.toml`

### Adding Custom Merchants
Edit `config/new_mappings.toml` and follow instructions in the file to add properly formatted and categorized mappings.

**Categorization Guidelines:**
The [Plaid PFC (Personal Finance Categories)](https://plaid.com/docs/transactions/pfc-migration/) is used as a standard and can be referenced. The taxonomy has 16 primary and 104 detailed categories. 

**Scope Guidelines:**
- `scope = "private"` - Local businesses, personal services, your employer
- `scope = "public"` - National chains, widely-known brands

**Example Mapping Entries:**
```toml
"starbucks" = { name = "Starbucks", category = "FOOD_AND_DRINK", subcategory = "FOOD_AND_DRINK_COFFEE", scope = "public" }
"joes pizza downtown" = { name = "Joe's Pizza", category = "FOOD_AND_DRINK", subcategory = "FOOD_AND_DRINK_RESTAURANT", scope = "private" }
"shell gas" = { name = "Shell", category = "TRANSPORTATION", subcategory = "TRANSPORTATION_GAS", scope = "public" }
```

### Mapping Processing & Management

The `add-mappings` command provides a comprehensive workflow:

```bash
python src/cli.py add-mappings
```

Features:
1. **Process New Mappings**: Add mappings from `new_mappings.toml`
2. **Validate Existing**: Check for invalid categories or missing fields
3. **Fix Issues Interactively**: Guided fixing of validation problems
4. **Detect Duplicates**: Find and resolve duplicate patterns across files
5. **Automatic Backups**: Creates timestamped backups before changes

### Validation

Check your mappings for errors:

```bash
python src/cli.py check-mappings
```

This validates:
- Required fields (name, category, subcategory, scope)
- Category/subcategory against PFC taxonomy
- Scope values (must be "public" or "private")
- Duplicate patterns across files

## File Structure

```
money-mapper/
├── src/
│   ├── cli.py                      # Command-line interface
│   ├── statement_parser.py         # PDF parsing logic
│   ├── transaction_enricher.py     # Categorization logic
│   ├── utils.py                    # Shared utilities
│   ├── config_manager.py           # Configuration management
│   └── mapping_processor.py        # Mapping validation & management
├── config/
│   ├── settings.toml               # Main configuration (paths, privacy, etc.)
│   ├── statement_patterns.toml     # PDF parsing patterns
│   ├── plaid_categories.toml       # Official Plaid PFC taxonomy
│   ├── private_mappings.toml       # Your personal/local merchant mappings
│   ├── public_mappings.toml        # National chain merchant mappings (580+)
│   └── new_mappings.toml           # Template for adding new mappings
├── statements/                     # Place PDF statements here (gitignored)
├── output/                         # Generated JSON files (gitignored)
├── backups/                        # Automatic mapping backups (gitignored)
├── requirements.txt
└── README.md
```

## Output Format

### Raw Transactions (`output/financial_transactions.json`)
```json
{
    "date": "2025-04-02",
    "description": "WALMART.COM 555-555-5555 CA 1234 5678",
    "amount": -27.03,
    "account_type": "credit",
    "source_file": "eStmt_2025-07-26.pdf",
    "processing_date": "2025-04-03T12:30:00.000000"
}
```

### Enriched Transactions (`output/enriched_transactions.json`)
```json
{
    "date": "2025-04-02",
    "description": "WALMART.COM [PHONE] CA 1234 5678",
    "amount": -27.03,
    "account_type": "credit",
    "source_file": "eStmt_2025-07-26.pdf",
    "processing_date": "2025-04-03T12:30:00.000000",
    "merchant_name": "Walmart",
    "category": "FOOD_AND_DRINK",
    "subcategory": "FOOD_AND_DRINK_GROCERIES",
    "confidence": 0.95,
    "categorization_method": "public_mapping",
    "enrichment_date": "2025-04-03T12:30:00.000000"
  }
```

## Supported Statement Types

### Currently Supported Banks
- **Bank of America**

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

- **16 Primary Categories**: FOOD_AND_DRINK, TRANSPORTATION, MEDICAL, INCOME, etc.
- **104 Detailed Subcategories**: FOOD_AND_DRINK_GROCERIES, TRANSPORTATION_GAS, etc.
- **Priority Order**: Private mappings → Public mappings → Plaid taxonomy → Fuzzy matching

### Categorization Methods
- `private_mapping` - Matched against your personal mappings (highest priority)
- `public_mapping` - Matched against national chain mappings
- `fuzzy_match` - Similar pattern found with confidence threshold
- `plaid_category` - Matched against Plaid taxonomy
- `none` - No match found (requires manual mapping)

## Privacy & Security

Money Mapper includes a comprehensive privacy redaction system that automatically protects sensitive information.

### Automatic Redaction (Enabled by Default)

The following data types are automatically redacted during PDF parsing:

| Data Type | Example | Redacted As |
|-----------|---------|-------------|
| Account Numbers | `1234 5678 9012 3456` | `[ACCOUNT]` |
| Partial Accounts | `CHK 7640 5875` | `CHK [ACCOUNT]` |
| Employee Names (ACH) | `INDN:JOHN SMITH` | `INDN:[NAME]` |
| Company IDs (ACH) | `COID:1362683258` | `COID:[COMPANY]` |
| Transaction IDs | `ID:1587637452` | `ID:[REF]` |
| Reference Numbers | `123456789012` | `[REF#]` |
| Phone Numbers | `555-123-4567` | `[PHONE]` |
| Email Addresses | `user@example.com` | `[EMAIL]` |

**Example:**
```
Before: ACME CORP DES:DIR DEP ID:1587637452 INDN:JOHN SMITH COID:1362683258
After:  ACME CORP DES:DIR DEP ID:[REF] INDN:[NAME] COID:[COMPANY]
```

### Fuzzy Keyword Redaction (User-Configured)

Protect your personal information by adding keywords to `config/settings.toml`:

```toml
[privacy.keywords]
# Names to redact (matches variations like "JOHN SMITH", "Smith, John", etc.)
names = [
    "John Smith",
    "Jane Doe",
]

# Employers/companies to redact
employers = [
    "Acme Corporation",
]

# Locations to redact (cities, addresses, etc.)
locations = [
    "123 Main Street",
    "Springfield",
]

# Custom keywords to redact
custom = [
    "my-bank-branch",
]
```

The system uses **fuzzy matching** (85% similarity threshold) to catch variations:
- `JOHN SMITH` → `[NAME]`
- `john smith` → `[NAME]`
- `ACME CORPORATION` → `[EMPLOYER]`

### Configuration

Enable/disable redaction in `config/settings.toml`:

```toml
[privacy]
enable_redaction = true              # Enable/disable all redaction
redaction_mode = "fuzzy"             # "exact" or "fuzzy" matching
fuzzy_redaction_threshold = 0.85     # Similarity threshold (0.0-1.0)
```

**Threshold Guidelines:**
- **0.90+**: Stricter matching, fewer false positives
- **0.80-0.89**: Balanced (recommended)
- **0.70-0.79**: More lenient, catches more variations

### Privacy Features

- **Local Processing**: All data stays on your machine
- **Automatic Backups**: Mappings backed up before modifications
- **No Cloud**: No data sent to external services
- **Configurable**: Easy to customize redaction rules
- **Non-invasive**: Only redacts configured keywords (except default patterns)

## Development

### Code Standards
- **PEP 8 Compliant**: Follows Python style guidelines
- **Well Documented**: Comprehensive docstrings and comments
- **Modular Design**: Clear separation of concerns
- **Error Handling**: Graceful failure with helpful messages
- **Progress Feedback**: Visual progress bars for long operations

### Extending the Parser

1. **New Statement Types**: Add patterns to `config/statement_patterns.toml`
2. **New Categories**: Extend `config/plaid_categories.toml` (use official PFC taxonomy)
3. **Custom Merchants**: Add to `config/private_mappings.toml` or `config/public_mappings.toml`
4. **Parsing Logic**: Modify functions in `src/statement_parser.py`
5. **Enrichment Logic**: Modify functions in `src/transaction_enricher.py`

### Configuration System

All configuration is centralized in `config/settings.toml`:

```toml
[directories]
statements = "statements"      # PDF input directory
output = "output"             # JSON output directory

[file_paths]
private_mappings = "private_mappings.toml"
public_mappings = "public_mappings.toml"

[fuzzy_matching]
enrichment_threshold = 0.7    # Minimum similarity for fuzzy matching

[processing]
validate_categories = true    # Validate against PFC taxonomy
interactive_conflicts = true  # Prompt for conflict resolution

[privacy]
enable_redaction = true
redaction_mode = "fuzzy"
fuzzy_redaction_threshold = 0.85
```

## Troubleshooting

### Common Issues

**No transactions found**:
- Check PDF file format and bank compatibility
- Verify PDF files are in the `statements/` directory
- Enable debug mode: `python src/cli.py parse --debug --dir statements`
- Check if PDF text can be extracted (try copying text from PDF)

**Low categorization confidence**:
- Add custom mappings for your frequent merchants
- Run analysis: `python src/cli.py analyze --file output/enriched_transactions.json`
- Check for typos in merchant names
- Review uncategorized transactions and add mappings

**Configuration errors**:
- Validate TOML syntax (use a TOML validator)
- Run: `python src/cli.py validate`
- Check file paths in `config/settings.toml`
- Ensure required fields are present in mappings

**Mapping conflicts**:
- Run: `python src/cli.py add-mappings`
- Choose to resolve duplicates interactively
- Review conflict messages and keep appropriate mapping

### Debug Mode

Enable detailed output for troubleshooting:

```bash
# Debug parsing
python src/cli.py parse --debug --dir statements

# Debug enrichment
python src/cli.py enrich --debug --input output/financial_transactions.json

# Debug mapping management
python src/cli.py add-mappings --debug
```

Debug mode shows:
- Detailed processing steps
- Pattern matching attempts
- File operations
- Validation results
- Error stack traces

### Getting Help

```bash
# Show all commands
python src/cli.py --help

# Show command-specific help
python src/cli.py parse --help
python src/cli.py enrich --help
python src/cli.py analyze --help
```

## Performance

- **Parsing**: ~1-2 seconds per PDF statement
- **Enrichment**: ~50-100 transactions per second
- **Progress Bars**: Visual feedback for operations taking >2 seconds
- **Automatic Backups**: Negligible overhead (~10ms per backup)

## Contributing

Contributions welcome! Please:

1. **Follow PEP 8** coding standards
2. **Add comprehensive comments** for maintainability
3. **Test with various statement formats** before submitting
4. **Update documentation** for new features
5. **Maintain backwards compatibility** when possible

## License

This project is provided as-is for personal financial management. Please ensure compliance with your bank's terms of service when processing statements.

## Acknowledgments

- **Plaid**: For the Personal Finance Category (PFC) taxonomy
- **pypdf**: For PDF text extraction capabilities