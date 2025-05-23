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

from db import create_db_connection, view_latest_readings

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


@app.route("/")
def index():
    """Serve the main application page."""
    # return render_template("index.html")
    return jsonify({"message": "Hello, World!"})


@app.route("/predict")
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

        # Process and sanitize data
        last_5_rows = sanitize(last_5_rows)
        velocity_list = [float(row[2]) for row in last_5_rows]
        viscosity_list = [float(row[4]) for row in last_5_rows]

        # Calculate additional features
        viscosity_ma = np.mean(viscosity_list)  # Moving average of viscosity
        velocity_std5 = np.std(velocity_list)  # Standard deviation of velocity

        # Prepare input data for prediction
        input_data = np.array(
            [
                [
                    json_data["elapsedtime"],
                    json_data["velocity"],
                    viscosity_ma,
                    velocity_std5,
                ]
            ]
        )

        # Make prediction
        prediction = model.predict(input_data)

        print(prediction)

        return jsonify({"prediction": prediction[0][0]})
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
        print("Sending data")
        data = view_latest_readings(create_db_connection, 3)
        sanitized_data = sanitize(data)
        print(sanitized_data)
        socketio.emit(
            "update_data",
            {"data": sanitized_data},
        )


if __name__ == "__main__":
    # Start background thread and run the application
    socketio.start_background_task(target=background_thread)
    socketio.run(app, debug=True, use_reloader=False)
