from google import genai
import streamlit as st


def generate_learning_plan(
    quiz_results,
    attendance_percentage,
    risk_level
):

    try:

        api_key = st.secrets["GEMINI_API_KEY"]

        client = genai.Client(
            api_key=api_key
        )

        # Prepare quiz information
        quiz_information = ""

        for row in quiz_results:

            subject = row[0]
            topic = row[1]
            score = row[2]
            total = row[3]
            percentage = row[4]

            quiz_information += (
                f"Subject: {subject}, "
                f"Topic: {topic}, "
                f"Score: {score}/{total}, "
                f"Percentage: {percentage:.1f}%\n"
            )

        if not quiz_information:

            quiz_information = "No quiz data available."

        prompt = f"""
You are EduAI, an AI-powered personalized learning assistant
for college students.

Analyze the student's academic information below.

QUIZ PERFORMANCE:
{quiz_information}

ATTENDANCE:
{attendance_percentage:.1f}%

ACADEMIC RISK:
{risk_level}

Create a personalized learning plan.

Use exactly this structure:

# 🎯 Personalized Learning Plan

## 📊 Academic Overview

Briefly describe the student's current academic situation.

## ⚠️ Weak Areas

Identify subjects or topics that need more practice.

## 📚 Topics to Study

List the most important topics the student should study.

## 🗓️ 7-Day Study Plan

Create a practical 7-day plan.

For each day include:
- Topic
- Study activity
- Suggested duration
- Practice activity

## 📝 Quiz Practice

Suggest quiz practice based on weak areas.

## 🔄 Revision Strategy

Give a simple revision strategy.

## 💡 AI Recommendations

Give 3-5 personalized recommendations.

Rules:
- Use the student's actual quiz data.
- Prioritize lower-scoring topics.
- Consider attendance when making recommendations.
- Do not invent quiz scores.
- Use simple language.
- Make the plan practical for a college student.
"""

        models = [
            "gemini-3.8-flash",
            "gemini-3.7-flash",
            "gemini-3.6-flash",
            "gemini-3.5-flash",
            "gemini-3.5-flash-lite"
        ]

        for model in models:

            try:

                response = client.models.generate_content(
                    model=model,
                    contents=prompt
                )

                if response.text:

                    return response.text

            except Exception:

                continue

        return None

    except Exception:

        return None