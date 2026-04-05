"""Vercel Serverless Function — Flight Price Comparison API (Kiwi/Tequila)."""

import hashlib
import json
import math
import os
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen
from urllib.error import URLError

TEQUILA_BASE = "https://tequila-api.kiwi.com"

# --- Airport Data ---

AIRPORTS = [
    {"iata": "TPE", "name": "Taoyuan International", "city": "Taipei", "country": "Taiwan", "name_ja": "桃園国際空港", "city_ja": "台北", "flag": "🇹🇼"},
    {"iata": "TSA", "name": "Songshan", "city": "Taipei", "country": "Taiwan", "name_ja": "松山空港", "city_ja": "台北", "flag": "🇹🇼"},
    {"iata": "ICN", "name": "Incheon International", "city": "Seoul", "country": "South Korea", "name_ja": "仁川国際空港", "city_ja": "ソウル", "flag": "🇰🇷"},
    {"iata": "GMP", "name": "Gimpo International", "city": "Seoul", "country": "South Korea", "name_ja": "金浦国際空港", "city_ja": "ソウル", "flag": "🇰🇷"},
    {"iata": "PUS", "name": "Gimhae International", "city": "Busan", "country": "South Korea", "name_ja": "金海国際空港", "city_ja": "釜山", "flag": "🇰🇷"},
    {"iata": "PEK", "name": "Capital International", "city": "Beijing", "country": "China", "name_ja": "首都国際空港", "city_ja": "北京", "flag": "🇨🇳"},
    {"iata": "PKX", "name": "Daxing International", "city": "Beijing", "country": "China", "name_ja": "大興国際空港", "city_ja": "北京", "flag": "🇨🇳"},
    {"iata": "PVG", "name": "Pudong International", "city": "Shanghai", "country": "China", "name_ja": "浦東国際空港", "city_ja": "上海", "flag": "🇨🇳"},
    {"iata": "SHA", "name": "Hongqiao International", "city": "Shanghai", "country": "China", "name_ja": "虹橋国際空港", "city_ja": "上海", "flag": "🇨🇳"},
    {"iata": "HKG", "name": "Hong Kong International", "city": "Hong Kong", "country": "China", "name_ja": "香港国際空港", "city_ja": "香港", "flag": "🇭🇰"},
    {"iata": "MFM", "name": "Macau International", "city": "Macau", "country": "China", "name_ja": "マカオ国際空港", "city_ja": "マカオ", "flag": "🇲🇴"},
    {"iata": "CAN", "name": "Baiyun International", "city": "Guangzhou", "country": "China", "name_ja": "白雲国際空港", "city_ja": "広州", "flag": "🇨🇳"},
    {"iata": "SZX", "name": "Bao'an International", "city": "Shenzhen", "country": "China", "name_ja": "宝安国際空港", "city_ja": "深圳", "flag": "🇨🇳"},
    {"iata": "BKK", "name": "Suvarnabhumi", "city": "Bangkok", "country": "Thailand", "name_ja": "スワンナプーム空港", "city_ja": "バンコク", "flag": "🇹🇭"},
    {"iata": "DMK", "name": "Don Mueang", "city": "Bangkok", "country": "Thailand", "name_ja": "ドンムアン空港", "city_ja": "バンコク", "flag": "🇹🇭"},
    {"iata": "CNX", "name": "Chiang Mai International", "city": "Chiang Mai", "country": "Thailand", "name_ja": "チェンマイ国際空港", "city_ja": "チェンマイ", "flag": "🇹🇭"},
    {"iata": "HKT", "name": "Phuket International", "city": "Phuket", "country": "Thailand", "name_ja": "プーケット国際空港", "city_ja": "プーケット", "flag": "🇹🇭"},
    {"iata": "SIN", "name": "Changi", "city": "Singapore", "country": "Singapore", "name_ja": "チャンギ空港", "city_ja": "シンガポール", "flag": "🇸🇬"},
    {"iata": "KUL", "name": "Kuala Lumpur International", "city": "Kuala Lumpur", "country": "Malaysia", "name_ja": "クアラルンプール国際空港", "city_ja": "クアラルンプール", "flag": "🇲🇾"},
    {"iata": "MNL", "name": "Ninoy Aquino International", "city": "Manila", "country": "Philippines", "name_ja": "ニノイ・アキノ国際空港", "city_ja": "マニラ", "flag": "🇵🇭"},
    {"iata": "CEB", "name": "Mactan-Cebu International", "city": "Cebu", "country": "Philippines", "name_ja": "マクタン・セブ国際空港", "city_ja": "セブ", "flag": "🇵🇭"},
    {"iata": "HAN", "name": "Noi Bai International", "city": "Hanoi", "country": "Vietnam", "name_ja": "ノイバイ国際空港", "city_ja": "ハノイ", "flag": "🇻🇳"},
    {"iata": "SGN", "name": "Tan Son Nhat International", "city": "Ho Chi Minh City", "country": "Vietnam", "name_ja": "タンソンニャット国際空港", "city_ja": "ホーチミン", "flag": "🇻🇳"},
    {"iata": "DAD", "name": "Da Nang International", "city": "Da Nang", "country": "Vietnam", "name_ja": "ダナン国際空港", "city_ja": "ダナン", "flag": "🇻🇳"},
    {"iata": "DPS", "name": "Ngurah Rai International", "city": "Bali", "country": "Indonesia", "name_ja": "ングラ・ライ国際空港", "city_ja": "バリ", "flag": "🇮🇩"},
    {"iata": "CGK", "name": "Soekarno-Hatta International", "city": "Jakarta", "country": "Indonesia", "name_ja": "スカルノ・ハッタ国際空港", "city_ja": "ジャカルタ", "flag": "🇮🇩"},
    {"iata": "PNH", "name": "Phnom Penh International", "city": "Phnom Penh", "country": "Cambodia", "name_ja": "プノンペン国際空港", "city_ja": "プノンペン", "flag": "🇰🇭"},
    {"iata": "REP", "name": "Siem Reap International", "city": "Siem Reap", "country": "Cambodia", "name_ja": "シェムリアップ国際空港", "city_ja": "シェムリアップ", "flag": "🇰🇭"},
    {"iata": "DEL", "name": "Indira Gandhi International", "city": "Delhi", "country": "India", "name_ja": "インディラ・ガンディー国際空港", "city_ja": "デリー", "flag": "🇮🇳"},
    {"iata": "BOM", "name": "Chhatrapati Shivaji Maharaj International", "city": "Mumbai", "country": "India", "name_ja": "チャトラパティ・シヴァージー国際空港", "city_ja": "ムンバイ", "flag": "🇮🇳"},
    {"iata": "DXB", "name": "Dubai International", "city": "Dubai", "country": "UAE", "name_ja": "ドバイ国際空港", "city_ja": "ドバイ", "flag": "🇦🇪"},
    {"iata": "DOH", "name": "Hamad International", "city": "Doha", "country": "Qatar", "name_ja": "ハマド国際空港", "city_ja": "ドーハ", "flag": "🇶🇦"},
    {"iata": "IST", "name": "Istanbul Airport", "city": "Istanbul", "country": "Turkey", "name_ja": "イスタンブール空港", "city_ja": "イスタンブール", "flag": "🇹🇷"},
    {"iata": "SYD", "name": "Kingsford Smith", "city": "Sydney", "country": "Australia", "name_ja": "シドニー空港", "city_ja": "シドニー", "flag": "🇦🇺"},
    {"iata": "MEL", "name": "Melbourne Airport", "city": "Melbourne", "country": "Australia", "name_ja": "メルボルン空港", "city_ja": "メルボルン", "flag": "🇦🇺"},
    {"iata": "AKL", "name": "Auckland Airport", "city": "Auckland", "country": "New Zealand", "name_ja": "オークランド空港", "city_ja": "オークランド", "flag": "🇳🇿"},
    {"iata": "GUM", "name": "Antonio B. Won Pat International", "city": "Guam", "country": "Guam", "name_ja": "グアム国際空港", "city_ja": "グアム", "flag": "🇬🇺"},
    {"iata": "LAX", "name": "Los Angeles International", "city": "Los Angeles", "country": "USA", "name_ja": "ロサンゼルス国際空港", "city_ja": "ロサンゼルス", "flag": "🇺🇸"},
    {"iata": "SFO", "name": "San Francisco International", "city": "San Francisco", "country": "USA", "name_ja": "サンフランシスコ国際空港", "city_ja": "サンフランシスコ", "flag": "🇺🇸"},
    {"iata": "JFK", "name": "John F. Kennedy International", "city": "New York", "country": "USA", "name_ja": "ジョン・F・ケネディ国際空港", "city_ja": "ニューヨーク", "flag": "🇺🇸"},
    {"iata": "SEA", "name": "Seattle-Tacoma International", "city": "Seattle", "country": "USA", "name_ja": "シアトル・タコマ国際空港", "city_ja": "シアトル", "flag": "🇺🇸"},
    {"iata": "HNL", "name": "Daniel K. Inouye International", "city": "Honolulu", "country": "USA", "name_ja": "ダニエル・K・イノウエ国際空港", "city_ja": "ホノルル", "flag": "🌺"},
    {"iata": "YVR", "name": "Vancouver International", "city": "Vancouver", "country": "Canada", "name_ja": "バンクーバー国際空港", "city_ja": "バンクーバー", "flag": "🇨🇦"},
    {"iata": "LHR", "name": "Heathrow", "city": "London", "country": "UK", "name_ja": "ヒースロー空港", "city_ja": "ロンドン", "flag": "🇬🇧"},
    {"iata": "CDG", "name": "Charles de Gaulle", "city": "Paris", "country": "France", "name_ja": "シャルル・ド・ゴール空港", "city_ja": "パリ", "flag": "🇫🇷"},
    {"iata": "FRA", "name": "Frankfurt Airport", "city": "Frankfurt", "country": "Germany", "name_ja": "フランクフルト空港", "city_ja": "フランクフルト", "flag": "🇩🇪"},
    {"iata": "AMS", "name": "Schiphol", "city": "Amsterdam", "country": "Netherlands", "name_ja": "スキポール空港", "city_ja": "アムステルダム", "flag": "🇳🇱"},
    {"iata": "FCO", "name": "Leonardo da Vinci-Fiumicino", "city": "Rome", "country": "Italy", "name_ja": "フィウミチーノ空港", "city_ja": "ローマ", "flag": "🇮🇹"},
    {"iata": "BCN", "name": "Josep Tarradellas Barcelona-El Prat", "city": "Barcelona", "country": "Spain", "name_ja": "バルセロナ空港", "city_ja": "バルセロナ", "flag": "🇪🇸"},
    {"iata": "HEL", "name": "Helsinki-Vantaa", "city": "Helsinki", "country": "Finland", "name_ja": "ヘルシンキ・ヴァンター空港", "city_ja": "ヘルシンキ", "flag": "🇫🇮"},
]

AIRPORT_MAP = {a["iata"]: a for a in AIRPORTS}


# --- Kiwi/Tequila API ---

def tequila_available():
    return bool(os.getenv("KIWI_API_KEY"))


def tequila_request(endpoint, params):
    """Make a request to the Tequila API."""
    api_key = os.getenv("KIWI_API_KEY")
    query = "&".join(f"{k}={v}" for k, v in params.items())
    url = f"{TEQUILA_BASE}{endpoint}?{query}"
    req = Request(url, headers={"apikey": api_key})
    with urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def search_kiwi(origin, destination, date_from, date_to):
    """Search flights via Kiwi/Tequila API for a date range.

    Returns list of cheapest flight per day.
    """
    params = {
        "fly_from": origin,
        "fly_to": destination,
        "date_from": date_from.strftime("%d/%m/%Y"),
        "date_to": date_to.strftime("%d/%m/%Y"),
        "flight_type": "oneway",
        "curr": "JPY",
        "locale": "ja",
        "limit": 300,
        "sort": "price",
        "max_stopovers": 2,
    }
    data = tequila_request("/v2/search", params)

    # Group by departure date and keep cheapest per day
    by_date = {}
    for flight in data.get("data", []):
        dep_date = flight["local_departure"][:10]  # YYYY-MM-DD
        price = flight["price"]
        if dep_date not in by_date or price < by_date[dep_date]["price"]:
            airlines = list({r["airline"] for r in flight.get("route", [])})
            stopovers = len(flight.get("route", [])) - 1
            by_date[dep_date] = {
                "date": dep_date,
                "price": price,
                "currency": "JPY",
                "origin": origin,
                "destination": destination,
                "direct": stopovers == 0,
                "stopovers": stopovers,
                "airline": ", ".join(airlines[:2]),
                "deep_link": flight.get("deep_link", ""),
                "departure_time": flight["local_departure"][11:16],
                "arrival_time": flight["local_arrival"][11:16],
                "duration_hours": round(flight.get("duration", {}).get("departure", 0) / 3600, 1),
            }
    return sorted(by_date.values(), key=lambda x: x["date"])


# --- Demo Price Generator (fallback) ---

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

        results.append({
            "date": date.strftime("%Y-%m-%d"),
            "price": price,
            "currency": "JPY",
            "origin": origin,
            "destination": destination,
            "direct": day_hash % 3 != 0,
            "stopovers": 0 if day_hash % 3 != 0 else 1,
            "airline": ["ANA", "JAL", "Peach", "Jetstar", "Spring Japan"][day_hash % 5],
            "deep_link": "",
            "departure_time": f"{9 + day_hash % 12:02d}:00",
            "arrival_time": f"{12 + day_hash % 10:02d}:30",
            "duration_hours": round(2.5 + (day_hash % 20) / 10, 1),
        })
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

    # Calculate date range for the month
    first_day = datetime(year, month, 1)
    if month == 12:
        last_day = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = datetime(year, month + 1, 1) - timedelta(days=1)

    # Don't search past dates
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    if first_day < today:
        first_day = today

    if last_day < today:
        return 200, {
            "origins": {"HND": [], "NRT": []},
            "destination": destination,
            "year": year,
            "month": month,
            "data_source": "none",
        }

    results = {}
    data_source = "demo"

    if tequila_available():
        data_source = "kiwi"
        for origin in origins:
            try:
                results[origin] = search_kiwi(origin, destination, first_day, last_day)
            except Exception as e:
                results[origin] = generate_demo_prices(origin, destination, year, month)
                results[f"{origin}_error"] = str(e)
    else:
        for origin in origins:
            results[origin] = generate_demo_prices(origin, destination, year, month)

    # Airport info for the destination
    dest_info = AIRPORT_MAP.get(destination, {"iata": destination, "city_ja": destination, "name_ja": "", "flag": ""})

    return 200, {
        "origins": results,
        "destination": destination,
        "destination_info": dest_info,
        "year": year,
        "month": month,
        "data_source": data_source,
    }


def handle_airports(params):
    keyword = params.get("q", [""])[0].strip()
    if len(keyword) < 2:
        return 200, []

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


def handle_destinations(params):
    """Return all available destinations for the top page."""
    return 200, AIRPORTS


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
        elif path == "/api/destinations":
            status, body = handle_destinations(params)
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
