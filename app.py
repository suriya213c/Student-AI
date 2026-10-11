import streamlit as st
from abc import ABC, abstractmethod
from datetime import datetime
from pypdf import PdfReader

from database import (
    create_table,
    register_user,
    login_user,
    save_quiz_result,
    get_quiz_results,
    save_attendance,
    get_attendance
)

from Pages.Attendance import show_attendance
from Pages.performance import show_performance
from AI.resources import analyze_resource
from AI.Tutor import get_ai_response
from AI.summarizer import extract_pdf_text, summarize_notes
from AI.quiz_generator import generate_quiz
from AI.predictor import calculate_academic_risk, predict_next_score
from AI.learning_plan import generate_learning_plan

def show_performance(user_id):
    """Render useful quiz performance analytics for a student."""
    results = get_quiz_results(user_id) or []
    valid_results = [row for row in results if len(row) > 4]

    st.subheader("Quiz Performance")
    if not valid_results:
        st.info("No quiz results are available yet. Complete a quiz to see your progress.")
        return

    scores = [float(row[4]) for row in valid_results]
    average_score = sum(scores) / len(scores)
    best_score = max(scores)
    latest_score = scores[-1]

    metric_columns = st.columns(3)
    metric_columns[0].metric("Quiz Average", f"{average_score:.1f}%")
    metric_columns[1].metric("Best Score", f"{best_score:.1f}%")
    metric_columns[2].metric("Latest Score", f"{latest_score:.1f}%")

    st.subheader("Score Trend")
    st.line_chart({"Quiz": list(range(1, len(scores) + 1)), "Score (%)": scores}, x="Quiz", y="Score (%)")

    subject_scores = {}
    for row in valid_results:
        subject_scores.setdefault(str(row[0]), []).append(float(row[4]))
    subject_averages = {
        subject: sum(subject_marks) / len(subject_marks)
        for subject, subject_marks in subject_scores.items()
    }
    if subject_averages:
        st.subheader("Average by Subject")
        st.bar_chart(subject_averages)

    st.subheader("Recent Quiz Results")
    for row in reversed(valid_results[-5:]):
        subject = row[0] or "Unspecified subject"
        topic = row[1] or "Unspecified topic"
        st.write(f"**{subject} — {topic}:** {float(row[4]):.1f}% ({row[2]}/{row[3]})")
def generate_learning_plan(quiz_results, attendance_percentage, risk_level):
    """Create a simple AI-style study plan from academic data."""
    quiz_average = 0
    if quiz_results:
        scores = [row[4] for row in quiz_results if len(row) > 4]
        if scores:
            quiz_average = sum(scores) / len(scores)

    risk_label = str(risk_level or "N/A").upper()
    actions = [
        "## Personalized Study Plan",
        f"- Quiz average: {quiz_average:.1f}%",
        f"- Attendance: {attendance_percentage:.1f}%",
        f"- Risk level: {risk_label}",
        "- Review your weakest topics first and spend extra time on practice questions.",
        "- Schedule short daily revision sessions to improve retention and confidence.",
        "- Attend class consistently and complete all assigned tasks on time.",
    ]

    if risk_label in {"HIGH", "CRITICAL"}:
        actions.append("- Prioritize foundational concepts and seek support from your teacher or tutor.")
    elif risk_label == "MEDIUM":
        actions.append("- Maintain a steady study routine and focus on improving missed concepts.")
    else:
        actions.append("- Keep up the current pace and challenge yourself with advanced practice exercises.")

    return "<br>".join(actions)


class BaseUser(ABC):
    """Contract for application users."""

    @abstractmethod
    def get_id(self):
        raise NotImplementedError

    @abstractmethod
    def get_name(self):
        raise NotImplementedError

    @abstractmethod
    def get_email(self):
        raise NotImplementedError

    @abstractmethod
    def get_username(self):
        raise NotImplementedError

    @abstractmethod
    def get_password(self):
        raise NotImplementedError

    @abstractmethod
    def validate_password(self, password):
        raise NotImplementedError

    @abstractmethod
    def to_dict(self):
        raise NotImplementedError


class Summary(ABC):
    """Contract for AI-generated study summaries."""

    @abstractmethod
    def get_text(self):
        raise NotImplementedError

    @abstractmethod
    def get_title(self):
        raise NotImplementedError

    @abstractmethod
    def get_source(self):
        raise NotImplementedError

    @abstractmethod
    def get_created_at(self):
        raise NotImplementedError

    @abstractmethod
    def preview(self, max_length=180):
        raise NotImplementedError

    @abstractmethod
    def is_empty(self):
        raise NotImplementedError

    @abstractmethod
    def to_dict(self):
        raise NotImplementedError


class summary(Summary):
    """Concrete summary model used for notes and AI-generated content."""

    def __init__(
        self,
        text="",
        title="Study Summary",
        source="Uploaded Material",
        created_at=None,
    ):
        self.text = text or ""
        self.title = title or "Study Summary"
        self.source = source or "Uploaded Material"
        self.created_at = created_at or datetime.now().isoformat(timespec="seconds")

    def get_text(self):
        return self.text

    def get_title(self):
        return self.title

    def get_source(self):
        return self.source

    def get_created_at(self):
        return self.created_at

    def preview(self, max_length=180):
        cleaned = (self.text or "").strip()
        if not cleaned:
            return ""
        if len(cleaned) <= max_length:
            return cleaned
        trimmed = cleaned[:max_length].rsplit(" ", 1)[0]
        return f"{trimmed}..." if trimmed else f"{cleaned[:max_length]}..."

    def is_empty(self):
        return not bool((self.text or "").strip())

    def to_dict(self):
        return {
            "title": self.title,
            "source": self.source,
            "text": self.text,
            "created_at": self.created_at,
            "preview": self.preview(),
        }

    def __str__(self):
        return self.text

    @classmethod
    def from_text(cls, text, title="Study Summary", source="Uploaded Material"):
        return cls(text=text, title=title, source=source)


class user(BaseUser):
    """Concrete student model used across the app."""

    def __init__(
        self,
        user_id=None,
        name="",
        email="",
        username="",
        password="",
    ):
        self.user_id = user_id
        self.name = name
        self.email = email
        self.username = username
        self.password = password

    def get_id(self):
        return self.user_id

    def get_name(self):
        return self.name

    def get_email(self):
        return self.email

    def get_username(self):
        return self.username

    def get_password(self):
        return self.password

    def validate_password(self, password):
        return isinstance(password, str) and bool(password.strip()) and self.password == password

    def display_name(self):
        return self.name or self.username or "Student"

    def to_dict(self):
        return {
            "id": self.user_id,
            "name": self.name,
            "email": self.email,
            "username": self.username,
            "display_name": self.display_name(),
        }

    def as_session_tuple(self):
        return (
            self.user_id,
            self.name,
            self.email,
            self.username,
            self.password,
        )

    @classmethod
    def from_row(cls, row):
        if not row:
            return None

        if len(row) >= 5:
            return cls(
                user_id=row[0],
                name=row[1],
                email=row[2],
                username=row[3],
                password=row[4],
            )

        if len(row) >= 4:
            return cls(
                user_id=row[0],
                name=row[1],
                email=row[2],
                username=row[3],
            )

        return cls(user_id=row[0])

    @classmethod
    def login(cls, username, password):
        record = login_user(username, password)
        return cls.from_row(record) if record else None

    @classmethod
    def register(cls, name, email, username, password):
        success, message = register_user(name, email, username, password)
        if not success:
            return None, message

        record = login_user(username, password)
        if record:
            return cls.from_row(record), message

        return cls(
            name=name,
            email=email,
            username=username,
            password=password,
        ), message

    def update_profile(self, **kwargs):
        if "name" in kwargs:
            self.name = kwargs["name"]
        if "email" in kwargs:
            self.email = kwargs["email"]
        if "username" in kwargs:
            self.username = kwargs["username"]
        if "password" in kwargs:
            self.password = kwargs["password"]
        return self


class Attendance(ABC):
    """Represents a student's attendance record for a single subject."""

    def __init__(
        self,
        user_id=None,
        subject="",
        total_classes=0,
        attended_classes=0,
        recorded_at=None,
    ):
        self.user_id = user_id
        self.subject = subject or "General"
        self.total_classes = max(int(total_classes or 0), 0)
        self.attended_classes = max(int(attended_classes or 0), 0)
        self.recorded_at = recorded_at or datetime.now().isoformat(timespec="seconds")

    def get_user_id(self):
        return self.user_id

    def get_subject(self):
        return self.subject

    def get_total_classes(self):
        return self.total_classes

    def get_attended_classes(self):
        return self.attended_classes

    def get_attendance_percentage(self):
        if self.total_classes <= 0:
            return 0.0
        return (self.attended_classes / self.total_classes) * 100

    def get_recorded_at(self):
        return self.recorded_at

    def mark_present(self, count=1):
        delta = max(int(count or 0), 0)
        self.attended_classes += delta
        self.total_classes += delta
        return self

    def mark_absent(self, count=1):
        delta = max(int(count or 0), 0)
        self.total_classes += delta
        return self

    def update(self, subject=None, total_classes=None, attended_classes=None):
        if subject is not None:
            self.subject = str(subject).strip() or self.subject
        if total_classes is not None:
            self.total_classes = max(int(total_classes), 0)
        if attended_classes is not None:
            self.attended_classes = min(max(int(attended_classes), 0), self.total_classes)
        return self

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "subject": self.subject,
            "total_classes": self.total_classes,
            "attended_classes": self.attended_classes,
            "attendance_percentage": self.get_attendance_percentage(),
            "recorded_at": self.recorded_at,
        }

    def __str__(self):
        return (
            f"{self.subject}: {self.attended_classes}/{self.total_classes} "
            f"({self.get_attendance_percentage():.1f}%)"
        )

    @classmethod
    def from_row(cls, row):
        if not row:
            return None

        if len(row) >= 5:
            user_id, subject, total_classes, attended_classes, recorded_at = row[:5]
            return cls(
                user_id=user_id,
                subject=subject,
                total_classes=total_classes,
                attended_classes=attended_classes,
                recorded_at=recorded_at,
            )

        if len(row) >= 4:
            user_id, subject, total_classes, attended_classes = row[:4]
            return cls(
                user_id=user_id,
                subject=subject,
                total_classes=total_classes,
                attended_classes=attended_classes,
            )

        return cls(user_id=row[0] if len(row) > 0 else None)


# ==========================================
# PAGE CONFIGURATION
# ==========================================

st.set_page_config(
    page_title="EduAI",
    page_icon="🎓",
    layout="centered"
)

# ==========================================
# DATABASE
# ==========================================

create_table()

# ==========================================
# SESSION STATE
# ==========================================

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "show_performance" not in st.session_state:
    st.session_state.show_performance = False

if "active_page" not in st.session_state:
    st.session_state.active_page = "Dashboard"

if "show_attendance" not in st.session_state:
    st.session_state.show_attendance = False

if "show_risk" not in st.session_state:
    st.session_state.show_risk = False

if "show_prediction" not in st.session_state:
    st.session_state.show_prediction = False

if "show_learning_plan" not in st.session_state:
    st.session_state.show_learning_plan = False

if "user" not in st.session_state:
    st.session_state.user = None

if "show_login" not in st.session_state:
    st.session_state.show_login = False

if "show_register" not in st.session_state:
    st.session_state.show_register = False


# ==========================================
# CSS
# ==========================================

st.markdown("""
<style>

.main {
    background-color: #f5f7fb;
}

/* Main title */

.eduai-title {
    font-size: 38px;
    font-weight: 800;
    color: #1f2937;
    margin-bottom: 5px;
}

.eduai-subtitle {
    font-size: 16px;
    color: #6b7280;
    margin-bottom: 25px;
}

/* Cards */

.dashboard-card {
    background: white;
    padding: 22px;
    border-radius: 16px;
    border: 1px solid #e5e7eb;
    margin-bottom: 18px;
}

.dashboard-card:hover {
    border-color: #c7d2fe;
}

/* Metric cards */

.metric-card {
    background: white;
    padding: 20px;
    border-radius: 14px;
    border: 1px solid #e5e7eb;
    text-align: center;
}

/* Section headers */

.section-title {
    font-size: 24px;
    font-weight: 700;
    color: #111827;
    margin-top: 20px;
    margin-bottom: 15px;
}

/* Welcome box */

.welcome-box {
    background: white;
    padding: 25px;
    border-radius: 16px;
    border: 1px solid #e5e7eb;
    margin-bottom: 25px;
}

/* Sidebar */

[data-testid="stSidebar"] {
    background-color: #111827;
}

[data-testid="stSidebar"] * {
    color: white;
}

/* Buttons */

.stButton > button {
    border-radius: 10px;
    min-height: 42px;
    font-weight: 600;
}

/* Hide Streamlit footer */

footer {
    visibility: hidden;
}

</style>
""", unsafe_allow_html=True)
# ==========================================
# STUDENT DASHBOARD
# ==========================================

def show_dashboard():

    # --------------------------------------
    # SAFETY CHECK
    # --------------------------------------

    user = st.session_state.get("user")

    if user is None:
        st.warning("Please login to access your dashboard.")
        st.stop()

    user_id = user[0]
    user_name = user[1] if len(user) > 1 else "Student"

    # --------------------------------------
    # GET ACADEMIC DATA
    # --------------------------------------

    quiz_results = get_quiz_results(user_id) or []
    attendance_results = get_attendance(user_id) or []

    # --------------------------------------
    # CALCULATE QUIZ AVERAGE
    # --------------------------------------

    valid_quiz_results = [
        row for row in quiz_results
        if len(row) > 4
    ]

    if valid_quiz_results:

        quiz_scores = []

        for row in valid_quiz_results:
            try:
                quiz_scores.append(float(row[4]))
            except (ValueError, TypeError):
                pass

        if quiz_scores:
            quiz_average = sum(quiz_scores) / len(quiz_scores)
        else:
            quiz_average = 0.0

    else:
        quiz_average = 0.0

    # --------------------------------------
    # CALCULATE ATTENDANCE
    # --------------------------------------

    total_classes = 0
    attended_classes = 0

    for row in attendance_results:

        if len(row) >= 3:

            try:
                total_classes += int(row[1])
                attended_classes += int(row[2])
            except (ValueError, TypeError):
                pass

    if total_classes > 0:
        attendance_average = (
            attended_classes / total_classes
        ) * 100
    else:
        attendance_average = 0.0

    # --------------------------------------
    # CALCULATE ACADEMIC RISK
    # --------------------------------------

    try:

        risk = calculate_academic_risk(
            attendance_average,
            quiz_average
        )

    except Exception:

        risk = {
            "risk_level": "N/A",
            "academic_score": 0
        }

    if not isinstance(risk, dict):
        risk = {
            "risk_level": "N/A",
            "academic_score": 0
        }

    risk_level = risk.get(
        "risk_level",
        "N/A"
    )

    # ======================================
    # SIDEBAR NAVIGATION
    # ======================================

    with st.sidebar:

        st.markdown(
            """
            <h1 style="text-align:center;">
                🎓 EduAI
            </h1>
            """,
            unsafe_allow_html=True
        )

        st.markdown(
            f"""
            <div style="
                text-align:center;
                padding:10px;
                margin-bottom:15px;
            ">
                👋 Welcome<br>
                <b>{user_name}</b>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.divider()

        st.caption("MAIN MENU")

        if st.button(
            "🏠 Dashboard",
            width="stretch"
        ):
            st.session_state.active_page = "Dashboard"
            st.rerun()

        if st.button(
            "🤖 AI Tutor",
            width="stretch"
        ):
            st.session_state.active_page = "AI Tutor"
            st.rerun()

        if st.button(
            "📄 Notes Summarizer",
            width="stretch"
        ):
            st.session_state.active_page = "Notes"
            st.rerun()

        if st.button(
            "📝 Smart Quiz",
            width="stretch"
        ):
            st.session_state.active_page = "Quiz"
            st.rerun()

        if st.button(
            "📊 Performance",
            width="stretch"
        ):
            st.session_state.active_page = "Performance"
            st.rerun()

        if st.button(
            "📅 Attendance",
            width="stretch"
        ):
            st.session_state.active_page = "Attendance"
            st.rerun()

        if st.button(
            "⚠️ Academic Risk",
            width="stretch"
        ):
            st.session_state.active_page = "Risk"
            st.rerun()

        if st.button(
            "🔮 Prediction",
            width="stretch"
        ):
            st.session_state.active_page = "Prediction"
            st.rerun()

        if st.button(
            "🎯 Learning Plan",
            width="stretch"
        ):
            st.session_state.active_page = "Learning Plan"
            st.rerun()

        if st.button(
            "🌐 Study Resources",
            use_container_width=True
        ):
            st.session_state.active_page = "Resources"
            st.rerun()

        st.divider()

        if st.button(
            "🚪 Logout",
            width="stretch"
        ):
            st.session_state.logged_in = False
            st.session_state.user = None
            st.session_state.active_page = "Dashboard"

            # Clear quiz-related session data
            for key in [
                "quiz",
                "quiz_answers",
                "quiz_score",
                "quiz_submitted",
                "quiz_subject_value",
                "quiz_topic_value"
            ]:
                st.session_state.pop(key, None)

            st.rerun()

    # ======================================
# PAGE ROUTER
# ======================================

active_page = st.session_state.get(
    "active_page",
    "Dashboard"
)


# ==========================================
# ADVANCED STUDY RESOURCES
# ==========================================

if active_page == "Resources":

    st.title("🌐 Advanced Study Resources")

    st.write(
        "Add YouTube videos, Google Drive files "
        "or online study resources."
    )

    st.divider()

    resource_url = st.text_input(
        "🔗 Enter Resource URL",
        placeholder=(
            "Paste YouTube or Google Drive URL here..."
        ),
        key="resource_url"
    )

    if st.button(
        "🔍 Analyze Resource",
        use_container_width=True,
        type="primary"
    ):

        if not resource_url.strip():

            st.warning(
                "Please enter a resource URL."
            )

        else:

            with st.spinner(
                "🤖 EduAI is analyzing the resource..."
            ):

                resource = analyze_resource(
                    resource_url
                )

            if not resource:

                st.error(
                    "Unable to analyze this resource."
                )

            else:

                resource_type = resource.get(
                    "type",
                    "Unknown"
                )

                st.success(
                    f"Resource detected: {resource_type}"
                )

                # ------------------------------
                # YOUTUBE
                # ------------------------------

                if resource_type == "YouTube":

                    st.subheader(
                        "▶️ YouTube Learning Resource"
                    )

                    st.video(
                        resource["watch_url"]
                    )

                    st.info(
                        "YouTube video loaded successfully."
                    )

                # ------------------------------
                # GOOGLE DRIVE
                # ------------------------------

                elif resource_type == "Google Drive":

                    st.subheader(
                        "📁 Google Drive Resource"
                    )

                    st.write(
                        "Google Drive URL detected."
                    )

                    st.link_button(
                        "📂 Open Google Drive File",
                        resource["url"],
                        use_container_width=True
                    )

                # ------------------------------
                # WEB RESOURCE
                # ------------------------------

                else:

                    st.subheader(
                        "🌐 Web Study Resource"
                    )

                    st.link_button(
                        "🔗 Open Resource",
                        resource["url"],
                        use_container_width=True
                    )

                    text = resource.get(
                        "text",
                        ""
                    )

                    if text.startswith(
                        "RESOURCE_ERROR"
                    ):

                        st.error(text)

                    elif text:

                        st.text_area(
                            "Extracted Content",
                            text[:10000],
                            height=300
                        )

                    else:

                        st.warning(
                            "No readable content found."
                        )

    st.stop()


# ======================================
# AI TUTOR
# ======================================

if active_page == "AI Tutor":

    st.title("🤖 AI Tutor")

    st.write(
        "Ask EduAI any academic question "
        "and get an AI-powered explanation."
    )

    st.divider()

    st.markdown(
        """
        <div class="dashboard-card">
            <h3>💡 Ask Your Question</h3>
            <p>
            Get simple, detailed and
            student-friendly explanations
            for your academic topics.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    question = st.text_area(
        "Your Question",
        placeholder=(
            "Example: Explain DSB-SC modulation "
            "in simple terms."
        ),
        height=180,
        key="ai_tutor_question"
    )

    if st.button(
        "✨ Ask EduAI",
        width="stretch",
        type="primary"
    ):

        if not question.strip():

            st.warning(
                "Please enter a question first."
            )

        else:

            with st.spinner(
                "🤖 EduAI is thinking..."
            ):

                try:
                    answer = get_ai_response(
                        question
                    )

                    if answer:
                        st.markdown(
                            "### 🤖 EduAI Answer"
                        )

                        st.markdown(answer)

                    else:
                        st.warning(
                            "No answer was generated."
                        )

                except Exception as e:

                    st.error(
                        f"Unable to get AI response: {e}"
                    )

    st.stop()

    # ======================================
    # NOTES SUMMARIZER
    # ======================================

    if active_page == "Notes":

        st.title("📄 Notes Summarizer")

        st.write(
            "Upload your study material and "
            "generate an AI-powered summary."
        )

        st.divider()

        uploaded_file = st.file_uploader(
            "Upload PDF",
            type=["pdf"],
            key="notes_pdf_page"
        )

        if uploaded_file:

            st.success(
                f"Uploaded: {uploaded_file.name}"
            )

            if st.button(
                "✨ Summarize Notes",
                width="stretch",
                type="primary"
            ):

                with st.spinner(
                    "📖 EduAI is reading your notes..."
                ):

                    try:

                        pdf_text = extract_pdf_text(
                            uploaded_file
                        )

                    except Exception as e:

                        st.error(
                            f"Could not read PDF: {e}"
                        )
                        st.stop()

                if not pdf_text:

                    st.warning(
                        "No readable text was found in this PDF."
                    )

                elif pdf_text.startswith(
                    "PDF_ERROR"
                ):

                    st.error(pdf_text)

                else:

                    with st.spinner(
                        "🤖 EduAI is generating your summary..."
                    ):

                        try:

                            summary_text = summarize_notes(
                                pdf_text
                            )

                        except Exception as e:

                            st.error(
                                f"Could not generate summary: {e}"
                            )
                            st.stop()

                    st.divider()

                    st.subheader(
                        "🤖 EduAI Notes Summary"
                    )

                    if summary_text:

                        st.markdown(summary_text)

                    else:

                        st.warning(
                            "No summary was generated."
                        )

        else:

            st.info(
                "Upload a PDF file to generate a summary."
            )

        st.stop()

    # ======================================
    # SMART QUIZ
    # ======================================

    if active_page == "Quiz":

        st.title("📝 Smart Quiz")

        st.write(
            "Generate AI-powered quizzes "
            "and test your knowledge."
        )

        st.divider()

        subject = st.text_input(
            "Subject",
            placeholder=(
                "Example: Communication Systems"
            ),
            key="quiz_page_subject"
        )

        topic = st.text_input(
            "Topic",
            placeholder=(
                "Example: AM Modulation"
            ),
            key="quiz_page_topic"
        )

        number_of_questions = st.selectbox(
            "Number of Questions",
            [5, 10, 15],
            key="quiz_page_number"
        )

        if st.button(
            "✨ Generate Quiz",
            width="stretch",
            type="primary"
        ):

            if not subject.strip():

                st.warning(
                    "Please enter the subject."
                )

            elif not topic.strip():

                st.warning(
                    "Please enter the topic."
                )

            else:

                with st.spinner(
                    "🤖 EduAI is creating your quiz..."
                ):

                    try:

                        quiz = generate_quiz(
                            subject,
                            topic,
                            number_of_questions
                        )

                    except Exception as e:

                        quiz = None

                        st.error(
                            f"Quiz generation failed: {e}"
                        )

                if quiz:

                    st.session_state.quiz = quiz

                    st.session_state.quiz_subject_value = (
                        subject
                    )

                    st.session_state.quiz_topic_value = (
                        topic
                    )

                    st.session_state.quiz_submitted = False

                    st.session_state.quiz_answers = {}

                    st.success(
                        f"Quiz generated with "
                        f"{len(quiz)} questions!"
                    )

                else:

                    st.error(
                        "Unable to generate the quiz. "
                        "Please try again."
                    )

        # ----------------------------------
        # DISPLAY GENERATED QUIZ
        # ----------------------------------

        if st.session_state.get(
            "quiz"
        ):

            st.divider()

            st.subheader(
                "📝 Your AI Generated Quiz"
            )

            quiz = st.session_state.quiz

            if "quiz_answers" not in st.session_state:
                st.session_state.quiz_answers = {}

            for i, question in enumerate(quiz):

                st.markdown(
                    f"### Question {i + 1}"
                )

                st.write(
                    question.get(
                        "question",
                        "Question unavailable"
                    )
                )

                options = question.get(
                    "options",
                    []
                )

                if options:

                    answer = st.radio(
                        "Select your answer:",
                        options,
                        key=f"quiz_page_answer_{i}",
                        index=None
                    )

                    st.session_state.quiz_answers[i] = (
                        answer
                    )

            st.divider()

            if st.button(
                "📊 Submit Quiz",
                width="stretch",
                type="primary"
            ):

                score = 0
                total = len(quiz)

                for i, question in enumerate(quiz):

                    user_answer = (
                        st.session_state.quiz_answers.get(
                            i
                        )
                    )

                    correct_answer = question.get(
                        "answer"
                    )

                    if (
                        user_answer is not None
                        and user_answer == correct_answer
                    ):
                        score += 1

                if total > 0:

                    percentage = (
                        score / total
                    ) * 100

                else:

                    percentage = 0

                try:

                    current_user = st.session_state.get("user")
                    current_user_id = None

                    if current_user is not None:
                        if isinstance(current_user, (list, tuple)):
                            current_user_id = current_user[0] if len(current_user) > 0 else None
                        elif hasattr(current_user, "get_id"):
                            current_user_id = current_user.get_id()

                    if current_user_id is not None:
                        save_quiz_result(
                            current_user_id,
                            st.session_state.get(
                                "quiz_subject_value",
                                ""
                            ),
                            st.session_state.get(
                                "quiz_topic_value",
                                ""
                            ),
                            score,
                            total
                        )
                    else:
                        st.warning("Unable to save the quiz result because no active user was found.")

                except Exception as e:

                    st.error(
                        f"Could not save quiz result: {e}"
                    )

                st.session_state.quiz_score = score
                st.session_state.quiz_submitted = True

            # ----------------------------------
            # QUIZ RESULT
            # ----------------------------------

            if st.session_state.get(
                "quiz_submitted",
                False
            ):

                score = st.session_state.get(
                    "quiz_score",
                    0
                )

                total = len(quiz)

                if total > 0:

                    percentage = (
                        score / total
                    ) * 100

                else:

                    percentage = 0

                st.divider()

                st.subheader(
                    "🏆 Quiz Result"
                )

                col1, col2, col3 = st.columns(3)

                with col1:

                    st.metric(
                        "Score",
                        f"{score}/{total}"
                    )

                with col2:

                    st.metric(
                        "Percentage",
                        f"{percentage:.1f}%"
                    )

                with col3:

                    if percentage >= 80:
                        status = "Excellent"

                    elif percentage >= 60:
                        status = "Good"

                    elif percentage >= 40:
                        status = "Needs Improvement"

                    else:
                        status = "Needs Attention"

                    st.metric(
                        "Performance",
                        status
                    )

        st.stop()

    # ======================================
    # PERFORMANCE
    # ======================================

    if active_page == "Performance":

        st.title("📊 Performance Analytics")

        st.write(
            "Analyze your quiz performance "
            "and learning progress."
        )

        st.divider()

        show_performance(user_id)

        st.stop()

    # ======================================
    # ATTENDANCE
    # ======================================

    if active_page == "Attendance":

        st.title("📅 Attendance")

        st.write(
            "Track your attendance and identify "
            "low-attendance subjects."
        )

        st.divider()

        show_attendance(user_id)

        st.stop()

    # ======================================
    # ACADEMIC RISK
    # ======================================

    if active_page == "Risk":

        st.title("⚠️ Academic Risk Detection")

        st.write(
            "Analyze your attendance and "
            "quiz performance."
        )

        st.divider()

        col1, col2, col3 = st.columns(3)

        with col1:

            st.metric(
                "Quiz Average",
                f"{quiz_average:.1f}%"
            )

        with col2:

            st.metric(
                "Attendance",
                f"{attendance_average:.1f}%"
            )

        with col3:

            academic_score = risk.get(
                "academic_score",
                0
            )

            try:
                academic_score = float(
                    academic_score
                )
            except (ValueError, TypeError):
                academic_score = 0.0

            st.metric(
                "Academic Score",
                f"{academic_score:.1f}%"
            )

        st.divider()

        st.subheader("Risk Level")

        if risk_level == "High Risk":

            st.error(
                f"🔴 {risk_level}"
            )

        elif risk_level == "Medium Risk":

            st.warning(
                f"🟠 {risk_level}"
            )

        else:

            st.success(
                f"🟢 {risk_level}"
            )

        st.stop()

    # ======================================
    # PERFORMANCE PREDICTION
    # ======================================

    if active_page == "Prediction":

        st.title("🔮 AI Performance Prediction")

        st.write(
            "Predict your next quiz performance "
            "using previous results."
        )

        st.divider()

        if not valid_quiz_results:

            st.info(
                "Complete some Smart Quizzes first "
                "to generate a prediction."
            )

        else:

            try:

                predicted_score, trend = (
                    predict_next_score(
                        quiz_results
                    )
                )

                if predicted_score is not None:

                    col1, col2 = st.columns(2)

                    with col1:

                        st.metric(
                            "Predicted Next Quiz Score",
                            f"{float(predicted_score):.1f}%"
                        )

                    with col2:

                        st.metric(
                            "Performance Trend",
                            str(trend)
                        )

                else:

                    st.warning(
                        "Not enough data to predict "
                        "your next score."
                    )

            except Exception as e:

                st.error(
                    f"Prediction failed: {e}"
                )

        st.stop()

    # ======================================
    # PERSONALIZED LEARNING PLAN
    # ======================================

    if active_page == "Learning Plan":

        st.title(
            "🎯 Personalized Learning Plan"
        )

        st.write(
            "Generate a personalized study plan "
            "based on your academic performance."
        )

        st.divider()

        st.markdown(
            """
            <div class="dashboard-card">
                <h3>🧠 AI-Powered Study Planning</h3>
                <p>
                EduAI analyzes your quiz performance,
                attendance and academic risk to create
                a personalized learning plan.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

        col1, col2, col3 = st.columns(3)

        with col1:

            st.metric(
                "Quiz Average",
                f"{quiz_average:.1f}%"
            )

        with col2:

            st.metric(
                "Attendance",
                f"{attendance_average:.1f}%"
            )

        with col3:

            st.metric(
                "Risk Level",
                risk_level
            )

        st.divider()

        if st.button(
            "✨ Generate Learning Plan",
            width="stretch",
            type="primary"
        ):

            with st.spinner(
                "🤖 EduAI is creating your "
                "personalized learning plan..."
            ):

                try:

                    learning_plan = (
                        generate_learning_plan(
                            quiz_results,
                            attendance_average,
                            risk_level
                        )
                    )

                except Exception as e:

                    learning_plan = None

                    st.error(
                        f"Could not generate plan: {e}"
                    )

            if learning_plan:

                st.subheader(
                    "📚 Your Personalized Study Plan"
                )

                st.markdown(
                    f"""
                    <div class="dashboard-card">
                        {learning_plan}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            else:

                st.warning(
                    "EduAI could not generate the "
                    "learning plan right now."
                )

        st.stop()

    # ======================================
    # MAIN DASHBOARD
    # ======================================

    st.markdown(
        f"""
        <div class="welcome-box">
            <h2>Welcome back, {user_name}! 👋</h2>
            <p>
            Continue your learning journey with EduAI.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="section-title">'
        '📊 Academic Overview'
        '</div>',
        unsafe_allow_html=True
    )

    st.caption(
        "AI-Powered Student Learning Platform"
    )

    st.divider()

    # --------------------------------------
    # OVERVIEW CARDS
    # --------------------------------------

    col1, col2, col3 = st.columns(3)

    with col1:

        st.markdown(
            f"""
            <div class="metric-card">
                <h3>📝 Quiz Average</h3>
                <h2>{quiz_average:.1f}%</h2>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col2:

        st.markdown(
            f"""
            <div class="metric-card">
                <h3>📅 Attendance</h3>
                <h2>{attendance_average:.1f}%</h2>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col3:

        st.markdown(
            f"""
            <div class="metric-card">
                <h3>⚠️ Academic Risk</h3>
                <h2>{risk_level}</h2>
            </div>
            """,
            unsafe_allow_html=True
        )

    # --------------------------------------
    # RECENT QUIZ ACTIVITY
    # --------------------------------------

    st.divider()

    st.subheader("📝 Recent Quiz Activity")

    if valid_quiz_results:

        recent_results = valid_quiz_results[-5:]

        for row in reversed(recent_results):

            subject = (
                row[0]
                if len(row) > 0 and row[0]
                else "Subject"
            )

            topic = (
                row[1]
                if len(row) > 1 and row[1]
                else "Topic"
            )

            try:
                score = float(row[4])
            except (ValueError, TypeError):
                score = 0.0

            total = (
                row[3]
                if len(row) > 3
                else 0
            )

            correct = (
                row[2]
                if len(row) > 2
                else 0
            )

            st.markdown(
                f"""
                <div class="dashboard-card">
                    <b>📚 {subject}</b><br>
                    Topic: {topic}<br>
                    Score: {correct}/{total}
                    &nbsp; | &nbsp;
                    Performance: {score:.1f}%
                </div>
                """,
                unsafe_allow_html=True
            )

    else:

        st.info(
            "No quiz activity yet. "
            "Start your first Smart Quiz!"
        )
# ==========================================
# HOME / LOGIN / REGISTER
# ==========================================

def show_home():

    st.markdown(
        '<div class="eduai-title">🎓 EduAI</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="eduai-subtitle">'
        'AI-Powered Student Learning & Academic Support System'
        '</div>',
        unsafe_allow_html=True
    )

    # --------------------------------------
    # MAIN BUTTONS
    # --------------------------------------

    col1, col2, col3 = st.columns(
        [1, 2, 1]
    )

    with col2:

        if st.button(
            "🔐 Login",
            width="stretch"
        ):

            st.session_state.show_login = True
            st.session_state.show_register = False

            st.rerun()

        if st.button(
            "📝 Create Account",
            width="stretch"
        ):

            st.session_state.show_register = True
            st.session_state.show_login = False

            st.rerun()

    # ======================================
    # LOGIN
    # ======================================

    if st.session_state.show_login:

        st.divider()

        st.header("🔐 Student Login")

        username = st.text_input(
            "Username",
            key="login_username"
        )

        password = st.text_input(
            "Password",
            type="password",
            key="login_password"
        )

        if st.button(
            "Login",
            width="stretch",
            type="primary"
        ):

            if not username.strip():

                st.error(
                    "Please enter your username."
                )

            elif not password:

                st.error(
                    "Please enter your password."
                )

            else:

                try:

                    logged_user = login_user(
                        username,
                        password
                    )

                except Exception as e:

                    logged_user = None

                    st.error(
                        f"Login failed: {e}"
                    )

                if logged_user:

                    st.session_state.logged_in = True
                    st.session_state.user = logged_user
                    st.session_state.active_page = "Dashboard"
                    st.session_state.show_login = False
                    st.session_state.show_register = False

                    st.rerun()

                elif logged_user is not None:

                    st.error(
                        "Invalid username or password."
                    )

        st.stop()

    # ======================================
    # REGISTRATION
    # ======================================

    if st.session_state.show_register:

        st.divider()

        st.header(
            "📝 Create Student Account"
        )

        name = st.text_input(
            "Full Name",
            key="register_name"
        )

        email = st.text_input(
            "Email",
            key="register_email"
        )

        username = st.text_input(
            "Create Username",
            key="register_username"
        )

        password = st.text_input(
            "Create Password",
            type="password",
            key="register_password"
        )

        confirm_password = st.text_input(
            "Confirm Password",
            type="password",
            key="confirm_password"
        )

        if st.button(
            "Create Account",
            width="stretch",
            type="primary"
        ):

            if not name.strip():

                st.error(
                    "Please enter your name."
                )

            elif not email.strip():

                st.error(
                    "Please enter your email."
                )

            elif not username.strip():

                st.error(
                    "Please create a username."
                )

            elif not password:

                st.error(
                    "Please create a password."
                )

            elif password != confirm_password:

                st.error(
                    "Passwords do not match."
                )

            elif len(password) < 6:

                st.error(
                    "Password must contain at least 6 characters."
                )

            else:

                try:

                    success, message = register_user(
                        name,
                        email,
                        username,
                        password
                    )

                except Exception as e:

                    success = False
                    message = (
                        f"Registration failed: {e}"
                    )

                if success:

                    st.success(message)

                    st.session_state.show_register = False
                    st.session_state.show_login = True

                    st.rerun()

                else:

                    st.error(message)

        st.stop()

    # ======================================
    # FEATURES
    # ======================================

    st.divider()

    st.markdown(
        """
        <div class="feature">
        🤖 AI Doubt Solver &nbsp; | &nbsp;
        📄 Notes Summarizer &nbsp; | &nbsp;
        📝 Smart Quiz &nbsp; | &nbsp;
        📊 Performance Analytics
        </div>
        """,
        unsafe_allow_html=True
    )
# ==========================================
# START APPLICATION
# ==========================================

if st.session_state.logged_in:
    show_dashboard()
else:
    show_home()