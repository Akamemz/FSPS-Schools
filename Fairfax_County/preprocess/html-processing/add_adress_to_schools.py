import requests
import json
import time

# Load your address dictionary here
with open("Fairfax_County/Tim_test/fcps_school_addresses.json") as f:
    schools = json.load(f)

#%%
# Your OpenCage API key
API_KEY = "da8d3dc1fd8c40ae968513f9959dda7d"
GEOCODE_URL = "https://api.opencagedata.com/geocode/v1/json"

# Function to enrich each address
def enrich_address(address):
    params = {
        "q": address,
        "key": API_KEY,
        "limit": 1
    }
    response = requests.get(GEOCODE_URL, params=params)
    data = response.json()
    if data["results"]:
        result = data["results"][0]
        components = result["components"]
        return {
            "zipcode": components.get("postcode", ""),
            "latitude": result["geometry"]["lat"],
            "longitude": result["geometry"]["lng"]
        }
    return {"zipcode": "", "latitude": "", "longitude": ""}

# Add info to each school
for school, info in schools.items():
    enriched = enrich_address(info["address"])
    schools[school].update(enriched)
    time.sleep(1)  # Respect API rate limits

# Save the enriched data
with open("schools_enriched.json", "w") as f:
    json.dump(schools, f, indent=2)
