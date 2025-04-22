#!/usr/bin/env python3
"""
Database setup script for the Corgi Recommender Service.

This script initializes the database schema for the Corgi recommender system.
It can be run directly to create or reset the database.

Usage:
  python setup.py          # Initialize database
  python setup.py --reset  # Drop all tables and recreate schema (DANGEROUS)
"""

import sys
import psycopg2
import logging
import argparse
from config import DB_CONFIG
from db.schema import create_tables, reset_tables, init_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def setup_database(reset=False, dry_run=False):
    """
    Set up the database schema.
    
    Args:
        reset: If True, drops all tables before recreating them
        dry_run: If True, don't actually connect to the database, just print SQL
    """
    if dry_run:
        from db.schema import CREATE_TABLES_SQL, CREATE_INDEXES_SQL, DROP_TABLES_SQL
        logger.info("DRY RUN MODE - Printing SQL that would be executed")
        if reset:
            logger.warning("⚠️  Would reset database schema (DROP TABLES)")
            print("\n=== DROP TABLES SQL ===\n")
            print(DROP_TABLES_SQL)
            
        print("\n=== CREATE TABLES SQL ===\n")
        print(CREATE_TABLES_SQL)
        
        print("\n=== CREATE INDEXES SQL ===\n")
        print(CREATE_INDEXES_SQL)
        
        logger.info("✅ Dry run complete - no database changes were made")
        return
        
    try:
        # Connect to PostgreSQL server
        logger.info("Connecting to PostgreSQL server...")
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = True  # Important for creating database
        
        if reset:
            # Reset all tables
            logger.warning("⚠️  Resetting database schema - ALL DATA WILL BE LOST!")
            reset_tables(conn)
        else:
            # Just init the schema
            logger.info("Initializing database schema...")
            init_db(conn)
        
        # Verify tables exist
        with conn.cursor() as cur:
            cur.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
            tables = [row[0] for row in cur.fetchall()]
            logger.info(f"Tables in database: {', '.join(tables)}")
        
        logger.info("✅ Database setup complete!")
        
    except Exception as e:
        logger.error(f"❌ Database setup failed: {e}")
        sys.exit(1)
    finally:
        if 'conn' in locals():
            conn.close()

def main():
    """Command-line entry point for database setup."""
    parser = argparse.ArgumentParser(description="Setup the Corgi Recommender Service database")
    parser.add_argument('--reset', action='store_true', help='Reset database (drops all tables!)')
    parser.add_argument('--create-db', action='store_true', help='Create the database if it doesn\'t exist')
    parser.add_argument('--dry-run', action='store_true', help='Print SQL but don\'t execute it')
    args = parser.parse_args()
    
    # If dry run is enabled, skip the database creation
    if args.dry_run:
        logger.info("Dry run mode - skipping database creation")
        setup_database(reset=args.reset, dry_run=True)
        return
    
    if args.create_db:
        try:
            # Connect to default database to create our database
            conn_params = DB_CONFIG.copy()
            db_name = conn_params.pop('dbname')
            conn_params['dbname'] = 'postgres'  # Connect to default postgres database
            
            logger.info(f"Attempting to create database '{db_name}'...")
            conn = psycopg2.connect(**conn_params)
            conn.autocommit = True
            
            with conn.cursor() as cur:
                # Check if database exists
                cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
                exists = cur.fetchone()
                
                if not exists:
                    logger.info(f"Creating database '{db_name}'...")
                    cur.execute(f'CREATE DATABASE "{db_name}"')
                    logger.info(f"Database '{db_name}' created successfully")
                else:
                    logger.info(f"Database '{db_name}' already exists")
            
            conn.close()
        except Exception as e:
            logger.error(f"Failed to create database: {e}")
            sys.exit(1)
    
    # Now set up tables
    setup_database(reset=args.reset, dry_run=False)

if __name__ == "__main__":
    main()