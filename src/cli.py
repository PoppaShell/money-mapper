#!/usr/bin/env python3
"""
Financial Parser CLI - Simple command-line interface.

Provides an easy-to-use command line interface for processing bank statements
and enriching transactions with categories and merchant names.
"""

import argparse
import os
import sys
from typing import Optional

# Add the src directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from statement_parser import process_pdf_statements
from transaction_enricher import process_transaction_enrichment, analyze_categorization_accuracy
from utils import load_transactions_from_json, ensure_directories_exist, validate_toml_files

try:
    from config_manager import get_config_manager
except ImportError:
    print("Error: Could not import config_manager. Please ensure config_manager.py is in the same directory.")
    sys.exit(1)

# Import MappingProcessor only when needed to avoid automatic execution
def get_mapping_processor(config_dir: str = "config", debug_mode: bool = False):
    """Import and return MappingProcessor class only when needed."""
    import importlib.util
    import sys
    import os
    
    # Get the path to mapping_processor.py
    current_dir = os.path.dirname(os.path.abspath(__file__))
    mapping_processor_path = os.path.join(current_dir, 'mapping_processor.py')
    
    if not os.path.exists(mapping_processor_path):
        print(f"Error: mapping_processor.py not found at {mapping_processor_path}")
        sys.exit(1)
    
    try:
        # Load the module dynamically
        spec = importlib.util.spec_from_file_location("mapping_processor", mapping_processor_path)
        mapping_processor_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mapping_processor_module)
        
        # Get the MappingProcessor class
        MappingProcessor = mapping_processor_module.MappingProcessor
        return MappingProcessor(config_dir=config_dir, debug_mode=debug_mode)
        
    except Exception as e:
        print(f"Error loading MappingProcessor: {e}")
        sys.exit(1)


def print_banner():
    """Print application banner."""
    print("=" * 60)
    print("  Money Mapper - Financial Transaction Parser & Enricher")
    print("  Extract and categorize transactions from bank statements")
    print("=" * 60)


def validate_directory(directory: str) -> bool:
    """
    Validate that directory exists and contains PDF files.
    
    Args:
        directory: Directory path to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not os.path.exists(directory):
        print(f"Error: Directory '{directory}' does not exist")
        print("Please check your config/public_settings.toml [directories] section or create the directory")
        return False
    
    if not os.path.isdir(directory):
        print(f"Error: '{directory}' is not a directory")
        return False
    
    # Check for PDF files
    pdf_files = [f for f in os.listdir(directory) if f.lower().endswith('.pdf')]
    if not pdf_files:
        print(f"Warning: No PDF files found in '{directory}'")
        print("Please add PDF files to process or check your directory configuration")
        return False
    
    print(f"Found {len(pdf_files)} PDF files in '{directory}'")
    return True


def validate_json_file(file_path: str) -> bool:
    """
    Validate that JSON file exists and contains transactions.
    
    Args:
        file_path: Path to JSON file
        
    Returns:
        True if valid, False otherwise
    """
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' does not exist")
        print("Please run the parse command first or check your file path configuration")
        return False
    
    try:
        transactions = load_transactions_from_json(file_path)
        if not transactions:
            print(f"Warning: No transactions found in '{file_path}'")
            return False
        
        print(f"Found {len(transactions)} transactions in '{file_path}'")
        return True
    except Exception as e:
        print(f"Error: Cannot read transactions from '{file_path}': {e}")
        return False


def validate_output_path(file_path: str, prompt_overwrite: bool = True) -> bool:
    """
    Validate output file path and handle overwrite confirmation.
    
    Args:
        file_path: Path to output file
        prompt_overwrite: Whether to prompt for overwrite confirmation
        
    Returns:
        True if path is valid and ready to use, False otherwise
    """
    # Ensure output directory exists
    output_dir = os.path.dirname(file_path)
    if output_dir and not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir)
            print(f"Created output directory: {output_dir}")
        except Exception as e:
            print(f"Error: Cannot create output directory '{output_dir}': {e}")
            return False
    
    # Check if file exists and prompt for overwrite
    if os.path.exists(file_path) and prompt_overwrite:
        if not confirm_action(f"File '{file_path}' already exists. Overwrite?"):
            print("Operation cancelled")
            return False
    
    return True


def validate_config_paths(config_manager, command: str = None) -> bool:
    """
    Validate that configured paths exist and are accessible.
    
    Args:
        config_manager: ConfigManager instance
        command: Specific command being run (for targeted validation)
        
    Returns:
        True if all required paths are valid, False otherwise
    """
    validation_errors = []
    
    # Check directories based on command
    if command in ['parse', 'pipeline', None]:
        statements_dir = config_manager.get_directory_path('statements')
        if not os.path.exists(statements_dir):
            validation_errors.append(f"Statements directory not found: {statements_dir}")
    
    if command in ['enrich', 'analyze', 'pipeline', None]:
        output_dir = config_manager.get_directory_path('output')
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir)
                print(f"Created output directory: {output_dir}")
            except Exception as e:
                validation_errors.append(f"Cannot create output directory: {output_dir} ({e})")
    
    # Check config directory
    config_dir = config_manager.get_directory_path('config')
    if not os.path.exists(config_dir):
        validation_errors.append(f"Config directory not found: {config_dir}")
    
    # Check required config files exist
    required_files = ['statement_patterns', 'plaid_categories']
    for file_key in required_files:
        file_path = config_manager.get_file_path(file_key)
        if not os.path.exists(file_path):
            validation_errors.append(f"Required config file missing: {file_path}")
    
    # Check optional config files and warn if missing
    optional_files = ['private_mappings', 'public_mappings']
    for file_key in optional_files:
        try:
            file_path = config_manager.get_file_path(file_key)
            if not os.path.exists(file_path):
                print(f"Info: Optional file missing: {file_path}")
        except:
            pass  # File key might not be configured
    
    if validation_errors:
        print("Configuration validation failed:")
        for error in validation_errors:
            print(f"  - {error}")
        print(f"\nPlease check your config files (public_settings.toml, private_settings.toml)")
        print(f"or create the missing directories/files.")
        print(f"Current config directory: {config_dir}")
        return False
    
    return True


def confirm_action(message: str) -> bool:
    """
    Ask user for confirmation.
    
    Args:
        message: Confirmation message
        
    Returns:
        True if user confirms, False otherwise
    """
    while True:
        response = input(f"{message} (y/n): ").lower().strip()
        if response in ['y', 'yes']:
            return True
        elif response in ['n', 'no']:
            return False
        else:
            print("Please enter 'y' or 'n'")


def parse_statements_interactive():
    """Interactive mode for parsing PDF statements."""
    print("\n--- PDF Statement Parsing ---")
    
    # Get defaults from config manager
    config = get_config_manager()
    
    # Show current configuration
    default_dir = config.get_directory_path('statements')
    default_output = config.get_default_file_path('parsed_transactions')

    print(f"Current configuration:")
    print(f"  Input directory: {default_dir}")
    print(f"  Output file: {default_output}")
    
    # Allow user to override defaults
    directory = input(f"\nEnter directory containing PDF files (Enter for default): ").strip()
    if not directory:
        directory = default_dir
    
    output_file = input(f"Enter output file name (Enter for default): ").strip()
    if not output_file:
        output_file = default_output
    
    # Show what will be used
    print(f"\nUsing configuration:")
    print(f"  Input directory: {directory}")
    print(f"  Output file: {output_file}")
    
    # Validate paths
    if not validate_directory(directory):
        return
    
    if not validate_output_path(output_file):
        return

    print(f"\nProcessing PDF files in '{directory}'...")

    # Process statements (debug mode disabled in interactive mode - use CLI flags for debug)
    try:
        transactions = process_pdf_statements(directory, debug=False)
        
        if transactions:
            from utils import save_transactions_to_json
            save_transactions_to_json(transactions, output_file)
            print(f"\nSuccessfully processed {len(transactions)} transactions")
            print(f"Results saved to '{output_file}'")
            
            # Ask if user wants to proceed to enrichment
            if confirm_action("\nWould you like to enrich these transactions with categories?"):
                enrich_transactions_interactive(output_file)
        else:
            print("\nNo transactions found")
            
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
    except Exception as e:
        print(f"\nError processing statements: {e}")


def enrich_transactions_interactive(input_file: Optional[str] = None):
    """Interactive mode for enriching transactions."""
    print("\n--- Transaction Enrichment ---")
    
    # Get defaults from config manager
    config = get_config_manager()
    
    # Show current configuration and allow overrides
    if not input_file:
        default_input = config.get_default_file_path('parsed_transactions')
        print(f"Current input file: {default_input}")

        input_file = input(f"Enter input file name (Enter for default): ").strip()
        if not input_file:
            input_file = default_input

    default_output = config.get_default_file_path('enriched_transactions')
    print(f"Current output file: {default_output}")
    
    output_file = input(f"Enter output file name (Enter for default): ").strip()
    if not output_file:
        output_file = default_output
    
    # Show what will be used
    print(f"\nUsing configuration:")
    print(f"  Input file: {input_file}")
    print(f"  Output file: {output_file}")
    
    # Validate paths
    if not validate_json_file(input_file):
        return
    
    if not validate_output_path(output_file):
        return

    print(f"\nEnriching transactions from '{input_file}'...")

    # Process enrichment (debug mode disabled in interactive mode - use CLI flags for debug)
    try:
        process_transaction_enrichment(input_file, output_file, debug=False)
        print(f"\nEnrichment complete! Results saved to '{output_file}'")
        
        # Ask if user wants to analyze results
        if confirm_action("\nWould you like to analyze categorization accuracy?"):
            analyze_interactive(output_file)
            
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
    except Exception as e:
        print(f"\nError enriching transactions: {e}")


def analyze_interactive(file_path: Optional[str] = None):
    """Interactive mode for analyzing categorization accuracy."""
    print("\n--- Categorization Analysis ---")
    
    # Get config manager
    config = get_config_manager()
    
    # Get file path
    if not file_path:
        default_file = config.get_default_file_path('enriched_transactions')
        file_path = input(f"Enter enriched transactions file [{default_file}]: ").strip()
        if not file_path:
            file_path = default_file
    
    # Validate file
    if not validate_json_file(file_path):
        return

    # Run analysis with basic output (use CLI flags --verbose or --debug for more detail)
    print(f"\nAnalyzing categorization accuracy...")
    analyze_categorization_accuracy(file_path, verbose=False, debug=False)


def manage_mappings_interactive():
    """Interactive mode for comprehensive mapping management.

    This combines:
    1. Processing new mappings from new_mappings.toml
    2. Validating existing mappings
    3. Interactive fixing of validation issues
    4. Interactive resolution of duplicates
    """
    print("\n--- Transaction Mapping Management ---")
    print("This will:")
    print("  1. Process any new mappings from new_mappings.toml")
    print("  2. Validate existing mappings and offer to fix issues")
    print("  3. Detect duplicates and offer to resolve them")
    print()

    # Get config manager
    config = get_config_manager()

    # Get config directory
    default_config = config.config_dir
    config_dir = input(f"Enter config directory [{default_config}]: ").strip()
    if not config_dir:
        config_dir = default_config

    print(f"\nProcessing mappings in '{config_dir}'...")

    try:
        # Initialize processor (debug mode disabled in interactive mode - use CLI flags for debug)
        processor = get_mapping_processor(config_dir=config_dir, debug_mode=False)

        # Run combined workflow
        success = processor.run_combined_processing()

        if success:
            print(f"\nMapping management complete!")
        else:
            print(f"\nMapping management completed with warnings")

    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
    except Exception as e:
        print(f"\nError managing mappings: {e}")
        if debug_mode:
            import traceback
            traceback.print_exc()


def run_full_pipeline_interactive():
    """Interactive mode for complete pipeline."""
    print("\n--- Complete Pipeline: Parse & Enrich ---")
    
    # Get config manager
    config = get_config_manager()
    
    # Show current configuration
    default_dir = config.get_directory_path('statements')
    parsed_file = config.get_default_file_path('parsed_transactions')
    enriched_file = config.get_default_file_path('enriched_transactions')
    
    print(f"Current configuration:")
    print(f"  Input directory: {default_dir}")
    print(f"  Parsed output: {parsed_file}")
    print(f"  Enriched output: {enriched_file}")
    
    # Allow user to override input directory
    directory = input(f"\nEnter directory containing PDF files (Enter for default): ").strip()
    if not directory:
        directory = default_dir
    
    # Validate directory
    if not validate_directory(directory):
        return
    
    # Validate output paths
    if not validate_output_path(parsed_file):
        return
    
    if not validate_output_path(enriched_file):
        return
    
    print(f"\nPipeline will create:")
    print(f"  1. {parsed_file} (raw transactions)")
    print(f"  2. {enriched_file} (enriched transactions)")
    
    if not confirm_action("\nProceed with full pipeline?"):
        print("Operation cancelled")
        return
    
    try:
        # Step 1: Parse statements (debug mode disabled in interactive mode - use CLI flags for debug)
        print(f"\nStep 1: Processing PDF files in '{directory}'...")
        transactions = process_pdf_statements(directory, debug=False)

        if not transactions:
            print("No transactions found in PDF files")
            return

        from utils import save_transactions_to_json
        save_transactions_to_json(transactions, parsed_file)
        print(f"Parsed {len(transactions)} transactions")

        # Step 2: Enrich transactions
        print(f"\nStep 2: Enriching transactions...")
        process_transaction_enrichment(parsed_file, enriched_file, debug=False)
        print(f"Enrichment complete!")
        
        # Step 3: Analysis
        print(f"\nStep 3: Analyzing results...")
        analyze_categorization_accuracy(enriched_file, verbose=False, debug=False)
        
        print(f"\nPipeline complete! Check '{enriched_file}' for final results.")
        
        # Ask if user wants detailed analysis
        if confirm_action("\nWould you like to run detailed analysis?"):
            analyze_interactive(enriched_file)
        
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
    except Exception as e:
        print(f"\nPipeline error: {e}")


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        description="Money Mapper - Financial Transaction Parser & Enricher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                           # Interactive mode
  %(prog)s parse --dir statements    # Parse PDFs in statements directory
  %(prog)s enrich --input output/txns.json  # Enrich existing transactions
  %(prog)s pipeline --dir statements # Complete parse + enrich pipeline
  %(prog)s validate                  # Validate TOML configuration files
  %(prog)s analyze --file output/enriched.json  # Analyze categorization accuracy
  %(prog)s analyze --file output/enriched.json --verbose  # Detailed analysis
  %(prog)s analyze --file output/enriched.json --debug    # Full diagnostic analysis
  %(prog)s check-mappings             # Validate existing mappings only
  %(prog)s add-mappings              # Manage transaction mappings
  %(prog)s add-mappings --config config --debug  # Debug mapping management
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Parse command
    parse_parser = subparsers.add_parser('parse', help='Parse PDF statements')
    parse_parser.add_argument('--dir', 
                             help='Directory containing PDF files (default: from config)')
    parse_parser.add_argument('--output',
                             help='Output JSON file (default: from config)')
    parse_parser.add_argument('--debug', action='store_true',
                             help='Enable debug output')
    
    # Enrich command
    enrich_parser = subparsers.add_parser('enrich', help='Enrich transactions with categories')
    enrich_parser.add_argument('--input',
                              help='Input JSON file (default: from config)')
    enrich_parser.add_argument('--output',
                              help='Output JSON file (default: from config)')
    enrich_parser.add_argument('--debug', action='store_true',
                              help='Enable debug output for detailed processing information')
    
    # Pipeline command
    pipeline_parser = subparsers.add_parser('pipeline', help='Run complete parse + enrich pipeline')
    pipeline_parser.add_argument('--dir',
                                help='Directory containing PDF files (default: from config)')
    pipeline_parser.add_argument('--debug', action='store_true',
                                help='Enable debug output')
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate TOML configuration files')
    
    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze categorization accuracy')
    analyze_parser.add_argument('--file',
                               help='Enriched transactions file (default: from config)')
    analyze_parser.add_argument('--verbose', action='store_true',
                               help='Enable verbose analysis with detailed examples and patterns')
    analyze_parser.add_argument('--debug', action='store_true',
                               help='Enable debug analysis with full diagnostic information')
    
    # Check mappings command
    check_mappings_parser = subparsers.add_parser('check-mappings', help='Validate existing transaction mappings')
    check_mappings_parser.add_argument('--config',
                                     help='Configuration directory (default: from config)')
    check_mappings_parser.add_argument('--debug', action='store_true',
                                     help='Enable debug output for detailed processing information')
    
    # Add mappings command
    add_mappings_parser = subparsers.add_parser('add-mappings', help='Manage transaction mappings')
    add_mappings_parser.add_argument('--config',
                                   help='Configuration directory (default: from config)')
    add_mappings_parser.add_argument('--debug', action='store_true',
                                   help='Enable debug output for detailed processing information')

    # Setup command
    setup_parser = subparsers.add_parser('setup', help='Run first-time setup wizard')
    setup_parser.add_argument('--config',
                             help='Configuration directory (default: config)')

    args = parser.parse_args()

    # Print banner first
    print_banner()

    # Check for first-run and launch setup wizard if needed
    try:
        from setup_wizard import check_first_run, run_setup_wizard

        if check_first_run():
            print()
            if not run_setup_wizard():
                print("Setup was not completed. Please run setup wizard again.")
                sys.exit(1)
            print()
            print("Setup complete! You can now use Money Mapper.")
            print()
            # If no command was specified, exit after setup
            if not args.command:
                sys.exit(0)
    except ImportError:
        print("Warning: Could not import setup wizard. Continuing without first-run setup.")
    except Exception as e:
        print(f"Warning: Setup wizard encountered an error: {e}")
        print("Continuing with existing configuration.")

    # Only initialize config manager when needed, not at startup
    if args.command:
        # For specific commands, get config manager
        try:
            config = get_config_manager()
        except Exception as e:
            print(f"Error initializing configuration: {e}")
            sys.exit(1)
        
        # Validate configuration for specific commands (but not for validate command)
        if args.command != 'validate':
            try:
                if not ensure_directories_exist():
                    print("Setup incomplete. Exiting.")
                    sys.exit(1)
                    
                if not validate_toml_files(verbose=False):
                    print("Configuration validation failed. Please fix TOML files before proceeding.")
                    print("\nTo check mapping files specifically, try:")
                    print("  python cli.py check-mappings")
                    sys.exit(1)
            except Exception as e:
                print(f"Configuration validation failed: {e}")
                print("\nTo check mapping files specifically, try:")
                print("  python cli.py check-mappings")
                sys.exit(1)
    else:
        # For interactive mode, try to initialize config but don't fail if it doesn't work
        try:
            config = get_config_manager()
            # Basic validation for interactive mode
            if not validate_toml_files(verbose=False):
                print("Warning: Some TOML configuration files have issues.")
                print("Some features may not work correctly.")
        except Exception as e:
            print(f"Warning: Configuration issues detected: {e}")
            print("Some features may not work correctly.")
            config = None
    
    if args.command == 'parse':
        # Use config defaults with flag overrides
        directory = args.dir if args.dir else config.get_directory_path('statements')
        output_file = args.output if args.output else config.get_default_file_path('parsed_transactions')
        
        print(f"Parse Configuration:")
        print(f"  Input directory: {directory}")
        print(f"  Output file: {output_file}")
        if args.dir:
            print(f"  (Directory overridden by --dir flag)")
        if args.output:
            print(f"  (Output overridden by --output flag)")
        
        # Validate paths
        if not validate_directory(directory):
            sys.exit(1)
        
        if not validate_output_path(output_file, prompt_overwrite=False):
            sys.exit(1)
        
        print(f"\nProcessing PDF files in '{directory}'...")
        transactions = process_pdf_statements(directory, args.debug)
        
        if transactions:
            from utils import save_transactions_to_json
            save_transactions_to_json(transactions, output_file)
            print(f"Successfully processed {len(transactions)} transactions")
            print(f"Results saved to '{output_file}'")
        else:
            print("No transactions found")
            sys.exit(1)
    
    elif args.command == 'enrich':
        # Use config defaults with flag overrides
        input_file = args.input if args.input else config.get_default_file_path('parsed_transactions')
        output_file = args.output if args.output else config.get_default_file_path('enriched_transactions')
        
        print(f"Enrich Configuration:")
        print(f"  Input file: {input_file}")
        print(f"  Output file: {output_file}")
        if args.input:
            print(f"  (Input overridden by --input flag)")
        if args.output:
            print(f"  (Output overridden by --output flag)")
        
        # Validate paths
        if not validate_json_file(input_file):
            sys.exit(1)
        
        if not validate_output_path(output_file, prompt_overwrite=False):
            sys.exit(1)
        
        print(f"\nEnriching transactions from '{input_file}'...")
        process_transaction_enrichment(input_file, output_file, args.debug)
        print(f"Results saved to '{output_file}'")
    
    elif args.command == 'pipeline':
        # Use config defaults with flag overrides
        directory = args.dir if args.dir else config.get_directory_path('statements')
        parsed_file = config.get_default_file_path('parsed_transactions')
        enriched_file = config.get_default_file_path('enriched_transactions')
        
        print(f"Pipeline Configuration:")
        print(f"  Input directory: {directory}")
        print(f"  Parsed output: {parsed_file}")
        print(f"  Enriched output: {enriched_file}")
        if args.dir:
            print(f"  (Directory overridden by --dir flag)")
        
        # Validate paths
        if not validate_directory(directory):
            sys.exit(1)
        
        if not validate_output_path(parsed_file, prompt_overwrite=False):
            sys.exit(1)
        
        if not validate_output_path(enriched_file, prompt_overwrite=False):
            sys.exit(1)
        
        print(f"\nRunning complete pipeline on '{directory}'...")
        
        # Parse
        transactions = process_pdf_statements(directory, args.debug)
        if not transactions:
            print("No transactions found")
            sys.exit(1)
        
        from utils import save_transactions_to_json
        save_transactions_to_json(transactions, parsed_file)
        print(f"Parsed {len(transactions)} transactions")
        
        # Enrich
        process_transaction_enrichment(parsed_file, enriched_file, args.debug)
        print(f"Pipeline complete! Results in '{enriched_file}'")
        
        # Basic analysis
        analyze_categorization_accuracy(enriched_file, verbose=False, debug=False)
    
    elif args.command == 'validate':
        # Special handling for validate command - don't pre-validate
        try:
            if not ensure_directories_exist():
                print("Directory setup incomplete.")
        except Exception:
            pass  # Continue with validation anyway
        
        # Validate TOML files with detailed output
        if validate_toml_files(verbose=True):
            print("All TOML configuration files are valid.")
            
            # Also validate configured paths
            try:
                config = get_config_manager()
                if validate_config_paths(config):
                    print("All configured paths are accessible.")
                else:
                    print("Some configured paths have issues (see above).")
            except Exception as e:
                print(f"Could not validate paths: {e}")
        else:
            print("One or more TOML files have syntax errors. Please fix them.")
            print("\nTo check mapping files specifically, try:")
            print("  python cli.py check-mappings")
            sys.exit(1)
    
    elif args.command == 'analyze':
        # Use config defaults with flag overrides
        file_path = args.file if args.file else config.get_default_file_path('enriched_transactions')
        
        print(f"Analyze Configuration:")
        print(f"  Input file: {file_path}")
        if args.file:
            print(f"  (File overridden by --file flag)")
        
        # Validate file
        if not validate_json_file(file_path):
            sys.exit(1)
        
        print(f"\nAnalyzing categorization accuracy...")
        analyze_categorization_accuracy(file_path, args.verbose, args.debug)
    
    elif args.command == 'check-mappings':
        # Use config defaults with flag overrides
        config_dir = args.config if args.config else config.config_dir
        
        print(f"Check-mappings Configuration:")
        print(f"  Config directory: {config_dir}")
        if args.config:
            print(f"  (Directory overridden by --config flag)")
        
        print(f"\nValidating existing mappings in '{config_dir}'...")
        
        try:
            processor = get_mapping_processor(config_dir=config_dir, debug_mode=args.debug)
            success = processor.run_check_only()
            
            if success:
                print(f"Mapping validation complete!")
            else:
                print(f"Mapping validation failed")
                sys.exit(1)
                
        except Exception as e:
            print(f"Error validating mappings: {e}")
            if args.debug:
                import traceback
                traceback.print_exc()
            sys.exit(1)
    
    elif args.command == 'add-mappings':
        # Use config defaults with flag overrides
        config_dir = args.config if args.config else config.config_dir

        print(f"Add-mappings Configuration:")
        print(f"  Config directory: {config_dir}")
        if args.config:
            print(f"  (Directory overridden by --config flag)")

        print(f"\nAnalyzing mappings in '{config_dir}'...")

        try:
            processor = get_mapping_processor(config_dir=config_dir, debug_mode=args.debug)
            success = processor.run_full_processing()

            if success:
                print(f"Mapping analysis complete!")
            else:
                print(f"Mapping analysis failed")
                sys.exit(1)

        except Exception as e:
            print(f"Error analyzing mappings: {e}")
            if args.debug:
                import traceback
                traceback.print_exc()
            sys.exit(1)

    elif args.command == 'setup':
        # Run setup wizard manually
        from setup_wizard import run_setup_wizard

        config_dir = args.config if args.config else "config"
        print(f"\nRunning setup wizard...")
        print(f"  Config directory: {config_dir}")
        print()

        if run_setup_wizard(config_dir):
            print("\nSetup wizard completed successfully!")
        else:
            print("\nSetup wizard was not completed.")
            sys.exit(1)

    else:
        # Interactive mode
        print("\nWhat would you like to do?")
        print()
        print("1. Extract transactions from PDFs")
        print("2. Categorize transactions")
        print("3. Extract & categorize (full process)")
        print("4. Review categorization results")
        print("5. Check configuration files")
        print("6. Manage merchant mappings")
        print("7. Exit")

        while True:
            choice = input("\nEnter your choice (1-7): ").strip()
            
            if choice == '1':
                parse_statements_interactive()
                break
            elif choice == '2':
                enrich_transactions_interactive()
                break
            elif choice == '3':
                run_full_pipeline_interactive()
                break
            elif choice == '4':
                analyze_interactive()
                break
            elif choice == '5':
                if validate_toml_files(verbose=True):
                    print("\n✓ All configuration files are valid.")
                else:
                    print("\n✗ Configuration errors found. Please fix them.")
                break
            elif choice == '6':
                manage_mappings_interactive()
                break
            elif choice == '7':
                print("\nGoodbye!")
                break
            else:
                print("Invalid choice. Please enter 1-7.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nGoodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)