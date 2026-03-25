import requests
try:
    r = requests.get("https://flask-api-latest-hr11.onrender.com/index", timeout=5)
    print("INDEX Status:", r.status_code)
    print("Body:", r.text)
except Exception as e:
    print("Error:", e)
