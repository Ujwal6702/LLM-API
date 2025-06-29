# 🚀 LLM API Aggregator

> **API aggregating multiple Free LLM APIs with rate limiting and load balancing**

A FastAPI-based service that aggregates multiple free LLM providers (Groq, Cerebras, Google Gemini) into a single unified API endpoint. Features intelligent load balancing, rate limiting, and automatic failover between providers.

## 📋 Table of Contents

- [Features](#-features)
- [Supported Providers](#-supported-providers)
- [Prerequisites](#-prerequisites)
- [Installation](#-installation)
  - [1. Install pyenv](#1-install-pyenv)
  - [2. Install Python 3.13.3](#2-install-python-3133)  
  - [3. Create Virtual Environment](#3-create-virtual-environment)
  - [4. Install Poetry](#4-install-poetry)
  - [5. Install Dependencies](#5-install-dependencies)
- [Configuration](#-configuration)
- [Usage](#-usage)
- [API Documentation](#-api-documentation)
- [Development](#-development)
- [Architecture](#-architecture)
- [Contributing](#-contributing)

## ✨ Features

- **Multi-Provider Support**: Integrates with Groq, Cerebras, and Google Gemini
- **Load Balancing**: Intelligent request distribution across providers
- **Rate Limiting**: Per-provider rate limiting with automatic backoff
- **Automatic Failover**: Seamless switching between providers on failures
- **Free Tier Focus**: All providers offer generous free tiers (no credit card required)
- **FastAPI**: Modern, fast, and automatically documented API
- **MVC Architecture**: Clean, maintainable code structure
- **CORS Support**: Ready for web application integration
- **Environment Management**: Secure API key management

## 🤖 Supported Providers

| Provider | Model | Parameters | Context Window | Rate Limit | Status |
|----------|-------|------------|----------------|------------|--------|
| **Groq** | llama-3.3-70b-versatile | 70B | 131k tokens | 30 req/min | ✅ Production |
| **Cerebras** | llama-3.3-70b | 70B | 65k tokens | 30 req/min | ✅ Production |
| **Cerebras** | llama-4-scout-17b-16e-instruct | 17B | 8k tokens | 30 req/min | ✅ Production |
| **Google Gemini** | gemini-2.5-flash | Multimodal | 1M tokens | Free tier* | ✅ Production |

> 🔥 **All providers verified as FREE with NO CREDIT CARD requirements** (as of June 29, 2025)

*Note: Gemini API rate limits are not publicly specified for the free tier. Limits vary by model and usage tier. See [official rate limits page](https://ai.google.dev/gemini-api/docs/rate-limits) for current information.

## 📋 Prerequisites

- **Python**: 3.13.3 (recommended)
- **Poetry**: For dependency management
- **API Keys**: From supported providers (all free)

## 🛠 Installation

### 1. Install pyenv

pyenv allows you to easily install and manage multiple Python versions.

#### macOS
```bash
# Using Homebrew (recommended)
brew install pyenv

# Or using curl
curl https://pyenv.run | bash
```

#### Linux (Ubuntu/Debian)

```bash
# Install dependencies
sudo apt update
sudo apt install make build-essential libssl-dev zlib1g-dev \
libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm \
libncursesw5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev

# Install pyenv
curl https://pyenv.run | bash
```

#### Linux (CentOS/RHEL/Fedora)

```bash
# Install dependencies
sudo dnf groupinstall "Development Tools"
sudo dnf install zlib-devel bzip2 bzip2-devel readline-devel sqlite \
sqlite-devel openssl-devel tk-devel libffi-devel xz-devel

# Install pyenv
curl https://pyenv.run | bash
```

#### Windows

```powershell
# Install pyenv-win using Git
git clone https://github.com/pyenv-win/pyenv-win.git %USERPROFILE%\.pyenv

# Or using PowerShell (run as Administrator)
Invoke-WebRequest -UseBasicParsing -Uri "https://raw.githubusercontent.com/pyenv-win/pyenv-win/master/pyenv-win/install-pyenv-win.ps1" -OutFile "./install-pyenv-win.ps1"; &"./install-pyenv-win.ps1"
```

#### Add pyenv to PATH

Add these lines to your shell profile (`~/.bashrc`, `~/.zshrc`, etc.):

```bash
# For macOS/Linux
export PYENV_ROOT="$HOME/.pyenv"
[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"
```

For Windows, add `%USERPROFILE%\.pyenv\pyenv-win\bin` and `%USERPROFILE%\.pyenv\pyenv-win\shims` to your PATH.

**Restart your terminal** after installation.

### 2. Install Python 3.13.3

```bash
# Install Python 3.13.3
pyenv install 3.13.3

# Set as global default (optional)
pyenv global 3.13.3

# Verify installation
python --version
# Should output: Python 3.13.3
```

### 3. Create Virtual Environment

```bash
# Navigate to project directory
cd /path/to/LLM-API

# Create virtual environment using Python 3.13.3
python -m venv venv

# Activate virtual environment
# macOS/Linux:
source venv/bin/activate

# Windows:
venv\Scripts\activate

# Verify Python version in venv
python --version
# Should output: Python 3.13.3
```

### 4. Install Poetry

```bash
# Make sure your virtual environment is activated
# Install Poetry in the virtual environment
pip install poetry

# Verify installation
poetry --version

# Configure Poetry to use current venv
poetry config virtualenvs.in-project true
```

### 5. Install Dependencies

```bash
# Install all dependencies using Poetry
poetry install

# This will install all packages defined in pyproject.toml
```

## ⚙️ Configuration

### 1. Environment Setup

```bash
# Copy example environment file
cp .env.example .env

# Edit the .env file with your API keys
nano .env  # or use your preferred editor
```

### 2. Get API Keys (All Free!)

#### Groq API Key (FREE)
1. Visit [console.groq.com/keys](https://console.groq.com/keys)
2. Sign up with GitHub or Google (no credit card required)
3. Create an API key
4. Add to `.env`: `GROQ_API_KEY=your_key_here`

#### Cerebras API Key (FREE)
1. Visit [cloud.cerebras.ai/platform/api-keys](https://cloud.cerebras.ai/platform/api-keys)
2. Sign up for free account (no credit card required)
3. Generate API key
4. Add to `.env`: `CEREBRAS_API_KEY=your_key_here`

#### Google Gemini API Key (FREE)
1. Visit [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
2. Sign in with Google account
3. Create API key
4. Add to `.env`: `GEMINI_API_KEY=your_key_here`

**Available Models:**
- `gemini-2.5-flash` - Latest multimodal model with 1M token context
- `gemini-2.0-flash` - Previous generation with native tool use
- `gemini-1.5-flash` - High-speed model for diverse tasks

### 3. Example .env Configuration

```bash
# Application Configuration
HOST=127.0.0.1
PORT=8000
DEBUG=True

# API Keys (get these for free from the providers)
GROQ_API_KEY=gsk_your_groq_key_here
CEREBRAS_API_KEY=your_cerebras_key_here
GEMINI_API_KEY=your_gemini_key_here
```

## 🚀 Usage

### Start the Server

```bash
# Make sure virtual environment is activated
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate     # Windows

# Start the server using the run script
python run.py

# Or start directly with Poetry
poetry run python run.py

# Or start with uvicorn directly
poetry run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

The server will start at `http://127.0.0.1:8000`

### Basic API Usage

```bash
# Health check
curl http://127.0.0.1:8000/api/v1/health

# List available providers
curl http://127.0.0.1:8000/api/v1/providers

# Generate text completion
curl -X POST http://127.0.0.1:8000/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Hello, how are you?"}
    ],
    "max_tokens": 100
  }'
```

### Python Client Example

```python
import httpx
import asyncio

async def test_llm_api():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://127.0.0.1:8000/api/v1/chat/completions",
            json={
                "messages": [
                    {"role": "user", "content": "Explain quantum computing in simple terms"}
                ],
                "max_tokens": 200,
                "temperature": 0.7
            }
        )
        result = response.json()
        print(result["choices"][0]["message"]["content"])

# Run the async function
asyncio.run(test_llm_api())
```

## 📚 API Documentation

Once the server is running, visit:

- **Swagger UI**: http://127.0.0.1:8000/docs
- **ReDoc**: http://127.0.0.1:8000/redoc
- **OpenAPI JSON**: http://127.0.0.1:8000/openapi.json

### Main Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Root endpoint with API information |
| `/api/v1/health` | GET | Health check and system status |
| `/api/v1/providers` | GET | List available LLM providers |
| `/api/v1/chat/completions` | POST | OpenAI-compatible chat completions |

## 🔧 Development

### Project Structure

```
LLM-API/
├── app/
│   ├── controllers/       # Request handlers (MVC Controllers)
│   ├── services/         # Business logic (LLM providers, load balancing)
│   ├── models/           # Pydantic models for request/response
│   ├── config/           # Configuration and settings
│   ├── utils/            # Utilities (rate limiting, helpers)
│   └── views/            # Response formatting
├── pyproject.toml        # Poetry configuration
├── run.py               # Application entry point
└── .env.example         # Environment variables template
```

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=app

# Run specific test file
poetry run pytest tests/test_llm_providers.py
```

### Code Quality

```bash
# Format code with black
poetry run black app/

# Lint with flake8
poetry run flake8 app/

# Type checking with mypy
poetry run mypy app/
```

## 🏗 Architecture

The application follows an MVC (Model-View-Controller) architecture:

- **Controllers**: Handle HTTP requests and responses
- **Services**: Contain business logic for LLM providers and load balancing
- **Models**: Define data structures using Pydantic
- **Views**: Format responses for clients
- **Utils**: Provide cross-cutting concerns (rate limiting, helpers)

### Key Components

1. **Provider Manager**: Manages multiple LLM providers
2. **Load Balancer**: Distributes requests across available providers
3. **Rate Limiter**: Prevents API quota exhaustion
4. **Health Monitor**: Tracks provider availability and performance

## 🙏 Acknowledgments

- **Groq**: For providing lightning-fast LLM inference
- **Cerebras**: For high-performance AI compute
- **Google**: For Gemini's advanced multimodal capabilities
- **FastAPI**: For the excellent web framework
- **Poetry**: For dependency management

## 📞 Support

If you encounter any issues:

1. Check the [Issues](https://github.com/your-username/LLM-API/issues) page
2. Review the API documentation at `/docs`
3. Ensure all API keys are correctly configured
4. Verify your Python version is 3.13.3

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.


---

**Made for early developers by [Ujwal](mailto:ujwalujwalc@gmail.com)**

> 🔥 **All LLM providers verified as FREE with generous quotas** - Updated June 29, 2025
