# User Acceptance Testing (UAT) Plan - Phase 0

## Test Environment
- OS: Windows 10
- Python: 3.13
- Branch: test/57-test-infrastructure-v2 (integrated Phase 0)

## UAT Test Cases

### 1. CLI Entry Point
```
Test: Run money-mapper --help
Expected: Display help message with all available commands
Status: [ ] Pass [ ] Fail
Notes:
```

### 2. Interactive Mode
```
Test: Run money-mapper (no args)
Expected: Display main interactive menu with options
Status: [ ] Pass [ ] Fail
Notes:
```

### 3. Parse Functionality
```
Test: Run money-mapper parse --dir tests/fixtures/sample_statements
Expected: Parse CSV files and create output JSON
Status: [ ] Pass [ ] Fail
Notes:
```

### 4. Config Loading
```
Test: Check if config/public_settings.toml loads correctly
Expected: No errors, paths resolve correctly
Status: [ ] Pass [ ] Fail
Notes:
```

### 5. Error Handling
```
Test: Run parse with non-existent directory
Expected: Show helpful error message (not stack trace)
Status: [ ] Pass [ ] Fail
Notes:
```

### 6. Test Data Loading
```
Test: Load sample transactions from tests/fixtures/sample_transactions.json
Expected: Successfully parse 4 test transactions
Status: [ ] Pass [ ] Fail
Notes:
```

### 7. Mapping Validation
```
Test: Run money-mapper validate
Expected: Validate TOML config files successfully
Status: [ ] Pass [ ] Fail
Notes:
```

### 8. Character Encoding (Windows CP1252)
```
Test: Verify all output displays without Unicode errors
Expected: No encoding errors, ASCII-only output
Status: [ ] Pass [ ] Fail
Notes:
```

## Summary
- Total Tests: 8
- Passed: __
- Failed: __
- Blocked: __

## Sign-Off
Tested by: ______  
Date: ______  
Ready for merge: [ ] Yes [ ] No
