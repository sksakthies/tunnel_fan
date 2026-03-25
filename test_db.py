import firebase_admin
from firebase_admin import credentials, db
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
cred_path = os.path.join(BASE_DIR, "project_final", "realtime_database.json")
if not os.path.exists(cred_path):
    print("No DB creds found.")
    exit()

cred = credentials.Certificate(cred_path)
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://tunnelventilation-8ba9a-default-rtdb.firebaseio.com/'
})
fan_ref = db.reference("Fan-1/24-03-2026")
data = fan_ref.get()
print("Type:", type(data))
if isinstance(data, list):
    print("List length:", len(data))
elif isinstance(data, dict):
    print("Dict keys:", list(data.keys())[:5])
else:
    print("Data:", data)
