import requests
base = "http://127.0.0.1:5000"
for p in ["/", "/model", "/graphs", "/map", "/table", "/forecast"]:
    r = requests.get(base + p)
    print(f"{p}: {r.status_code}")

# Check Shamol in API responses
r = requests.get(base + "/api/data")
data = r.json()
if data:
    print(f"\n/api/data sample keys: {list(data[0].keys())}")
    print(f"Shamol present: {'Shamol' in data[0]}")

r = requests.get(base + "/api/map-data")
mapdata = r.json()
if mapdata:
    print(f"\n/api/map-data sample keys: {list(mapdata[0].keys())}")
    print(f"Shamol present: {'Shamol' in mapdata[0]}")
