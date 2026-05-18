import sys
import os
sys.path.append(os.getcwd())
from database.db import engine
from sqlalchemy import text

with engine.connect() as conn:
    print("Executing ALTER TYPE to add 'refund'...")
    # PostgreSQL specific command to add a value to an existing ENUM
    # 'IF NOT EXISTS' is NOT supported for ADD VALUE in many Postgres versions 
    # but we can try-except or check first.
    try:
        conn.execute(text("ALTER TYPE transaction_type_enum ADD VALUE 'refund'"))
        conn.commit()
        print("Successfully added 'refund' to transaction_type_enum.")
    except Exception as e:
        # Likely already exists
        print(f"Skipping: {e}")
