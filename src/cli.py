def parse_statements_interactive():
    """Interactive mode for parsing PDF statements."""
    print("\n--- PDF Statement Parsing ---")
    
    # Get directory
    default_dir = "statements"
    directory = input(f"Enter directory containing PDF files [{default_dir}]: ").strip()
    if not directory:
        directory = default_dir
    
    # Validate directory
    if not validate_directory(directory):
        return
    
    # Get output file
    default_output = "output/financial_transactions.json"
    output_file = input(f"Enter output file name [{default_output}]: ").strip()
    if not output_file:
        output_file = default_output
    
    # Check if output file exists
    if os.path.exists(output_file):
        if not confirm_action(f"File '{output_file}' already exists. Overwrite?"):
            print("Operation cancelled")
            return
    
    # Debug mode
    debug_mode = confirm_action("Enable debug mode for detailed output?")
    
    print(f"\nProcessing PDF files in '{directory}'...")
    
    # Process statements
    try:
        transactions = process_pdf_statements(directory, debug_mode)
        
        if transactions:
            from utils import save_transactions_to_json
            save_transactions_to_json(transactions, output_file)
            print(f"\n✓ Successfully processed {len(transactions)} transactions")
            print(f"✓ Results saved to '{output_file}'")
            
            # Ask if user wants to proceed to enrichment
            if confirm_action("\nWould you like to enrich these transactions with categories?"):
                enrich_transactions_interactive(output_file)
        else:
            print("\n✗ No transactions found")
            
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
    except Exception as e:
        print(f"\n✗ Error processing statements: {e}")


def enrich_transactions_interactive(input_file: Optional[str] = None):
    """Interactive mode for enriching transactions."""
    print("\n--- Transaction Enrichment ---")
    
    # Get input file
    if not input_file:
        default_input = "output/financial_transactions.json"
        input_file = input(f"Enter input file name [{default_input}]: ").strip()
        if not input_file:
            input_file = default_input
    
    # Validate input file
    if not validate_json_file(input_file):
        return
    
    # Get output file
    default_output = "output/enriched_transactions.json"
    output_file = input(f"Enter output file name [{default_output}]: ").strip()
    if not output_file:
        output_file = default_output
    
    # Check if output file exists
    if os.path.exists(output_file):
        if not confirm_action(f"File '{output_file}' already exists. Overwrite?"):
            print("Operation cancelled")
            return
    
    print(f"\nEnriching transactions from '{input_file}'...")
    
    # Process enrichment
    try:
        process_transaction_enrichment(input_file, output_file)
        print(f"\n✓ Enrichment complete! Results saved to '{output_file}'")
        
        # Ask if user wants to analyze results
        if confirm_action("\nWould you like to analyze categorization accuracy?"):
            analyze_categorization_accuracy(output_file)
            
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
    except Exception as e:
        print(f"\n✗ Error enriching transactions: {e}")


def run_full_pipeline_interactive():
    """Interactive mode for complete pipeline."""
    print("\n--- Complete Pipeline: Parse & Enrich ---")
    
    # Get directory
    default_dir = "statements"
    directory = input(f"Enter directory containing PDF files [{default_dir}]: ").strip()
    if not directory:
        directory = default_dir
    
    # Validate directory
    if not validate_directory(directory):
        return
    
    # Get output files
    parsed_file = "output/financial_transactions.json" 
    enriched_file = "output/enriched_transactions.json"
    
    print(f"Pipeline will create:")
    print(f"  1. {parsed_file} (raw transactions)")
    print(f"  2. {enriched_file} (enriched transactions)")
    
    if not confirm_action("\nProceed with full pipeline?"):
        print("Operation cancelled")
        return
    
    # Debug mode
    debug_mode = confirm_action("Enable debug mode for detailed output?")
    
    try:
        # Step 1: Parse statements
        print(f"\nStep 1: Processing PDF files in '{directory}'...")
        transactions = process_pdf_statements(directory, debug_mode)
        
        if not transactions:
            print("✗ No transactions found in PDF files")
            return
        
        from utils import save_transactions_to_json
        save_transactions_to_json(transactions, parsed_file)
        print(f"✓ Parsed {len(transactions)} transactions")
        
        # Step 2: Enrich transactions
        print(f"\nStep 2: Enriching transactions...")
        process_transaction_enrichment(parsed_file, enriched_file)
        print(f"✓ Enrichment complete!")
        
        # Step 3: Analysis
        print(f"\nStep 3: Analyzing results...")
        analyze_categorization_accuracy(enriched_file)
        
        print(f"\n🎉 Pipeline complete! Check '{enriched_file}' for final results.")
        
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
    except Exception as e:
        print(f"\n✗ Pipeline error: {e}")


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        description="Financial Transaction Parser & Enricher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                           # Interactive mode
  %(prog)s parse --dir statements    # Parse PDFs in statements directory
  %(prog)s enrich --input output/txns.json  # Enrich existing transactions
  %(prog)s pipeline --dir statements # Complete parse + enrich pipeline
  %(prog)s analyze --file output/enriched.json  # Analyze categorization accuracy
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Parse command
    parse_parser = subparsers.add_parser('parse', help='Parse PDF statements')
    parse_parser.add_argument('--dir', default='statements', 
                             help='Directory containing PDF files (default: statements)')
    parse_parser.add_argument('--output', default='output/financial_transactions.json',
                             help='Output JSON file (default: output/financial_transactions.json)')
    parse_parser.add_argument('--debug', action='store_true',
                             help='Enable debug output')
    
    # Enrich command
    enrich_parser = subparsers.add_parser('enrich', help='Enrich transactions with categories')
    enrich_parser.add_argument('--input', default='output/financial_transactions.json',
                              help='Input JSON file (default: output/financial_transactions.json)')
    enrich_parser.add_argument('--output', default='output/enriched_transactions.json',
                              help='Output JSON file (default: output/enriched_transactions.json)')
    
    # Pipeline command
    pipeline_parser = subparsers.add_parser('pipeline', help='Run complete parse + enrich pipeline')
    pipeline_parser.add_argument('--dir', default='statements',
                                help='Directory containing PDF files (default: statements)')
    pipeline_parser.add_argument('--debug', action='store_true',
                                help='Enable debug output')
    
    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze categorization accuracy')
    analyze_parser.add_argument('--file', default='output/enriched_transactions.json',
                               help='Enriched transactions file (default: output/enriched_transactions.json)')
    
    args = parser.parse_args()
    
    # Ensure directories exist
    ensure_directories_exist()
    
    # Print banner
    print_banner()
    
    if args.command == 'parse':
        # Non-interactive parse
        if not validate_directory(args.dir):
            sys.exit(1)
        
        print(f"Processing PDF files in '{args.dir}'...")
        transactions = process_pdf_statements(args.dir, args.debug)
        
        if transactions:
            from utils import save_transactions_to_json
            save_transactions_to_json(transactions, args.output)
            print(f"✓ Successfully processed {len(transactions)} transactions")
            print(f"✓ Results saved to '{args.output}'")
        else:
            print("✗ No transactions found")
            sys.exit(1)
    
    elif args.command == 'enrich':
        # Non-interactive enrich
        if not validate_json_file(args.input):
            sys.exit(1)
        
        print(f"Enriching transactions from '{args.input}'...")
        process_transaction_enrichment(args.input, args.output)
        print(f"✓ Results saved to '{args.output}'")
    
    elif args.command == 'pipeline':
        # Non-interactive pipeline
        if not validate_directory(args.dir):
            sys.exit(1)
        
        parsed_file = "output/financial_transactions.json"
        enriched_file = "output/enriched_transactions.json"
        
        print(f"Running complete pipeline on '{args.dir}'...")
        
        # Parse
        transactions = process_pdf_statements(args.dir, args.debug)
        if not transactions:
            print("✗ No transactions found")
            sys.exit(1)
        
        from utils import save_transactions_to_json
        save_transactions_to_json(transactions, parsed_file)
        print(f"✓ Parsed {len(transactions)} transactions")
        
        # Enrich
        process_transaction_enrichment(parsed_file, enriched_file)
        print(f"✓ Pipeline complete! Results in '{enriched_file}'")
    
    elif args.command == 'analyze':
        # Analyze results
        if not validate_json_file(args.file):
            sys.exit(1)
        
        analyze_categorization_accuracy(args.file)
    
    else:
        # Interactive mode
        print("\nChoose an option:")
        print("1. Parse PDF statements only")
        print("2. Enrich existing transactions only") 
        print("3. Complete pipeline (parse + enrich)")
        print("4. Analyze categorization accuracy")
        print("5. Exit")
        
        while True:
            choice = input("\nEnter your choice (1-5): ").strip()
            
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
                file_path = input("Enter enriched transactions file [output/enriched_transactions.json]: ").strip()
                if not file_path:
                    file_path = "output/enriched_transactions.json"
                
                if validate_json_file(file_path):
                    analyze_categorization_accuracy(file_path)
                break
            elif choice == '5':
                print("Goodbye!")
                break
            else:
                print("Invalid choice. Please enter 1-5.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nGoodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)#!/usr/bin/env python3
"""
Financial Parser CLI - Simple command-line interface.

Provides an easy-to-use command line interface for processing bank statements
and enriching transactions with categories and merchant names.
"""

import argparse
import os
import sys
from typing import Optional

from statement_parser import process_pdf_statements
from transaction_enricher import process_transaction_enrichment, analyze_categorization_accuracy
from utils import load_transactions_from_json, ensure_directories_exist


def print_banner():
    """Print application banner."""
    print("=" * 60)
    print("  Financial Transaction Parser & Enricher")
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
        return False
    
    if not os.path.isdir(directory):
        print(f"Error: '{directory}' is not a directory")
        return False
    
    # Check for PDF files
    pdf_files = [f for f in os.listdir(directory) if f.lower().endswith('.pdf')]
    if not pdf_files:
        print(f"Warning: No PDF files found in '{directory}'")
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
    
    # Get directory
    default_dir = "."
    directory = input(f"Enter directory containing PDF files [{default_dir}]: ").strip()
    if not directory:
        directory = default_dir
    
    # Validate directory
    if not validate_directory(directory):
        return
    
    # Get output file
    default_output = "financial_transactions.json"
    output_file = input(f"Enter output file name [{default_output}]: ").strip()
    if not output_file:
        output_file = default_output
    
    # Check if output file exists
    if os.path.exists(output_file):
        if not confirm_action(f"File '{output_file}' already exists. Overwrite?"):
            print("Operation cancelled")
            return
    
    # Debug mode
    debug_mode = confirm_action("Enable debug mode for detailed output?")
    
    print(f"\nProcessing PDF files in '{directory}'...")
    
    # Process statements
    try:
        transactions = process_pdf_statements(directory, debug_mode)
        
        if transactions:
            from utils import save_transactions_to_json
            save_transactions_to_json(transactions, output_file)
            print(f"\n✓ Successfully processed {len(transactions)} transactions")
            print(f"✓ Results saved to '{output_file}'")
            
            # Ask if user wants to proceed to enrichment
            if confirm_action("\nWould you like to enrich these transactions with categories?"):
                enrich_transactions_interactive(output_file)
        else:
            print("\n✗ No transactions found")
            
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
    except Exception as e:
        print(f"\n✗ Error processing statements: {e}")


def enrich_transactions_interactive(input_file: Optional[str] = None):
    """Interactive mode for enriching transactions."""
    print("\n--- Transaction Enrichment ---")
    
    # Get input file
    if not input_file:
        default_input = "financial_transactions.json"
        input_file = input(f"Enter input file name [{default_input}]: ").strip()
        if not input_file:
            input_file = default_input
    
    # Validate input file
    if not validate_json_file(input_file):
        return
    
    # Get output file
    default_output = "enriched_transactions.json"
    output_file = input(f"Enter output file name [{default_output}]: ").strip()
    if not output_file:
        output_file = default_output
    
    # Check if output file exists
    if os.path.exists(output_file):
        if not confirm_action(f"File '{output_file}' already exists. Overwrite?"):
            print("Operation cancelled")
            return
    
    print(f"\nEnriching transactions from '{input_file}'...")
    
    # Process enrichment
    try:
        process_transaction_enrichment(input_file, output_file)
        print(f"\n✓ Enrichment complete! Results saved to '{output_file}'")
        
        # Ask if user wants to analyze results
        if confirm_action("\nWould you like to analyze categorization accuracy?"):
            analyze_categorization_accuracy(output_file)
            
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
    except Exception as e:
        print(f"\n✗ Error enriching transactions: {e}")


def run_full_pipeline_interactive():
    """Interactive mode for complete pipeline."""
    print("\n--- Complete Pipeline: Parse & Enrich ---")
    
    # Get directory
    default_dir = "."
    directory = input(f"Enter directory containing PDF files [{default_dir}]: ").strip()
    if not directory:
        directory = default_dir
    
    # Validate directory
    if not validate_directory(directory):
        return
    
    # Get output files
    parsed_file = "financial_transactions.json" 
    enriched_file = "enriched_transactions.json"
    
    print(f"Pipeline will create:")
    print(f"  1. {parsed_file} (raw transactions)")
    print(f"  2. {enriched_file} (enriched transactions)")
    
    if not confirm_action("\nProceed with full pipeline?"):
        print("Operation cancelled")
        return
    
    # Debug mode
    debug_mode = confirm_action("Enable debug mode for detailed output?")
    
    try:
        # Step 1: Parse statements
        print(f"\nStep 1: Processing PDF files in '{directory}'...")
        transactions = process_pdf_statements(directory, debug_mode)
        
        if not transactions:
            print("✗ No transactions found in PDF files")
            return
        
        from utils import save_transactions_to_json
        save_transactions_to_json(transactions, parsed_file)
        print(f"✓ Parsed {len(transactions)} transactions")
        
        # Step 2: Enrich transactions
        print(f"\nStep 2: Enriching transactions...")
        process_transaction_enrichment(parsed_file, enriched_file)
        print(f"✓ Enrichment complete!")
        
        # Step 3: Analysis
        print(f"\nStep 3: Analyzing results...")
        analyze_categorization_accuracy(enriched_file)
        
        print(f"\n🎉 Pipeline complete! Check '{enriched_file}' for final results.")
        
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
    except Exception as e:
        print(f"\n✗ Pipeline error: {e}")


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        description="Financial Transaction Parser & Enricher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                           # Interactive mode
  %(prog)s parse --dir ./statements  # Parse PDFs in directory
  %(prog)s enrich --input txns.json  # Enrich existing transactions
  %(prog)s pipeline --dir ./docs     # Complete parse + enrich pipeline
  %(prog)s analyze --file enriched.json  # Analyze categorization accuracy
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Parse command
    parse_parser = subparsers.add_parser('parse', help='Parse PDF statements')
    parse_parser.add_argument('--dir', default='.', 
                             help='Directory containing PDF files (default: current directory)')
    parse_parser.add_argument('--output', default='financial_transactions.json',
                             help='Output JSON file (default: financial_transactions.json)')
    parse_parser.add_argument('--debug', action='store_true',
                             help='Enable debug output')
    
    # Enrich command
    enrich_parser = subparsers.add_parser('enrich', help='Enrich transactions with categories')
    enrich_parser.add_argument('--input', default='financial_transactions.json',
                              help='Input JSON file (default: financial_transactions.json)')
    enrich_parser.add_argument('--output', default='enriched_transactions.json',
                              help='Output JSON file (default: enriched_transactions.json)')
    
    # Pipeline command
    pipeline_parser = subparsers.add_parser('pipeline', help='Run complete parse + enrich pipeline')
    pipeline_parser.add_argument('--dir', default='.',
                                help='Directory containing PDF files (default: current directory)')
    pipeline_parser.add_argument('--debug', action='store_true',
                                help='Enable debug output')
    
    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze categorization accuracy')
    analyze_parser.add_argument('--file', default='enriched_transactions.json',
                               help='Enriched transactions file (default: enriched_transactions.json)')
    
    args = parser.parse_args()
    
    # Print banner
    print_banner()
    
    if args.command == 'parse':
        # Non-interactive parse
        if not validate_directory(args.dir):
            sys.exit(1)
        
        print(f"Processing PDF files in '{args.dir}'...")
        transactions = process_pdf_statements(args.dir, args.debug)
        
        if transactions:
            from utils import save_transactions_to_json
            save_transactions_to_json(transactions, args.output)
            print(f"✓ Successfully processed {len(transactions)} transactions")
            print(f"✓ Results saved to '{args.output}'")
        else:
            print("✗ No transactions found")
            sys.exit(1)
    
    elif args.command == 'enrich':
        # Non-interactive enrich
        if not validate_json_file(args.input):
            sys.exit(1)
        
        print(f"Enriching transactions from '{args.input}'...")
        process_transaction_enrichment(args.input, args.output)
        print(f"✓ Results saved to '{args.output}'")
    
    elif args.command == 'pipeline':
        # Non-interactive pipeline
        if not validate_directory(args.dir):
            sys.exit(1)
        
        parsed_file = "financial_transactions.json"
        enriched_file = "enriched_transactions.json"
        
        print(f"Running complete pipeline on '{args.dir}'...")
        
        # Parse
        transactions = process_pdf_statements(args.dir, args.debug)
        if not transactions:
            print("✗ No transactions found")
            sys.exit(1)
        
        from utils import save_transactions_to_json
        save_transactions_to_json(transactions, parsed_file)
        print(f"✓ Parsed {len(transactions)} transactions")
        
        # Enrich
        process_transaction_enrichment(parsed_file, enriched_file)
        print(f"✓ Pipeline complete! Results in '{enriched_file}'")
    
    elif args.command == 'analyze':
        # Analyze results
        if not validate_json_file(args.file):
            sys.exit(1)
        
        analyze_categorization_accuracy(args.file)
    
    else:
        # Interactive mode
        print("\nChoose an option:")
        print("1. Parse PDF statements only")
        print("2. Enrich existing transactions only") 
        print("3. Complete pipeline (parse + enrich)")
        print("4. Analyze categorization accuracy")
        print("5. Exit")
        
        while True:
            choice = input("\nEnter your choice (1-5): ").strip()
            
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
                file_path = input("Enter enriched transactions file [enriched_transactions.json]: ").strip()
                if not file_path:
                    file_path = "enriched_transactions.json"
                
                if validate_json_file(file_path):
                    analyze_categorization_accuracy(file_path)
                break
            elif choice == '5':
                print("Goodbye!")
                break
            else:
                print("Invalid choice. Please enter 1-5.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nGoodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)