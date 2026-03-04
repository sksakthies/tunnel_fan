import io
import json
import time
from datetime import datetime

import numpy as np
import pandas as pd
import joblib
import matplotlib
matplotlib.use("Agg")  # IMPORTANT for server
import matplotlib.pyplot as plt

from flask import Flask, Response, render_template, send_file, request, jsonify
from flask_cors import CORS

import firebase_admin
from firebase_admin import credentials, db

# Initialize Flask
app = Flask(__name__)
CORS(app,origin="https://tunnel-fan.vercel.app?_vercel_share=yVvvovDYAbfW9vtD9834hfLDbsmaX4Hq")

# Initialize Firebase
cred = credentials.Certificate(r"C:\tunnel_fan\project_final\realtime_database.json")

firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://tunnelbooster-ff01f-default-rtdb.asia-southeast1.firebasedatabase.app'
})

# Load trained ML model
model = joblib.load("isolation_model.pkl")

# Route for home page
@app.route('/')
def index():
    return render_template('index.html')

# Route for real-time streaming
@app.route("/stream")
def stream():
    def generate_data():
        fan_ids = ["Fan-1", "Fan-2"]  # use your fans

        last_seen_ts = {}        # fan -> last timestamp
        stale_count = {}         # fan -> loops without new timestamp

        SLEEP_SEC = 2            # your loop delay
        STALE_LIMIT = 5          # 5 loops * 2 sec = 10 sec no updates => STOP
        NO_DATA_LIMIT = 5        # if Firebase returns None for 10 sec => STOP

        no_data_count = 0

        while True:
            current_date = datetime.today().strftime("%d-%m-%Y")
            fans_data: dict = {}

            any_fan_has_data = False
            any_fan_updated = False

            for fan in fan_ids:
                path = f"{fan}/{current_date}"
                fan_data = db.reference(path).get()

                if not fan_data:
                    fans_data[fan] = None
                    continue

                any_fan_has_data = True

                latest_timestamp = sorted(fan_data.keys())[-1]
                latest_data = fan_data[latest_timestamp]

                # ---- NEW: stale detection (no new timestamp means no new live data)
                if last_seen_ts.get(fan) == latest_timestamp:
                    stale_count[fan] = stale_count.get(fan, 0) + 1
                else:
                    last_seen_ts[fan] = latest_timestamp
                    stale_count[fan] = 0
                    any_fan_updated = True

                # ---- KEEP YOUR EXISTING ML + THRESHOLD LOGIC EXACTLY AS IS ----
                features = [
                    latest_data.get("temperature", 0),
                    latest_data.get("humidity", 0),
                    latest_data.get("current", 0),
                    latest_data.get("rpm", 0),
                    latest_data.get("vibration", 0),
                ]

                features_array = np.array(features).reshape(1, -1)
                ml_prediction = model.predict(features_array)[0]

                threshold_anomaly_params = []

                if latest_data.get("temperature", 0) < 20 or latest_data.get("temperature", 0) > 34:
                    threshold_anomaly_params.append("temperature")

                if latest_data.get("humidity", 0) < 30 or latest_data.get("humidity", 0) > 40:
                    threshold_anomaly_params.append("humidity")

                if latest_data.get("current", 0) < 0.776 or latest_data.get("current", 0) > 1.0:
                    threshold_anomaly_params.append("current")

                if latest_data.get("rpm", 0) < 3800 or latest_data.get("rpm", 0) > 6400:
                    threshold_anomaly_params.append("rpm")

                # vibration anomaly only high vibration (fan-off not anomaly)
                if latest_data.get("vibration", 0) > 2.7:
                    threshold_anomaly_params.append("vibration")

                anomaly_status = "anomaly" if (
                    ml_prediction == -1 or len(threshold_anomaly_params) > 0
                ) else "normal"

                error_details = {
                    "parameters": threshold_anomaly_params,
                    "timestamp": latest_timestamp
                } if anomaly_status == "anomaly" else None

                fans_data[fan] = {
                    "timestamp": latest_timestamp,
                    "temperature": latest_data.get("temperature", 0),
                    "humidity": latest_data.get("humidity", 0),
                    "current": latest_data.get("current", 0),
                    "rpm": latest_data.get("rpm", 0),
                    "vibration": latest_data.get("vibration", 0),
                    "status": anomaly_status,
                    "error_details": error_details
                }

            # ---- NEW: stop conditions ----
            # Case A: no data at all
            if not any_fan_has_data:
                no_data_count += 1  # type: ignore
            else:
                no_data_count = 0

            # If no Firebase data for NO_DATA_LIMIT cycles => STOP stream
            if no_data_count >= NO_DATA_LIMIT:
                # send final message then stop
                yield f"data: {json.dumps({'stream_state': 'stopped', 'reason': 'no_data_from_firebase'})}\n\n"
                return  # ✅ closes SSE connection

            # Case B: data exists but never updates (latest timestamp not changing)
            # If every fan is stale for STALE_LIMIT cycles => STOP stream
            all_stale = True
            for fan in fan_ids:
                # only consider fans that actually have data today
                if last_seen_ts.get(fan) is not None:
                    if stale_count.get(fan, 0) < STALE_LIMIT:
                        all_stale = False
                        break
                else:
                    # this fan has no data; ignore it for stale check
                    pass

            if any_fan_has_data and all_stale and not any_fan_updated:
                yield f"data: {json.dumps({'stream_state': 'stopped', 'reason': 'no_new_live_updates'})}\n\n"
                return  # ✅ closes SSE connection

            # normal streaming
            yield f"data: {json.dumps(fans_data)}\n\n"
            time.sleep(SLEEP_SEC)

    return Response(
        generate_data(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )
# ================================
# ADDITIONAL FEATURES (DO NOT MODIFY EXISTING CODE)
# ================================

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
            values.get("vibration")
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
            "vibration": values.get("vibration"),
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

        features = [
            values.get("temperature", 0),
            values.get("humidity", 0),
            values.get("current", 0),
            values.get("rpm", 0),
            values.get("vibration", 0)
        ]

        features_array = np.array(features).reshape(1, -1)

        try:
            ml_prediction = model.predict(features_array)[0]
            anomaly_status = 'anomaly' if ml_prediction == -1 else 'normal'
        except Exception as e:
            anomaly_status = 'unknown'

        records.append({
            "timestamp": timestamp,
            "temperature": values.get("temperature"),
            "humidity": values.get("humidity"),
            "current": values.get("current"),
            "rpm": values.get("rpm"),
            "vibration": values.get("vibration"),
            "status": anomaly_status   # ✅ FORCE ADD STATUS
        })

    df = pd.DataFrame(records)

    # Force column order (VERY IMPORTANT)
    df = df[[
        "timestamp",
        "temperature",
        "humidity",
        "current",
        "rpm",
        "vibration",
        "status"
    ]]

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
        features = [
            values.get("temperature", 0),
            values.get("humidity", 0),
            values.get("current", 0),
            values.get("rpm", 0),
            values.get("vibration", 0)
        ]

        features_array = np.array(features).reshape(1, -1)

        try:
            ml_prediction = model.predict(features_array)[0]
            anomaly_status = 'anomaly' if ml_prediction == -1 else 'normal'
        except Exception as e:
            anomaly_status = 'unknown'

        records.append({
            "timestamp": timestamp,
            "temperature": values.get("temperature"),
            "humidity": values.get("humidity"),
            "current": values.get("current"),
            "rpm": values.get("rpm"),
            "vibration": values.get("vibration"),
            "status": anomaly_status
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
