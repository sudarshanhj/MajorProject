import os
import multiprocessing
from waitress import serve
from app import app

if __name__ == "__main__":
    print("\n" + "="*50)
    print("🚀 Starting DeepStegAI Production Demo Server...")
    print("✨ Using Waitress WSGI server (Windows native concurrency)")
    print("✨ Serving up to 40 users efficiently")
    print("="*50 + "\n")
    
    # Run Waitress on all interfaces at port 5000.
    # 8 Threads allows for smooth handling of overlapping AI tasks 
    # without overwhelming the 1-thread locked PyTorch CPU models.
    serve(app, host='0.0.0.0', port=5000, threads=8)
