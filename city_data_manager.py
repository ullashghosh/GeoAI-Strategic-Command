import pandas as pd
import joblib
import os

# Define paths to your data
CSV_PATH = "city_stats_with_coords.csv"
MODEL_PATH = "best_cost_of_living_model.pkl"

class CityDataManager:
    def __init__(self):
        self.df = None
        self.model = None
        self._load_data()

    def _load_data(self):
        """Loads the CSV and Model safely"""
        if os.path.exists(CSV_PATH):
            self.df = pd.read_csv(CSV_PATH)
            # Create a lowercase column for easier searching
            if 'City' in self.df.columns:
                self.df['city_lower'] = self.df['City'].str.lower()
        else:
            print(f"Warning: {CSV_PATH} not found.")

        if os.path.exists(MODEL_PATH):
            try:
                self.model = joblib.load(MODEL_PATH)
            except Exception as e:
                print(f"Error loading model: {e}")

    def get_city_context(self, user_query):
        """
        Scans the user query for city names and returns their stats.
        """
        if self.df is None:
            return ""

        found_info = []
        user_query_lower = user_query.lower()

        # Simple keyword matching for cities in our database
        # (In a real app, you might use Named Entity Recognition (NER) here)
        for index, row in self.df.iterrows():
            city_name = str(row['City'])
            if city_name.lower() in user_query_lower:
                # We found a city mentioned in the user's query!
                info = (
                    f"Data for {city_name}, {row.get('Country', 'Unknown')}:\n"
                    f"- Cost of Living Index: {row.get('Cost of Living Index', 'N/A')}\n"
                    f"- Rent Index: {row.get('Rent Index', 'N/A')}\n"
                    f"- Groceries Index: {row.get('Groceries Index', 'N/A')}\n"
                    f"- Local Purchasing Power: {row.get('Local Purchasing Power Index', 'N/A')}\n"
                )
                found_info.append(info)

        if found_info:
            return "\nREAL-TIME DATABASE CONTEXT (Use this to answer):\n" + "\n".join(found_info)
        return ""

# Create a singleton instance
city_manager = CityDataManager()