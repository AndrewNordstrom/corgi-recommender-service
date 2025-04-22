#!/usr/bin/env python3
"""
Development Health Check for Corgi Recommender Service

This script performs quick health checks on the Corgi Recommender Service
development environment, including:

1. API server availability
2. Database connection
3. Database schema verification
4. Basic system configuration

Exit codes:
- 0: All checks passed
- 1: One or more checks failed
"""

import os
import sys
import json
import time
import logging
import requests
import psycopg2
from datetime import datetime

# ANSI color codes for terminal output
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
BOLD = "\033[1m"
RESET = "\033[0m"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("dev_check")

# Default settings
DEFAULT_API_URL = "http://localhost:5001"
DEFAULT_HEALTH_ENDPOINT = "/health"
EXPECTED_TABLES = ["privacy_settings", "post_metadata", "interactions", "post_rankings"]

def print_result(check_name, success, message=None, error=None):
    """Print a formatted check result."""
    status = f"{GREEN}✅ PASS{RESET}" if success else f"{RED}❌ FAIL{RESET}"
    print(f"{BOLD}{check_name}{RESET}: {status}")
    
    if message and success:
        print(f"  {GREEN}{message}{RESET}")
    
    if error and not success:
        print(f"  {RED}{error}{RESET}")
    
    return success

def check_api_health(base_url=DEFAULT_API_URL, endpoint=DEFAULT_HEALTH_ENDPOINT):
    """Check if the API server is running and healthy."""
    try:
        url = f"{base_url}{endpoint}"
        start_time = time.time()
        response = requests.get(url, timeout=5)
        latency = (time.time() - start_time) * 1000  # Convert to ms
        
        if response.status_code == 200:
            try:
                # Try to parse JSON response
                data = response.json()
                message = f"API is running (latency: {latency:.2f}ms)"
                if isinstance(data, dict) and "status" in data:
                    message += f", status: {data['status']}"
                return print_result("API Health", True, message)
            except ValueError:
                # Non-JSON response, still a success if 200
                return print_result("API Health", True, f"API is running (latency: {latency:.2f}ms)")
        else:
            return print_result("API Health", False, 
                               error=f"API returned status code {response.status_code}")
    
    except requests.exceptions.ConnectionError:
        return print_result("API Health", False, 
                           error=f"Could not connect to API at {base_url}. Is the server running?")
    except Exception as e:
        return print_result("API Health", False, error=f"API check failed: {str(e)}")

def get_db_connection():
    """Get a database connection using environment variables."""
    try:
        # Get connection parameters from environment variables
        db_params = {
            "dbname": os.environ.get("POSTGRES_DB", "corgi_recommender"),
            "user": os.environ.get("POSTGRES_USER", "postgres"),
            "password": os.environ.get("POSTGRES_PASSWORD", "postgres"),
            "host": os.environ.get("POSTGRES_HOST", "localhost"),
            "port": os.environ.get("DB_PORT", "5432"),
        }
        
        # Connect to the database
        conn = psycopg2.connect(**db_params)
        conn.autocommit = True
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        return None

def check_db_connection():
    """Check if the database connection works."""
    try:
        conn = get_db_connection()
        if conn is None:
            return print_result("Database Connection", False, 
                               error="Failed to connect to database. Check credentials and server status.")
        
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            result = cur.fetchone()
            
            if result and result[0] == 1:
                db_info = []
                
                # Get PostgreSQL version
                cur.execute("SELECT version()")
                version = cur.fetchone()[0].split()[1]
                db_info.append(f"PostgreSQL {version}")
                
                # Get database size
                cur.execute("SELECT pg_size_pretty(pg_database_size(current_database()))")
                size = cur.fetchone()[0]
                db_info.append(f"Size: {size}")
                
                conn.close()
                return print_result("Database Connection", True, ", ".join(db_info))
            else:
                conn.close()
                return print_result("Database Connection", False, 
                                   error="Database responded but returned unexpected result")
    except Exception as e:
        return print_result("Database Connection", False, error=f"Database check failed: {str(e)}")

def check_tables_exist():
    """Check if all expected tables exist in the database."""
    try:
        conn = get_db_connection()
        if conn is None:
            return print_result("Database Schema", False, 
                               error="Could not connect to database to check tables")
        
        with conn.cursor() as cur:
            # Get list of tables in the public schema
            cur.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
            tables = [row[0] for row in cur.fetchall()]
            
            # Check if all expected tables exist
            missing_tables = [table for table in EXPECTED_TABLES if table not in tables]
            
            if not missing_tables:
                # Get table row counts as extra info
                table_counts = {}
                for table in EXPECTED_TABLES:
                    cur.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cur.fetchone()[0]
                    table_counts[table] = count
                
                counts_str = ", ".join([f"{table}: {count} rows" for table, count in table_counts.items()])
                conn.close()
                return print_result("Database Schema", True, f"All required tables exist. {counts_str}")
            else:
                conn.close()
                missing_str = ", ".join(missing_tables)
                return print_result("Database Schema", False, 
                                   error=f"Missing tables: {missing_str}")
    except Exception as e:
        return print_result("Database Schema", False, error=f"Schema check failed: {str(e)}")

def check_environment():
    """Check if all required environment variables are set."""
    required_vars = {
        "POSTGRES_DB": os.environ.get("POSTGRES_DB", "corgi_recommender"),
        "POSTGRES_USER": os.environ.get("POSTGRES_USER"),
        "POSTGRES_PASSWORD": os.environ.get("POSTGRES_PASSWORD"),
    }
    
    missing_vars = [var for var, val in required_vars.items() if not val]
    
    if not missing_vars:
        env_info = [
            f"POSTGRES_DB={required_vars['POSTGRES_DB']}",
            f"POSTGRES_USER={required_vars['POSTGRES_USER']}",
            f"PORT={os.environ.get('PORT', '5001')}"
        ]
        return print_result("Environment", True, ", ".join(env_info))
    else:
        missing_str = ", ".join(missing_vars)
        return print_result("Environment", False, 
                           error=f"Missing environment variables: {missing_str}")

def main():
    """Run all health checks and print a summary."""
    print(f"\n{BOLD}{CYAN}Corgi Recommender Service Health Check{RESET}")
    print(f"{CYAN}=====================================\n{RESET}")
    
    # Track overall health
    checks_passed = 0
    checks_total = 0
    
    # Run all checks
    checks_total += 1
    if check_environment():
        checks_passed += 1
    
    checks_total += 1
    if check_api_health():
        checks_passed += 1
    
    checks_total += 1
    if check_db_connection():
        checks_passed += 1
        
        # Only check tables if DB connection works
        checks_total += 1
        if check_tables_exist():
            checks_passed += 1
    
    # Print summary
    print(f"\n{CYAN}Summary:{RESET}")
    if checks_passed == checks_total:
        print(f"{GREEN}{BOLD}✅ All checks passed ({checks_passed}/{checks_total}){RESET}")
        exit_code = 0
    else:
        print(f"{RED}{BOLD}❌ {checks_total - checks_passed} check(s) failed ({checks_passed}/{checks_total} passed){RESET}")
        exit_code = 1
    
    # Timestamp
    print(f"\n{YELLOW}Check completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{RESET}\n")
    
    sys.exit(exit_code)

if __name__ == "__main__":
    main()