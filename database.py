import sqlite3
import hashlib

DATABASE = "eduai.db"


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

    return hashlib.sha256(
        password.encode("utf-8")
    ).hexdigest()


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

    connection = get_connection()
    cursor = connection.cursor()

    hashed_password = hash_password(password)

    cursor.execute("""
        SELECT id, name, email, username
        FROM users
        WHERE username = ?
        AND password = ?
    """, (
        username,
        hashed_password
    ))

    user = cursor.fetchone()

    connection.close()

    return user


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