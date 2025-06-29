#!/usr/bin/env python3
"""
Enhanced run script for LLM API Aggregator
"""
import os
import sys
import asyncio
import subprocess
from pathlib import Path

def check_env_file():
    """Check if .env file exists"""
    env_file = Path(".env")
    return env_file.exists()

def install_dependencies():
    """Install required dependencies using Poetry"""
    print("📦 Installing dependencies...")
    try:
        # Check if poetry is installed
        subprocess.run(["poetry", "--version"], check=True, capture_output=True)
        # Install dependencies using poetry
        subprocess.run(["poetry", "install"], check=True)
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError:
        print("❌ Poetry not found or failed to install dependencies")
        print("💡 Please install Poetry first: https://python-poetry.org/docs/#installation")
        return False

def main():
    """Main function"""
    print("🚀 LLM API Aggregator Startup")
    print("=" * 40)
    
    # Check Python version
    if sys.version_info < (3, 9):
        print("❌ Python 3.9+ required")
        sys.exit(1)
    
    # Check .env file
    if not check_env_file():
        print("⚠️  .env file not found")
        print("📋 Please copy .env.example to .env and configure your API keys")
        
        response = input("Create .env from .env.example? (y/n): ").lower()
        if response == 'y':
            try:
                subprocess.run(["cp", ".env.example", ".env"], check=True)
                print("✅ Created .env file")
                print("🔑 Please edit .env file and add your API keys")
            except subprocess.CalledProcessError:
                print("❌ Failed to create .env file")
                sys.exit(1)
        else:
            sys.exit(1)
    
    # Rate limiting setup
    print("✅ Using in-memory rate limiting")
    
    # Install dependencies if needed
    try:
        import fastapi
        import uvicorn
        import httpx
        print("✅ Core dependencies available")
    except ImportError:
        print("📦 Installing missing dependencies...")
        if not install_dependencies():
            print("❌ Please install dependencies manually:")
            print("   poetry install")
            sys.exit(1)
    
    # Set environment variables
    os.environ.setdefault("PYTHONPATH", str(Path.cwd()))
    
    # Start the application
    print("\n🌟 Starting LLM API Aggregator...")
    print("🔗 API Documentation: http://localhost:8000/docs")
    print("📊 Health Check: http://localhost:8000/api/v1/health")
    print("🔍 Provider Status: http://localhost:8000/api/v1/providers")
    print("\n💡 Press Ctrl+C to stop")
    
    try:
        from app.main import app
        import uvicorn
        
        # Run with poetry if available, otherwise direct python
        try:
            subprocess.run(["poetry", "--version"], check=True, capture_output=True)
            print("🎯 Running with Poetry environment")
            subprocess.run([
                "poetry", "run", "uvicorn", 
                "app.main:app",
                "--host", "0.0.0.0",
                "--port", "8000",
                "--reload"
            ])
        except subprocess.CalledProcessError:
            print("🐍 Running with system Python")
            uvicorn.run(
                app,
                host="0.0.0.0",
                port=8000,
                reload=True,
                log_level="info"
            )
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
    except Exception as e:
        print(f"❌ Error starting application: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
