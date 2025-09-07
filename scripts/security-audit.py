#!/usr/bin/env python3
"""
Security Audit Script for ProLaunch MVP Chat System

This script performs a comprehensive security audit of the chat system,
checking all implemented security measures and generating a report.
"""

import asyncio
import sys
import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any
import subprocess
import re

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "backend"))

IMPORTS_AVAILABLE = True
try:
    from src.core.security.config import SecurityManager, SecurityConfig
    from src.core.security.rate_limiter import RedisRateLimiter, RateLimitType
    from src.core.security.content_security import ContentValidator, FileUploadSecurityValidator
    from src.core.security.websocket_security import WebSocketAuthenticator
except ImportError as e:
    print(f"Warning: Could not import security modules: {e}")
    IMPORTS_AVAILABLE = False

class SecurityAuditor:
    """Comprehensive security auditor for the chat system"""
    
    def __init__(self):
        self.results = {
            "timestamp": datetime.utcnow().isoformat(),
            "audit_version": "1.0",
            "categories": {},
            "overall_score": 0,
            "recommendations": [],
            "critical_issues": [],
            "warnings": []
        }
        
    async def run_audit(self) -> Dict[str, Any]:
        """Run complete security audit"""
        print("SECURITY AUDIT: Starting ProLaunch MVP Security Audit...")
        print("=" * 60)
        
        # Run all audit categories
        await self._audit_configuration()
        await self._audit_code_security()
        await self._audit_dependencies()
        await self._audit_file_permissions()
        await self._audit_environment()
        await self._audit_implementation_completeness()
        
        # Calculate overall score
        self._calculate_overall_score()
        
        # Generate report
        return self._generate_report()
    
    async def _audit_configuration(self):
        """Audit security configuration"""
        print("CONFIG: Auditing Security Configuration...")
        
        category = "configuration"
        self.results["categories"][category] = {
            "score": 0,
            "max_score": 100,
            "checks": {},
            "issues": []
        }
        
        checks = self.results["categories"][category]["checks"]
        issues = self.results["categories"][category]["issues"]
        
        # Check environment variables
        required_env_vars = [
            "SECRET_KEY", "SENTRY_DSN", "REDIS_URL", "DATABASE_URL"
        ]
        
        env_score = 0
        for var in required_env_vars:
            if os.getenv(var):
                env_score += 15
                checks[f"{var}_present"] = {"status": "PASS", "score": 15}
            else:
                checks[f"{var}_present"] = {"status": "FAIL", "score": 0}
                issues.append(f"Missing required environment variable: {var}")
                if var == "SECRET_KEY":
                    self.results["critical_issues"].append(f"Missing {var}")
        
        # Check security configuration values
        security_config_checks = {
            "ENABLE_RATE_LIMITING": ("true", 10),
            "ENABLE_CONTENT_VALIDATION": ("true", 10),
            "ENABLE_SECURITY_MONITORING": ("true", 10)
        }
        
        config_score = 0
        for var, (expected, points) in security_config_checks.items():
            actual = os.getenv(var, "false").lower()
            if actual == expected:
                config_score += points
                checks[f"{var}_configured"] = {"status": "PASS", "score": points}
            else:
                checks[f"{var}_configured"] = {"status": "FAIL", "score": 0}
                issues.append(f"{var} should be '{expected}', got '{actual}'")
        
        # Check SECRET_KEY strength
        secret_key = os.getenv("SECRET_KEY", "")
        if len(secret_key) < 32:
            issues.append("SECRET_KEY is too short (minimum 32 characters)")
            self.results["critical_issues"].append("Weak SECRET_KEY")
        elif len(secret_key) >= 64:
            config_score += 10
            checks["secret_key_strength"] = {"status": "PASS", "score": 10}
        else:
            config_score += 5
            checks["secret_key_strength"] = {"status": "WARN", "score": 5}
            self.results["warnings"].append("SECRET_KEY could be longer for better security")
        
        self.results["categories"][category]["score"] = env_score + config_score
    
    async def _audit_code_security(self):
        """Audit code-level security implementations"""
        print("CODE: Auditing Code Security...")
        
        category = "code_security"
        self.results["categories"][category] = {
            "score": 0,
            "max_score": 100,
            "checks": {},
            "issues": []
        }
        
        if not IMPORTS_AVAILABLE:
            self.results["categories"][category]["issues"].append("Cannot import security modules for testing")
            return
        
        checks = self.results["categories"][category]["checks"]
        issues = self.results["categories"][category]["issues"]
        score = 0
        
        # Test content validator
        try:
            validator = ContentValidator()
            
            # Test XSS protection
            test_result = validator.validate_and_sanitize_message(
                "<script>alert('test')</script>", "html"
            )
            if "<script>" not in test_result["content"]:
                score += 25
                checks["xss_protection"] = {"status": "PASS", "score": 25}
            else:
                checks["xss_protection"] = {"status": "FAIL", "score": 0}
                issues.append("XSS protection not working properly")
        except Exception as e:
            checks["xss_protection"] = {"status": "ERROR", "score": 0}
            issues.append(f"Error testing XSS protection: {e}")
        
        # Test file upload validator
        try:
            file_validator = FileUploadSecurityValidator()
            
            dangerous_extensions = [".exe", ".bat", ".scr", ".vbs"]
            if any(ext in file_validator.DANGEROUS_EXTENSIONS for ext in dangerous_extensions):
                score += 25
                checks["dangerous_file_blocking"] = {"status": "PASS", "score": 25}
            else:
                checks["dangerous_file_blocking"] = {"status": "FAIL", "score": 0}
                issues.append("Dangerous file extensions not properly blocked")
        except Exception as e:
            checks["dangerous_file_blocking"] = {"status": "ERROR", "score": 0}
            issues.append(f"Error testing file upload security: {e}")
        
        # Test WebSocket authenticator
        try:
            ws_auth = WebSocketAuthenticator("test-secret-key")
            score += 25
            checks["websocket_auth"] = {"status": "PASS", "score": 25}
        except Exception as e:
            checks["websocket_auth"] = {"status": "ERROR", "score": 0}
            issues.append(f"Error initializing WebSocket authenticator: {e}")
        
        # Test rate limiter configuration
        try:
            from src.core.security.rate_limiter import RateLimitConfig
            if hasattr(RateLimitConfig, 'LIMITS') and RateLimitConfig.LIMITS:
                score += 25
                checks["rate_limit_config"] = {"status": "PASS", "score": 25}
            else:
                checks["rate_limit_config"] = {"status": "FAIL", "score": 0}
                issues.append("Rate limiting not properly configured")
        except Exception as e:
            checks["rate_limit_config"] = {"status": "ERROR", "score": 0}
            issues.append(f"Error checking rate limit configuration: {e}")
        
        self.results["categories"][category]["score"] = score
    
    async def _audit_dependencies(self):
        """Audit dependency security"""
        print("📦 Auditing Dependencies...")
        
        category = "dependencies"
        self.results["categories"][category] = {
            "score": 0,
            "max_score": 100,
            "checks": {},
            "issues": []
        }
        
        checks = self.results["categories"][category]["checks"]
        issues = self.results["categories"][category]["issues"]
        
        # Check for security-related dependencies in requirements.txt
        requirements_file = project_root / "backend" / "requirements.txt"
        security_deps = {
            "sentry-sdk": 20,
            "bleach": 20,
            "python-magic": 15,
            "PyJWT": 20,
            "cryptography": 25
        }
        
        score = 0
        if requirements_file.exists():
            requirements = requirements_file.read_text()
            
            for dep, points in security_deps.items():
                if dep in requirements:
                    score += points
                    checks[f"{dep}_present"] = {"status": "PASS", "score": points}
                else:
                    checks[f"{dep}_present"] = {"status": "FAIL", "score": 0}
                    issues.append(f"Missing security dependency: {dep}")
        else:
            issues.append("requirements.txt not found")
            self.results["critical_issues"].append("Missing requirements.txt file")
        
        self.results["categories"][category]["score"] = score
    
    async def _audit_file_permissions(self):
        """Audit file and directory permissions"""
        print("🔐 Auditing File Permissions...")
        
        category = "file_permissions"
        self.results["categories"][category] = {
            "score": 0,
            "max_score": 100,
            "checks": {},
            "issues": []
        }
        
        checks = self.results["categories"][category]["checks"]
        issues = self.results["categories"][category]["issues"]
        score = 0
        
        # Check sensitive file permissions
        sensitive_files = [
            ".env",
            ".env.production", 
            ".env.staging"
        ]
        
        for file_path in sensitive_files:
            full_path = project_root / file_path
            if full_path.exists():
                try:
                    import stat
                    permissions = oct(os.stat(full_path).st_mode)[-3:]
                    
                    # Check if file is world-readable (should not be for sensitive files)
                    if permissions[2] in ['0', '4']:  # No world read access
                        score += 15
                        checks[f"{file_path}_permissions"] = {"status": "PASS", "score": 15}
                    else:
                        checks[f"{file_path}_permissions"] = {"status": "FAIL", "score": 0}
                        issues.append(f"File {file_path} has overly permissive permissions: {permissions}")
                except Exception as e:
                    issues.append(f"Error checking permissions for {file_path}: {e}")
        
        # Check if .env files are in .gitignore
        gitignore_file = project_root / ".gitignore"
        if gitignore_file.exists():
            gitignore_content = gitignore_file.read_text()
            if ".env" in gitignore_content:
                score += 25
                checks["env_files_ignored"] = {"status": "PASS", "score": 25}
            else:
                checks["env_files_ignored"] = {"status": "FAIL", "score": 0}
                issues.append(".env files not properly excluded from git")
                self.results["critical_issues"].append("Environment files not in .gitignore")
        
        self.results["categories"][category]["score"] = score
    
    async def _audit_environment(self):
        """Audit environment-specific security"""
        print("🌍 Auditing Environment Security...")
        
        category = "environment"
        self.results["categories"][category] = {
            "score": 0,
            "max_score": 100,
            "checks": {},
            "issues": []
        }
        
        checks = self.results["categories"][category]["checks"]
        issues = self.results["categories"][category]["issues"]
        score = 0
        
        # Check environment type
        env_type = os.getenv("ENVIRONMENT", "development").lower()
        
        if env_type == "production":
            # Production-specific checks
            prod_requirements = {
                "DEBUG": "false",
                "SENTRY_DSN": "required",
                "ENABLE_RATE_LIMITING": "true",
                "ENABLE_SECURITY_MONITORING": "true"
            }
            
            for var, expected in prod_requirements.items():
                actual = os.getenv(var, "").lower()
                
                if expected == "required" and actual:
                    score += 20
                    checks[f"prod_{var}"] = {"status": "PASS", "score": 20}
                elif expected != "required" and actual == expected:
                    score += 20
                    checks[f"prod_{var}"] = {"status": "PASS", "score": 20}
                else:
                    checks[f"prod_{var}"] = {"status": "FAIL", "score": 0}
                    issues.append(f"Production environment: {var} should be '{expected}', got '{actual}'")
                    if var in ["DEBUG", "SENTRY_DSN"]:
                        self.results["critical_issues"].append(f"Production config issue: {var}")
        
        else:
            # Development environment is more lenient
            score += 50
            checks["dev_environment"] = {"status": "PASS", "score": 50}
            
            # But still check for basic security
            if os.getenv("DEBUG", "false").lower() == "true":
                self.results["warnings"].append("DEBUG mode enabled - ensure this is intentional")
        
        self.results["categories"][category]["score"] = score
    
    async def _audit_implementation_completeness(self):
        """Audit completeness of security implementation"""
        print("✅ Auditing Implementation Completeness...")
        
        category = "implementation"
        self.results["categories"][category] = {
            "score": 0,
            "max_score": 100,
            "checks": {},
            "issues": []
        }
        
        checks = self.results["categories"][category]["checks"]
        issues = self.results["categories"][category]["issues"]
        score = 0
        
        # Check if all security modules exist
        required_modules = [
            "src/core/security/rate_limiter.py",
            "src/core/security/content_security.py",
            "src/core/security/websocket_security.py",
            "src/core/security/sentry_security.py",
            "src/core/security/middleware.py",
            "src/core/security/config.py"
        ]
        
        module_score = 0
        for module in required_modules:
            module_path = project_root / "backend" / module
            if module_path.exists():
                module_score += 10
                checks[f"{Path(module).stem}_exists"] = {"status": "PASS", "score": 10}
                
                # Check if module has meaningful content
                content = module_path.read_text()
                if len(content) > 1000:  # Arbitrary threshold for "meaningful" content
                    module_score += 5
                    checks[f"{Path(module).stem}_content"] = {"status": "PASS", "score": 5}
                else:
                    checks[f"{Path(module).stem}_content"] = {"status": "WARN", "score": 2}
                    self.results["warnings"].append(f"Module {module} may be incomplete")
            else:
                checks[f"{Path(module).stem}_exists"] = {"status": "FAIL", "score": 0}
                issues.append(f"Missing required security module: {module}")
                self.results["critical_issues"].append(f"Missing module: {module}")
        
        # Check if security tests exist
        security_test_dir = project_root / "backend" / "tests" / "security"
        if security_test_dir.exists() and any(security_test_dir.glob("*.py")):
            score += 10
            checks["security_tests_exist"] = {"status": "PASS", "score": 10}
        else:
            checks["security_tests_exist"] = {"status": "FAIL", "score": 0}
            issues.append("No security tests found")
        
        self.results["categories"][category]["score"] = module_score + score
    
    def _calculate_overall_score(self):
        """Calculate overall security score"""
        total_score = 0
        max_total_score = 0
        
        for category_data in self.results["categories"].values():
            total_score += category_data["score"]
            max_total_score += category_data["max_score"]
        
        if max_total_score > 0:
            self.results["overall_score"] = round((total_score / max_total_score) * 100, 1)
        else:
            self.results["overall_score"] = 0
        
        # Generate recommendations based on score
        if self.results["overall_score"] >= 90:
            self.results["recommendations"].append("Excellent security posture! Continue regular audits.")
        elif self.results["overall_score"] >= 75:
            self.results["recommendations"].append("Good security implementation. Address warnings to improve.")
        elif self.results["overall_score"] >= 60:
            self.results["recommendations"].append("Moderate security. Address critical issues immediately.")
        else:
            self.results["recommendations"].append("Poor security posture. Immediate action required.")
            self.results["critical_issues"].append("Overall security score below acceptable threshold")
    
    def _generate_report(self):
        """Generate human-readable security report"""
        print("\n" + "=" * 60)
        print("🔒 SECURITY AUDIT REPORT")
        print("=" * 60)
        
        # Overall score
        score = self.results["overall_score"]
        if score >= 90:
            score_emoji = "🟢"
        elif score >= 75:
            score_emoji = "🟡"
        elif score >= 60:
            score_emoji = "🟠"
        else:
            score_emoji = "🔴"
        
        print(f"\nOverall Security Score: {score_emoji} {score}%")
        print(f"Audit Timestamp: {self.results['timestamp']}")
        
        # Critical issues
        if self.results["critical_issues"]:
            print("\n🔴 CRITICAL ISSUES:")
            for issue in self.results["critical_issues"]:
                print(f"  • {issue}")
        
        # Warnings
        if self.results["warnings"]:
            print("\n🟡 WARNINGS:")
            for warning in self.results["warnings"]:
                print(f"  • {warning}")
        
        # Category breakdown
        print("\n📊 CATEGORY BREAKDOWN:")
        for category, data in self.results["categories"].items():
            category_score = (data["score"] / data["max_score"]) * 100 if data["max_score"] > 0 else 0
            category_emoji = "🟢" if category_score >= 80 else "🟡" if category_score >= 60 else "🔴"
            print(f"  {category_emoji} {category.replace('_', ' ').title()}: {category_score:.1f}%")
            
            if data["issues"]:
                for issue in data["issues"][:3]:  # Show max 3 issues per category
                    print(f"    - {issue}")
        
        # Recommendations
        if self.results["recommendations"]:
            print("\n💡 RECOMMENDATIONS:")
            for rec in self.results["recommendations"]:
                print(f"  • {rec}")
        
        # Save detailed report to file
        report_file = project_root / "security_audit_report.json"
        with open(report_file, "w") as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\n📄 Detailed report saved to: {report_file}")
        print("=" * 60)
        
        # Return exit code based on critical issues
        if self.results["critical_issues"]:
            print("\n❌ Audit completed with CRITICAL ISSUES. Exit code: 1")
            return 1
        elif self.results["warnings"]:
            print("\n⚠️  Audit completed with warnings. Exit code: 0")
            return 0
        else:
            print("\n✅ Audit completed successfully. Exit code: 0")
            return 0

async def main():
    """Main audit execution"""
    auditor = SecurityAuditor()
    
    try:
        exit_code = await auditor.run_audit()
        return exit_code
    except Exception as e:
        print(f"\nERROR: Security audit failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)