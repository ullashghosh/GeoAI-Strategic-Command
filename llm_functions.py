import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# --- OpenRouter Client Setup ---
# OpenRouter brilliantly uses the standard OpenAI library format
openrouter_key = os.getenv("OPENROUTER_API_KEY")
if not openrouter_key:
    print("❌ ERROR: OPENROUTER_API_KEY is missing!")

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=openrouter_key,
)

# --- The Persona ---
SYSTEM_PROMPT = """
You are a highly knowledgeable 'Cost of Living and Relocation Expert'.
Your goal is to help users compare cities, understand economic differences, and plan relocations based strictly on the data provided.

Instructions:
1. USE THE CONTEXT: You will receive "REAL-TIME DATABASE CONTEXT" with exact financial numbers. You MUST use these exact formatted numbers (like ₹84,000) in your answer. 
2. BE ANALYTICAL: Provide clear, concise insights about what the numbers mean for a person's lifestyle.
3. TONE: Professional, objective, yet accessible. 
4. FORMAT: Use bullet points for readability. Keep it under 150 words.
"""

# --- The Universal Fetch Function ---
def fetch_from_openrouter(full_query, model_id):
    """A single unified function to call any model via OpenRouter"""
    try:
        completion = client.chat.completions.create(
            model=model_id,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": full_query}
            ],
            temperature=0.7,
            max_tokens=500
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"API Error ({model_id}): {str(e)}"

# --- Model-Specific Wrapper Functions for the UI ---
def get_llama_response(full_query):
    # Free/Cheap routing for Llama 3.3
    return fetch_from_openrouter(full_query, "meta-llama/llama-3.3-70b-instruct")

def get_gemini_response(full_query):
    # Free/Cheap routing for Gemini 2.5 Flash
    return fetch_from_openrouter(full_query, "google/gemini-2.5-flash")

def get_deepseek_response(full_query):
    # DeepSeek V3 - Highly capable, excellent for financial reasoning
    return fetch_from_openrouter(full_query, "deepseek/deepseek-chat")