from google import genai
import streamlit as st
import json
import re


def generate_quiz(subject, topic, number_of_questions):

    try:

        api_key = st.secrets["GEMINI_API_KEY"]

        client = genai.Client(
            api_key=api_key
        )

        prompt = f"""
You are EduAI, an AI quiz generator for college students.

Subject:
{subject}

Topic:
{topic}

Generate exactly {number_of_questions} multiple-choice questions.

Each question must have:
- question
- 4 options
- correct answer
- short explanation

Return ONLY valid JSON.

Use this exact format:

[
  {{
    "question": "Question text",
    "options": [
      "Option A",
      "Option B",
      "Option C",
      "Option D"
    ],
    "answer": "Option A",
    "explanation": "Short explanation"
  }}
]

Rules:
- Exactly 4 options for every question.
- Only one correct answer.
- Questions should be suitable for college students.
- Do not include markdown.
- Do not include ```json.
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

                if not response.text:
                    continue

                result = response.text.strip()

                # Remove markdown code fences if Gemini adds them
                result = re.sub(
                    r"```json\s*",
                    "",
                    result
                )

                result = re.sub(
                    r"```\s*$",
                    "",
                    result
                )

                quiz = json.loads(result)

                if isinstance(quiz, list) and len(quiz) > 0:
                    return quiz

            except Exception:
                continue

        return None

    except Exception:
        return None