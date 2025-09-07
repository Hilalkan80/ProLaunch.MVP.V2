#!/usr/bin/env python3
"""
Basic syntax and import validation for M0 backend components
"""

import sys
import importlib
import traceback
from pathlib import Path

def test_import_modules():
    """Test importing core modules"""
    modules_to_test = [
        "src.models.base",
        "src.models.m0_feasibility", 
        "src.models.milestone",
        "src.models.user",
        "src.schemas",
    ]
    
    results = []
    
    for module in modules_to_test:
        try:
            importlib.import_module(module)
            results.append({"module": module, "status": "OK", "error": None})
            print(f"[OK] {module} - Import successful")
        except ImportError as e:
            results.append({"module": module, "status": "FAIL", "error": str(e)})
            print(f"[FAIL] {module} - Import failed: {e}")
        except Exception as e:
            results.append({"module": module, "status": "ERROR", "error": str(e)})
            print(f"[ERROR] {module} - Unexpected error: {e}")
    
    return results

def test_file_syntax():
    """Test Python syntax for key files"""
    src_path = Path("src")
    python_files = list(src_path.rglob("*.py"))
    
    syntax_results = []
    
    for py_file in python_files:
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Compile to check syntax
            compile(content, str(py_file), 'exec')
            syntax_results.append({"file": str(py_file), "status": "OK", "error": None})
            print(f"[OK] {py_file} - Syntax valid")
            
        except SyntaxError as e:
            syntax_results.append({"file": str(py_file), "status": "SYNTAX_ERROR", "error": str(e)})
            print(f"[SYNTAX_ERROR] {py_file} - {e}")
        except Exception as e:
            syntax_results.append({"file": str(py_file), "status": "ERROR", "error": str(e)})
            print(f"[ERROR] {py_file} - {e}")
    
    return syntax_results

def main():
    """Main validation test"""
    print("=" * 60)
    print("M0 BACKEND SYNTAX & IMPORT VALIDATION")
    print("=" * 60)
    
    print("\n1. SYNTAX VALIDATION:")
    print("-" * 30)
    syntax_results = test_file_syntax()
    
    print("\n2. IMPORT VALIDATION:")
    print("-" * 30)
    import_results = test_import_modules()
    
    # Summary
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    
    syntax_ok = sum(1 for r in syntax_results if r["status"] == "OK")
    syntax_total = len(syntax_results)
    
    import_ok = sum(1 for r in import_results if r["status"] == "OK")
    import_total = len(import_results)
    
    print(f"Syntax Tests: {syntax_ok}/{syntax_total} passed")
    print(f"Import Tests: {import_ok}/{import_total} passed")
    
    overall_status = "PASS" if syntax_ok == syntax_total and import_ok == import_total else "FAIL"
    print(f"Overall Status: {overall_status}")
    
    if overall_status == "FAIL":
        print("\nFAILED TESTS:")
        for r in syntax_results:
            if r["status"] != "OK":
                print(f"  [SYNTAX] {r['file']}: {r['error']}")
        
        for r in import_results:
            if r["status"] != "OK":
                print(f"  [IMPORT] {r['module']}: {r['error']}")

if __name__ == "__main__":
    main()