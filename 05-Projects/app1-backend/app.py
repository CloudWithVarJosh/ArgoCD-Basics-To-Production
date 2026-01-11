from flask import Flask, jsonify

app = Flask(__name__)

@app.get("/api/message")
def message():
    return jsonify(
        service="backend",
        message="Hello from Backend API",
        status="success"
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
