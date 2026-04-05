"""Flight Price Comparison API - Local dev server (Flask).

Mirrors the Vercel serverless function in api/index.py for local development.
"""

import os

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

load_dotenv()

app = Flask(__name__, static_folder="public", static_url_path="")
CORS(app)

# Import handlers from vercel function
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "api"))
from index import handle_search, handle_airports, handle_destinations, AIRPORTS  # noqa: E402


@app.route("/")
def index():
    return send_from_directory("public", "index.html")


@app.route("/destinations/<code>")
def destination_page(code):
    return send_from_directory("public", "destination.html")


@app.route("/api/search")
def api_search():
    params = {k: [v] for k, v in request.args.items()}
    status, body = handle_search(params)
    return jsonify(body), status


@app.route("/api/airports")
def api_airports():
    params = {k: [v] for k, v in request.args.items()}
    status, body = handle_airports(params)
    return jsonify(body), status


@app.route("/api/destinations")
def api_destinations():
    status, body = handle_destinations({})
    return jsonify(body), status


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
