#!/usr/bin/env python
"""Start the CreditIQ FastAPI application"""
import os
import sys
import uvicorn

# Ensure we're in the right directory
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)
sys.path.insert(0, script_dir)

if __name__ == "__main__":
    print(f"Starting CreditIQ API from: {script_dir}")
    print(f"Python: {sys.version}")
    
    # Start uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
