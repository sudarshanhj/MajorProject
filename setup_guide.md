# DeepStegAI-V2 Handover & Setup Guide 🚀

This guide explains how to pull the latest **DeepStegAI-V2** code and integrate the database exactly as configured.

## 1. Prerequisites
- **Python 3.10+**
- **Node.js 18+**
- **PostgreSQL** (running locally or on a server)
- **Antigravity AI Agent**

## 2. Pushing/Pulling the Code
If you are pulling this for the first time:
```bash
git clone https://github.com/sudarshanhj/DEEPSTEGAI-V2.git
cd DEEPSTEGAI-V2
```

## 3. Database Integration 🐘
The system uses a PostgreSQL database named `deepstegai`.

### Step A: Create the Database
In your PostgreSQL terminal (psql or pgAdmin):
```sql
CREATE DATABASE deepstegai;
```

### Step B: Configure environment
Create a `backend/.env` file and update the `DATABASE_URL`:
```env
DATABASE_URL=postgresql://your_user:your_password@localhost:5432/deepstegai
```
*Replace `your_user` and `your_password` with your local PostgreSQL credentials.*

### Step C: Automatic Migration
The backend is designed to **auto-initialize** tables on first run. You don't need manual SQL migrations. Just start the backend!

## 4. Backend Setup ⚙️
```powershell
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
$env:PYTHONPATH="."
python app.py
```

## 5. Frontend Setup 💻
```powershell
cd frontend
npm install
npm run dev
```
Open [http://localhost:5173](http://localhost:5173).

## 6. Email Setup (Gmail SMTP) 📬
To enable working password resets:
1.  **Enable 2FA** on your Gmail account.
2.  Go to [App Passwords](https://myaccount.google.com/apppasswords).
3.  Generate a new app password (16 characters).
4.  Update `backend/.env`:
    ```env
    SMTP_USER=deepstegai@gmail.com
    SMTP_PASS=your_16_char_password
    USE_MOCK_EMAIL=False
    FRONTEND_URL=http://localhost:5173
    ```

## 7. Working with Antigravity AI 🤖
If you are using the **Antigravity** agent to continue development:
1.  **Context**: Antigravity works best when it has access to the `.env` file and the project structure.
2.  **Handover Signal**: Tell Antigravity: *"I have pulled the latest DeepStegAI-V2 from GitHub. Please read `setup_guide.md` and verify the `.env` configuration to ensure the database and email systems are correctly integrated."*

---
*Handover completed by Antigravity AI.*
