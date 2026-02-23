import streamlit as st
import pandas as pd
import joblib
import os
import json  # Added for Render
import folium
from streamlit_folium import st_folium
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore

# --- FIREBASE DATABASE SETUP (RENDER COMPATIBLE) ---
if not firebase_admin._apps:
    try:
        # 1. First, check Render Environment Variable
        fb_config = os.environ.get("FIREBASE_CONFIG")
        
        if fb_config:
            # If on Render, parse the string from the dashboard
            cred_dict = json.loads(fb_config)
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            print("✅ Firebase Connected via Render Secrets")
        
        # 2. Fallback for Local VS Code
        elif os.path.exists("serviceAccountKey.json"):
            cred = credentials.Certificate("serviceAccountKey.json")
            firebase_admin.initialize_app(cred)
            print("✅ Firebase Connected via Local JSON")
            
        else:
            print("⚠️ Firebase credentials not found. Logging disabled.")
            
    except Exception as e:
        print(f"❌ Firebase Error: {e}")

# Function to Save Logs
def log_interaction(user_query, city, year, prediction, responses):
    # Only run if Firebase is initialized
    if firebase_admin._apps:
        try:
            db = firestore.client()
            
            # Data Packet to Save
            log_data = {
                "timestamp": datetime.now(),
                "city": city,
                "forecast_year": year,
                "user_query": user_query,
                "ai_prediction_score": float(prediction),
                "responses": {
                    "llama_groq": responses[0],
                    "gemini": responses[1],
                    "claude": responses[2]
                }
            }
            
            # Save to collection 'consultation_logs'
            db.collection("consultation_logs").add(log_data)
            return True
        except Exception as e:
            print(f"Failed to log: {e}")
            return False
    return False

# --- IMPORT EXISTING BRAINS ---
try:
    from llm_functions import get_response_from_openai, get_gemini_response, get_claude_response
except ImportError:
    st.error("⚠️ Critical Error: 'llm_functions.py' not found.")
    st.stop()

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="GeoAI Strategic Command",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 1. ASSET LOADING ---
# Try looking in the current working directory first, then the absolute path
model_filename = "best_cost_of_living_model.pkl"
data_filename = "city_stats_with_coords.csv"

@st.cache_resource
def load_system_assets():
    # List of possible paths to check
    possible_paths = [
        os.path.join(os.getcwd(), model_filename),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), model_filename)
    ]
    
    m, d = None, None
    
    # Try to find the model
    for path in possible_paths:
        if os.path.exists(path):
            try:
                m = joblib.load(path)
                # If model is found, look for data in the same spot
                data_path = path.replace(model_filename, data_filename)
                if os.path.exists(data_path):
                    d = pd.read_csv(data_path)
                    return m, d
            except Exception as e:
                print(f"Error loading at {path}: {e}")
                
    return None, None

model, city_stats = load_system_assets()

# --- 2. SIDEBAR CONTROLS ---
st.sidebar.title("🎮 Control Panel")
st.sidebar.subheader("Predictive Parameters")

all_cities = sorted(city_stats['City'].unique())
selected_city = st.sidebar.selectbox("📍 Target City", all_cities)
forecast_years = list(range(2026, 2036))
prediction_year = st.sidebar.selectbox("📅 Forecast Year", forecast_years, index=0) 
annual_inflation = st.sidebar.slider("📈 Est. Annual Inflation (%)", 0.0, 10.0, 3.5, 0.1) / 100

st.sidebar.markdown("---")
# Status Indicator for Database
if firebase_admin._apps:
    st.sidebar.success("🟢 Database Online")
else:
    st.sidebar.warning("⚪ Database Offline (Key Missing)")

st.sidebar.info("💡 **Pro Tip:** Use the Map to spot high-stress zones.")

# --- 3. MAIN DASHBOARD ---
st.markdown("## 🌍 Global Emergency & Economic Risk Monitor")

# A. MAP VISUALIZATION
city_stats['Stress'] = (city_stats['Rent Index'] / city_stats['Local Purchasing Power Index']).fillna(0)
m = folium.Map(location=[20, 0], zoom_start=2, tiles="CartoDB dark_matter")

for i, row in city_stats.iterrows():
    if row['City'] == selected_city:
        color, radius = 'cyan', 10
    elif row['Stress'] > 2.5:
        color, radius = 'red', 6
    else:
        color, radius = 'green', 3
    
    popup = f"<b>{row['City']}</b><br>Stress: {row['Stress']:.2f}"
    folium.CircleMarker([row['Latitude'], row['Longitude']], radius=radius, color=color, fill=True, popup=popup).add_to(m)

st_folium(m, width=1200, height=400)

# B. PREDICTION CALCULATION
city_data = city_stats[city_stats['City'] == selected_city].iloc[0]
years_ahead = prediction_year - 2025
multiplier = (1 + annual_inflation) ** years_ahead

pred_rent = city_data['Rent Index'] * multiplier
pred_groceries = city_data['Groceries Index'] * multiplier
pred_restaurant = city_data['Restaurant Price Index'] * multiplier
pred_power = city_data['Local Purchasing Power Index'] 

future_input = pd.DataFrame({
    'Rent Index': [pred_rent], 'Groceries Index': [pred_groceries],
    'Restaurant Price Index': [pred_restaurant], 'Local Purchasing Power Index': [pred_power]
})
final_prediction = model.predict(future_input)[0]

# --- NEW SECTION: CURRENT ACTUALS ---
st.markdown(f"### 🏙️ Current Baseline: **{selected_city}** (2025 Actuals)")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Current Rent", f"{city_data['Rent Index']:.1f}")
c2.metric("Current Groceries", f"{city_data['Groceries Index']:.1f}")
c3.metric("Purchasing Power", f"{city_data['Local Purchasing Power Index']:.1f}")
c4.metric("Cost of Living", f"{city_data['Cost of Living Index']:.1f}")

st.divider()

# --- C. FORECAST METRICS ---
st.markdown(f"### 🚀 AI Forecast for **{selected_city}** in **{prediction_year}**")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Predicted Rent", f"{pred_rent:.1f}", delta=f"{(pred_rent - city_data['Rent Index']):.1f}")
m2.metric("Predicted Groceries", f"{pred_groceries:.1f}", delta=f"{(pred_groceries - city_data['Groceries Index']):.1f}")
m3.metric("Purchasing Power", f"{pred_power:.1f}", "Stable")
m4.metric("Total Cost of Living", f"{final_prediction:.1f}", delta=f"{(final_prediction - city_data['Cost of Living Index']):.1f}", delta_color="inverse")

st.markdown("---")

# --- 4. MULTI-MODEL ANALYSIS ---
st.subheader("🤖 Comparative AI Analysis")
st.markdown("Ask a question to see how the three leading AI models interpret this data differently.")

with st.form("chat_form"):
    user_query = st.text_input("Your Question", placeholder="e.g., Is this city affordable for a student in 2026?")
    submitted = st.form_submit_button("Get 3 Opinions")

if submitted and user_query:
    context_str = (
        f"CONTEXT: Looking at {selected_city} in {prediction_year}. "
        f"Predicted COL: {final_prediction:.1f}, Rent: {pred_rent:.1f}. "
    )
    full_query = context_str + user_query
    
    with st.spinner("Connecting to Neural Networks..."):
        resp_1 = get_response_from_openai(full_query, [])
        resp_2 = get_gemini_response(full_query, [])
        resp_3 = get_claude_response(full_query, [])

    # --- FIREBASE LOGGING ---
    is_saved = log_interaction(user_query, selected_city, prediction_year, final_prediction, [resp_1, resp_2, resp_3])
    if is_saved:
        st.toast("✅ Conversation Saved to Database", icon="💾")

    # Display Columns
    col1, col2, col3 = st.columns(3)
    with col1:
        st.header("Meta Llama 3")
        st.success(resp_1)
    with col2:
        st.header("Google Gemini")
        st.info(resp_2)
    with col3:
        st.header("Anthropic Claude")
        st.warning(resp_3)

# --- 5. FINAL VERDICT ---
st.divider()
st.subheader("⚖️ The Final Verdict")

def interpret_index(value, index_type):
    if index_type == "COL":
        if value < 40: return "Very Cheap 🟢", "Your money goes a long way here."
        if value < 70: return "Affordable 🟢", "Reasonable costs for most people."
        if value < 100: return "Expensive 🟡", "Comparable to major Western cities."
        return "Very Expensive 🔴", "High cost of living."
    elif index_type == "Rent":
        if value < 20: return "Dirt Cheap 🟢", "Rent is significantly lower than average."
        if value < 50: return "Manageable 🟢", "Rent is affordable."
        if value < 80: return "High 🟡", "Housing eats a large chunk of salary."
        return "Sky High 🔴", "Prepare for NYC level rents."
    elif index_type == "Power":
        if value < 40: return "Low 🔴", "Salaries struggle to cover needs."
        if value < 80: return "Moderate 🟡", "Typical salary covers basics."
        if value < 120: return "Strong 🟢", "Good balance."
        return "Excellent 🟢", "High disposable income!"

col_verdict, col_desc = interpret_index(final_prediction, "COL")
rent_verdict, rent_desc = interpret_index(pred_rent, "Rent")
power_verdict, power_desc = interpret_index(pred_power, "Power")

recommendation = ""
if pred_power > 80 and final_prediction < 60:
    recommendation = "💎 HIDDEN GEM: High purchasing power with low costs."
elif pred_power < 40 and final_prediction > 80:
    recommendation = "⚠️ HIGH RISK: Costs are high but local purchasing power is low."
elif pred_power > final_prediction:
    recommendation = "✅ STABLE: Income generally outweighs costs."
else:
    recommendation = "⚖️ CHALLENGING: Costs may exceed typical local purchasing power."

with st.container(border=True):
    st.markdown(f"### 🎯 Summary: {recommendation}")
    v1, v2, v3 = st.columns(3)
    with v1:
        st.markdown(f"**Cost of Living**: {col_verdict}")
        st.caption(col_desc)
    with v2:
        st.markdown(f"**Housing Cost**: {rent_verdict}")
        st.caption(rent_desc)
    with v3:
        st.markdown(f"**Buying Power**: {power_verdict}")
        st.caption(power_desc)

st.markdown("*System powered by GeoAI Custom Models & Multi-LLM Orchestration.*")