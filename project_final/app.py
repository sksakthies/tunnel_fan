from flask_cors import CORS
from flask import Flask, Response, render_template
import firebase_admin
from firebase_admin import credentials, db
import numpy as np
import joblib
import json
import time
from datetime import datetime
from flask import send_file, request
import matplotlib
matplotlib.use("Agg")  # IMPORTANT for server
import matplotlib.pyplot as plt
import io


# Initialize Flask
app = Flask(__name__)
CORS(app)

# Initialize Firebase
cred = credentials.Certificate("C:/project_final/real_database.json")

firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://test1209-99790-default-rtdb.asia-southeast1.firebasedatabase.app'
})

# Load trained ML model
model = joblib.load("isolation_model.pkl")

# Route for home page
@app.route('/')
def index():
    return render_template('index.html')

# Route for real-time streaming
@app.route('/stream')
def stream():

    def generate_data():

        fan_ids = ['Fan-1','Fan-2']

        while True:
            fans_data = {}

            current_date = datetime.today().strftime('%d-%m-%Y')

            for fan in fan_ids:
                fan_ref = db.reference(f"{fan}/{current_date}")
                fan_data = fan_ref.get()

                if fan_data:
                    latest_timestamp = list(fan_data.keys())[-1]
                    latest_data = fan_data[latest_timestamp]

                    # Prepare features for ML model
                    features = [
                        latest_data['temperature'],
                        latest_data['humidity'],
                        latest_data['current'],
                        latest_data['rpm'],
                        latest_data['pressure']
                    ]

                    features_array = np.array(features).reshape(1, -1)
                    ml_prediction = model.predict(features_array)[0]

                    # Threshold anomaly check (YOUR ORIGINAL LOGIC)
                    threshold_anomaly_params = []

                    if latest_data['temperature'] < 20 or latest_data['temperature'] > 40:
                        threshold_anomaly_params.append('temperature')

                    if latest_data['humidity'] < 30 or latest_data['humidity'] > 65:
                        threshold_anomaly_params.append('humidity')

                    if latest_data['current'] < 0.776 or latest_data['current'] > 2.430:
                        threshold_anomaly_params.append('current')

                    if latest_data['rpm'] < 3800 or latest_data['rpm'] > 4300:
                        threshold_anomaly_params.append('rpm')

                    if latest_data['pressure'] < 720 or latest_data['pressure'] > 780:
                        threshold_anomaly_params.append('pressure')

                    # Final anomaly decision
                    anomaly_status = 'anomaly' if (
                        ml_prediction == -1 or len(threshold_anomaly_params) > 0
                    ) else 'normal'

                    error_details = {
                        'parameters': threshold_anomaly_params,
                        'timestamp': latest_timestamp
                    } if anomaly_status == 'anomaly' else None

                    fans_data[fan] = {
                        'timestamp': latest_timestamp,
                        'temperature': latest_data['temperature'],
                        'humidity': latest_data['humidity'],
                        'current': latest_data['current'],
                        'rpm': latest_data['rpm'],
                        'pressure': latest_data['pressure'],
                        'status': anomaly_status,
                        'error_details': error_details
                    }

                else:
                    fans_data[fan] = None

            yield f"data: {json.dumps(fans_data)}\n\n"
            time.sleep(5)

    return Response(generate_data(), content_type='text/event-stream')
# ================================
# ADDITIONAL FEATURES (DO NOT MODIFY EXISTING CODE)
# ================================

from flask import request, jsonify
import pandas as pd
import io


# -------------------------------
# 1️⃣ Historical Data by Date
# -------------------------------
@app.route('/history')
def get_history():
    selected_date = request.args.get('date')

    if not selected_date:
        return jsonify({"error": "Date parameter required"}), 400

    fan_ref = db.reference(f"Fan-1/{selected_date}")
    fan_data = fan_ref.get()

    if not fan_data:
        return jsonify([])

    records = []

    for timestamp, values in fan_data.items():
         # ---- ML anomaly prediction (same as stream) ----
        features = [
            values.get("temperature"),
            values.get("humidity"),
            values.get("current"),
            values.get("rpm"),
            values.get("pressure")
        ]

        features_array = np.array(features).reshape(1, -1)
        ml_prediction = model.predict(features_array)[0]

        anomaly_status = 'anomaly' if ml_prediction == -1 else 'normal'

        # ---- record with status ----
        records.append({
            "timestamp": timestamp,
            "temperature": values.get("temperature"),
            "humidity": values.get("humidity"),
            "current": values.get("current"),
            "rpm": values.get("rpm"),
            "pressure": values.get("pressure"),
            "status": anomaly_status
        })    
        

    return jsonify(records)


# -------------------------------
# 2️⃣ Download CSV
# -------------------------------
@app.route('/download/csv')
def download_csv():
    selected_date = request.args.get('date')

    if not selected_date:
        return "Date parameter required", 400

    fan_ref = db.reference(f"Fan-1/{selected_date}")
    fan_data = fan_ref.get()

    if not fan_data:
        return "No data found", 404

    records = []

    for timestamp, values in fan_data.items():
        records.append({
            "timestamp": timestamp,
            "temperature": values.get("temperature"),
            "humidity": values.get("humidity"),
            "current": values.get("current"),
            "rpm": values.get("rpm"),
            "pressure": values.get("pressure")
        })

    df = pd.DataFrame(records)

    output = io.StringIO()
    df.to_csv(output, index=False)

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition":
            f"attachment;filename=fan_data_{selected_date}.csv"
        }
    )


# -------------------------------
# 3️⃣ Download Excel
# -------------------------------
@app.route('/download/excel')
def download_excel():
    selected_date = request.args.get('date')

    if not selected_date:
        return "Date parameter required", 400

    fan_ref = db.reference(f"Fan-1/{selected_date}")
    fan_data = fan_ref.get()

    if not fan_data:
        return "No data found", 404

    records = []

    for timestamp, values in fan_data.items():
        records.append({
            "timestamp": timestamp,
            "temperature": values.get("temperature"),
            "humidity": values.get("humidity"),
            "current": values.get("current"),
            "rpm": values.get("rpm"),
            "pressure": values.get("pressure")
        })

    df = pd.DataFrame(records)

    output = io.BytesIO()
    df.to_excel(output, index=False, engine='openpyxl')
    output.seek(0)

    return Response(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition":
            f"attachment;filename=fan_data_{selected_date}.xlsx"
        }
    )

@app.route("/chart/prediction")
def chart_prediction_from_db():
    selected_date = request.args.get("date")
    fan = request.args.get("fan", "Fan-1")

    if not selected_date:
        return {"error": "date required (DD-MM-YYYY)"}, 400

    fan_ref = db.reference(f"{fan}/{selected_date}")
    fan_data = fan_ref.get()

    if not fan_data:
        return {"error": "no data found"}, 404

    timestamps = sorted(fan_data.keys())

    y = []
    x_labels = []

    for ts in timestamps:
        status = fan_data[ts].get("status")  # <-- stored status
        if status is None:
            continue

        y.append(1 if status == "anomaly" else 0)
        x_labels.append(ts)

    if len(y) == 0:
        return {"error": "no status field found. Stream must run once to store status."}, 404

    fig = plt.figure(figsize=(10, 3.8))
    plt.plot(range(len(y)), y, marker="o", linestyle="-")
    plt.yticks([0, 1], ["Normal", "Anomaly"])
    plt.title(f"{fan} Stored Prediction Timeline ({selected_date})")
    plt.xlabel("Sample Index (time order)")
    plt.ylabel("Stored Status")
    plt.grid(True, axis="y", linestyle="--", alpha=0.4)

    step = max(1, len(x_labels) // 8)
    idxs = list(range(0, len(x_labels), step))
    plt.xticks(idxs, [x_labels[i] for i in idxs], rotation=30, ha="right")

    buf = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)

    return send_file(buf, mimetype="image/png")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
