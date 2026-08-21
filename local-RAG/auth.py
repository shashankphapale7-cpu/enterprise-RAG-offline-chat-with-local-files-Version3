"""
AI Memory OS — Authentication Module
SQLite-backed user management with bcrypt password hashing.
Seeds 1000 users on first initialization.
"""

import os
import sqlite3
import hashlib
from pathlib import Path

import bcrypt

# ─── Config ───────────────────────────────────────────────────────────
ROOT_DIR = Path(__file__).parent
DB_PATH = ROOT_DIR / "users.db"
DATA_DIR = ROOT_DIR / "data"

NUM_SEED_USERS = 1000  # user1/password1 ... user1000/password1000


# ─── Database Setup ───────────────────────────────────────────────────
def _get_connection() -> sqlite3.Connection:
    """Get a SQLite connection with WAL mode for concurrent reads."""
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """
    Initialize the users database and seed default users.
    Safe to call multiple times — skips if users already exist.
    """
    conn = _get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        """)
        conn.commit()

        # Check if users are already seeded
        row = conn.execute("SELECT COUNT(*) as cnt FROM users").fetchone()
        if row["cnt"] >= NUM_SEED_USERS:
            return  # Already seeded

        # Seed users in batches for performance
        print(f"🔐 Seeding {NUM_SEED_USERS} users (first-time setup)...")
        batch_size = 100
        for batch_start in range(1, NUM_SEED_USERS + 1, batch_size):
            batch_end = min(batch_start + batch_size, NUM_SEED_USERS + 1)
            users_batch = []
            for i in range(batch_start, batch_end):
                username = f"user{i}"
                password = f"password{i}"
                pw_hash = bcrypt.hashpw(
                    password.encode("utf-8"),
                    bcrypt.gensalt(rounds=10)
                ).decode("utf-8")
                users_batch.append((username, pw_hash))

            conn.executemany(
                "INSERT OR IGNORE INTO users (username, password_hash) VALUES (?, ?)",
                users_batch
            )
            conn.commit()

        # Create per-user data directories
        for i in range(1, NUM_SEED_USERS + 1):
            user_dir = DATA_DIR / f"user{i}"
            user_dir.mkdir(parents=True, exist_ok=True)

        print(f"✅ Seeded {NUM_SEED_USERS} users successfully.")
    finally:
        conn.close()


# ─── Authentication ──────────────────────────────────────────────────
def authenticate(username: str, password: str) -> bool:
    """
    Verify username and password against stored hash.
    Returns True if credentials are valid, False otherwise.
    """
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT password_hash FROM users WHERE username = ?",
            (username,)
        ).fetchone()

        if row is None:
            return False

        stored_hash = row["password_hash"].encode("utf-8")
        if bcrypt.checkpw(password.encode("utf-8"), stored_hash):
            # Update last login timestamp
            conn.execute(
                "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE username = ?",
                (username,)
            )
            conn.commit()
            return True
        return False
    finally:
        conn.close()


def change_password(username: str, old_password: str, new_password: str) -> tuple[bool, str]:
    """
    Change user's password after verifying old password.
    Returns (success: bool, message: str).
    """
    if not new_password or len(new_password) < 4:
        return False, "New password must be at least 4 characters."

    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT password_hash FROM users WHERE username = ?",
            (username,)
        ).fetchone()

        if row is None:
            return False, "User not found."

        stored_hash = row["password_hash"].encode("utf-8")
        if not bcrypt.checkpw(old_password.encode("utf-8"), stored_hash):
            return False, "Current password is incorrect."

        new_hash = bcrypt.hashpw(
            new_password.encode("utf-8"),
            bcrypt.gensalt(rounds=10)
        ).decode("utf-8")

        conn.execute(
            "UPDATE users SET password_hash = ? WHERE username = ?",
            (new_hash, username)
        )
        conn.commit()
        return True, "Password changed successfully."
    finally:
        conn.close()


def get_user_data_dir(username: str) -> Path:
    """Get the per-user data directory, creating it if needed."""
    user_dir = DATA_DIR / username
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir


def get_user_info(username: str) -> dict | None:
    """Get user information (without password hash)."""
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT id, username, created_at, last_login FROM users WHERE username = ?",
            (username,)
        ).fetchone()
        if row:
            return dict(row)
        return None
    finally:
        conn.close()


def get_total_users() -> int:
    """Get total number of registered users."""
    conn = _get_connection()
    try:
        row = conn.execute("SELECT COUNT(*) as cnt FROM users").fetchone()
        return row["cnt"]
    finally:
        conn.close()
