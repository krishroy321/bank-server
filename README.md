<div align="center">

# 🏦 Krish Bank

### A Multi-User Banking REST API — Built with Pure Python

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docker.com)
[![License](https://img.shields.io/badge/License-MIT-22c55e?style=for-the-badge)](LICENSE)
[![Zero Dependencies](https://img.shields.io/badge/Dependencies-Zero-f97316?style=for-the-badge)]()
[![Network Ready](https://img.shields.io/badge/Network-WiFi%20Ready-8b5cf6?style=for-the-badge)]()

<br/>

> A fully functional banking system REST API — no frameworks, no external libraries.  
> Just Python's standard library, running on any machine or in Docker, accessible across your local network.

<br/>

```
╔══════════════════════════════════════════════════════╗
║             KRISH BANK - HTTP SERVER                 ║
╠══════════════════════════════════════════════════════╣
║  Local:     http://localhost:8080                    ║
║  Network:   http://192.168.1.42:8080                 ║
║  (Share the Network URL with devices on same WiFi)   ║
╠══════════════════════════════════════════════════════╣
║  Multi-user: YES  │  File Storage: YES  │  CORS: YES ║
╚══════════════════════════════════════════════════════╝
```

</div>

---

## ✨ Features

| Feature | Details |
|---|---|
| 🔐 **Authentication** | UUID Bearer token auth, session management |
| 👥 **Multi-user** | Thread-safe concurrent access for multiple users |
| 💾 **File Storage** | JSON file persistence — no database needed |
| 🌐 **Network Ready** | Binds to `0.0.0.0`, auto-detects and prints your WiFi IP |
| 🔄 **CORS Support** | Full preflight + headers, works with any frontend |
| 🐳 **Docker Ready** | Single command deploy with `docker compose up` |
| 🛡️ **Edge Cases** | 20+ validation checks for all inputs and operations |
| 📦 **Zero Dependencies** | Pure Python standard library only |

---

## 🚀 Quick Start

### Option 1 — Run directly with Python

```bash
# Clone the repo
git clone https://github.com/yourusername/krish-bank.git
cd krish-bank

# Start the server
python bank_server.py
```

### Option 2 — Run with Docker

```bash
# Clone the repo
git clone https://github.com/yourusername/krish-bank.git
cd krish-bank

# Build and run (data persists in a Docker volume)
docker compose up --build
```

### Option 3 — Docker without Compose

```bash
docker build -t krish-bank .
docker run -p 8080:8080 -v krish_data:/data krish-bank
```

The server will print your local network IP on startup — share it with any device on the same WiFi to use the API.

---

## 📡 API Reference

**Base URL:** `http://localhost:8080`  
**Auth:** Protected routes require `Authorization: Bearer <token>` header  
**Body:** All POST requests use `Content-Type: application/json`

### 🔓 Public Endpoints

#### `POST /register` — Create a new account
```json
{
  "name": "Krish Patel",
  "username": "krish",
  "password": "pass123",
  "email": "krish@example.com"
}
```
```json
{
  "status": "success",
  "message": "Account created successfully. Welcome, Krish Patel!",
  "account_number": "123456789012"
}
```

#### `POST /login` — Login and receive a token
```json
{
  "username": "krish",
  "password": "pass123"
}
```
```json
{
  "status": "success",
  "token": "550e8400-e29b-41d4-a716-446655440000",
  "account_number": "123456789012",
  "name": "Krish Patel"
}
```

---

### 🔒 Protected Endpoints

> All routes below require: `Authorization: Bearer <your_token>`

#### `POST /logout`
Invalidates your session token immediately.

---

#### `GET /balance`
```json
{
  "status": "success",
  "account_number": "123456789012",
  "name": "Krish Patel",
  "balance": 45000.00
}
```

---

#### `GET /profile`
```json
{
  "status": "success",
  "name": "Krish Patel",
  "email": "krish@example.com",
  "username": "krish",
  "account_number": "123456789012",
  "balance": 45000.00,
  "member_since": "2024-01-15 10:30:00",
  "total_transactions": 12
}
```

---

#### `GET /transactions?limit=10`
Returns transaction history, newest first. `limit` defaults to 20 (max 100).

```json
{
  "status": "success",
  "transactions": [
    {
      "id": "a1b2c3d4",
      "type": "CREDIT",
      "amount": 5000.00,
      "note": "Salary",
      "time": "2024-01-20 09:00:00",
      "balance_after": 45000.00
    }
  ],
  "total": 12
}
```

---

#### `POST /deposit`
```json
{ "amount": 5000, "note": "Salary" }
```
```json
{ "status": "success", "message": "₹5000.00 deposited successfully.", "new_balance": 50000.00 }
```

---

#### `POST /withdraw`
```json
{ "amount": 2000, "note": "Groceries" }
```
```json
{ "status": "success", "message": "₹2000.00 withdrawn successfully.", "new_balance": 48000.00 }
```

---

#### `POST /transfer`
```json
{
  "to_account": "987654321098",
  "amount": 1000,
  "note": "Splitting the bill"
}
```
```json
{
  "status": "success",
  "message": "₹1000.00 transferred to Arjun Sharma (987654321098) successfully.",
  "new_balance": 47000.00,
  "transaction_id": "f5e6d7c8"
}
```

---

#### `POST /change-password`
```json
{
  "old_password": "pass123",
  "new_password": "newpass456"
}
```
> All active sessions for this user are invalidated immediately after a password change.

---

## 🧪 Testing

Run the included automated test suite that covers every endpoint and edge case:

```bash
python test_bank.py
```

Or test manually with curl:

```bash
# 1. Register
curl -X POST http://localhost:8080/register \
  -H "Content-Type: application/json" \
  -d '{"name":"Krish Patel","username":"krish","password":"pass123","email":"krish@example.com"}'

# 2. Login — copy the token from the response
curl -X POST http://localhost:8080/login \
  -H "Content-Type: application/json" \
  -d '{"username":"krish","password":"pass123"}'

# 3. Check balance (replace TOKEN)
curl http://localhost:8080/balance \
  -H "Authorization: Bearer TOKEN"

# 4. Deposit
curl -X POST http://localhost:8080/deposit \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN" \
  -d '{"amount": 10000, "note": "Initial deposit"}'
```

---

## 🛡️ Edge Cases Handled

- ❌ Duplicate username or email on registration
- ❌ Passwords under 6 characters / usernames under 3 characters
- ❌ Invalid email format
- ❌ Negative or zero deposit/withdraw/transfer amounts
- ❌ Deposit over ₹10,00,000 at once
- ❌ Withdrawal exceeding available balance (overdraft protection)
- ❌ Transfer to your own account
- ❌ Transfer to a non-existent account
- ❌ Missing required JSON fields / malformed JSON body
- ❌ Invalid or expired Bearer token
- ❌ Using old token after logout or password change
- ❌ Incorrect old password on change-password
- ❌ New password same as old password
- ✅ All file writes are thread-safe — concurrent users won't corrupt data

---

## 🏗️ Project Structure

```
krish-bank/
│
├── bank_server.py       # Main server — all logic in one file
├── test_bank.py         # Automated test suite for all endpoints
├── Dockerfile           # Docker image definition
├── docker-compose.yml   # One-command Docker deployment
├── .dockerignore        # Files excluded from Docker build
├── .gitignore           # Files excluded from git
└── README.md            # You are here
```

---

## ⚙️ Architecture

```
HTTP Request
     │
     ▼
BankHandler (BaseHTTPRequestHandler)
     │  ├── CORS preflight (OPTIONS)
     │  ├── Parse path + query string
     │  └── Route to handler function
     │
     ├── Public Routes ──────► create_user() / login_user()
     │
     └── Protected Routes
           │
           ├── require_auth() ──► sessions{} (in-memory dict)
           │
           └── Business Logic
                 │
                 └── data_lock ──► bank_data.json (file storage)
```

**Storage:** `bank_data.json` holds all users, accounts, and transaction history.  
**Sessions:** Stored in-memory as a `dict` — fast lookups, resets on server restart.  
**Concurrency:** `threading.Lock` on all file reads/writes; `sessions_lock` for the session map.

---

## 🐳 Docker Details

The Docker image is based on `python:3.11-slim` for a minimal footprint. Bank data is stored in a named Docker volume at `/data` — this means **your data survives container restarts and rebuilds**.

```bash
# View live logs
docker compose logs -f

# Stop the server
docker compose down

# Stop and wipe all data (fresh start)
docker compose down -v
```

---

## 📋 Requirements

**To run with Python:** Python 3.8 or higher. No `pip install` needed — ever.

**To run with Docker:** Docker Desktop (Windows/Mac) or Docker Engine + Compose (Linux).

---

## 📄 License

This project is open source under the [MIT License](LICENSE).

---

<div align="center">

Made with ❤️ by **Krish**

*Pure Python. Zero dependencies. Just works.*

</div>