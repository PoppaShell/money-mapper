#!/usr/bin/env python3
"""
User Acceptance Testing (UAT) Script for Money Mapper

Run this script locally before pushing any changes to ensure:
1. CLI entry points work correctly
2. All major commands execute without errors
3. Output is valid and well-formed
4. Error handling is user-friendly
5. No Unicode encoding issues (especially on Windows)
"""

import json
import os
import subprocess
import sys
from pathlib import Path


def run_test(test_name: str, command: list) -> tuple[bool, str]:
    """
    Run a single UAT test command.
    
    Returns: (success, output)
    """
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        success = result.returncode == 0
        output = result.stdout if success else result.stderr
        
        return success, output
    except subprocess.TimeoutExpired:
        return False, "Test timed out after 30 seconds"
    except Exception as e:
        return False, f"Test failed with error: {e}"


def test_cli_help() -> bool:
    """Test: CLI --help displays usage correctly"""
    cmd = [sys.executable, "-c", 
           "import sys; sys.path.insert(0, 'src'); from money_mapper.cli import main; "
           "sys.argv = ['money-mapper', '--help']; main()"]
    
    success, output = run_test("CLI Help", cmd)
    
    if success:
        # Verify output contains expected subcommands
        required = ["parse", "enrich", "pipeline", "validate", "analyze", "check-deps"]
        if all(cmd in output for cmd in required):
            print("  PASS: CLI help shows all commands")
            return True
        else:
            print("  FAIL: CLI help missing expected commands")
            print(f"  Output: {output[:200]}")
            return False
    else:
        print("  FAIL: CLI help command failed")
        print(f"  Error: {output[:200]}")
        return False


def test_check_deps() -> bool:
    """Test: check-deps command validates dependencies"""
    cmd = [sys.executable, "-c",
           "import sys; sys.path.insert(0, 'src'); from money_mapper.cli import main; "
           "sys.argv = ['money-mapper', 'check-deps']; main()"]
    
    success, output = run_test("Check Dependencies", cmd)
    
    if success and "[OK]" in output:
        print("  PASS: Dependencies validated successfully")
        return True
    else:
        print("  FAIL: check-deps command failed")
        print(f"  Output: {output[:200]}")
        return False


def test_validate() -> bool:
    """Test: validate command checks TOML files"""
    cmd = [sys.executable, "-c",
           "import sys; sys.path.insert(0, 'src'); from money_mapper.cli import main; "
           "sys.argv = ['money-mapper', 'validate']; main()"]
    
    success, output = run_test("Validate Config", cmd)
    
    if success and ("valid" in output.lower() or "accessible" in output.lower()):
        print("  PASS: Configuration validation works")
        return True
    else:
        print("  FAIL: validate command failed")
        print(f"  Output: {output[:200]}")
        return False


def test_enrich() -> bool:
    """Test: enrich command processes JSON transactions"""
    test_output = "tests/fixtures/uat_enriched.json"
    
    cmd = [sys.executable, "-c",
           f"import sys; sys.path.insert(0, 'src'); from money_mapper.cli import main; "
           f"sys.argv = ['money-mapper', 'enrich', '--input', 'tests/fixtures/sample_transactions.json', "
           f"'--output', '{test_output}']; main()"]
    
    success, output = run_test("Enrich Transactions", cmd)
    
    if success:
        # Verify output file was created
        if os.path.exists(test_output):
            try:
                with open(test_output) as f:
                    data = json.load(f)
                
                if len(data) > 0 and all('category' in t for t in data):
                    print(f"  PASS: Enriched {len(data)} transactions with categories")
                    # Cleanup
                    os.remove(test_output)
                    return True
                else:
                    print("  FAIL: Output JSON missing expected fields")
                    return False
            except json.JSONDecodeError:
                print("  FAIL: Output file is not valid JSON")
                return False
        else:
            print("  FAIL: Output file was not created")
            return False
    else:
        print("  FAIL: enrich command failed")
        print(f"  Error: {output[:200]}")
        return False


def test_no_relative_imports() -> bool:
    """Test: Verify no relative imports remain in source code"""
    src_dir = Path("src/money_mapper")
    relative_import_pattern = "from (utils|config_manager|statement_parser|transaction_enricher|mapping_processor|setup_wizard|interactive_mapper|cli) import"
    
    import re
    found_issues = []
    
    for py_file in src_dir.glob("*.py"):
        with open(py_file, encoding='utf-8', errors='ignore') as f:
            for i, line in enumerate(f, 1):
                if re.search(relative_import_pattern, line):
                    found_issues.append(f"  {py_file.name}:{i}: {line.strip()}")
    
    if found_issues:
        print("  FAIL: Found relative imports:")
        for issue in found_issues:
            print(issue)
        return False
    else:
        print("  PASS: No relative imports found")
        return True


def main():
    """Run all UAT tests"""
    print("\n" + "=" * 60)
    print("  Money Mapper - User Acceptance Testing (UAT)")
    print("=" * 60 + "\n")
    
    tests = [
        ("CLI Help", test_cli_help),
        ("Check Dependencies", test_check_deps),
        ("Validate Configuration", test_validate),
        ("Enrich Transactions", test_enrich),
        ("No Relative Imports", test_no_relative_imports),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"Testing: {test_name}")
        try:
            passed = test_func()
            results.append((test_name, passed))
        except Exception as e:
            print(f"  ERROR: {e}")
            results.append((test_name, False))
        print()
    
    # Summary
    print("=" * 60)
    print("  UAT Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"  {status}: {test_name}")
    
    print()
    print(f"Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\nAll UAT tests PASSED - Ready for push!")
        print("=" * 60)
        return 0
    else:
        print("\nSome UAT tests FAILED - Fix issues before pushing!")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
