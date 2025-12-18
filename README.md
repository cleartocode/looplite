<p align="center">
  <img src="https://github.com/user-attachments/assets/3100f952-913d-4a51-a0fc-45f4044391be" width="600" />
</p>

# looplite
<p align="center">
  <img src="https://github.com/user-attachments/assets/beb9fbae-af38-4417-a4a1-f48ef675538a" width="480" />
  <img src="https://github.com/user-attachments/assets/fbe5c8c3-1d6e-48f5-bce2-691891f49b62" width="480" />
</p>



**looplite** is a minimal, asynchronous HTTP server built 100% in pure Python using `asyncio`. It uses no external frameworks and responds in JSON by default.

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Poetry](https://img.shields.io/badge/managed%20with-poetry-blueviolet)](https://python-poetry.org/)

### 🚀 Usage Example

```bash
poetry run python looplite/server.py
```

The server will be running at `http://127.0.0.1:8080`.

### 🧪 Included Dummy Routes for live testing

- `/` -> welcome message
- `/getuserinfo?user_id=<id>&username=<username>` -> retrieves a user id and a user name 
- `/add/<a>/<b>` -> Adds a + b
- `/submitsomething` -> POST a `data` payload
- `/status` -> JSON status with timestamp

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
