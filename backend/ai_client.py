import os
from dotenv import load_dotenv
from groq import Groq
from google import genai
from google.genai import types


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, ".env")

load_dotenv(ENV_PATH)


# =========================
# API KEYS
# =========================

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


# =========================
# CLIENTS
# =========================

groq_client = Groq(
    api_key=GROQ_API_KEY
)

gemini_client = genai.Client(
    api_key=GEMINI_API_KEY
)


# =========================
# MODELS
# =========================

# Main model
GROQ_MODEL = "openai/gpt-oss-20b"


# Gemini fallback models
GEMINI_MODELS = [
    "gemini-2.5-flash-lite",
    "gemini-flash-lite-latest",
    "gemini-flash-latest",
    "gemini-2.5-flash"
]


# =========================
# GENERATE WITH FALLBACK
# =========================

def generate_with_fallback(prompt):

    # ---------------------------------
    # 1. TRY GROQ FIRST
    # ---------------------------------

    try:
        print(f"\nTrying Groq: {GROQ_MODEL}")

        response = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant. Follow the instructions carefully and return only the requested output."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0
        )

        print(f"Success using Groq: {GROQ_MODEL}")

        return response.choices[0].message.content

    except Exception as e:

        print(f"Groq failed: {e}")
        print("Switching to Gemini fallback...")


    # ---------------------------------
    # 2. TRY GEMINI MODELS
    # ---------------------------------

    last_error = None

    for model in GEMINI_MODELS:

        try:

            print(f"Trying Gemini: {model}")

            response = gemini_client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0
                )
            )

            print(f"Success using Gemini: {model}")

            return response.text

        except Exception as e:

            print(f"Gemini {model} failed: {e}")

            last_error = e


    # ---------------------------------
    # 3. ALL MODELS FAILED
    # ---------------------------------

    raise Exception(
        f"All AI models failed. Last error: {last_error}"
    )