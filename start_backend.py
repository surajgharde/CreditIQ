#!/usr/bin/env python
"""Start the CreditIQ backend API server"""
import os
import sys
import subprocess

# Get the backend directory
backend_dir = os.path.join(os.path.dirname(__file__), "backend")

# Start the backend
print("=" * 70)
print("Starting CreditIQ Backend (FastAPI)")
print("=" * 70)
print(f"Backend directory: {backend_dir}")
print(f"API will be available at: http://localhost:8000")
print(f"API Docs: http://localhost:8000/docs")
print("\nPress Ctrl+C to stop the server\n")

os.chdir(backend_dir)
subprocess.run([sys.executable, "run_backend.py"])
