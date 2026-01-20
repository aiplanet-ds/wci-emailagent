"""
Setup and run database integration tests

This script:
1. Installs required testing dependencies
2. Checks Docker and PostgreSQL setup
3. Runs all database integration tests
4. Provides a detailed report

Usage:
    python test/database_integration/setup_and_test.py
"""

import sys
import os
import subprocess

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


def install_dependencies():
    """Install testing dependencies"""
    print_section("Installing Testing Dependencies")
    
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "pytest>=7.4.0", "pytest-asyncio>=0.21.0", "pytest-cov>=4.1.0"],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode == 0:
            print("✅ Testing dependencies installed successfully")
            return True
        else:
            print(f"❌ Failed to install dependencies:\n{result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error installing dependencies: {e}")
        return False


def check_docker():
    """Check if Docker is running"""
    print_section("Checking Docker Setup")
    
    try:
        # Check Docker
        result = subprocess.run(
            ["docker", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            print(f"✅ Docker installed: {result.stdout.strip()}")
        else:
            print("❌ Docker is not installed")
            return False
        
        # Check if Docker is running
        result = subprocess.run(
            ["docker", "ps"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            print("✅ Docker is running")
        else:
            print("❌ Docker is not running. Please start Docker Desktop.")
            return False
        
        return True
        
    except FileNotFoundError:
        print("❌ Docker is not installed or not in PATH")
        return False
    except Exception as e:
        print(f"❌ Error checking Docker: {e}")
        return False


def check_postgres_container():
    """Check if PostgreSQL container is running"""
    print_section("Checking PostgreSQL Container")
    
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=wci-emailagent-postgres", "--format", "{{.Names}}\t{{.Status}}"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if "wci-emailagent-postgres" in result.stdout:
            status = result.stdout.strip().split('\t')[1] if '\t' in result.stdout else "running"
            print(f"✅ PostgreSQL container is running: {status}")
            return True
        else:
            print("❌ PostgreSQL container is not running")
            print("\nTo start the container, run:")
            print("  docker-compose up -d postgres")
            return False
            
    except Exception as e:
        print(f"❌ Error checking PostgreSQL container: {e}")
        return False


def run_tests():
    """Run the database integration tests"""
    print_section("Running Database Integration Tests")
    
    test_dir = os.path.dirname(__file__)
    
    cmd = [
        sys.executable, "-m", "pytest",
        test_dir,
        "-v",
        "--color=yes",
        "--tb=short",
        "-s"
    ]
    
    print(f"Running: {' '.join(cmd[2:])}\n")
    
    result = subprocess.run(cmd)
    
    return result.returncode == 0


def main():
    """Main function"""
    print_header("Database Integration Test Setup & Runner")
    
    # Step 1: Install dependencies
    if not install_dependencies():
        print("\n❌ Failed to install dependencies. Please install manually:")
        print("   pip install pytest pytest-asyncio pytest-cov")
        return 1
    
    # Step 2: Check Docker
    if not check_docker():
        print("\n❌ Docker is not available. Please install and start Docker Desktop.")
        return 1
    
    # Step 3: Check PostgreSQL container
    if not check_postgres_container():
        print("\n❌ PostgreSQL container is not running.")
        print("\nPlease run the following commands:")
        print("  1. docker-compose up -d postgres")
        print("  2. python scripts/init_db.py")
        print("  3. python test/database_integration/setup_and_test.py")
        return 1
    
    # Step 4: Run tests
    print("\n✅ All prerequisites met! Running tests...\n")
    
    success = run_tests()
    
    # Step 5: Print summary
    print_header("Test Summary")
    
    if success:
        print("✅ All database integration tests passed!")
        print("\n🎉 Your Docker PostgreSQL integration is working correctly!")
        print("\nNext steps:")
        print("  1. Start your application:")
        print("     python start.py")
        print("\n  2. Migrate existing data (if you have JSON files):")
        print("     python scripts/migrate_json_to_db.py --dry-run")
        print("     python scripts/migrate_json_to_db.py")
        print("\n  3. Access your application at the URL configured in your environment")
        return 0
    else:
        print("❌ Some tests failed!")
        print("\nPlease review the test output above and fix any issues.")
        print("\nCommon issues:")
        print("  - Database not initialized: python scripts/init_db.py")
        print("  - Wrong credentials in .env file")
        print("  - PostgreSQL extensions not installed")
        print("\nFor detailed troubleshooting, see:")
        print("  test/database_integration/README.md")
        return 1


if __name__ == "__main__":
    sys.exit(main())

