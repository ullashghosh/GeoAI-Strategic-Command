import os
from dotenv import load_dotenv
import google.generativeai as genai
from groq import Groq
import anthropic 
from city_data_manager import city_manager  # Import your new tool

load_dotenv()

# --- Configuration ---
# Groq: Free Llama 3.3 (Acts as OpenAI replacement)
GROQ_MODEL = "llama-3.3-70b-versatile" 

# Gemini: Free Gemini 2.5 Flash
GEMINI_MODEL = "gemini-2.5-flash"

# Claude: PAID Model (Requires $$)
CLAUDE_MODEL = "claude-3-5-sonnet-20241022"

# --- Clients ---
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
claude_client = anthropic.Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))

# --- NEW SYSTEM PROMPT (The "City Index" Persona) ---
SYSTEM_PROMPT = """
You are a highly knowledgeable 'Cost of Living and Relocation Expert'.
Your goal is to help users compare cities, understand economic differences, and plan relocations.

Instructions:
1. USE THE CONTEXT: You will often receive "REAL-TIME DATABASE CONTEXT" with exact numbers for cities. You MUST use these numbers in your answer. Do not hallucinate numbers if they are provided.
2. BE ANALYTICAL: If the user asks about "New York vs London", compare their indices (Rent, Groceries, Purchasing Power).
3. BE HELPFUL: If no data is provided in the context, use your general knowledge but mention that specific data wasn't found in the live database.
4. TONE: Professional, objective, yet accessible. 
5. FORMAT: Use bullet points for comparisons.
You are a data analyst.
"""

# --- Functions ---

def get_response_from_openai(user_query, chat_history):
    """Uses Groq (Free) to simulate OpenAI"""
    try:
        # 1. Fetch Real Data
        data_context = city_manager.get_city_context(user_query)
        full_query = f"{data_context}\n\nUser Question: {user_query}"

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for msg in chat_history:
            role = "assistant" if msg['role'] == 'assistant' else "user"
            messages.append({"role": role, "content": msg["content"]})
        
        messages.append({"role": "user", "content": full_query})

        completion = groq_client.chat.completions.create(
            model=GROQ_MODEL, messages=messages, temperature=0.7, max_tokens=1024
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Groq Error: {str(e)}"

def get_gemini_response(user_query, chat_history):
    """Uses Gemini 2.5 Flash (Free Tier)"""
    try:
        # 1. Fetch Real Data
        data_context = city_manager.get_city_context(user_query)
        
        model = genai.GenerativeModel(GEMINI_MODEL)
        formatted_history = []
        for msg in chat_history:
            role = "user" if msg['role'] == 'user' else "model"
            formatted_history.append({"role": role, "parts": [msg["content"]]})

        chat = model.start_chat(history=formatted_history)
        
        # Inject system prompt + data context
        final_prompt = f"{SYSTEM_PROMPT}\n\n{data_context}\n\nUser Question: {user_query}"
        
        response = chat.send_message(final_prompt)
        return response.text
    except Exception as e:
        return f"Gemini Error: {str(e)}"

def get_claude_response(user_query, chat_history):
    """Uses Paid Claude API"""
    try:
        # 1. Fetch Real Data
        data_context = city_manager.get_city_context(user_query)
        full_query = f"{data_context}\n\nUser Question: {user_query}"

        messages = []
        for msg in chat_history:
            role = "assistant" if msg['role'] == 'assistant' or msg['role'] == 'model' else "user"
            messages.append({"role": role, "content": msg["content"]})
        messages.append({"role": "user", "content": full_query})

        message = claude_client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=messages
        )
        return message.content[0].text
    except Exception as e:

        return f"Claude Error: {str(e)}"
