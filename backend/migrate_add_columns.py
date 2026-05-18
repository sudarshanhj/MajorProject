"""One-time migration: add missing columns to existing tables."""
from database.db import engine
from sqlalchemy import text

MIGRATIONS = [
    # Users table — new columns added after initial table creation
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_verified BOOLEAN DEFAULT FALSE",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS otp_code VARCHAR",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS otp_expiry TIMESTAMP",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS reset_token VARCHAR",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS reset_token_expiry TIMESTAMP",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS credits INTEGER DEFAULT 50",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR DEFAULT 'user'",
]

def run():
    with engine.connect() as conn:
        for sql in MIGRATIONS:
            try:
                conn.execute(text(sql))
                print(f"[OK] {sql[:60]}...")
            except Exception as e:
                print(f"[SKIP] {sql[:60]}... ({e})")
        conn.commit()
    print("\nMigration complete.")

if __name__ == "__main__":
    run()
