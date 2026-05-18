import subprocess
import os
import sys
import time
import signal

def run_services():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.join(root_dir, 'backend')
    frontend_dir = os.path.join(root_dir, 'frontend')
    
    # Path to the virtual environment python
    # Based on the current setup, it's in the root .venv
    python_exe = os.path.join(root_dir, '.venv', 'Scripts', 'python.exe')
    
    if not os.path.exists(python_exe):
        # Fallback to backend/venv if root .venv doesn't exist
        python_exe = os.path.join(backend_dir, 'venv', 'Scripts', 'python.exe')
    
    if not os.path.exists(python_exe):
        print(f"Error: Could not find python virtual environment at {python_exe}")
        sys.exit(1)

    print("Starting DeepStegAI Suite...")

    # 1. Start Backend
    print("  [1/2] Launching Backend API (Port 5000)...")
    backend_env = os.environ.copy()
    backend_env["PYTHONPATH"] = "."
    backend_process = subprocess.Popen(
        [python_exe, "app.py"],
        cwd=backend_dir,
        env=backend_env
    )

    # 2. Start Frontend
    print("  [2/2] Launching Frontend UI (Port 5173)...")
    # Using npx vite with host/port to be safe as per previous diagnostics
    frontend_process = subprocess.Popen(
        ["npx", "vite", "--host", "127.0.0.1", "--port", "5173"],
        cwd=frontend_dir,
        shell=True # Needed for npx on Windows
    )

    print("\nBoth services are starting!")
    print("  Frontend: http://localhost:5173")
    print("  Backend:  http://127.0.0.1:5000")
    print("\nPress Ctrl+C to stop both services.\n")

    try:
        while True:
            time.sleep(1)
            # Check if processes are still running
            if backend_process.poll() is not None:
                print("Error: Backend process exited unexpectedly.")
                break
            if frontend_process.poll() is not None:
                print("Error: Frontend process exited unexpectedly.")
                break
    except KeyboardInterrupt:
        print("\nStopping DeepStegAI Suite...")
    finally:
        # Gracefully terminate both processes
        backend_process.terminate()
        frontend_process.terminate()
        print("Done.")

if __name__ == "__main__":
    run_services()
