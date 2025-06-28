# looplite

**looplite** is a minimal, asynchronous HTTP server built 100% in pure Python using `asyncio`. It uses no external frameworks and responds in JSON by default.

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Poetry](https://img.shields.io/badge/managed%20with-poetry-blueviolet)](https://python-poetry.org/)

### 🚀 Usage Example

```bash
poetry run python looplite/server.py
```

The server will be running at `http://127.0.0.1:8080`.

### 🧪 Included Routes

- `/` → welcome message  
- `/status` → JSON status with timestamp

### 📦 Installation

```bash
poetry install
```

### 🎯 Goals

- Ultra lightweight server  
- Educational codebase  
- Zero external dependencies

---

**License:** MIT
