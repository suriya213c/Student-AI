import hashlib
import hmac
import re
import secrets
import sqlite3
from contextlib import closing

DATABASE = "eduai.db"
_PASSWORD_HASH_PREFIX = "pbkdf2_sha256"
_PASSWORD_HASH_ITERATIONS = 600_000
_MIN_PASSWORD_HASH_ITERATIONS = 100_000
_MAX_PASSWORD_HASH_ITERATIONS = 2_000_000


def get_connection():
    return sqlite3.connect(DATABASE)


def create_table():

    connection = get_connection()
    cursor = connection.cursor()

    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    """)

    # Quiz results table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS quiz_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subject TEXT NOT NULL,
            topic TEXT NOT NULL,
            score INTEGER NOT NULL,
            total_questions INTEGER NOT NULL,
            percentage REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    connection.commit()
    connection.close()


def hash_password(password):
    salt = secrets.token_bytes(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        _PASSWORD_HASH_ITERATIONS,
    )
    return (
        f"{_PASSWORD_HASH_PREFIX}${_PASSWORD_HASH_ITERATIONS}$"
        f"{salt.hex()}${password_hash.hex()}"
    )


def _verify_password(password, stored_hash):
    """Return whether a password matches and whether its hash needs migration."""

    if not isinstance(stored_hash, str):
        return False, False

    parts = stored_hash.split("$")
    if len(parts) == 4 and parts[0] == _PASSWORD_HASH_PREFIX:
        try:
            iterations = int(parts[1])
            salt = bytes.fromhex(parts[2])
            expected_hash = bytes.fromhex(parts[3])
        except ValueError:
            return False, False

        if (
            not _MIN_PASSWORD_HASH_ITERATIONS <= iterations <= _MAX_PASSWORD_HASH_ITERATIONS
            or len(salt) < 16
            or len(expected_hash) != hashlib.sha256().digest_size
        ):
            return False, False

        actual_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            iterations,
        )
        return hmac.compare_digest(actual_hash, expected_hash), False

    if re.fullmatch(r"[0-9a-f]{64}", stored_hash):
        legacy_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
        return hmac.compare_digest(legacy_hash, stored_hash), True

    return False, False


def verify_password(password, stored_hash):
    return _verify_password(password, stored_hash)[0]


def register_user(
    name,
    email,
    username,
    password
):

    connection = get_connection()
    cursor = connection.cursor()

    hashed_password = hash_password(password)

    try:

        cursor.execute("""
            INSERT INTO users
            (name, email, username, password)
            VALUES (?, ?, ?, ?)
        """, (
            name,
            email,
            username,
            hashed_password
        ))

        connection.commit()
        connection.close()

        return True, "Account created successfully!"

    except sqlite3.IntegrityError:

        connection.close()

        return False, "Username or email already exists."


def login_user(
    username,
    password
):
    with closing(get_connection()) as connection:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT id, name, email, username, password
            FROM users
            WHERE username = ?
        """, (username,))
        user = cursor.fetchone()

        if user is None:
            return None

        is_valid, needs_migration = _verify_password(password, user[4])
        if not is_valid:
            return None

        if needs_migration:
            cursor.execute(
                "UPDATE users SET password = ? WHERE id = ? AND password = ?",
                (hash_password(password), user[0], user[4]),
            )
            connection.commit()

        return user[:4]


def save_quiz_result(
    user_id,
    subject,
    topic,
    score,
    total_questions
):

    connection = get_connection()
    cursor = connection.cursor()

    percentage = (
        score / total_questions
    ) * 100

    cursor.execute("""
        INSERT INTO quiz_results
        (
            user_id,
            subject,
            topic,
            score,
            total_questions,
            percentage
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        subject,
        topic,
        score,
        total_questions,
        percentage
    ))

    connection.commit()
    connection.close()


def get_quiz_results(user_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            subject,
            topic,
            score,
            total_questions,
            percentage,
            created_at
        FROM quiz_results
        WHERE user_id = ?
        ORDER BY created_at ASC
    """, (user_id,))

    results = cursor.fetchall()

    connection.close()

    return results

def save_attendance(
    user_id,
    subject,
    total_classes,
    attended_classes
):

    connection = get_connection()
    cursor = connection.cursor()

    if total_classes <= 0:
        connection.close()
        return False

    percentage = (
        attended_classes / total_classes
    ) * 100

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subject TEXT NOT NULL,
            total_classes INTEGER NOT NULL,
            attended_classes INTEGER NOT NULL,
            percentage REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    cursor.execute("""
        INSERT INTO attendance
        (
            user_id,
            subject,
            total_classes,
            attended_classes,
            percentage
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        user_id,
        subject,
        total_classes,
        attended_classes,
        percentage
    ))

    connection.commit()
    connection.close()

    return True


def get_attendance(user_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            subject,
            total_classes,
            attended_classes,
            percentage,
            created_at
        FROM attendance
        WHERE user_id = ?
        ORDER BY subject
    """, (user_id,))

    results = cursor.fetchall()

    connection.close()

    return results