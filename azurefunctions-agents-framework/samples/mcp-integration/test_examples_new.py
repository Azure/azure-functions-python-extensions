#!/usr/bin/env python3
"""
Test script for MCP integration examples.

This script validates that all MCP integration examples are properly structured,
have valid Python syntax, correct imports, and necessary configuration files.
"""

import os
import sys
import ast
import json
from pathlib import Path
from typing import List, Dict, Any

def check_python_syntax(file_path: Path) -> List[str]:
    """Check if a Python file has valid syntax."""
    errors = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()
        ast.parse(source)
        print(f"✓ {file_path.name}: Syntax OK")
    except SyntaxError as e:
        error_msg = f"✗ {file_path.name}: Syntax Error - {e}"
        errors.append(error_msg)
        print(error_msg)
    except Exception as e:
        error_msg = f"✗ {file_path.name}: Error reading file - {e}"
        errors.append(error_msg)
        print(error_msg)
    
    return errors

def check_imports(file_path: Path) -> List[str]:
    """Check if all imports in a Python file are resolvable."""
    errors = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()
        
        tree = ast.parse(source)
        imports = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
        
        # Check critical imports
        critical_imports = ['azure.functions', 'openai', 'azurefunctions.agents']
        missing_critical = []
        
        for critical in critical_imports:
            found = any(imp.startswith(critical) for imp in imports)
            if not found and 'azure.functions' in critical:
                # Check if it's imported differently
                found = any('azure' in imp and 'functions' in imp for imp in imports)
            if not found:
                missing_critical.append(critical)
        
        if missing_critical:
            error_msg = f"✗ {file_path.name}: Missing critical imports: {missing_critical}"
            errors.append(error_msg)
            print(error_msg)
        else:
            print(f"✓ {file_path.name}: Critical imports OK")
            
    except Exception as e:
        error_msg = f"✗ {file_path.name}: Error checking imports - {e}"
        errors.append(error_msg)
        print(error_msg)
    
    return errors

def check_json_file(file_path: Path) -> List[str]:
    """Check if a JSON file is valid."""
    errors = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            json.load(f)
        print(f"✓ {file_path.name}: Valid JSON")
    except json.JSONDecodeError as e:
        error_msg = f"✗ {file_path.name}: Invalid JSON - {e}"
        errors.append(error_msg)
        print(error_msg)
    except Exception as e:
        error_msg = f"✗ {file_path.name}: Error reading JSON - {e}"
        errors.append(error_msg)
        print(error_msg)
    
    return errors

def check_example_structure(example_dir: Path) -> List[str]:
    """Check if an example directory has the required structure."""
    errors = []
    required_files = ['README.md', 'requirements.txt', 'host.json', 'local.settings.json.template']
    
    print(f"\nChecking example structure: {example_dir.name}")
    print("-" * 50)
    
    for required_file in required_files:
        file_path = example_dir / required_file
        if file_path.exists():
            print(f"✓ {required_file}: Found")
        else:
            error_msg = f"✗ {required_file}: Missing in {example_dir.name}"
            errors.append(error_msg)
            print(error_msg)
    
    # Check for Python files
    python_files = list(example_dir.glob("*.py"))
    if python_files:
        print(f"✓ Python files: {[f.name for f in python_files]}")
    else:
        error_msg = f"✗ No Python files found in {example_dir.name}"
        errors.append(error_msg)
        print(error_msg)
    
    return errors

def validate_example(example_dir: Path) -> Dict[str, Any]:
    """Validate a single example directory."""
    result = {
        'name': example_dir.name,
        'errors': [],
        'warnings': [],
        'files_checked': 0
    }
    
    # Check directory structure
    structure_errors = check_example_structure(example_dir)
    result['errors'].extend(structure_errors)
    
    # Check Python files
    python_files = list(example_dir.glob("*.py"))
    for py_file in python_files:
        result['files_checked'] += 1
        
        # Check syntax
        syntax_errors = check_python_syntax(py_file)
        result['errors'].extend(syntax_errors)
        
        # Check imports
        import_errors = check_imports(py_file)
        result['errors'].extend(import_errors)
    
    # Check JSON files
    json_files = [example_dir / "host.json"]
    for json_file in json_files:
        if json_file.exists():
            result['files_checked'] += 1
            json_errors = check_json_file(json_file)
            result['errors'].extend(json_errors)
    
    return result

def main():
    """Main validation function."""
    print("MCP Integration Examples Validation")
    print("=" * 50)
    
    # Get the directory containing this script
    script_dir = Path(__file__).parent
    
    # Find all example directories
    example_dirs = [
        script_dir / "weather-agent",
        script_dir / "git-agent", 
        script_dir / "sse-integration"
    ]
    
    total_errors = 0
    total_files = 0
    results = []
    
    for example_dir in example_dirs:
        if example_dir.is_dir():
            result = validate_example(example_dir)
            results.append(result)
            total_errors += len(result['errors'])
            total_files += result['files_checked']
    
    # Print summary
    print("\n" + "=" * 50)
    print("VALIDATION SUMMARY")
    print("=" * 50)
    
    for result in results:
        status = "✓ PASS" if len(result['errors']) == 0 else "✗ FAIL"
        print(f"{result['name']}: {status} ({result['files_checked']} files checked)")
        if result['errors']:
            for error in result['errors'][:3]:  # Show first 3 errors
                print(f"  - {error}")
            if len(result['errors']) > 3:
                print(f"  - ... and {len(result['errors']) - 3} more errors")
    
    print(f"\nTotal files checked: {total_files}")
    print(f"Total errors found: {total_errors}")
    
    if total_errors == 0:
        print("\n🎉 All examples passed validation!")
        return 0
    else:
        print(f"\n❌ {total_errors} errors found. Please fix before deployment.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
