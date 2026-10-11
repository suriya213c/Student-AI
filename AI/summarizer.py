from google import genai
import streamlit as st
from pypdf import PdfReader


def extract_pdf_text(uploaded_file):

    try:
        reader = PdfReader(uploaded_file)

        text = ""

        for page in reader.pages:
            page_text = page.extract_text()

            if page_text:
                text += page_text + "\n"

        return text

    except Exception as e:
        return f"PDF_ERROR: {str(e)}"


def summarize_notes(text):

    try:

        api_key = st.secrets["GEMINI_API_KEY"]

        client = genai.Client(
            api_key=api_key
        )

        prompt = f"""
You are EduAI, an AI academic assistant for college students.

Analyze the following study material.

STUDY MATERIAL:
{text}

Create a student-friendly study summary using this format:

# 📚 Summary

Give a clear and easy-to-understand summary.

# 🔑 Key Points

List the most important concepts as bullet points.

# 🧠 Important Concepts

Explain the major concepts briefly.

# 📝 Important Questions

Create 5 important questions that a student should prepare for an exam.

# 📌 Quick Revision

Give 5 short points for last-minute revision.

Rules:
- Use simple language.
- Do not add information that is not supported by the study material.
- Keep the response organized.
"""

        # Try multiple available Gemini models
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

        return (
            "⚠️ EduAI is temporarily unable to summarize the notes.\n\n"
            "All available Gemini models are currently unavailable. "
            "Please try again in a few moments."
        )

    except Exception as e:

        return (
            "⚠️ Could not summarize the notes.\n\n"
            "Please check your Gemini API configuration.\n\n"
            f"Error: {str(e)}"
        )