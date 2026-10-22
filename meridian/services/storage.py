"""Private SQLite persistence with Argon2 passwords and hashed expiring sessions."""
import hashlib
import json
import os
import re
import secrets
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError

HASHER = PasswordHasher()


@contextmanager
def connect():
    root = Path(os.environ.get('MERIDIAN_DATA_DIR', '.meridian'))
    root.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(root / 'accounts.sqlite3', timeout=15)
    db.row_factory = sqlite3.Row
    db.executescript('''
      CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL, profile TEXT NOT NULL DEFAULT '{}',
        documents TEXT NOT NULL DEFAULT '{}', results TEXT NOT NULL DEFAULT '{}');
      CREATE TABLE IF NOT EXISTS sessions (token TEXT PRIMARY KEY, user_id INTEGER, expires REAL NOT NULL);
      CREATE TABLE IF NOT EXISTS attempts (email TEXT PRIMARY KEY, count INTEGER, reset REAL);
    ''')
    try:
        with db:
            yield db
    finally:
        db.close()


def valid_email(email):
    return bool(re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email)) and len(email) <= 254


def digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


def authenticate(email, password, register=False, name=''):
    email = email.strip().lower()
    if not valid_email(email):
        raise ValueError('Enter a valid email address.')
    if len(password) > 128 or (register and len(password) < 12):
        raise ValueError('Use a password between 12 and 128 characters.')
    with connect() as db:
        attempt = db.execute('SELECT * FROM attempts WHERE email=?', (email,)).fetchone()
        if attempt and attempt['reset'] > time.time() and attempt['count'] >= 8:
            raise ValueError('Too many attempts. Try again in 15 minutes.')
        if register:
            if not name.strip():
                raise ValueError('Enter your name.')
            try:
                db.execute('INSERT INTO users(email,password,profile) VALUES(?,?,?)',
                           (email, HASHER.hash(password), json.dumps({'email': email, 'full_name': name.strip()})))
            except sqlite3.IntegrityError:
                raise ValueError('Unable to register this email. Try signing in.') from None
        row = db.execute('SELECT * FROM users WHERE email=?', (email,)).fetchone()
        try:
            HASHER.verify(row['password'] if row else HASHER.hash(secrets.token_hex(16)), password)
        except (VerificationError, InvalidHashError):
            count = attempt['count'] + 1 if attempt and attempt['reset'] > time.time() else 1
            db.execute('INSERT OR REPLACE INTO attempts VALUES(?,?,?)', (email, count, time.time()+900))
            db.commit()
            raise ValueError('Invalid email or password.') from None
        if row is None:
            raise ValueError('Invalid email or password.')
        db.execute('DELETE FROM attempts WHERE email=?', (email,))
        token = secrets.token_urlsafe(32)
        db.execute('DELETE FROM sessions WHERE expires<?', (time.time(),))
        db.execute('INSERT INTO sessions VALUES(?,?,?)', (digest(token), row['id'], time.time()+86400))
        return token


def user(token):
    if not token:
        raise ValueError('Please sign in to continue.')
    with connect() as db:
        row = db.execute('SELECT users.* FROM users JOIN sessions ON users.id=sessions.user_id WHERE token=? AND expires>?',
                         (digest(token), time.time())).fetchone()
    if row is None:
        raise ValueError('Your session has expired. Please sign in.')
    return dict(row)


def save(token, column, value):
    if column not in ('profile', 'documents', 'results'):
        raise ValueError('Invalid storage field')
    account = user(token)
    with connect() as db:
        db.execute(f'UPDATE users SET {column}=? WHERE id=?', (json.dumps(value), account['id']))


def logout(token):
    with connect() as db:
        db.execute('DELETE FROM sessions WHERE token=?', (digest(token),))
