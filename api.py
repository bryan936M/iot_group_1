# Import required libraries
import math
import joblib  # type: ignore
import numpy as np  # type: ignore

# Import and configure eventlet for async operations
import eventlet  # type: ignore

eventlet.monkey_patch()

import threading
from flask import Flask, request, jsonify, render_template  # type: ignore
from flask_socketio import SocketIO  # type: ignore
from flask_cors import CORS  # type: ignore

from db import (
    create_db_connection,
    view_latest_readings,
    view_latest_readings_before_id,
)

# Configuration
POLL_INTERVAL = 5  # Interval in seconds for background data polling

# Load model and define feature names
feature_names = ["elapsedtime", "velocity", "viscosity_ma", "velocity_std5"]
model = joblib.load("viscosity_model.joblib")

# Initialize Flask application and SocketIO
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "http://localhost:5173"}})
socketio = SocketIO(app, cors_allowed_origins="http://localhost:5173")
app.config["SECRET_KEY"] = "secret!"


def sanitize(data):
    """
    Clean data by replacing infinite values with zeros to ensure JSON serialization.

    Args:
        data: List of lists containing numerical data

    Returns:
        List of lists with infinite values replaced by zeros
    """
    clean = []
    for row in data:
        new_row = []
        for x in row:
            if isinstance(x, float) and not math.isfinite(x):
                new_row.append(0)
            else:
                new_row.append(x)
        clean.append(new_row)
    return clean


def get_last_5_readings_sanitized():
    """
    Get the last 5 readings from the database and sanitize them.
    """
    return sanitize(view_latest_readings(create_db_connection, 5))


def get_prediction(elapsedtime, velocity, last_5_readings_sanitized):
    """
    Get a prediction for the viscosity.
    """
    # Calculate additional features
    velocity_list = [float(row[2]) for row in last_5_readings_sanitized]
    viscosity_list = [float(row[4]) for row in last_5_readings_sanitized]

    viscosity_ma = np.mean(viscosity_list)  # Moving average of viscosity
    velocity_std5 = np.std(velocity_list)  # Standard deviation of velocity

    # Prepare input data for prediction
    input_data = np.array([[elapsedtime, velocity, viscosity_ma, velocity_std5]])

    # Make prediction
    prediction = model.predict(input_data)

    return float(prediction[0][0])


@app.route("/")
def index():
    """Serve the main application page."""
    # return render_template("index.html")
    return jsonify({"message": "Hello, World!"})


@app.route("/predict", methods=["POST"])
def predict():
    """
    Endpoint for making viscosity predictions.

    Expects JSON data with 'elapsedtime' and 'velocity' features.
    Uses the last 5 readings from the database to calculate additional features.

    Returns:
        JSON response with prediction or error message
    """
    try:
        json_data = request.get_json()

        # Validate required features are present
        if not all(f in json_data for f in feature_names[0:2]):
            return jsonify({"error": "Missing required features"}), 400

        # Get last 5 readings from database
        last_5_rows = view_latest_readings(create_db_connection, 5)
        if len(last_5_rows) < 5:
            return jsonify({"error": "Not enough data to predict"}), 400

        new_prediction = get_prediction(
            json_data["elapsedtime"],
            json_data["velocity"],
            get_last_5_readings_sanitized(),
        )
        print(new_prediction)

        return jsonify({"prediction": new_prediction})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def background_thread():
    """
    Background thread that periodically polls the database and emits updates via WebSocket.
    Runs every POLL_INTERVAL seconds.
    """
    socketio.sleep(1)
    while True:
        socketio.sleep(POLL_INTERVAL)
        data = view_latest_readings(create_db_connection, 5)
        sanitized_data = sanitize(data)
        print("Sensor data:", sanitized_data)

        predictions = []
        for row in data:
            sanitized_row = sanitize([row])[0]
            last_5_rows_before_row = sanitize(
                view_latest_readings_before_id(create_db_connection, row[0], 5)
            )
            
            if len(last_5_rows_before_row) < 5:
                predictions.append(0)
                continue
            
            predictions.append(
                get_prediction(
                    sanitized_row[1], sanitized_row[2], last_5_rows_before_row
                )
            )

        print("Predictions:", predictions)

        socketio.emit(
            "update_data",
            {"data": sanitized_data, "predictions": predictions},
        )


if __name__ == "__main__":
    # Start background thread and run the application
    socketio.start_background_task(target=background_thread)
    socketio.run(app, debug=True, use_reloader=False)
