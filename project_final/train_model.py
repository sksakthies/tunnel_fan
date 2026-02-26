import firebase_admin
from firebase_admin import credentials, db
import numpy as np
from sklearn.ensemble import IsolationForest
import joblib

# Initialize Firebase
cred = credentials.Certificate("C:/project_final/real_database.json")

firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://test1209-99790-default-rtdb.asia-southeast1.firebasedatabase.app'
})

fan_ids = ['Fan-1','Fan-2']
all_data = []

for fan in fan_ids:
    fan_ref = db.reference(fan)
    fan_data = fan_ref.get()

    if fan_data:
        for date in fan_data:
            date_data = fan_data[date]

            for timestamp in date_data:
                entry = date_data[timestamp]

                if all(k in entry for k in ['temperature','humidity','current','rpm','pressure']):
                    all_data.append([
                        float(entry['temperature']),
                        float(entry['humidity']),
                        float(entry['current']),
                        float(entry['rpm']),
                        float(entry['pressure'])
                    ])

print("Total samples:", len(all_data))

if len(all_data) == 0:
    print("❌ No data found")
    exit()

X_train = np.array(all_data)

model = IsolationForest(
    n_estimators=100,
    contamination=0.05,
    random_state=42
)

model.fit(X_train)

joblib.dump(model, "isolation_model.pkl")

print("✅ Model trained successfully and saved.")
