"""Vercel Serverless Function — Flight Price Comparison API."""

import hashlib
import json
import math
import os
import sys
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

# Add parent dir to path for data imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# --- Amadeus ---

_amadeus_client = None


def get_amadeus():
    global _amadeus_client
    if _amadeus_client is None:
        from amadeus import Amadeus

        _amadeus_client = Amadeus(
            client_id=os.getenv("AMADEUS_API_KEY"),
            client_secret=os.getenv("AMADEUS_API_SECRET"),
        )
    return _amadeus_client


def amadeus_available():
    return bool(os.getenv("AMADEUS_API_KEY") and os.getenv("AMADEUS_API_SECRET"))


# --- Airport Data (inline to avoid import issues on Vercel) ---

AIRPORTS = [
    {"iata": "TPE", "name": "Taoyuan International", "city": "Taipei", "country": "Taiwan", "name_ja": "桃園国際空港", "city_ja": "台北"},
    {"iata": "TSA", "name": "Songshan", "city": "Taipei", "country": "Taiwan", "name_ja": "松山空港", "city_ja": "台北"},
    {"iata": "ICN", "name": "Incheon International", "city": "Seoul", "country": "South Korea", "name_ja": "仁川国際空港", "city_ja": "ソウル"},
    {"iata": "GMP", "name": "Gimpo International", "city": "Seoul", "country": "South Korea", "name_ja": "金浦国際空港", "city_ja": "ソウル"},
    {"iata": "PUS", "name": "Gimhae International", "city": "Busan", "country": "South Korea", "name_ja": "金海国際空港", "city_ja": "釜山"},
    {"iata": "PEK", "name": "Capital International", "city": "Beijing", "country": "China", "name_ja": "首都国際空港", "city_ja": "北京"},
    {"iata": "PKX", "name": "Daxing International", "city": "Beijing", "country": "China", "name_ja": "大興国際空港", "city_ja": "北京"},
    {"iata": "PVG", "name": "Pudong International", "city": "Shanghai", "country": "China", "name_ja": "浦東国際空港", "city_ja": "上海"},
    {"iata": "SHA", "name": "Hongqiao International", "city": "Shanghai", "country": "China", "name_ja": "虹橋国際空港", "city_ja": "上海"},
    {"iata": "HKG", "name": "Hong Kong International", "city": "Hong Kong", "country": "China", "name_ja": "香港国際空港", "city_ja": "香港"},
    {"iata": "MFM", "name": "Macau International", "city": "Macau", "country": "China", "name_ja": "マカオ国際空港", "city_ja": "マカオ"},
    {"iata": "CAN", "name": "Baiyun International", "city": "Guangzhou", "country": "China", "name_ja": "白雲国際空港", "city_ja": "広州"},
    {"iata": "SZX", "name": "Bao'an International", "city": "Shenzhen", "country": "China", "name_ja": "宝安国際空港", "city_ja": "深圳"},
    {"iata": "BKK", "name": "Suvarnabhumi", "city": "Bangkok", "country": "Thailand", "name_ja": "スワンナプーム空港", "city_ja": "バンコク"},
    {"iata": "DMK", "name": "Don Mueang", "city": "Bangkok", "country": "Thailand", "name_ja": "ドンムアン空港", "city_ja": "バンコク"},
    {"iata": "CNX", "name": "Chiang Mai International", "city": "Chiang Mai", "country": "Thailand", "name_ja": "チェンマイ国際空港", "city_ja": "チェンマイ"},
    {"iata": "HKT", "name": "Phuket International", "city": "Phuket", "country": "Thailand", "name_ja": "プーケット国際空港", "city_ja": "プーケット"},
    {"iata": "SIN", "name": "Changi", "city": "Singapore", "country": "Singapore", "name_ja": "チャンギ空港", "city_ja": "シンガポール"},
    {"iata": "KUL", "name": "Kuala Lumpur International", "city": "Kuala Lumpur", "country": "Malaysia", "name_ja": "クアラルンプール国際空港", "city_ja": "クアラルンプール"},
    {"iata": "MNL", "name": "Ninoy Aquino International", "city": "Manila", "country": "Philippines", "name_ja": "ニノイ・アキノ国際空港", "city_ja": "マニラ"},
    {"iata": "CEB", "name": "Mactan-Cebu International", "city": "Cebu", "country": "Philippines", "name_ja": "マクタン・セブ国際空港", "city_ja": "セブ"},
    {"iata": "HAN", "name": "Noi Bai International", "city": "Hanoi", "country": "Vietnam", "name_ja": "ノイバイ国際空港", "city_ja": "ハノイ"},
    {"iata": "SGN", "name": "Tan Son Nhat International", "city": "Ho Chi Minh City", "country": "Vietnam", "name_ja": "タンソンニャット国際空港", "city_ja": "ホーチミン"},
    {"iata": "DAD", "name": "Da Nang International", "city": "Da Nang", "country": "Vietnam", "name_ja": "ダナン国際空港", "city_ja": "ダナン"},
    {"iata": "DPS", "name": "Ngurah Rai International", "city": "Bali", "country": "Indonesia", "name_ja": "ングラ・ライ国際空港", "city_ja": "バリ"},
    {"iata": "CGK", "name": "Soekarno-Hatta International", "city": "Jakarta", "country": "Indonesia", "name_ja": "スカルノ・ハッタ国際空港", "city_ja": "ジャカルタ"},
    {"iata": "PNH", "name": "Phnom Penh International", "city": "Phnom Penh", "country": "Cambodia", "name_ja": "プノンペン国際空港", "city_ja": "プノンペン"},
    {"iata": "REP", "name": "Siem Reap International", "city": "Siem Reap", "country": "Cambodia", "name_ja": "シェムリアップ国際空港", "city_ja": "シェムリアップ"},
    {"iata": "DEL", "name": "Indira Gandhi International", "city": "Delhi", "country": "India", "name_ja": "インディラ・ガンディー国際空港", "city_ja": "デリー"},
    {"iata": "BOM", "name": "Chhatrapati Shivaji Maharaj International", "city": "Mumbai", "country": "India", "name_ja": "チャトラパティ・シヴァージー国際空港", "city_ja": "ムンバイ"},
    {"iata": "DXB", "name": "Dubai International", "city": "Dubai", "country": "UAE", "name_ja": "ドバイ国際空港", "city_ja": "ドバイ"},
    {"iata": "DOH", "name": "Hamad International", "city": "Doha", "country": "Qatar", "name_ja": "ハマド国際空港", "city_ja": "ドーハ"},
    {"iata": "IST", "name": "Istanbul Airport", "city": "Istanbul", "country": "Turkey", "name_ja": "イスタンブール空港", "city_ja": "イスタンブール"},
    {"iata": "SYD", "name": "Kingsford Smith", "city": "Sydney", "country": "Australia", "name_ja": "シドニー空港", "city_ja": "シドニー"},
    {"iata": "MEL", "name": "Melbourne Airport", "city": "Melbourne", "country": "Australia", "name_ja": "メルボルン空港", "city_ja": "メルボルン"},
    {"iata": "AKL", "name": "Auckland Airport", "city": "Auckland", "country": "New Zealand", "name_ja": "オークランド空港", "city_ja": "オークランド"},
    {"iata": "GUM", "name": "Antonio B. Won Pat International", "city": "Guam", "country": "Guam", "name_ja": "グアム国際空港", "city_ja": "グアム"},
    {"iata": "LAX", "name": "Los Angeles International", "city": "Los Angeles", "country": "USA", "name_ja": "ロサンゼルス国際空港", "city_ja": "ロサンゼルス"},
    {"iata": "SFO", "name": "San Francisco International", "city": "San Francisco", "country": "USA", "name_ja": "サンフランシスコ国際空港", "city_ja": "サンフランシスコ"},
    {"iata": "JFK", "name": "John F. Kennedy International", "city": "New York", "country": "USA", "name_ja": "ジョン・F・ケネディ国際空港", "city_ja": "ニューヨーク"},
    {"iata": "SEA", "name": "Seattle-Tacoma International", "city": "Seattle", "country": "USA", "name_ja": "シアトル・タコマ国際空港", "city_ja": "シアトル"},
    {"iata": "HNL", "name": "Daniel K. Inouye International", "city": "Honolulu", "country": "USA", "name_ja": "ダニエル・K・イノウエ国際空港", "city_ja": "ホノルル"},
    {"iata": "YVR", "name": "Vancouver International", "city": "Vancouver", "country": "Canada", "name_ja": "バンクーバー国際空港", "city_ja": "バンクーバー"},
    {"iata": "LHR", "name": "Heathrow", "city": "London", "country": "UK", "name_ja": "ヒースロー空港", "city_ja": "ロンドン"},
    {"iata": "CDG", "name": "Charles de Gaulle", "city": "Paris", "country": "France", "name_ja": "シャルル・ド・ゴール空港", "city_ja": "パリ"},
    {"iata": "FRA", "name": "Frankfurt Airport", "city": "Frankfurt", "country": "Germany", "name_ja": "フランクフルト空港", "city_ja": "フランクフルト"},
    {"iata": "AMS", "name": "Schiphol", "city": "Amsterdam", "country": "Netherlands", "name_ja": "スキポール空港", "city_ja": "アムステルダム"},
    {"iata": "FCO", "name": "Leonardo da Vinci-Fiumicino", "city": "Rome", "country": "Italy", "name_ja": "フィウミチーノ空港", "city_ja": "ローマ"},
    {"iata": "BCN", "name": "Josep Tarradellas Barcelona-El Prat", "city": "Barcelona", "country": "Spain", "name_ja": "バルセロナ空港", "city_ja": "バルセロナ"},
    {"iata": "HEL", "name": "Helsinki-Vantaa", "city": "Helsinki", "country": "Finland", "name_ja": "ヘルシンキ・ヴァンター空港", "city_ja": "ヘルシンキ"},
]

# --- Demo Price Generator ---

DEMO_PRICES = {
    "HND": {"base": 35000, "variance": 15000},
    "NRT": {"base": 30000, "variance": 12000},
}


def generate_demo_prices(origin, destination, year, month):
    first_day = datetime(year, month, 1)
    if month == 12:
        next_month = datetime(year + 1, 1, 1)
    else:
        next_month = datetime(year, month + 1, 1)
    num_days = (next_month - first_day).days

    base = DEMO_PRICES.get(origin, DEMO_PRICES["NRT"])["base"]
    variance = DEMO_PRICES.get(origin, DEMO_PRICES["NRT"])["variance"]

    seed = hashlib.md5(f"{destination}".encode()).hexdigest()
    dest_offset = (int(seed[:4], 16) % 20000) - 5000

    results = []
    for day in range(1, num_days + 1):
        date = first_day + timedelta(days=day - 1)
        if date < datetime.now():
            continue

        dow = date.weekday()
        weekend_premium = 8000 if dow in (4, 5) else 0

        seasonal = int(variance * 0.5 * math.sin(2 * math.pi * (month - 3) / 12))

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
                "direct": day_hash % 3 != 0,
                "airline": ["ANA", "JAL", "Peach", "Jetstar", "Spring Japan"][day_hash % 5],
            }
        )
    return results


# --- Route Handlers ---


def handle_search(params):
    destination = params.get("destination", [""])[0].upper()
    try:
        year = int(params.get("year", [str(datetime.now().year)])[0])
        month = int(params.get("month", [str(datetime.now().month)])[0])
    except ValueError:
        return 400, {"error": "Invalid year or month"}

    if not destination:
        return 400, {"error": "destination is required"}

    origins = ["HND", "NRT"]

    if amadeus_available():
        return _search_amadeus(origins, destination, year, month)
    else:
        return _search_demo(origins, destination, year, month)


def _search_amadeus(origins, destination, year, month):
    amadeus = get_amadeus()
    results = {}

    for origin in origins:
        try:
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
            results[origin] = generate_demo_prices(origin, destination, year, month)
            results[f"{origin}_error"] = str(e)

    return 200, {
        "origins": results,
        "destination": destination,
        "year": year,
        "month": month,
        "data_source": "amadeus",
    }


def _search_demo(origins, destination, year, month):
    results = {}
    for origin in origins:
        results[origin] = generate_demo_prices(origin, destination, year, month)
    return 200, {
        "origins": results,
        "destination": destination,
        "year": year,
        "month": month,
        "data_source": "demo",
    }


def handle_airports(params):
    keyword = params.get("q", [""])[0].strip()
    if len(keyword) < 2:
        return 200, []

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
            return 200, airports
        except Exception:
            pass

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
    return 200, matches


# --- Vercel Handler ---


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        path = parsed.path

        if path == "/api/search":
            status, body = handle_search(params)
        elif path == "/api/airports":
            status, body = handle_airports(params)
        else:
            status, body = 404, {"error": "Not found"}

        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(body, ensure_ascii=False).encode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
