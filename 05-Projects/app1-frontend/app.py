from flask import Flask, jsonify
import requests
import os

app = Flask(__name__)

BACKEND_URL = os.getenv(
    "BACKEND_URL",
    "http://backend-svc:5000/api/message"
)

@app.get("/")
def home():
    backend_response = requests.get(BACKEND_URL).json()

    return jsonify(
        service="frontend",
        ui_message="Hello from Frontend",
        backend_response=backend_response
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=4000)
