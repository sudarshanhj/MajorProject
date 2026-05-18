from database.db import SessionLocal
from models.user import User
from utils.auth import hash_password

def seed_admin():
    db = SessionLocal()
    emails = ["hjsudarshan18@gmail.com", "aravalli813@gmail.com"]
    password = "Password@123"
    try:
        for email in emails:
            user = db.query(User).filter(User.email == email).first()
            if not user:
                print(f"Creating admin user: {email}")
                user = User(
                    email=email,
                    password_hash=hash_password(password),
                    role="admin",
                    credits=999999999,
                    is_verified=True
                )
                db.add(user)
                db.commit()
                print(f"Admin user {email} created successfully.")
            else:
                print(f"User {email} already exists. Updating role, credits, and password.")
                user.role = "admin"
                user.credits = 999999999
                user.is_verified = True
                user.password_hash = hash_password(password)
                db.commit()
                print(f"User {email} updated successfully.")
    except Exception as e:
        print(f"Error seeding admin: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_admin()
