import sqlite3
from pathlib import Path
from datetime import datetime
import csv
import logging
from utils.logger import setup_logger

logger = setup_logger("progress_tracker")

class ProgressTracker:
    def __init__(self, db_path="checkpoints/scraper_state.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    url TEXT PRIMARY KEY,
                    product_id TEXT,
                    status TEXT DEFAULT 'PENDING',
                    retries INTEGER DEFAULT 0,
                    last_updated TIMESTAMP
                )
            """)
            conn.commit()

    def load_from_csv(self, csv_path="checkpoints/engagement_rings_index.csv"):
        """Load discovered URLs from CSV into the database if they don't exist."""
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                urls = [(row['url'],) for row in reader if row.get('url')]
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.executemany(
                    "INSERT OR IGNORE INTO products (url, last_updated) VALUES (?, CURRENT_TIMESTAMP)",
                    urls
                )
                conn.commit()
            logger.info(f"Loaded {len(urls)} URLs into progress tracker.")
        except FileNotFoundError:
            logger.error(f"CSV index not found at {csv_path}. Please run discovery first.")

    def get_pending_batch(self, batch_size=50):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT url FROM products 
                WHERE status IN ('PENDING', 'FAILED') 
                AND retries < 5
                LIMIT ?
            """, (batch_size,))
            return [row[0] for row in cursor.fetchall()]

    def mark_status(self, url: str, status: str, product_id: str = None):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            if status == 'FAILED':
                cursor.execute("""
                    UPDATE products 
                    SET status = ?, retries = retries + 1, last_updated = CURRENT_TIMESTAMP
                    WHERE url = ?
                """, (status, url))
            else:
                if product_id:
                    cursor.execute("""
                        UPDATE products 
                        SET status = ?, product_id = ?, last_updated = CURRENT_TIMESTAMP
                        WHERE url = ?
                    """, (status, product_id, url))
                else:
                    cursor.execute("""
                        UPDATE products 
                        SET status = ?, last_updated = CURRENT_TIMESTAMP
                        WHERE url = ?
                    """, (status, url))
            conn.commit()

    def get_stats(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT status, COUNT(*) FROM products GROUP BY status")
            stats = dict(cursor.fetchall())
            
            cursor.execute("SELECT COUNT(*) FROM products")
            total = cursor.fetchone()[0]
            
            return {
                "total": total,
                "completed": stats.get('COMPLETED', 0),
                "pending": stats.get('PENDING', 0),
                "failed": stats.get('FAILED', 0)
            }
