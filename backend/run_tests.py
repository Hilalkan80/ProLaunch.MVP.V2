#!/usr/bin/env python3
"""
Test runner script to run tests with proper environment setup and mocking.
"""

import os
import sys
from unittest.mock import MagicMock, patch
import pytest

# Set environment variables for testing
os.environ.update({
    'TESTING': 'true',
    'ANTHROPIC_API_KEY': 'test_anthropic_key_for_testing',
    'OPENAI_API_KEY': 'test_openai_key_for_testing',
    'JWT_SECRET_KEY': 'test_secret_key_for_testing_only',
    'JWT_ALGORITHM': 'HS256',
    'JWT_ACCESS_TOKEN_EXPIRE_MINUTES': '30',
    'JWT_REFRESH_TOKEN_EXPIRE_DAYS': '7',
    'POSTGRES_HOST': 'localhost',
    'POSTGRES_PORT': '5432',
    'POSTGRES_USER': 'test',
    'POSTGRES_PASSWORD': 'test',
    'POSTGRES_DB': 'test_prolaunch',
    'REDIS_HOST': 'localhost',
    'REDIS_PORT': '6379',
    'REDIS_DB': '1'
})

def mock_llama_modules():
    """Mock llama-index modules that may not be available."""
    # Mock llama-index modules
    sys.modules['llama_index'] = MagicMock()
    sys.modules['llama_index.core'] = MagicMock()
    sys.modules['llama_index.llms'] = MagicMock()
    sys.modules['llama_index.llms.anthropic'] = MagicMock()
    sys.modules['llama_index.embeddings'] = MagicMock()
    sys.modules['llama_index.embeddings.openai'] = MagicMock()
    sys.modules['llama_index.vector_stores'] = MagicMock()
    sys.modules['llama_index.vector_stores.postgres'] = MagicMock()

def run_unit_tests():
    """Run unit tests with proper mocking."""
    mock_llama_modules()
    
    # Run pytest with specified arguments
    pytest_args = [
        'tests/unit/',
        '-v',
        '--tb=short',
        '--disable-warnings'
    ]
    
    return pytest.main(pytest_args)

def run_integration_tests():
    """Run integration tests."""
    mock_llama_modules()
    
    pytest_args = [
        'tests/integration/',
        '-v',
        '--tb=short',
        '--disable-warnings'
    ]
    
    return pytest.main(pytest_args)

def run_security_tests():
    """Run security tests."""
    mock_llama_modules()
    
    pytest_args = [
        'tests/security/',
        '-v',
        '--tb=short',
        '--disable-warnings',
        '-m', 'security'
    ]
    
    return pytest.main(pytest_args)

def run_all_tests():
    """Run all tests with coverage."""
    mock_llama_modules()
    
    pytest_args = [
        'tests/',
        '-v',
        '--tb=short',
        '--disable-warnings',
        '--cov=src',
        '--cov-report=term-missing',
        '--cov-report=html:htmlcov'
    ]
    
    return pytest.main(pytest_args)

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Run ProLaunch backend tests')
    parser.add_argument('--type', choices=['unit', 'integration', 'security', 'all'], 
                       default='all', help='Type of tests to run')
    
    args = parser.parse_args()
    
    if args.type == 'unit':
        exit_code = run_unit_tests()
    elif args.type == 'integration':
        exit_code = run_integration_tests()
    elif args.type == 'security':
        exit_code = run_security_tests()
    else:
        exit_code = run_all_tests()
    
    sys.exit(exit_code)