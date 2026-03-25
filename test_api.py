import requests
r = requests.get("https://flask-api-latest-hr11.onrender.com/history?date=24-03-2026")
print(f"Status: {r.status_code}")
print(f"Body: {r.text}")
