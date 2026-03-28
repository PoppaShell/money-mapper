"""Privacy audit pre-commit hook integration.

Provides pre-commit hook functionality to check staged mapping files
for PII leaks before allowing commits.
"""

import os
import subprocess
import sys
from typing import Any

from money_mapper.privacy_audit import audit_merchant_name


def get_override_env() -> bool:
    """
    Check if privacy audit should be skipped via environment variable.

    Returns:
        True if PRIVACY_AUDIT_SKIP is set to 1/true, False otherwise
    """
    skip_value = os.environ.get("PRIVACY_AUDIT_SKIP", "").lower()
    return skip_value in ("1", "true", "yes")


def check_staged_files() -> list[str]:
    """
    Get list of staged files in git.

    Returns:
        List of file paths that are staged for commit
    """
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.stdout:
            return [f.strip() for f in result.stdout.split("\n") if f.strip()]
        return []
    except Exception:
        return []


def filter_mapping_files(files: list[str]) -> list[str]:
    """
    Filter to keep only mapping files.

    Args:
        files: List of file paths

    Returns:
        List of files that appear to be mapping files
    """
    mapping_patterns = [
        "public_mappings",
        "private_mappings",
        "mappings.toml",
        "mappings.json",
        "enriched_transactions.json",
    ]

    result = []
    for file_path in files:
        file_lower = file_path.lower()
        # Check if file matches mapping patterns
        if any(pattern in file_lower for pattern in mapping_patterns):
            result.append(file_path)
        # Also check for .toml/.json in config or data directories
        elif ("config" in file_lower or "data" in file_lower) and (
            file_lower.endswith(".toml") or file_lower.endswith(".json")
        ):
            result.append(file_path)

    return result


def run_precommit_check(threshold: str = "high") -> int:
    """
    Run privacy audit check on staged mapping files.

    Args:
        threshold: Risk threshold to enforce
                 - "low": block all risks
                 - "medium": block medium/high risks
                 - "high": block only high risks (default)

    Returns:
        0 if check passes, 1 if check fails
    """
    # Check if override is set
    if get_override_env():
        print("Privacy audit check skipped (PRIVACY_AUDIT_SKIP=1)")
        return 0

    # Get staged files
    staged_files = check_staged_files()
    if not staged_files:
        return 0

    # Filter to mapping files only
    mapping_files = filter_mapping_files(staged_files)
    if not mapping_files:
        return 0

    # Audit each mapping file
    threshold_levels = {"low": 0, "medium": 30, "high": 70}
    block_threshold = threshold_levels.get(threshold, 70)

    violations = []

    for file_path in mapping_files:
        try:
            with open(file_path, "r") as f:
                content = f.read()

            # Parse file based on extension
            if file_path.endswith(".json"):
                import json

                data = json.load(open(file_path))
                # For JSON transaction files, check merchant names
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict):
                            merchant_name = item.get("merchant_name", item.get("name", ""))
                            if merchant_name:
                                audit = audit_merchant_name(merchant_name)
                                if audit["score"] >= block_threshold:
                                    violations.append({
                                        "file": file_path,
                                        "merchant": merchant_name,
                                        "score": audit["score"],
                                        "findings": audit["findings"],
                                    })

            elif file_path.endswith(".toml"):
                # For TOML mapping files, sample merchant names
                import re

                merchant_pattern = r'"([^"]+)"\s*=\s*\{'
                merchants = re.findall(merchant_pattern, content)
                for merchant_name in merchants:
                    audit = audit_merchant_name(merchant_name)
                    if audit["score"] >= block_threshold:
                        violations.append({
                            "file": file_path,
                            "merchant": merchant_name,
                            "score": audit["score"],
                            "findings": audit["findings"],
                        })

        except Exception as e:
            print(f"Error auditing {file_path}: {e}")
            continue

    # Report violations
    if violations:
        print(
            f"Privacy audit found {len(violations)} violation(s) with score >= {block_threshold}",
            file=sys.stderr,
        )
        for violation in violations:
            print(f"  - {violation['file']}: {violation['merchant']} (score: {violation['score']})",
                  file=sys.stderr)
            for finding in violation["findings"]:
                print(f"    * {finding.get('reason', 'Unknown risk')}", file=sys.stderr)
        return 1

    return 0


def main(argv: list[str] | None = None) -> int:
    """
    Main entry point for pre-commit hook.

    Args:
        argv: Command line arguments (for testing)

    Returns:
        Exit code (0 = pass, 1 = fail)
    """
    if argv is None:
        argv = sys.argv[1:]

    # Parse arguments
    threshold = "high"
    for arg in argv:
        if arg.startswith("--threshold="):
            threshold = arg.split("=")[1]
        elif arg == "--threshold" and len(argv) > argv.index(arg) + 1:
            threshold = argv[argv.index(arg) + 1]

    return run_precommit_check(threshold=threshold)


if __name__ == "__main__":
    sys.exit(main())
