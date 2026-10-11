import streamlit as st
import pandas as pd

from database import get_quiz_results


def show_performance(user_id):

    st.title("📊 Performance Analytics")

    st.write(
        "Analyze your quiz performance and learning progress."
    )

    results = get_quiz_results(user_id)

    if not results:

        st.info(
            "No quiz results available yet."
        )

        st.write(
            "Complete your first Smart Quiz "
            "to see your performance analytics."
        )

        return

    # Create DataFrame
    df = pd.DataFrame(
        results,
        columns=[
            "Subject",
            "Topic",
            "Score",
            "Total Questions",
            "Percentage",
            "Date"
        ]
    )

    st.divider()

    # -------------------------
    # Overall Statistics
    # -------------------------

    average_score = df["Percentage"].mean()

    highest_score = df["Percentage"].max()

    total_quizzes = len(df)

    col1, col2, col3 = st.columns(3)

    with col1:

        st.metric(
            "Average Score",
            f"{average_score:.1f}%"
        )

    with col2:

        st.metric(
            "Highest Score",
            f"{highest_score:.1f}%"
        )

    with col3:

        st.metric(
            "Quizzes Completed",
            total_quizzes
        )

    st.divider()

    # -------------------------
    # Performance Chart
    # -------------------------

    st.subheader("📈 Quiz Performance")

    chart_data = df[
        ["Percentage"]
    ].copy()

    chart_data.index = range(
        1,
        len(chart_data) + 1
    )

    st.line_chart(
        chart_data
    )

    # -------------------------
    # Subject Performance
    # -------------------------

    st.subheader(
        "📚 Subject-wise Performance"
    )

    subject_average = (
        df.groupby("Subject")["Percentage"]
        .mean()
        .sort_values(ascending=False)
    )

    st.bar_chart(
        subject_average
    )

    # -------------------------
    # Recent Quiz Results
    # -------------------------

    st.subheader(
        "📝 Quiz History"
    )

    display_df = df.copy()

    display_df["Percentage"] = (
        display_df["Percentage"]
        .round(1)
        .astype(str)
        + "%"
    )

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True
    )

    # -------------------------
    # Learning Status
    # -------------------------

    st.subheader(
        "🎯 Learning Status"
    )

    if average_score >= 80:

        st.success(
            "Excellent performance! "
            "Keep maintaining your learning consistency. 🎉"
        )

    elif average_score >= 60:

        st.info(
            "Good performance. "
            "Continue practicing to improve further. 👍"
        )

    elif average_score >= 40:

        st.warning(
            "Your performance indicates that "
            "some topics may need more practice. 📚"
        )

    else:

        st.error(
            "More practice is recommended. "
            "Review your notes and try the quizzes again. 💪"
        )

    # -------------------------
    # Weak Subjects
    # -------------------------

    st.subheader(
        "⚠️ Topics That May Need More Practice"
    )

    weak_subjects = subject_average[
        subject_average < 60
    ]

    if len(weak_subjects) > 0:

        for subject, score in weak_subjects.items():

            st.write(
                f"📚 **{subject}** — "
                f"{score:.1f}% average"
            )

    else:

        st.success(
            "No subject currently has an average "
            "below 60%."
        )