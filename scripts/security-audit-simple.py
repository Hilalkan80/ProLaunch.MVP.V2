#!/usr/bin/env python3
"""
Simple Security Audit Script for ProLaunch MVP Chat System
"""

import os
import json
from pathlib import Path

project_root = Path(__file__).parent.parent

def audit_security():
    """Simple security audit"""
    results = {
        "overall_score": 0,
        "categories": {},
        "issues": [],
        "recommendations": []
    }
    
    print("=" * 60)
    print("SECURITY AUDIT REPORT")
    print("=" * 60)
    
    # Check if security files exist
    security_files = [
        "backend/src/core/security/rate_limiter.py",
        "backend/src/core/security/content_security.py", 
        "backend/src/core/security/websocket_security.py",
        "backend/src/core/security/sentry_security.py",
        "backend/src/core/security/middleware.py",
        "backend/src/core/security/config.py",
        "backend/src/api/v1/file_upload.py",
        "backend/tests/security/test_chat_security.py"
    ]
    
    files_exist = 0
    print("\nSECURITY FILES CHECK:")
    for file_path in security_files:
        full_path = project_root / file_path
        if full_path.exists():
            files_exist += 1
            size = full_path.stat().st_size
            print(f"  PASS: {file_path} ({size} bytes)")
        else:
            print(f"  FAIL: {file_path} - NOT FOUND")
            results["issues"].append(f"Missing file: {file_path}")
    
    implementation_score = (files_exist / len(security_files)) * 100
    results["categories"]["implementation"] = {
        "score": implementation_score,
        "files_found": files_exist,
        "total_files": len(security_files)
    }
    
    # Check dependencies
    print("\nDEPENDENCY CHECK:")
    requirements_file = project_root / "backend" / "requirements.txt"
    security_deps = ["sentry-sdk", "bleach", "python-magic", "PyJWT", "cryptography"]
    
    if requirements_file.exists():
        requirements = requirements_file.read_text()
        deps_found = 0
        
        for dep in security_deps:
            if dep in requirements:
                deps_found += 1
                print(f"  PASS: {dep} found in requirements.txt")
            else:
                print(f"  FAIL: {dep} missing from requirements.txt")
                results["issues"].append(f"Missing dependency: {dep}")
        
        dependency_score = (deps_found / len(security_deps)) * 100
        results["categories"]["dependencies"] = {
            "score": dependency_score,
            "deps_found": deps_found,
            "total_deps": len(security_deps)
        }
    else:
        print("  FAIL: requirements.txt not found")
        results["issues"].append("Missing requirements.txt")
        dependency_score = 0
    
    # Check configuration
    print("\nCONFIGURATION CHECK:")
    config_vars = ["SECRET_KEY", "SENTRY_DSN", "REDIS_URL", "DATABASE_URL"]
    config_found = 0
    
    for var in config_vars:
        if os.getenv(var):
            config_found += 1
            # Don't print actual values for security
            print(f"  PASS: {var} is set")
        else:
            print(f"  FAIL: {var} not set")
            results["issues"].append(f"Missing environment variable: {var}")
    
    config_score = (config_found / len(config_vars)) * 100
    results["categories"]["configuration"] = {
        "score": config_score,
        "vars_found": config_found,
        "total_vars": len(config_vars)
    }
    
    # Check documentation
    print("\nDOCUMENTATION CHECK:")
    doc_files = ["SECURITY.md", "README.md"]
    docs_found = 0
    
    for doc in doc_files:
        doc_path = project_root / doc
        if doc_path.exists():
            docs_found += 1
            print(f"  PASS: {doc} exists")
        else:
            print(f"  FAIL: {doc} missing")
            results["issues"].append(f"Missing documentation: {doc}")
    
    doc_score = (docs_found / len(doc_files)) * 100
    results["categories"]["documentation"] = {
        "score": doc_score,
        "docs_found": docs_found,
        "total_docs": len(doc_files)
    }
    
    # Calculate overall score
    all_scores = [implementation_score, dependency_score, config_score, doc_score]
    results["overall_score"] = sum(all_scores) / len(all_scores)
    
    print("\n" + "=" * 60)
    print("AUDIT SUMMARY")
    print("=" * 60)
    print(f"Overall Security Score: {results['overall_score']:.1f}%")
    print()
    
    for category, data in results["categories"].items():
        print(f"{category.upper()}: {data['score']:.1f}%")
    
    if results["issues"]:
        print(f"\nISSUES FOUND ({len(results['issues'])}):")
        for issue in results["issues"]:
            print(f"  - {issue}")
    
    # Recommendations
    if results["overall_score"] >= 90:
        results["recommendations"].append("Excellent security implementation!")
    elif results["overall_score"] >= 75:
        results["recommendations"].append("Good security posture with minor improvements needed.")
    elif results["overall_score"] >= 50:
        results["recommendations"].append("Moderate security - address missing components.")
    else:
        results["recommendations"].append("Poor security posture - immediate attention required.")
    
    if results["recommendations"]:
        print("\nRECOMMENDATIONS:")
        for rec in results["recommendations"]:
            print(f"  - {rec}")
    
    # Save detailed report
    report_file = project_root / "security_audit_report.json"
    with open(report_file, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\nDetailed report saved to: {report_file}")
    print("=" * 60)
    
    return 0 if results["overall_score"] >= 50 else 1

if __name__ == "__main__":
    import sys
    exit_code = audit_security()
    sys.exit(exit_code)