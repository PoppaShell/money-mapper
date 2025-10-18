# Money Mapper - Financial Transaction Parser & Enricher

A Python tool for extracting and categorizing financial transactions from bank statements. Automatically detects statement types (checking, savings, credit), extracts transaction data, and enriches with merchant names and categories using the Plaid Personal Finance Category (PFC) taxonomy.

## Features

- **Multi-format Support**: Handles checking, savings, and credit card statements
- **Automatic Detection**: Intelligently identifies statement types
- **Transaction Extraction**: Parses transaction data with proper date handling
- **Merchant Recognition**: Extracts clean merchant names from descriptions
- **Smart Categorization**: Uses Plaid PFC taxonomy + custom mappings
- **Interactive Mapping Builder**: Guided workflow to categorize uncategorized transactions with smart suggestions
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

**First Run:** The setup wizard will automatically launch and guide you through:
- Creating private configuration files
- Configuring privacy settings
- Parsing existing statements (automatic if you opt in)
- Enriching and categorizing transactions
- Building initial merchant mappings

**Subsequent Runs:** You'll see the main menu with options:
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

### First-Run Setup Wizard

Money Mapper includes an interactive setup wizard that runs automatically on first use:

```bash
# Setup wizard runs automatically on first launch
python src/cli.py

# Or run setup manually anytime
python src/cli.py setup
```

The setup wizard will:
1. **Create private configuration files** from templates (gitignored)
2. **Configure privacy settings** interactively (names, employers, locations to redact)
3. **Parse existing statements** automatically if you opt in
4. **Enrich and categorize transactions** with immediate analysis results
5. **Launch Interactive Mapping Builder** for any uncategorized transactions
6. **Complete setup in one session** - ready to use immediately!

**What the Setup Wizard Does:**

**Privacy Configuration:**
- Creates `config/private_settings.toml` from template
- Creates `config/private_mappings.toml` from template
- Interactively configures names, employers, and locations to redact

**Automatic Processing (if you opt in):**
- Parses all PDF statements in `statements/` directory
- Enriches transactions with categories and merchant names
- Shows categorization analysis results
- Offers Interactive Mapping Builder for uncategorized transactions
- Completes full setup in one seamless workflow

**Manual Processing (if you decline):**
- Shows instructions for running commands later:
  - `python src/cli.py parse --dir statements`
  - `python src/cli.py enrich`
  - `python src/cli.py analyze`

### Configuration Files

Money Mapper uses a **public/private configuration split** for security:

**Public Configuration** (versioned in git, shared across users):
- `config/public_settings.toml` - Application settings (paths, thresholds, processing options)
- `config/public_mappings.toml` - National chain merchant mappings (580+)
- `config/plaid_categories.toml` - Plaid Personal Finance Category taxonomy
- `config/statement_patterns.toml` - PDF parsing patterns

**Private Configuration** (gitignored, user-specific):
- `config/private_settings.toml` - Privacy settings (names, employers, locations to redact)
- `config/private_mappings.toml` - Personal/local merchant mappings

**Templates** (versioned in git, used to create private configs):
- `config/templates/private_settings.toml` - Template for privacy settings
- `config/templates/private_mappings.toml` - Template for personal mappings

This structure ensures:
- ✅ **Zero risk** of committing private data to git
- ✅ **Easy setup** with automated configuration creation
- ✅ **Clear separation** between public and private settings

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

### Interactive Mapping Builder

The Interactive Mapping Builder provides a guided workflow to quickly categorize uncategorized transactions without manually editing files.

**When does it activate?**
- Automatically offered after running categorization analysis (CLI Option 2 or 4)
- When uncategorized transactions are found

**How it works:**

1. **Frequency Analysis**: Identifies top 25 most common uncategorized merchants
2. **Smart Suggestions**: Automatically suggests keywords and merchant names
3. **Guided Selection**: Choose categories from numbered menus with descriptions
4. **Batch Processing**: Process multiple merchants in one session with skip/back options
5. **Automatic Processing**: Adds mappings to `new_mappings.toml` and processes them
6. **Re-enrichment**: Offers to re-run categorization with new mappings
7. **Progress Tracking**: Shows before/after improvement

**Example workflow:**

```
--- Top Uncategorized Transactions ---
Found 12 unique uncategorized merchants:

1. LOCAL COFFEE SHOP DOWNTOWN (8 occurrences)
2. REGIONAL GROCERY STORE (5 occurrences)
3. ABC HARDWARE (4 occurrences)
...

Would you like to create mappings for these transactions? (y/n): y

--- Interactive Mapping Builder ---

[1/12] Transaction: "LOCAL COFFEE SHOP DOWNTOWN #123"
Occurrences: 8 transaction(s)

Suggested keyword(s): local coffee shop
Suggested name: Local Coffee Shop

Edit keyword(s) [Enter to accept, 'skip' to skip]:
Edit name [Enter to accept, 'skip' to skip, 'back' to restart]:

Select PRIMARY category:
  1. BANK_FEES                    - Banking fees and charges
  2. ENTERTAINMENT                - Recreation and entertainment
  3. FOOD_AND_DRINK               - Food and beverage purchases
  ...
Enter number (or 'q' to cancel): 3

Select FOOD_AND_DRINK subcategory:
  1. COFFEE                       - Coffee shops and cafes
  2. FAST_FOOD                    - Fast food and quick service
  3. RESTAURANT                   - Dining at restaurants
  ...
Enter number (or 'q' to cancel): 1

Select scope:
  1. public  - National/regional chain (shareable)
  2. private - Local business or personal (kept private)
Enter number (or 'q' to go back): 2

Create this mapping? (y/n/back): y

✓ Added to new_mappings.toml:
  "local coffee shop" = { name = "Local Coffee Shop", category = "FOOD_AND_DRINK", subcategory = "FOOD_AND_DRINK_COFFEE", scope = "private" }

[Continue with next transaction...]

======================================================================
Mapping Builder Summary:
  Mappings created: 8
  Transactions skipped: 4
  Total processed: 12
======================================================================

New mappings have been added to new_mappings.toml
They need to be processed to take effect.

Would you like to run the mapping processor now? (y/n): y

[Mapping processor runs, validates, and integrates mappings...]

✓ Mapping processor completed successfully!
Your new mappings are now active.

--- Next Steps ---

Would you like to re-run enrichment with the new mappings? (y/n): y

[Re-running enrichment...]

--- Updated Analysis ---
Total Transactions: 150
Successfully Categorized: 145 (96.7%)
Uncategorized: 5 (3.3%)

Categorization improved by 16.7%!
```

**Key features:**
- **Smart Suggestions**: Automatically extracts clean keywords and names from transaction descriptions
- **Category Descriptions**: Each category and subcategory shows a description to help with selection
- **Flexible Navigation**: Skip transactions (`skip`), go back to fix mistakes (`back`), or quit anytime (`q`)
- **Safe Processing**: Mappings are added to `new_mappings.toml` first, then validated and processed
- **Immediate Feedback**: Re-run enrichment to see improvements right away

**Tips:**
- Use the Interactive Mapping Builder regularly to maintain high categorization rates
- Process new uncategorized merchants as they appear each month
- Skip merchants you're unsure about - you can always categorize them later
- Use `back` if you select the wrong category to restart that transaction

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
│   ├── interactive_mapper.py       # Interactive mapping builder
│   ├── utils.py                    # Shared utilities
│   ├── config_manager.py           # Configuration management
│   ├── setup_wizard.py             # First-run setup wizard
│   └── mapping_processor.py        # Mapping validation & management
├── config/
│   ├── templates/                  # Configuration templates (versioned)
│   │   ├── private_settings.toml   # Template for privacy settings
│   │   └── private_mappings.toml   # Template for personal mappings
│   ├── public_settings.toml        # Public settings (versioned)
│   ├── private_settings.toml       # Private settings (gitignored)
│   ├── public_mappings.toml        # National chain mappings (versioned, 580+)
│   ├── private_mappings.toml       # Personal/local mappings (gitignored)
│   ├── plaid_categories.toml       # Official Plaid PFC taxonomy (versioned)
│   ├── statement_patterns.toml     # PDF parsing patterns (versioned)
│   └── new_mappings.toml           # Template for adding new mappings (versioned)
├── statements/                     # Place PDF statements here (gitignored)
├── output/                         # Generated JSON files (gitignored)
├── backups/                        # Automatic mapping backups (gitignored)
├── requirements.txt
└── README.md
```

## Output Format

### Raw Transactions (`output/financial_transactions.json`)

**Credit Card Transaction (with dual dates):**
```json
{
    "date": "01/15",
    "transaction_date": "01/15/2025",
    "posting_date": "01/17/2025",
    "description": "GROCERY STORE #1234",
    "amount": -127.43,
    "account_type": "credit",
    "account_number": "****5678",
    "source_file": "statement_2025_01.pdf"
}
```

**Banking Transaction (checking/savings):**
```json
{
    "date": "2025-01-20",
    "description": "DIRECT DEPOSIT PAYROLL",
    "amount": 2500.00,
    "account_type": "checking",
    "account_number": "****9012",
    "source_file": "checking_2025_01.pdf"
}
```

**Field Descriptions:**
- `date`: Original date format from statement (MM/DD or YYYY-MM-DD)
- `transaction_date`: Full date when purchase was made (MM/DD/YYYY) - credit cards only
- `posting_date`: Full date when transaction posted to account (MM/DD/YYYY) - credit cards with dual dates only
- `description`: Transaction description with normalized whitespace
- `amount`: Transaction amount (negative = expense, positive = income)
- `account_type`: Type of account (credit, checking, savings)
- `account_number`: Masked account number showing only last 4 digits (e.g., "****1234")
- `source_file`: Original PDF statement filename

### Enriched Transactions (`output/enriched_transactions.json`)
```json
{
    "date": "01/15",
    "transaction_date": "01/15/2025",
    "posting_date": "01/17/2025",
    "description": "GROCERY STORE #1234",
    "amount": -127.43,
    "account_type": "credit",
    "account_number": "****5678",
    "source_file": "statement_2025_01.pdf",
    "merchant_name": "Grocery Store",
    "category": "FOOD_AND_DRINK",
    "subcategory": "GROCERIES",
    "confidence": 0.95,
    "categorization_method": "public_mapping"
}
```

**Additional Enrichment Fields:**
- `merchant_name`: Cleaned merchant name extracted from description
- `category`: Primary category from Plaid taxonomy
- `subcategory`: Detailed subcategory
- `confidence`: Match confidence score (0.0-1.0)
- `categorization_method`: How category was determined (public_mapping, private_mapping, fuzzy_match, plaid_taxonomy)

## Supported Statement Types

### Currently Supported Banks
- **Bank of America**

### Bank Statement Formats
- **Checking Accounts**: Enhanced parsing for multi-line descriptions
- **Savings Accounts**: Interest and transfer tracking
- **Credit Cards**: Dual-date support (posting + transaction dates)

### Date Handling
- **Transaction Dates**: Captures both transaction date and posting date from credit card statements
- **Year Detection**: Automatically determines correct year for MM/DD dates using statement period
- **Cross-Year Support**: Handles statements spanning year boundaries (e.g., Dec 2024 - Jan 2025)
- **Format Preservation**: Keeps original `date` format while adding full `transaction_date` and `posting_date` fields
- **Backwards Compatible**: Existing code continues to work with `date` field

**Example - Cross-Year Statement:**
- Statement Period: December 2024 - January 2025
- Transaction on 12/25 → `transaction_date: "12/25/2024"`
- Transaction on 01/05 → `transaction_date: "01/05/2025"`

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

Protect your personal information by configuring privacy settings in `config/private_settings.toml` (created during setup wizard):

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

Enable/disable redaction in `config/private_settings.toml`:

```toml
[privacy]
enable_redaction = true              # Enable/disable all redaction
redaction_mode = "fuzzy"             # "exact" or "fuzzy" matching
fuzzy_redaction_threshold = 0.85     # Similarity threshold (0.0-1.0)
```

**Note:** Privacy settings are stored in `config/private_settings.toml` (gitignored) to prevent accidental commits of personal information.

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

Money Mapper uses a split configuration system for security:

**Public Settings** (`config/public_settings.toml`) - Shared application settings:
```toml
[directories]
statements = "statements"      # PDF input directory
output = "output"             # JSON output directory

[file_paths]
private_mappings = "private_mappings.toml"
public_mappings = "public_mappings.toml"
private_settings = "private_settings.toml"
public_settings = "public_settings.toml"

[fuzzy_matching]
enrichment_threshold = 0.7    # Minimum similarity for fuzzy matching

[processing]
validate_categories = true    # Validate against PFC taxonomy
interactive_conflicts = true  # Prompt for conflict resolution
```

**Private Settings** (`config/private_settings.toml`) - Personal privacy settings (gitignored):
```toml
[privacy]
enable_redaction = true
redaction_mode = "fuzzy"
fuzzy_redaction_threshold = 0.85

[privacy.keywords]
names = ["Your Name"]
employers = ["Your Company"]
locations = ["Your City"]
custom = []
```

The configuration manager automatically merges both files, with private settings taking precedence.

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
- Check file paths in `config/public_settings.toml`
- Ensure `config/private_settings.toml` exists (run setup wizard if missing)
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