import pandas as pd
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import os
import time

# 1. SETUP PATHS
base_dir = r"D:\UG\2. Work\ML_ DL_&_AI\IIT_Patna\Capstone_Projects\Capstone_AI_Model_City_Index"
input_file = os.path.join(base_dir, "latest_city_stats.csv")
output_file = os.path.join(base_dir, "city_stats_with_coords.csv")

# 2. INITIALIZE GEOSPATIAL ENGINE
geolocator = Nominatim(user_agent="iit_patna_capstone_project")
# Note: Ensure this variable name matches the one used in the loop below
geocode_service = RateLimiter(geolocator.geocode, min_delay_seconds=1.5)

# 3. PROCESS DATA
if os.path.exists(input_file):
    df = pd.read_csv(input_file)
    cities = df['City'].unique()
    
    print(f"Starting Geocoding for {len(cities)} unique cities...")
    
    coords_dict = {}
    for city in cities:
        try:
            # FIX: Using 'geocode_service' consistently
            location = geocode_service(city)
            if location:
                coords_dict[city] = (location.latitude, location.longitude)
                print(f"Mapped: {city} -> ({location.latitude}, {location.longitude})")
            else:
                print(f"Warning: Could not find coordinates for {city}")
        except Exception as e:
            print(f"Error processing {city}: {e}")
            time.sleep(2) 

    # 4. MERGE AND EXPORT
    df['Latitude'] = df['City'].map(lambda x: coords_dict.get(x, (None, None))[0])
    df['Longitude'] = df['City'].map(lambda x: coords_dict.get(x, (None, None))[1])
    
    df_final = df.dropna(subset=['Latitude', 'Longitude'])
    df_final.to_csv(output_file, index=False)
    
    print("-" * 50)
    print(f"Success! GIS-Ready file saved: {output_file}")
    print(f"Total cities successfully mapped: {len(df_final)}")
else:
    print("Error: latest_city_stats.csv not found.")