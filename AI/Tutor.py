from google import genai
import streamlit as st


def get_ai_response(question):

    try:
        # Get Gemini API key
        api_key = st.secrets["GEMINI_API_KEY"]

        # Create Gemini client
        client = genai.Client(
            api_key=api_key
        )

        prompt = f"""
You are EduAI, an AI tutor designed for college students.

Student question:
{question}

Instructions:
1. Explain the concept clearly.
2. Use simple language.
3. Give examples when useful.
4. For engineering topics, include important formulas when appropriate.
5. Break difficult concepts into simple steps.
6. End with 2-3 important points to remember.
7. Keep the answer concise and useful.
"""

        # Models will be tried one by one
        models = [
            "gemini-3.8-flash",
            "gemini-3.7-flash",
            "gemini-3.6-flash",
            "gemini-3.5-flash-lite"
        ]

        last_error = None

        for model in models:

            try:
                response = client.models.generate_content(
                    model=model,
                    contents=prompt
                )

                if response.text:
                    return response.text

            except Exception as e:
                last_error = e
                continue

        # If every model fails
        return (
            "⚠️ EduAI is temporarily unable to generate a response.\n\n"
            "All available Gemini models are currently unavailable. "
            "Please try again in a few moments."
        )

    except Exception as e:

        return (
            "⚠️ EduAI could not connect to the AI service.\n\n"
            "Please check your API key and try again."
        )