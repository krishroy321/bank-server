"""
Krish Bank - HTTP Banking Server
Handles multiple users, file-based storage, full CORS, JSON API
"""

import json
import os
import uuid
import hashlib
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# ─── CONFIG ───────────────────────────────────────────────────────────────────
HOST = "0.0.0.0"   # listen on all interfaces (WiFi, LAN, localhost)
PORT = 8080
DATA_FILE = "bank_data.json"

# ─── FILE STORAGE ─────────────────────────────────────────────────────────────
data_lock = threading.Lock()   # thread-safe file access

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"users": {}, "accounts": {}}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ─── HELPERS ──────────────────────────────────────────────────────────────────
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def generate_account_number():
    return str(uuid.uuid4().int)[:12]

def generate_token():
    return str(uuid.uuid4())

def timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def ok(data):
    return 200, {"status": "success", **data}

def err(code, message):
    return code, {"status": "error", "message": message}

# Active sessions: token -> username  (in-memory, fast)
sessions = {}
sessions_lock = threading.Lock()

def get_user_from_token(token):
    with sessions_lock:
        return sessions.get(token)

# ─── BUSINESS LOGIC ───────────────────────────────────────────────────────────
def create_user(body):
    name     = body.get("name", "").strip()
    username = body.get("username", "").strip()
    password = body.get("password", "")
    email    = body.get("email", "").strip()

    if not all([name, username, password, email]):
        return err(400, "name, username, password and email are all required.")
    if len(username) < 3:
        return err(400, "Username must be at least 3 characters.")
    if len(password) < 6:
        return err(400, "Password must be at least 6 characters.")
    if "@" not in email:
        return err(400, "Invalid email address.")

    with data_lock:
        data = load_data()
        if username in data["users"]:
            return err(409, "Username already exists.")
        if any(u["email"] == email for u in data["users"].values()):
            return err(409, "Email already registered.")

        acc_no = generate_account_number()
        while acc_no in data["accounts"]:
            acc_no = generate_account_number()

        data["users"][username] = {
            "name":     name,
            "email":    email,
            "password": hash_password(password),
            "acc_no":   acc_no,
            "created":  timestamp()
        }
        data["accounts"][acc_no] = {
            "username":    username,
            "balance":     0,
            "transactions": []
        }
        save_data(data)

    return ok({
        "message": f"Account created successfully. Welcome, {name}!",
        "account_number": acc_no
    })


def login_user(body):
    username = body.get("username", "").strip()
    password = body.get("password", "")

    if not username or not password:
        return err(400, "username and password are required.")

    with data_lock:
        data = load_data()
        user = data["users"].get(username)

    if not user or user["password"] != hash_password(password):
        return err(401, "Invalid username or password.")

    token = generate_token()
    with sessions_lock:
        sessions[token] = username

    return ok({
        "message": f"Welcome back, {user['name']}!",
        "token": token,
        "account_number": user["acc_no"],
        "name": user["name"]
    })


def logout_user(token):
    with sessions_lock:
        removed = sessions.pop(token, None)
    if removed:
        return ok({"message": "Logged out successfully."})
    return err(401, "Invalid or expired token.")


def get_balance(username):
    with data_lock:
        data = load_data()
        user = data["users"].get(username)
        if not user:
            return err(404, "User not found.")
        acc = data["accounts"][user["acc_no"]]
    return ok({
        "account_number": user["acc_no"],
        "name": user["name"],
        "balance": acc["balance"]
    })


def deposit(username, body):
    amount = body.get("amount")
    note   = body.get("note", "Deposit")

    if amount is None:
        return err(400, "amount is required.")
    try:
        amount = float(amount)
    except (ValueError, TypeError):
        return err(400, "amount must be a number.")
    if amount <= 0:
        return err(400, "Deposit amount must be greater than 0.")
    if amount > 1_000_000:
        return err(400, "Cannot deposit more than ₹10,00,000 at once.")

    with data_lock:
        data = load_data()
        user = data["users"].get(username)
        if not user:
            return err(404, "User not found.")
        acc = data["accounts"][user["acc_no"]]
        acc["balance"] = round(acc["balance"] + amount, 2)
        acc["transactions"].append({
            "id":     str(uuid.uuid4())[:8],
            "type":   "CREDIT",
            "amount": amount,
            "note":   note,
            "time":   timestamp(),
            "balance_after": acc["balance"]
        })
        save_data(data)

    return ok({
        "message": f"₹{amount:.2f} deposited successfully.",
        "new_balance": acc["balance"]
    })


def withdraw(username, body):
    amount = body.get("amount")
    note   = body.get("note", "Withdrawal")
    mpin   = str(body.get("mpin", ""))

    if amount is None:
        return err(400, "amount is required.")
    try:
        amount = float(amount)
    except (ValueError, TypeError):
        return err(400, "amount must be a number.")
    if amount <= 0:
        return err(400, "Withdrawal amount must be greater than 0.")

    with data_lock:
        data = load_data()
        user = data["users"].get(username)
        if not user:
            return err(404, "User not found.")
        acc = data["accounts"][user["acc_no"]]

        if acc["balance"] < amount:
            return err(400, f"Insufficient balance. Available: ₹{acc['balance']:.2f}")

        acc["balance"] = round(acc["balance"] - amount, 2)
        acc["transactions"].append({
            "id":     str(uuid.uuid4())[:8],
            "type":   "DEBIT",
            "amount": amount,
            "note":   note,
            "time":   timestamp(),
            "balance_after": acc["balance"]
        })
        save_data(data)

    return ok({
        "message": f"₹{amount:.2f} withdrawn successfully.",
        "new_balance": acc["balance"]
    })


def transfer(username, body):
    amount       = body.get("amount")
    to_acc       = str(body.get("to_account", "")).strip()
    note         = body.get("note", "Transfer")

    if not to_acc:
        return err(400, "to_account is required.")
    if amount is None:
        return err(400, "amount is required.")
    try:
        amount = float(amount)
    except (ValueError, TypeError):
        return err(400, "amount must be a number.")
    if amount <= 0:
        return err(400, "Transfer amount must be greater than 0.")

    with data_lock:
        data = load_data()
        user = data["users"].get(username)
        if not user:
            return err(404, "User not found.")

        from_acc_no = user["acc_no"]
        if from_acc_no == to_acc:
            return err(400, "Cannot transfer to your own account.")

        if to_acc not in data["accounts"]:
            return err(404, "Destination account not found.")

        from_acc = data["accounts"][from_acc_no]
        to_acc_data = data["accounts"][to_acc]

        if from_acc["balance"] < amount:
            return err(400, f"Insufficient balance. Available: ₹{from_acc['balance']:.2f}")

        to_username = to_acc_data["username"]
        to_user = data["users"].get(to_username, {})
        to_name = to_user.get("name", "Unknown")

        from_acc["balance"] = round(from_acc["balance"] - amount, 2)
        to_acc_data["balance"] = round(to_acc_data["balance"] + amount, 2)

        txn_id = str(uuid.uuid4())[:8]
        from_acc["transactions"].append({
            "id":     txn_id,
            "type":   "DEBIT",
            "amount": amount,
            "note":   f"Transfer to {to_acc} ({to_name}): {note}",
            "time":   timestamp(),
            "balance_after": from_acc["balance"]
        })
        to_acc_data["transactions"].append({
            "id":     txn_id,
            "type":   "CREDIT",
            "amount": amount,
            "note":   f"Transfer from {from_acc_no} ({user['name']}): {note}",
            "time":   timestamp(),
            "balance_after": to_acc_data["balance"]
        })
        save_data(data)

    return ok({
        "message": f"₹{amount:.2f} transferred to {to_name} ({to_acc}) successfully.",
        "new_balance": from_acc["balance"],
        "transaction_id": txn_id
    })


def get_transactions(username, limit=20):
    with data_lock:
        data = load_data()
        user = data["users"].get(username)
        if not user:
            return err(404, "User not found.")
        acc = data["accounts"][user["acc_no"]]
        txns = acc["transactions"][-limit:][::-1]   # latest first

    return ok({
        "account_number": user["acc_no"],
        "transactions": txns,
        "total": len(acc["transactions"])
    })


def get_profile(username):
    with data_lock:
        data = load_data()
        user = data["users"].get(username)
        if not user:
            return err(404, "User not found.")
        acc = data["accounts"][user["acc_no"]]

    return ok({
        "name":           user["name"],
        "email":          user["email"],
        "username":       username,
        "account_number": user["acc_no"],
        "balance":        acc["balance"],
        "member_since":   user["created"],
        "total_transactions": len(acc["transactions"])
    })


def change_password(username, body):
    old_password = body.get("old_password", "")
    new_password = body.get("new_password", "")

    if not old_password or not new_password:
        return err(400, "old_password and new_password are required.")
    if len(new_password) < 6:
        return err(400, "New password must be at least 6 characters.")
    if old_password == new_password:
        return err(400, "New password must be different from old password.")

    with data_lock:
        data = load_data()
        user = data["users"].get(username)
        if not user:
            return err(404, "User not found.")
        if user["password"] != hash_password(old_password):
            return err(401, "Old password is incorrect.")
        data["users"][username]["password"] = hash_password(new_password)
        save_data(data)

    # Invalidate all sessions for this user
    with sessions_lock:
        to_remove = [t for t, u in sessions.items() if u == username]
        for t in to_remove:
            del sessions[t]

    return ok({"message": "Password changed. Please login again."})


# ─── HTTP HANDLER ─────────────────────────────────────────────────────────────
class BankHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        print(f"[{timestamp()}] {self.address_string()} {format % args}")

    def send_json(self, status, data):
        body = json.dumps(data, indent=2).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self._add_cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def _add_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Max-Age", "86400")

    def do_OPTIONS(self):
        self.send_response(204)
        self._add_cors_headers()
        self.end_headers()

    def read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    def get_token(self):
        auth = self.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            return auth[7:].strip()
        return None

    def require_auth(self):
        token = self.get_token()
        if not token:
            return None, err(401, "Authorization header with Bearer token is required.")
        username = get_user_from_token(token)
        if not username:
            return None, err(401, "Invalid or expired token. Please login again.")
        return username, None

    def route(self, method, path, query):
        # ── PUBLIC ROUTES ──────────────────────────────────────────────
        if method == "GET" and path == "/":
            return ok({
                "server":  "Krish Bank HTTPS API",
                "version": "1.0",
                "endpoints": {
                    "POST /register":          "Create new account",
                    "POST /login":             "Login",
                    "POST /logout":            "Logout (Auth required)",
                    "GET  /balance":           "Get balance (Auth)",
                    "GET  /profile":           "Get profile (Auth)",
                    "GET  /transactions":      "Get transactions (Auth)",
                    "POST /deposit":           "Deposit money (Auth)",
                    "POST /withdraw":          "Withdraw money (Auth)",
                    "POST /transfer":          "Transfer money (Auth)",
                    "POST /change-password":   "Change password (Auth)"
                }
            })

        if method == "POST" and path == "/register":
            body = self.read_body()
            if body is None:
                return err(400, "Invalid JSON body.")
            return create_user(body)

        if method == "POST" and path == "/login":
            body = self.read_body()
            if body is None:
                return err(400, "Invalid JSON body.")
            return login_user(body)

        # ── PROTECTED ROUTES ───────────────────────────────────────────
        if method == "POST" and path == "/logout":
            token = self.get_token()
            if not token:
                return err(401, "Token required.")
            return logout_user(token)

        if method == "GET" and path == "/balance":
            username, error = self.require_auth()
            if error:
                return error
            return get_balance(username)

        if method == "GET" and path == "/profile":
            username, error = self.require_auth()
            if error:
                return error
            return get_profile(username)

        if method == "GET" and path == "/transactions":
            username, error = self.require_auth()
            if error:
                return error
            limit = int(query.get("limit", ["20"])[0]) if "limit" in query else 20
            limit = max(1, min(limit, 100))
            return get_transactions(username, limit)

        if method == "POST" and path == "/deposit":
            username, error = self.require_auth()
            if error:
                return error
            body = self.read_body()
            if body is None:
                return err(400, "Invalid JSON body.")
            return deposit(username, body)

        if method == "POST" and path == "/withdraw":
            username, error = self.require_auth()
            if error:
                return error
            body = self.read_body()
            if body is None:
                return err(400, "Invalid JSON body.")
            return withdraw(username, body)

        if method == "POST" and path == "/transfer":
            username, error = self.require_auth()
            if error:
                return error
            body = self.read_body()
            if body is None:
                return err(400, "Invalid JSON body.")
            return transfer(username, body)

        if method == "POST" and path == "/change-password":
            username, error = self.require_auth()
            if error:
                return error
            body = self.read_body()
            if body is None:
                return err(400, "Invalid JSON body.")
            return change_password(username, body)

        return err(404, f"Endpoint '{method} {path}' not found.")

    def handle_request(self, method):
        parsed = urlparse(self.path)
        path   = parsed.path.rstrip("/") or "/"
        query  = parse_qs(parsed.query)

        try:
            status, data = self.route(method, path, query)
            self.send_json(status, data)
        except Exception as e:
            print(f"[ERROR] {e}")
            self.send_json(500, {"status": "error", "message": "Internal server error."})

    def do_GET(self):  self.handle_request("GET")
    def do_POST(self): self.handle_request("POST")
    def do_PUT(self):  self.handle_request("PUT")
    def do_DELETE(self): self.handle_request("DELETE")


# ─── IP DETECTION ─────────────────────────────────────────────────────────────
def get_local_ip():
    import socket
    try:
        # Connects to an external address to find the outbound interface IP
        # No data is actually sent
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

# ─── MAIN ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    server = HTTPServer((HOST, PORT), BankHandler)
    server.daemon_threads = True

    local_ip = get_local_ip()

    print(f"""
╔══════════════════════════════════════════════════════╗
║             KRISH BANK - HTTP SERVER                 ║
╠══════════════════════════════════════════════════════╣
║  Local:     http://localhost:{PORT}                ║
║  Network:   http://{local_ip}:{PORT}                 ║
║  (Share the Network URL with devices on same WiFi)   ║
╠══════════════════════════════════════════════════════╣
║  Data file:  {DATA_FILE}                             ║
║  Multi-user: YES (threading enabled)                 ║
╠══════════════════════════════════════════════════════╣
║  ENDPOINTS                                           ║
║  POST /register        - Create account              ║
║  POST /login           - Login                       ║
║  POST /logout          - Logout                      ║
║  GET  /balance         - View balance                ║
║  GET  /profile         - View profile                ║
║  GET  /transactions    - Transaction history         ║
║  POST /deposit         - Deposit money               ║
║  POST /withdraw        - Withdraw money              ║
║  POST /transfer        - Transfer money              ║
║  POST /change-password - Change password             ║
╚══════════════════════════════════════════════════════╝
    """)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")