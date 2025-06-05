from db.connection import get_db_connection
with get_db_connection() as conn:
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM crawled_posts")
        count = cursor.fetchone()[0]
        print(f"✅ crawled_posts table exists with {count} records")
    except Exception as e:
        print(f"❌ crawled_posts table does not exist or error: {e}")