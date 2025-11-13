"""
Test runner for database integration tests

This script runs all database integration tests and provides a summary report.

Usage:
    python test/database_integration/run_tests.py
    python test/database_integration/run_tests.py --verbose
    python test/database_integration/run_tests.py --specific connection
"""

import sys
import os
import subprocess
import argparse

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))


def print_header(text):
    """Print a formatted header"""
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80 + "\n")


def print_section(text):
    """Print a formatted section"""
    print("\n" + "-" * 80)
    print(f"  {text}")
    print("-" * 80 + "\n")


def check_prerequisites():
    """Check if all prerequisites are met"""
    print_section("Checking Prerequisites")
    
    issues = []
    
    # Check if pytest is installed
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print(f"✅ pytest installed: {result.stdout.strip()}")
        else:
            issues.append("pytest is not installed")
    except Exception as e:
        issues.append(f"pytest check failed: {e}")
    
    # Check if Docker is running
    try:
        result = subprocess.run(
            ["docker", "ps"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print("✅ Docker is running")
        else:
            issues.append("Docker is not running")
    except FileNotFoundError:
        issues.append("Docker is not installed or not in PATH")
    except Exception as e:
        issues.append(f"Docker check failed: {e}")
    
    # Check if PostgreSQL container is running
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=wci-emailagent-postgres", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if "wci-emailagent-postgres" in result.stdout:
            print("✅ PostgreSQL container is running")
        else:
            issues.append("PostgreSQL container is not running. Run: docker-compose up -d postgres")
    except Exception as e:
        issues.append(f"Container check failed: {e}")
    
    # Check if .env file exists
    env_file = os.path.join(os.path.dirname(__file__), '../../.env')
    if os.path.exists(env_file):
        print("✅ .env file exists")
    else:
        issues.append(".env file not found")
    
    return issues


def run_tests(test_file=None, verbose=False):
    """Run the tests"""
    test_dir = os.path.dirname(__file__)
    
    # Build pytest command
    cmd = [sys.executable, "-m", "pytest"]
    
    if test_file:
        # Run specific test file
        test_path = os.path.join(test_dir, f"test_{test_file}.py")
        if not os.path.exists(test_path):
            print(f"❌ Test file not found: {test_path}")
            return False
        cmd.append(test_path)
    else:
        # Run all tests in the directory
        cmd.append(test_dir)
    
    # Add options
    if verbose:
        cmd.extend(["-v", "-s"])
    else:
        cmd.append("-v")
    
    # Add color output
    cmd.append("--color=yes")
    
    # Add summary
    cmd.append("--tb=short")
    
    print_section(f"Running Tests: {' '.join(cmd[3:])}")
    
    # Run tests
    result = subprocess.run(cmd)
    
    return result.returncode == 0


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Run database integration tests")
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Run tests in verbose mode"
    )
    parser.add_argument(
        "--specific", "-s",
        type=str,
        help="Run specific test file (e.g., 'connection', 'tables', 'services')"
    )
    parser.add_argument(
        "--skip-prereq",
        action="store_true",
        help="Skip prerequisite checks"
    )
    
    args = parser.parse_args()
    
    print_header("Database Integration Test Suite")
    
    # Check prerequisites
    if not args.skip_prereq:
        issues = check_prerequisites()
        
        if issues:
            print("\n❌ Prerequisites check failed:")
            for issue in issues:
                print(f"   - {issue}")
            print("\nPlease fix the issues above before running tests.")
            return 1
        
        print("\n✅ All prerequisites met!")
    
    # Run tests
    success = run_tests(test_file=args.specific, verbose=args.verbose)
    
    # Print summary
    print_header("Test Summary")
    
    if success:
        print("✅ All tests passed!")
        print("\nYour Docker PostgreSQL integration is working correctly.")
        print("\nNext steps:")
        print("  1. Start your application: python start.py")
        print("  2. Migrate existing data: python scripts/migrate_json_to_db.py")
        return 0
    else:
        print("❌ Some tests failed!")
        print("\nPlease review the test output above and fix any issues.")
        print("\nCommon issues:")
        print("  - PostgreSQL container not running: docker-compose up -d postgres")
        print("  - Database not initialized: python scripts/init_db.py")
        print("  - Wrong credentials in .env file")
        return 1


if __name__ == "__main__":
    sys.exit(main())

