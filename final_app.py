import streamlit as st
import pandas as pd
import joblib
import os
import json
import requests
import folium
from streamlit_folium import st_folium
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="GeoAI Strategic Command",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CURRENCY AND INCOME CONVERSION LOGIC (LIVE API) ---
NYC_BASE_COL = 1500       
NYC_BASE_RENT = 3500      
NYC_BASE_GROCERIES = 500  
NYC_BASE_INCOME = 6000    

CURRENCY_MAP = {
    "India": ("₹", "INR"),
    "United States": ("$", "USD"),
    "United Kingdom": ("£", "GBP"),
    "Germany": ("€", "EUR"),
    "France": ("€", "EUR"),
    "Italy": ("€", "EUR"),
    "Spain": ("€", "EUR"),
    "Canada": ("C$", "CAD"),
    "Australia": ("A$", "AUD"),
    "Japan": ("¥", "JPY"),
    "Brazil": ("R$", "BRL"),
    "South Africa": ("R", "ZAR"),
    "China": ("¥", "CNY"),
    "Mexico": ("Mex$", "MXN"),
    "United Arab Emirates": ("AED", "AED")
}

@st.cache_data(ttl=86400)
def fetch_live_exchange_rates():
    try:
        url = "https://open.er-api.com/v6/latest/USD"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json().get("rates", {})
    except Exception:
        return {}

def get_local_currency(city_string, index_val, category):
    try:
        country = city_string.split(", ")[-1]
    except:
        country = "United States"
        
    symbol, currency_code = CURRENCY_MAP.get(country, ("$", "USD"))
    live_rates = fetch_live_exchange_rates()
    dynamic_rate = live_rates.get(currency_code, 1.0)
    
    if category == "Rent":
        usd_val = (index_val / 100) * NYC_BASE_RENT
    elif category == "Groceries":
        usd_val = (index_val / 100) * NYC_BASE_GROCERIES
    elif category == "Income":
        usd_val = (index_val / 100) * NYC_BASE_INCOME
    else: 
        usd_val = (index_val / 100) * NYC_BASE_COL
        
    local_val = usd_val * dynamic_rate
    return f"{symbol}{local_val:,.0f}/mo"

# --- FIREBASE DATABASE SETUP (RENDER COMPATIBLE) ---
if not firebase_admin._apps:
    try:
        fb_config = os.environ.get("FIREBASE_CONFIG")
        if fb_config:
            cred_dict = json.loads(fb_config)
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            print("✅ Firebase Connected via Render Secrets")
        elif os.path.exists("serviceAccountKey.json"):
            cred = credentials.Certificate("serviceAccountKey.json")
            firebase_admin.initialize_app(cred)
            print("✅ Firebase Connected via Local JSON")
        else:
            print("⚠️ Firebase credentials not found. Logging disabled.")
    except Exception as e:
        print(f"❌ Firebase Error: {e}")

def log_interaction(user_query, city, year, prediction, responses):
    if firebase_admin._apps:
        try:
            db = firestore.client()
            log_data = {
                "timestamp": datetime.now(),
                "city": city,
                "forecast_year": year,
                "user_query": user_query,
                "ai_prediction_score": float(prediction),
                "responses": {
                    "llama_groq": responses[0],
                    "gemini": responses[1]
                }
            }
            db.collection("consultation_logs").add(log_data)
            return True
        except Exception as e:
            print(f"Failed to log: {e}")
            return False
    return False

# --- IMPORT EXISTING BRAINS ---
try:
    # Claude removed
    from llm_functions import get_response_from_openai, get_gemini_response
except ImportError:
    st.error("⚠️ Critical Error: 'llm_functions.py' not found.")
    st.stop()

# --- 1. ASSET LOADING (ROCK-SOLID VERSION) ---
@st.cache_resource
def load_system_assets():
    model_name = "best_cost_of_living_model.pkl"
    data_name = "city_stats_with_coords.csv"
    script_dir = os.path.dirname(os.path.abspath(__file__))
    potential_model_paths = [
        os.path.join(script_dir, model_name),
        os.path.join(os.getcwd(), model_name),
        model_name
    ]
    
    model, stats = None, None
    for path in potential_model_paths:
        if os.path.exists(path):
            try:
                model = joblib.load(path)
                csv_path = path.replace(model_name, data_name)
                if os.path.exists(csv_path):
                    stats = pd.read_csv(csv_path)
                    return model, stats
            except Exception as e:
                print(f"Error loading assets at {path}: {e}")
                
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
if firebase_admin._apps:
    st.sidebar.success("🟢 Database Online")
else:
    st.sidebar.warning("⚪ Database Offline (Key Missing)")

st.sidebar.info("💡 **Pro Tip:** Use the Map to spot high-stress zones.")
st.sidebar.divider()
st.sidebar.caption("💱 Exchange Rates Updated: **Today (Live API)**")

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
c1.metric("Rent Index (NYC=100)", f"{city_data['Rent Index']:.1f}")
c1.caption(f"**Est. Local Cost:** {get_local_currency(selected_city, city_data['Rent Index'], 'Rent')}")

c2.metric("Groceries Index", f"{city_data['Groceries Index']:.1f}")
c2.caption(f"**Est. Local Cost:** {get_local_currency(selected_city, city_data['Groceries Index'], 'Groceries')}")

c3.metric("Purchasing Power Index", f"{city_data['Local Purchasing Power Index']:.1f}")
c3.caption(f"**Est. Net Salary:** {get_local_currency(selected_city, city_data['Local Purchasing Power Index'], 'Income')}")

c4.metric("Total COL Index", f"{city_data['Cost of Living Index']:.1f}")
c4.caption(f"**Est. Total/Month:** {get_local_currency(selected_city, city_data['Cost of Living Index'], 'COL')}")

st.divider()

# --- C. FORECAST METRICS ---
st.markdown(f"### 🚀 AI Forecast for **{selected_city}** in **{prediction_year}**")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Predicted Rent Index", f"{pred_rent:.1f}", delta=f"{(pred_rent - city_data['Rent Index']):.1f}")
m1.caption(f"**Est. Local Cost:** {get_local_currency(selected_city, pred_rent, 'Rent')}")

m2.metric("Predicted Groceries Index", f"{pred_groceries:.1f}", delta=f"{(pred_groceries - city_data['Groceries Index']):.1f}")
m2.caption(f"**Est. Local Cost:** {get_local_currency(selected_city, pred_groceries, 'Groceries')}")

m3.metric("Predicted Purchasing Power", f"{pred_power:.1f}", "Stable")
m3.caption(f"**Est. Net Salary:** {get_local_currency(selected_city, pred_power, 'Income')}")

m4.metric("Predicted COL Index", f"{final_prediction:.1f}", delta=f"{(final_prediction - city_data['Cost of Living Index']):.1f}", delta_color="inverse")
m4.caption(f"**Est. Total/Month:** {get_local_currency(selected_city, final_prediction, 'COL')}")

st.markdown("---")

# --- 4. MULTI-MODEL ANALYSIS ---
st.subheader("🤖 Comparative AI Analysis")
st.markdown("Ask a question to see how the two leading AI models interpret this data differently.")

with st.form("chat_form"):
    user_query = st.text_input("Your Question", placeholder="e.g., Is this city affordable for a student in 2026?")
    submitted = st.form_submit_button("Get 2 Opinions")

if submitted and user_query:
    context_str = (
        f"CONTEXT: Looking at {selected_city} in {prediction_year}. "
        f"Predicted COL: {final_prediction:.1f}, Rent: {pred_rent:.1f}. "
    )
    full_query = context_str + user_query
    
    with st.spinner("Connecting to Neural Networks..."):
        resp_1 = get_response_from_openai(full_query, [])
        resp_2 = get_gemini_response(full_query, [])

    # --- FIREBASE LOGGING ---
    is_saved = log_interaction(user_query, selected_city, prediction_year, final_prediction, [resp_1, resp_2])
    if is_saved:
        st.toast("✅ Conversation Saved to Database", icon="💾")

    # Display 2 Columns instead of 3
    col1, col2 = st.columns(2)
    with col1:
        st.header("Meta Llama 3")
        st.success(resp_1)
    with col2:
        st.header("Google Gemini")
        st.info(resp_2)

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
    
    # NEW: Layman's Sentence Generation
    est_income = get_local_currency(selected_city, pred_power, 'Income')
    est_rent = get_local_currency(selected_city, pred_rent, 'Rent')
    est_col = get_local_currency(selected_city, final_prediction, 'COL')
    
    st.info(f"**Layman's Financial Breakdown:** In {prediction_year}, the average person taking home **{est_income}** will spend roughly **{est_rent}** on rent and **{est_col}** on general living expenses each month.")
    
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