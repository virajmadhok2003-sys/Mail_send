from flask import Flask, jsonify
from threading import Thread
from main import start_monitoring 
import os # 🔗 this connects it

app = Flask(__name__)
    
@app.route('/')
def home():
    return "Monitoring service is running."
    
@app.route('/status')
def status():
    return jsonify({"status": "Running", "message": "Email monitoring in background"})
    
if __name__ == "__main__":
    # 🧵 Start monitor in background thread
    monitor_thread = Thread(target=start_monitoring, daemon=True)
    monitor_thread.start()

    
    # 🌐 Start Flask server
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)