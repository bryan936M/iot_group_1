import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template
from flask_socketio import SocketIO
import threading
import math


from db import create_db_connection, view_latest_readings

POLL_INTERVAL = 5

app = Flask(__name__)
socketio = SocketIO(app)
app.config['SECRET_KEY'] = 'secret!'

def sanitize(data):
    """ Replace inf / -inf with None so that JSON encoding won’t fail. """
    clean = []
    for row in data:
        newrow = []
        for x in row:
            if isinstance(x, float) and not math.isfinite(x):
                newrow.append(0)
            else:
                newrow.append(x)
        clean.append(newrow)
    return clean

@app.route("/")
def index():
    return render_template('index.html')

def background_thread():
    socketio.sleep(1)
    while True:
      socketio.sleep(POLL_INTERVAL)
      print("Sending data")
      data = view_latest_readings(create_db_connection, 3)
      sanitizedData = sanitize(data)
      print(sanitizedData)
      socketio.emit("update_data", {"data": sanitizedData},)

if __name__ == "__main__":
  socketio.start_background_task(target=background_thread)
  socketio.run(app, debug=True, use_reloader=False)
