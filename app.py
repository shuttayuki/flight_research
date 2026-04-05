"""Flight Price Comparison API - Find cheapest flights from HND/NRT."""

import os
from datetime import datetime, timedelta

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

load_dotenv()

app = Flask(__name__, static_folder="static", static_url_path="")
CORS(app)

# --- Amadeus API Client ---

_amadeus_client = None


def get_amadeus():
    """Lazy-initialize Amadeus client."""
    global _amadeus_client
    if _amadeus_client is None:
        from amadeus import Amadeus

        _amadeus_client = Amadeus(
            client_id=os.getenv("AMADEUS_API_KEY"),
            client_secret=os.getenv("AMADEUS_API_SECRET"),
        )
    return _amadeus_client


def amadeus_available():
    """Check if Amadeus credentials are configured."""
    return os.getenv("AMADEUS_API_KEY") and os.getenv("AMADEUS_API_SECRET")


# --- Demo Data (used when Amadeus API key is not configured) ---

DEMO_PRICES = {
    "HND": {"base": 35000, "variance": 15000},
    "NRT": {"base": 30000, "variance": 12000},
}


def generate_demo_prices(origin, destination, year, month):
    """Generate realistic-looking demo price data for a month."""
    import hashlib
    import math

    first_day = datetime(year, month, 1)
    if month == 12:
        next_month = datetime(year + 1, 1, 1)
    else:
        next_month = datetime(year, month + 1, 1)
    num_days = (next_month - first_day).days

    base = DEMO_PRICES.get(origin, DEMO_PRICES["NRT"])["base"]
    variance = DEMO_PRICES.get(origin, DEMO_PRICES["NRT"])["variance"]

    # Destination-based offset
    seed = hashlib.md5(f"{destination}".encode()).hexdigest()
    dest_offset = (int(seed[:4], 16) % 20000) - 5000

    results = []
    for day in range(1, num_days + 1):
        date = first_day + timedelta(days=day - 1)
        if date < datetime.now():
            continue

        # Price varies by day of week (weekends more expensive)
        dow = date.weekday()
        weekend_premium = 8000 if dow in (4, 5) else 0  # Fri/Sat departure

        # Seasonal variation
        seasonal = int(variance * 0.5 * math.sin(2 * math.pi * (month - 3) / 12))

        # Day-specific pseudo-random variation
        day_hash = int(
            hashlib.md5(f"{origin}{destination}{date}".encode()).hexdigest()[:6], 16
        )
        day_variance = (day_hash % variance) - variance // 2

        price = max(15000, base + dest_offset + weekend_premium + seasonal + day_variance)

        results.append(
            {
                "date": date.strftime("%Y-%m-%d"),
                "price": price,
                "currency": "JPY",
                "origin": origin,
                "destination": destination,
                "direct": day_hash % 3 != 0,  # ~66% direct flights
                "airline": ["ANA", "JAL", "Peach", "Jetstar", "Spring Japan"][
                    day_hash % 5
                ],
            }
        )
    return results


# --- API Routes ---


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/search", methods=["GET"])
def search_prices():
    """Search flight prices for a given destination and month.

    Query params:
        destination: IATA airport code (e.g., TPE, BKK, ICN)
        year: Year (e.g., 2026)
        month: Month (1-12)
    """
    destination = request.args.get("destination", "").upper()
    try:
        year = int(request.args.get("year", datetime.now().year))
        month = int(request.args.get("month", datetime.now().month))
    except ValueError:
        return jsonify({"error": "Invalid year or month"}), 400

    if not destination:
        return jsonify({"error": "destination is required"}), 400

    origins = ["HND", "NRT"]

    if amadeus_available():
        return _search_amadeus(origins, destination, year, month)
    else:
        return _search_demo(origins, destination, year, month)


def _search_amadeus(origins, destination, year, month):
    """Search using Amadeus API."""
    amadeus = get_amadeus()
    results = {}

    for origin in origins:
        try:
            # Use Flight Offers Search for cheapest prices
            first_day = datetime(year, month, 1)
            if month == 12:
                last_day = datetime(year + 1, 1, 1) - timedelta(days=1)
            else:
                last_day = datetime(year, month + 1, 1) - timedelta(days=1)

            response = amadeus.shopping.flight_dates.get(
                origin=origin,
                destination=destination,
                departureDate=f"{year}-{month:02d}-01",
                oneWay=True,
            )

            prices = []
            for offer in response.data:
                dep_date = offer["departureDate"]
                price_info = offer["price"]
                prices.append(
                    {
                        "date": dep_date,
                        "price": int(float(price_info["total"])),
                        "currency": price_info.get("currency", "JPY"),
                        "origin": origin,
                        "destination": destination,
                        "direct": offer.get("links", {}).get("flightOffers", "").find("nonstop") >= 0,
                        "airline": "",
                    }
                )
            results[origin] = prices

        except Exception as e:
            # Fallback to demo data for this origin
            results[origin] = generate_demo_prices(origin, destination, year, month)
            results[f"{origin}_error"] = str(e)

    return jsonify(
        {
            "origins": results,
            "destination": destination,
            "year": year,
            "month": month,
            "data_source": "amadeus",
        }
    )


def _search_demo(origins, destination, year, month):
    """Search using demo data."""
    results = {}
    for origin in origins:
        results[origin] = generate_demo_prices(origin, destination, year, month)

    return jsonify(
        {
            "origins": results,
            "destination": destination,
            "year": year,
            "month": month,
            "data_source": "demo",
        }
    )


@app.route("/api/airports", methods=["GET"])
def search_airports():
    """Search airports by keyword."""
    keyword = request.args.get("q", "").strip()
    if len(keyword) < 2:
        return jsonify([])

    if amadeus_available():
        try:
            amadeus = get_amadeus()
            response = amadeus.reference_data.locations.get(
                keyword=keyword,
                subType="AIRPORT",
            )
            airports = [
                {
                    "iata": loc["iataCode"],
                    "name": loc["name"],
                    "city": loc.get("address", {}).get("cityName", ""),
                    "country": loc.get("address", {}).get("countryName", ""),
                }
                for loc in response.data[:10]
            ]
            return jsonify(airports)
        except Exception:
            pass

    # Fallback: static airport list
    return jsonify(_search_static_airports(keyword))


def _search_static_airports(keyword):
    """Search from built-in airport data."""
    from data.airports import AIRPORTS

    keyword_lower = keyword.lower()
    matches = []
    for apt in AIRPORTS:
        if (
            keyword_lower in apt["iata"].lower()
            or keyword_lower in apt["name"].lower()
            or keyword_lower in apt["city"].lower()
            or keyword_lower in apt.get("name_ja", "").lower()
            or keyword_lower in apt.get("city_ja", "").lower()
        ):
            matches.append(apt)
        if len(matches) >= 10:
            break
    return matches


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
