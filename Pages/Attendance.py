import streamlit as st
import pandas as pd

from database import (
    get_attendance
)


def show_attendance(user_id):

    st.title("📅 Smart Attendance")

    st.write(
        "Track your subject-wise attendance and identify "
        "subjects that need attention."
    )

    results = get_attendance(user_id)

    if not results:

        st.info(
            "No attendance records available yet."
        )

        st.write(
            "Add your subject attendance from the dashboard."
        )

        return

    df = pd.DataFrame(
        results,
        columns=[
            "Subject",
            "Total Classes",
            "Attended Classes",
            "Percentage",
            "Date"
        ]
    )

    # Overall attendance
    total_classes = df["Total Classes"].sum()
    total_attended = df["Attended Classes"].sum()

    if total_classes > 0:

        overall_percentage = (
            total_attended / total_classes
        ) * 100

    else:

        overall_percentage = 0

    st.divider()

    col1, col2, col3 = st.columns(3)

    with col1:

        st.metric(
            "Overall Attendance",
            f"{overall_percentage:.1f}%"
        )

    with col2:

        st.metric(
            "Total Classes",
            int(total_classes)
        )

    with col3:

        st.metric(
            "Classes Attended",
            int(total_attended)
        )

    st.divider()

    # Subject-wise attendance
    st.subheader(
        "📚 Subject-wise Attendance"
    )

    subject_data = df[
        ["Subject", "Percentage"]
    ].set_index("Subject")

    st.bar_chart(
        subject_data
    )

    st.divider()

    # Attendance table
    st.subheader(
        "📋 Attendance Records"
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

    st.divider()

    # Attendance warnings
    st.subheader(
        "⚠️ Attendance Alerts"
    )

    low_attendance = df[
        df["Percentage"] < 75
    ]

    if len(low_attendance) > 0:

        for _, row in low_attendance.iterrows():

            st.warning(
                f"**{row['Subject']}** — "
                f"{row['Percentage']:.1f}% attendance. "
                f"More classes should be attended."
            )

    else:

        st.success(
            "All subjects currently have attendance "
            "of 75% or above. 👍"
        )