# app.py
from flask import Flask, request, jsonify
from flask_cors import CORS

# Initialize the Flask application
app = Flask(__name__)

# Enable CORS (Cross-Origin Resource Sharing)
# This is necessary to allow our React app (running on localhost:3000)
# to send requests to our Python API (running on localhost:5000).
CORS(app)

@app.route('/log_event', methods=['POST'])
def log_event():
    """
    This function defines the /log_event endpoint.
    It listens for POST requests and processes the incoming data.
    """
    # Get the JSON data sent from the React application
    event_data = request.get_json()

    # For now, we'll just print the data to the console to confirm
    # that our API is receiving it correctly.
    print("Received event:", event_data)

    # Send a success response back to the React app
    return jsonify({"status": "success", "message": "Event received"}), 200

if __name__ == '__main__':
    # Run the Flask app on port 5000 in debug mode.
    # Debug mode allows the server to auto-reload when you save changes.
    app.run(debug=True, port=5000)
