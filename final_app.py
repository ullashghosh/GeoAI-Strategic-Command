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

# --- CURRENCY AND BASELINE CONSTANTS ---
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

def get_raw_usd(index_val, category, col_index=100, nyc_income=4500):
    """Helper function enforcing the 40% Rent and 15% Groceries rule across the math engine"""
    if category == "Rent":
        return (index_val / 100) * (nyc_income * 0.40)
    elif category == "Groceries":
        return (index_val / 100) * (nyc_income * 0.15)
    elif category == "Income":
        return (index_val / 100) * (col_index / 100) * nyc_income
    else: 
        return (index_val / 100) * (nyc_income * 0.45)

def get_local_currency(city_string, index_val, category, col_index=100, nyc_income=4500):
    """Formats the raw USD into live local currency strings for the UI"""
    try:
        country = city_string.split(", ")[-1]
    except:
        country = "United States"
        
    symbol, currency_code = CURRENCY_MAP.get(country, ("$", "USD"))
    live_rates = fetch_live_exchange_rates()
    dynamic_rate = live_rates.get(currency_code, 1.0)
    
    usd_val = get_raw_usd(index_val, category, col_index, nyc_income)
    local_val = usd_val * dynamic_rate
    return f"{symbol}{local_val:,.0f}/mo"

# --- FIREBASE DATABASE SETUP ---
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
            print("⚠️ Firebase credentials not found.")
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
        except Exception:
            return False
    return False

# --- IMPORT EXISTING BRAINS ---
try:
    from llm_functions import get_response_from_openai, get_gemini_response
except ImportError:
    st.error("⚠️ Critical Error: 'llm_functions.py' not found.")
    st.stop()

# --- ASSET LOADING ---
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
            except Exception:
                pass
                
    return None, None

model, city_stats = load_system_assets()

# --- SIDEBAR CONTROLS ---
st.sidebar.title("🎮 Control Panel")

st.sidebar.subheader("User Profile")
career_level = st.sidebar.selectbox("🧑‍💼 Financial Bracket", ["Student / Entry Level", "Average Worker", "Senior Professional"], index=1)

if career_level == "Student / Entry Level":
    active_nyc_income = 2500
elif career_level == "Average Worker":
    active_nyc_income = 4500
else:
    active_nyc_income = 9000

st.sidebar.subheader("Predictive Parameters")
all_cities = sorted(city_stats['City'].unique())
selected_city = st.sidebar.selectbox("📍 Target City", all_cities)
forecast_years = list(range(2026, 2036))
prediction_year = st.sidebar.selectbox("📅 Forecast Year", forecast_years, index=0) 

annual_inflation = st.sidebar.slider("📈 Est. Annual Inflation (%)", 0.0, 15.0, 6.0, 0.1) / 100
annual_increment = st.sidebar.slider("💰 Est. Annual Income Increment (%)", 0.0, 15.0, 4.0, 0.1) / 100

st.sidebar.markdown("---")
if firebase_admin._apps:
    st.sidebar.success("🟢 Database Online")
else:
    st.sidebar.warning("⚪ Database Offline (Key Missing)")

st.sidebar.info("💡 **Pro Tip:** Use the Map to spot high-stress zones.")
st.sidebar.divider()
st.sidebar.caption("💱 Exchange Rates Updated: **Today (Live API)**")

# --- MAIN DASHBOARD ---
st.markdown("## 🌍 Global Emergency & Economic Risk Monitor")

# A. MAP VISUALIZATION 
city_stats['Stress'] = ((city_stats['Rent Index'] + city_stats['Cost of Living Index']) / city_stats['Local Purchasing Power Index']).fillna(0)
m = folium.Map(location=[20, 0], zoom_start=2, tiles="CartoDB dark_matter")

for i, row in city_stats.iterrows():
    if row['City'] == selected_city:
        color, radius = 'cyan', 10
    elif row['Stress'] > 1.5:
        color, radius = 'red', 6
    else:
        color, radius = 'green', 3
    
    popup = f"<b>{row['City']}</b><br>Stress Ratio: {row['Stress']:.2f}"
    folium.CircleMarker([row['Latitude'], row['Longitude']], radius=radius, color=color, fill=True, popup=popup).add_to(m)

st_folium(m, width=1200, height=400)

# B. REALISTIC PREDICTION CALCULATION 
city_data = city_stats[city_stats['City'] == selected_city].iloc[0]
years_ahead = prediction_year - 2025

cost_multiplier = (1 + annual_inflation) ** years_ahead
wage_multiplier = (1 + annual_increment) ** years_ahead 

pred_rent = city_data['Rent Index'] * cost_multiplier
pred_groceries = city_data['Groceries Index'] * cost_multiplier
pred_restaurant = city_data['Restaurant Price Index'] * cost_multiplier
pred_power = city_data['Local Purchasing Power Index'] * (wage_multiplier / cost_multiplier)

future_input = pd.DataFrame({
    'Rent Index': [pred_rent], 'Groceries Index': [pred_groceries],
    'Restaurant Price Index': [pred_restaurant], 'Local Purchasing Power Index': [pred_power]
})
final_prediction = model.predict(future_input)[0]

st.divider()

st.info("ℹ️ **Data Note:** All Index values on this dashboard are calculated using **New York City as the global baseline (where NYC = 100)**. Budget baselines follow a strict 40% Rent and 15% Groceries allocation.")

# --- CURRENT ACTUALS ---
st.markdown(f"### 🏙️ Current Baseline: **{selected_city}** (2025 Actuals)")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Rent Index", f"{city_data['Rent Index']:.1f}")
c1.caption(f"**Est. Local Cost:** {get_local_currency(selected_city, city_data['Rent Index'], 'Rent', nyc_income=active_nyc_income)}")

c2.metric("Groceries Index", f"{city_data['Groceries Index']:.1f}")
c2.caption(f"**Est. Local Cost:** {get_local_currency(selected_city, city_data['Groceries Index'], 'Groceries', nyc_income=active_nyc_income)}")

c3.metric("Purchasing Power Index", f"{city_data['Local Purchasing Power Index']:.1f}")
c3.caption(f"**Est. Net Salary:** {get_local_currency(selected_city, city_data['Local Purchasing Power Index'], 'Income', city_data['Cost of Living Index'], active_nyc_income)}")

c4.metric("Total Cost of Living Index", f"{city_data['Cost of Living Index']:.1f}")
c4.caption(f"**Est. Total/Month:** {get_local_currency(selected_city, city_data['Cost of Living Index'], 'Cost of Living', nyc_income=active_nyc_income)}")

st.divider()

# --- FORECAST METRICS ---
st.markdown(f"### 🚀 AI Forecast for **{selected_city}** in **{prediction_year}**")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Predicted Rent Index", f"{pred_rent:.1f}", delta=f"{(pred_rent - city_data['Rent Index']):.1f}")
m1.caption(f"**Est. Local Cost:** {get_local_currency(selected_city, pred_rent, 'Rent', nyc_income=active_nyc_income)}")

m2.metric("Predicted Groceries Index", f"{pred_groceries:.1f}", delta=f"{(pred_groceries - city_data['Groceries Index']):.1f}")
m2.caption(f"**Est. Local Cost:** {get_local_currency(selected_city, pred_groceries, 'Groceries', nyc_income=active_nyc_income)}")

m3.metric("Predicted Purchasing Power", f"{pred_power:.1f}", delta=f"{(pred_power - city_data['Local Purchasing Power Index']):.1f}")
m3.caption(f"**Est. Net Salary:** {get_local_currency(selected_city, pred_power, 'Income', final_prediction, active_nyc_income)}")

m4.metric("Predicted Cost of Living Index", f"{final_prediction:.1f}", delta=f"{(final_prediction - city_data['Cost of Living Index']):.1f}", delta_color="inverse")
m4.caption(f"**Est. Total/Month:** {get_local_currency(selected_city, final_prediction, 'Cost of Living', nyc_income=active_nyc_income)}")

st.markdown("---")

# --- MULTI-MODEL ANALYSIS ---
st.subheader("🤖 Comparative AI Analysis")
st.markdown("Ask a question to see how the two leading AI models interpret this data differently.")

with st.form("chat_form"):
    user_query = st.text_input("Your Question", placeholder="e.g., Is this city affordable for a student in 2026?")
    submitted = st.form_submit_button("Get Opinions")

if submitted and user_query:
    local_curr_code = CURRENCY_MAP.get(selected_city.split(", ")[-1], ("$", "USD"))[0]
    inc_str = get_local_currency(selected_city, pred_power, 'Income', final_prediction, active_nyc_income)
    rent_str = get_local_currency(selected_city, pred_rent, 'Rent', nyc_income=active_nyc_income)
    col_str = get_local_currency(selected_city, final_prediction, 'Cost of Living', nyc_income=active_nyc_income)

    context_str = (
        f"REAL-TIME DATABASE CONTEXT for {selected_city} in {prediction_year}:\n"
        f"- Estimated Net Monthly Income: {inc_str}\n"
        f"- Estimated Monthly Rent: {rent_str}\n"
        f"- Estimated Monthly General Living Costs: {col_str}\n"
        f"CRITICAL INSTRUCTION: You MUST use these exact {local_curr_code} figures in your response to accurately answer the user. Do not use generic US Dollars unless the city uses USD.\n\n"
    )
    full_query = context_str + "User Question: " + user_query
    
    with st.spinner("Connecting to Neural Networks..."):
        resp_1 = get_response_from_openai(full_query, [])
        resp_2 = get_gemini_response(full_query, [])

    is_saved = log_interaction(user_query, selected_city, prediction_year, final_prediction, [resp_1, resp_2])
    if is_saved:
        st.toast("✅ Conversation Saved to Database", icon="💾")

    col1, col2 = st.columns(2)
    with col1:
        st.header("Meta Llama 3")
        st.success(resp_1)
    with col2:
        st.header("Google Gemini")
        st.info(resp_2)

# --- FINAL VERDICT ---
st.divider()
st.subheader("⚖️ The Final Verdict")

raw_income = get_raw_usd(pred_power, 'Income', final_prediction, active_nyc_income)
raw_rent = get_raw_usd(pred_rent, 'Rent', nyc_income=active_nyc_income)
raw_col = get_raw_usd(final_prediction, 'Cost of Living', nyc_income=active_nyc_income)

rent_burden = raw_rent / raw_income if raw_income > 0 else 1
col_burden = raw_col / raw_income if raw_income > 0 else 1
total_burden = rent_burden + col_burden

# --- DYNAMIC PERCENTAGE FIX APPLIED HERE ---
rent_pct = round(rent_burden * 100, 1)

if col_burden < 0.40: col_v, col_d = "Highly Affordable 🟢", "General living costs are comfortably low."
elif col_burden < 0.60: col_v, col_d = "Moderate 🟡", "Balanced living expenses."
elif col_burden < 0.80: col_v, col_d = "Expensive 🔴", "Basic expenses consume most of the salary."
else: col_v, col_d = "Severe Risk 🔴", "General expenses exceed standard income."

if rent_burden < 0.20: rent_v, rent_d = "Very Affordable 🟢", f"Takes up {rent_pct}% of local income."
elif rent_burden < 0.35: rent_v, rent_d = "Manageable 🟡", f"Takes up {rent_pct}% of local income."
elif rent_burden < 0.50: rent_v, rent_d = "High 🔴", f"Takes up {rent_pct}% of local income."
else: rent_v, rent_d = "Extreme 🔴", f"Takes up {rent_pct}% of local income (Crisis)."

if total_burden < 0.60: power_v, power_d = "Excellent 🟢", "High savings potential."
elif total_burden < 0.80: power_v, power_d = "Strong 🟢", "Comfortable buffer for savings."
elif total_burden < 0.95: power_v, power_d = "Low 🔴", "Living paycheck to paycheck."
else: power_v, power_d = "Deficit 🔴", "Financial deficit. Total expenses exceed income."

recommendation = ""
if total_burden < 0.50:
    recommendation = "💎 HIDDEN GEM: High purchasing power with highly manageable local costs."
elif total_burden > 0.90:
    recommendation = "⚠️ HIGH RISK: Total estimated costs severely outweigh expected purchasing power."
elif rent_burden > 0.40:
    recommendation = "🏘️ HOUSING TRAP: General costs are okay, but housing is highly unaffordable."
else:
    recommendation = "✅ STABLE: Income generally balances well against costs."

with st.container(border=True):
    st.markdown(f"### 🎯 Summary: {recommendation}")
    
    est_income_str = get_local_currency(selected_city, pred_power, 'Income', final_prediction, active_nyc_income)
    est_rent_str = get_local_currency(selected_city, pred_rent, 'Rent', nyc_income=active_nyc_income)
    est_col_str = get_local_currency(selected_city, final_prediction, 'Cost of Living', nyc_income=active_nyc_income)
    
    st.info(f"**Layman's Financial Breakdown:** In {prediction_year}, the average person taking home **{est_income_str}** will spend roughly **{est_rent_str}** on rent and **{est_col_str}** on general living expenses each month.")
    
    v1, v2, v3 = st.columns(3)
    with v1:
        st.markdown(f"**Cost of Living**: {col_v}")
        st.caption(col_d)

st.markdown("*System powered by GeoAI Custom Models & Multi-LLM Orchestration.*")