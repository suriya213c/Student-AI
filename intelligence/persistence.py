"""SQLite persistence for adaptive learner mastery."""

from database import get_connection
from intelligence.learner_model import BayesianKnowledgeTracer


def initialize_learning_tables():
    """Create the additive learner mastery table if it does not exist."""
    connection = get_connection()
    try:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS learner_mastery (
                user_id INTEGER NOT NULL,
                subject TEXT NOT NULL,
                topic TEXT NOT NULL,
                mastery REAL NOT NULL DEFAULT 0.2,
                attempts INTEGER NOT NULL DEFAULT 0,
                correct_answers INTEGER NOT NULL DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, subject, topic),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        connection.commit()
    finally:
        connection.close()


def get_topic_mastery(user_id, subject, topic):
    """Return saved topic mastery, or the initial mastery for a new topic."""
    initialize_learning_tables()
    connection = get_connection()
    try:
        row = connection.execute("""
            SELECT mastery
            FROM learner_mastery
            WHERE user_id = ? AND subject = ? AND topic = ?
        """, (user_id, subject, topic)).fetchone()

        if row is None:
            return BayesianKnowledgeTracer().initial_mastery()

        return float(row[0])
    finally:
        connection.close()


def record_quiz_mastery(user_id, subject, topic, score, total_questions):
    """Update topic mastery using an aggregate quiz score."""
    if not isinstance(total_questions, int) or total_questions <= 0:
        raise ValueError("total_questions must be a positive integer")

    if not isinstance(score, int) or not 0 <= score <= total_questions:
        raise ValueError("score must be between zero and total_questions")

    subject = str(subject).strip()
    topic = str(topic).strip()

    if not subject or not topic:
        raise ValueError("Subject and topic cannot be empty")

    initialize_learning_tables()
    connection = get_connection()
    tracer = BayesianKnowledgeTracer()

    try:
        connection.execute("BEGIN IMMEDIATE")

        row = connection.execute("""
            SELECT mastery, attempts, correct_answers
            FROM learner_mastery
            WHERE user_id = ? AND subject = ? AND topic = ?
        """, (user_id, subject, topic)).fetchone()

        if row:
            mastery, attempts, correct_answers = (
                float(row[0]), int(row[1]), int(row[2])
            )
        else:
            mastery = tracer.initial_mastery()
            attempts = 0
            correct_answers = 0

        # Aggregate scores do not reveal the exact answer sequence.
        # Apply the observed correct and incorrect counts consistently.
        for _ in range(score):
            mastery = tracer.update(mastery, True)

        for _ in range(total_questions - score):
            mastery = tracer.update(mastery, False)

        attempts += total_questions
        correct_answers += score

        connection.execute("""
            INSERT INTO learner_mastery
                (user_id, subject, topic, mastery, attempts,
                 correct_answers, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id, subject, topic) DO UPDATE SET
                mastery = excluded.mastery,
                attempts = excluded.attempts,
                correct_answers = excluded.correct_answers,
                updated_at = CURRENT_TIMESTAMP
        """, (
            user_id, subject, topic, mastery, attempts, correct_answers
        ))

        connection.commit()
        return {
            "mastery": mastery,
            "attempts": attempts,
            "correct_answers": correct_answers,
            "accuracy": correct_answers / attempts if attempts else 0.0,
        }
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def get_all_mastery(user_id):
    """Return mastery records for one student."""
    initialize_learning_tables()
    connection = get_connection()
    try:
        rows = connection.execute("""
            SELECT subject, topic, mastery, attempts,
                   correct_answers, updated_at
            FROM learner_mastery
            WHERE user_id = ?
            ORDER BY subject, topic
        """, (user_id,)).fetchall()

        return [
            {
                "subject": row[0],
                "topic": row[1],
                "mastery": float(row[2]),
                "attempts": int(row[3]),
                "correct_answers": int(row[4]),
                "updated_at": row[5],
            }
            for row in rows
        ]
    finally:
        connection.close()
