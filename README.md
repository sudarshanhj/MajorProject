---
title: DeepStegAI Backend
emoji: 🛡️
colorFrom: blue
colorTo: blue
sdk: docker
app_port: 7860
---

# DeepStegAI: Cinematic Intelligence Suite

DeepStegAI is a secure information hiding (steganography) and AI-driven detection (steganalysis) platform.
It uses an advanced PyTorch Spatial Rich Model CNN for detecting anomalies and an adaptive edge algorithm for hiding data securely.

This repository contains the split modern architecture: a React built frontend and a Python Flask backend API.

## 📁 Repository Structure

* `backend/`: Core AI logic, steganography engines, and the API-only Flask server.
* `frontend/`: Modern React (Vite+TS) UI using TailwindCSS and Three.js.

---

## 🚀 Getting Started

To run the DeepStegAI suite locally, you need two terminals—one for the backend API and one for the frontend UI.

### 1. Prerequisites
- **PostgreSQL**: Install and create a database named `deepstegai`.
- **Python 3.10+**
- **Node.js 18+**

### 2. Running the API Backend

The backend provides AI detection, steganography, and user authentication on **Port 8000**.

```bash
# Terminal 1
cd backend
cp .env.example .env  # Update DATABASE_URL with your local DB password
python app.py
```

*Note: The database tables will be automatically created on the first run.*

### 3. Running the React Frontend

The frontend provides the main "Obsidian Industrial" interface.

```bash
# Terminal 2
cd frontend
npm install   # Only needed the first time
npm run dev
```

The frontend will start at `http://localhost:5173`. It is configured to communicate with the backend on **Port 8000**.

---

## 🛠️ Technology Stack
- **Frontend UI**: React 18, Vite, TypeScript, TailwindCSS, Zustand, React-Three-Fiber
- **Backend API**: Python 3.10+, Flask, SQLAlchemy
- **Database**: PostgreSQL (User Authentication & Credits)
- **Deep Learning**: PyTorch (SRM-CNN Architecture)
- **Authentication**: JWT & Bcrypt

*Powered by DeepStegAI Research Group*
