import base64
import hashlib
import hmac
import os
import secrets
from datetime import datetime
from urllib.parse import quote_plus

import pandas as pd
import requests
import streamlit as st
from sqlalchemy import create_engine, text

from dotenv import load_dotenv
load_dotenv(".env")


def hash_password(password):
    if not password:
        raise ValueError("Password is required")
    salt = secrets.token_hex(16)
    iterations = 200_000
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations)
    digest = base64.urlsafe_b64encode(key).decode("utf-8").rstrip("=")
    return f"pbkdf2_sha256${iterations}${salt}${digest}"


def verify_password(password, stored_password):
    if not password or not stored_password:
        return False
    stored_password = str(stored_password)
    if stored_password.startswith("pbkdf2_sha256$"):
        try:
            _, iterations, salt, digest = stored_password.split("$")
            iterations = int(iterations)
            key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations)
            candidate = base64.urlsafe_b64encode(key).decode("utf-8").rstrip("=")
            return hmac.compare_digest(candidate, digest)
        except (ValueError, TypeError):
            return False
    return hmac.compare_digest(password, stored_password)


def compute_order_totals(cart, delivery_fee=0):
    subtotal = sum(info["qty"] * info["price"] for info in cart.values())
    total = subtotal + delivery_fee
    return subtotal, delivery_fee, total


def summarize_order_history(orders):
    rows = []
    for order in orders:
        rows.append({
            "id": order.get("id"),
            "restaurant": order.get("restaurant"),
            "items": order.get("items", ""),
            "status": order.get("status", "Placed"),
            "total": int(float(order.get("total", 0) or 0)),
            "created_at": order.get("created_at"),
        })
    return rows


def filter_hotels(hotels, query="", cuisine="All", sort_by="rating"):
    query = (query or "").strip().lower()
    filtered = {}
    for name, hotel in hotels.items():
        cuisine_name = hotel.get("cuisine", "")
        if query and query not in name.lower() and query not in cuisine_name.lower():
            continue
        if cuisine != "All" and cuisine_name != cuisine:
            continue
        filtered[name] = hotel

    if sort_by == "rating":
        filtered = dict(sorted(filtered.items(), key=lambda item: item[1].get("rating", 0), reverse=True))
    elif sort_by == "name":
        filtered = dict(sorted(filtered.items()))
    return filtered


def estimate_delivery_distance_km(start, end):
    start_lat, start_lon = start
    end_lat, end_lon = end
    delta_lat = abs(end_lat - start_lat)
    delta_lon = abs(end_lon - start_lon)
    return max(0.5, (delta_lat * 111) + (delta_lon * 111 * 0.7))


def calculate_eta_minutes(distance_km, prep_minutes=15, traffic_factor=1.0):
    base_eta = prep_minutes + max(10, distance_km * 8)
    return int(base_eta * traffic_factor)


def summarize_admin_dashboard(orders):
    status_counts = {"Placed": 0, "Preparing": 0, "Out for Delivery": 0, "Delivered": 0}
    revenue = 0
    for order in orders:
        status = order.get("status", "Placed")
        if status in status_counts:
            status_counts[status] += 1
        revenue += int(float(order.get("total", 0) or 0))
    open_orders = sum(1 for order in orders if order.get("status") != "Delivered")
    return {"revenue": revenue, "status_counts": status_counts, "open_orders": open_orders}


def filter_dashboard_orders(orders, status="All", restaurant="All"):
    filtered = []
    for order in orders:
        if status != "All" and order.get("status") != status:
            continue
        if restaurant != "All" and order.get("restaurant") != restaurant:
            continue
        filtered.append(order)
    return filtered


def build_active_delivery_cards(orders):
    colors = {"Placed": "gray", "Preparing": "orange", "Out for Delivery": "red", "Delivered": "green"}
    cards = []
    for order in orders:
        status = order.get("status", "Placed")
        cards.append({
            "id": order.get("id"),
            "restaurant": order.get("restaurant", "Unknown"),
            "status": status,
            "total": int(float(order.get("total", 0) or 0)),
            "color": colors.get(status, "gray"),
        })
    return cards


def build_order_timeline(orders):
    timeline = {"Placed": [], "Preparing": [], "Out for Delivery": [], "Delivered": []}
    for order in orders:
        status = order.get("status", "Placed")
        if status in timeline:
            timeline[status].append({"id": order.get("id"), "restaurant": order.get("restaurant"), "total": int(float(order.get("total", 0) or 0))})
    return timeline


def build_active_driver_map(orders):
    points = []
    for index, order in enumerate(orders):
        if order.get("status") in {"Preparing", "Out for Delivery"}:
            points.append({
                "id": order.get("id"),
                "lat": 12.9716 + (index + 1) * 0.004,
                "lon": 77.5946 + (index + 1) * 0.003,
                "status": order.get("status", "Preparing"),
                "restaurant": order.get("restaurant", "Unknown"),
            })
    return points


def determine_user_navigation(email, owner_email):
    email = (email or "").strip().lower()
    owner_email = (owner_email or "").strip().lower()
    nav = ["Home", "Orders", "Tracking", "Profile"]
    if email == owner_email:
        nav.append("Admin")
    return nav


def delivery_status_steps(current_status):
    steps = ["Placed", "Preparing", "Out for Delivery", "Delivered"]
    status_index = steps.index(current_status) if current_status in steps else 0
    return [
        {"name": step, "completed": index < status_index, "active": index == status_index}
        for index, step in enumerate(steps)
    ]


def generate_delivery_route(start, end, points=3):
    start_lat, start_lon = start
    end_lat, end_lon = end
    route = []
    for i in range(points):
        ratio = i / max(1, points - 1)
        lat = start_lat + (end_lat - start_lat) * ratio
        lon = start_lon + (end_lon - start_lon) * ratio
        route.append((lat, lon))
    return route


def live_status(created_at):
    created_at = datetime.fromisoformat(created_at) if isinstance(created_at, str) else created_at
    seconds = (datetime.now() - created_at).total_seconds()
    return "Delivered" if seconds > 180 else "Out for Delivery" if seconds > 120 else "Preparing" if seconds > 60 else "Placed"


def bill(order, user):
    items = "\n".join(f"- {item}" for item in order['items'].split(", "))
    return "\n".join([
        "GoBite Bill",
        f"Customer: {user['name']}",
        f"Hotel: {order['restaurant']}",
        f"Items:\n{items}",
        f"Total: Rs {int(order['total'])}",
        f"Status: {order['status']}",
        f"Time: {order['created_at']}",
    ])


@st.cache_data(ttl=3600)
def geocode(address):
    if not os.getenv("RAPIDAPI_KEY"):
        return 12.9716, 77.5946
    resp = requests.get(
        f"https://{os.getenv('RAPIDAPI_GEO_HOST', 'forward-reverse-geocoding.p.rapidapi.com')}/v1/search",
        headers={"X-RapidAPI-Key": os.getenv("RAPIDAPI_KEY"), "X-RapidAPI-Host": os.getenv("RAPIDAPI_GEO_HOST", "forward-reverse-geocoding.p.rapidapi.com")},
        params={"q": address, "accept-language": "en", "polygon_threshold": "0.0"},
        timeout=10,
    )
    first = resp.json()[0]
    return float(first["lat"]), float(first["lon"])


@st.cache_data(ttl=3600)
def recipes():
    return requests.get("https://dummyjson.com/recipes?limit=0&select=name,cuisine,rating,image,caloriesPerServing", timeout=10).json()["recipes"]


def cuisine_for(name):
    text_name = name.lower()
    for word, cuisine in (("dosa", "Indian"), ("udupi", "Indian"), ("kachori", "Indian"), ("pizza", "Italian"), ("pasta", "Italian"), ("biryani", "Pakistani"), ("kebab", "Pakistani"), ("karahi", "Pakistani"), ("mughlai", "Pakistani")):
        if word in text_name:
            return cuisine
    return ("Indian", "Italian", "Pakistani")[sum(map(ord, text_name)) % 3]


@st.cache_data(ttl=1800)
def nearby_hotels(address):
    places = requests.get("https://nominatim.openstreetmap.org/search", params={"q": f"restaurants in {address}", "format": "jsonv2", "limit": 6}, headers={"User-Agent": "gobite-app"}, timeout=20).json()
    data = {}
    for place in places:
        name = place.get("name") or place["display_name"].split(",")[0]
        cuisine = cuisine_for(f"{name} {place['display_name']}")
        menu = [r for r in recipes() if r["cuisine"] == cuisine or cuisine == "Indian" and any(k in r["name"].lower() for k in ("dosa", "lassi"))][:4]
        if menu:
            data[name] = {"cuisine": cuisine, "lat": float(place["lat"]), "lon": float(place["lon"]), "menu": menu, "rating": round(sum(i["rating"] for i in menu) / len(menu), 1)}
    return data


def build_engine():
    db_user = os.getenv("DB_USER")
    db_host = os.getenv("DB_HOST")
    db_name = os.getenv("DB_NAME")
    if not all([db_user, db_host, db_name]):
        return None
    return create_engine(
        f"mysql+pymysql://{db_user}:{quote_plus(os.getenv('DB_PASSWORD', ''))}@{db_host}:{os.getenv('DB_PORT', '3306')}/{db_name}",
        pool_pre_ping=True,
    )


engine = build_engine()
if engine is not None:
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE IF NOT EXISTS users (id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(120), email VARCHAR(160) UNIQUE, password VARCHAR(120), address VARCHAR(255), lat DOUBLE, lng DOUBLE)"))
        conn.execute(text("CREATE TABLE IF NOT EXISTS orders (id INT AUTO_INCREMENT PRIMARY KEY, user_id INT, restaurant VARCHAR(120), items TEXT, total DOUBLE, status VARCHAR(40) DEFAULT 'Placed', created_at DATETIME DEFAULT CURRENT_TIMESTAMP)"))

def main():
    st.set_page_config(page_title="GoBite", page_icon="🛵", layout="wide")
    st.markdown(
        """
        <style>
        .stApp { background: linear-gradient(180deg, #fff7ed 0%, #f8fafc 100%); }
        div[data-testid="stHorizontalBlock"] > div { border-radius: 16px; }
        .stButton > button {
            background: linear-gradient(90deg, #f97316, #fb7185);
            color: white;
            border: none;
            border-radius: 12px;
            font-weight: 700;
            padding: 0.65rem 1.1rem;
            box-shadow: 0 6px 18px rgba(249,115,22,0.25);
        }
        .stProgress > div > div { background: linear-gradient(90deg, #f97316, #ef4444); }
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0b1120 0%, #111827 100%);
            color: white;
        }
        [data-testid="stSidebar"] .stMarkdown, [data-testid="stSidebar"] .stSelectbox, [data-testid="stSidebar"] .stRadio {
            color: white;
        }
        [data-testid="stSidebar"] .stButton > button {
            background: linear-gradient(90deg, #fb7185, #f97316);
            border: none;
            width: 100%;
        }
        [data-testid="stSidebarNavLink"] {
            border-radius: 10px;
            padding: 0.5rem 0.7rem;
            font-weight: 600;
            letter-spacing: 0.02em;
        }
        [data-testid="stSidebarNavLink"]:hover {
            background: rgba(255,255,255,0.06);
        }
        [data-testid="stSidebarNavLink"][aria-current="page"] {
            background: linear-gradient(90deg, rgba(249,115,22,0.2), rgba(251,113,133,0.12));
            border: 1px solid rgba(249,115,22,0.3);
            color: #fff;
        }
        .admin-metric-strip {
            display: flex;
            gap: 0.8rem;
            flex-wrap: wrap;
            margin: 0.8rem 0 1rem;
        }
        .admin-metric-pill {
            flex: 1 1 150px;
            background: linear-gradient(180deg, #111827, #1f2937);
            border: 1px solid rgba(148,163,184,0.22);
            border-radius: 14px;
            padding: 0.8rem 1rem;
            color: white;
            min-width: 150px;
        }
        .admin-metric-pill .small {
            font-size: 0.7rem;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: #cbd5e1;
        }
        .admin-metric-pill .big {
            font-size: 1.5rem;
            font-weight: 800;
            margin-top: 0.2rem;
        }
        .gobite-sidebar-box {
            background: rgba(255,255,255,0.06);
            border: 1px solid rgba(255,255,255,0.12);
            border-radius: 18px;
            padding: 1rem;
            margin-bottom: 1rem;
        }
        .gobite-admin-badge {
            display: inline-block;
            background: linear-gradient(90deg, #7f1d1d, #c2410c);
            color: white;
            border-radius: 999px;
            padding: 0.38rem 0.8rem;
            font-size: 0.72rem;
            font-weight: 800;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            box-shadow: 0 8px 24px rgba(194,65,12,0.35);
        }
        .gobite-owner-gate {
            background: linear-gradient(135deg, #111827 0%, #1f2937 45%, #7f1d1d 100%);
            border: 1px solid rgba(251,146,60,0.4);
            border-radius: 20px;
            padding: 1rem 1.1rem;
            margin-bottom: 1rem;
            box-shadow: 0 12px 30px rgba(15,23,42,0.28);
        }
        .gobite-owner-gate .secure-label {
            display: inline-block;
            background: rgba(251,146,60,0.14);
            border: 1px solid rgba(251,146,60,0.3);
            border-radius: 999px;
            color: #fbbf24;
            padding: 0.35rem 0.8rem;
            font-size: 0.72rem;
            font-weight: 800;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }
        .admin-command {
            background: linear-gradient(180deg, #0f172a 0%, #111827 100%);
            border: 1px solid rgba(148,163,184,0.2);
            border-radius: 22px;
            padding: 1.2rem;
            box-shadow: 0 10px 30px rgba(15,23,42,0.25);
        }
        .admin-topbar {
            background: linear-gradient(90deg, #111827 0%, #1f2937 35%, #111827 100%);
            border: 1px solid rgba(148,163,184,0.18);
            border-radius: 18px;
            padding: 0.9rem 1rem;
            margin-bottom: 1rem;
            color: white;
            box-shadow: 0 8px 20px rgba(15,23,42,0.2);
        }
        .admin-kpi {
            background: linear-gradient(180deg, #111827 0%, #1f2937 100%);
            border: 1px solid rgba(148,163,184,0.22);
            border-radius: 18px;
            padding: 1rem;
            min-height: 110px;
            color: white;
        }
        .admin-kpi .label {
            color: #cbd5e1;
            font-size: 0.76rem;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }
        .admin-kpi .value {
            font-size: 1.8rem;
            font-weight: 800;
            margin-top: 0.5rem;
        }
        .admin-alert {
            background: linear-gradient(90deg, rgba(127,29,29,0.18), rgba(194,65,12,0.12));
            border-left: 4px solid #f97316;
            border-radius: 14px;
            padding: 0.8rem 1rem;
            color: #fef2f2;
            margin: 0.8rem 0 1rem;
        }
        .admin-action {
            background: linear-gradient(90deg, #f97316, #ef4444);
            color: white;
            border: none;
            border-radius: 12px;
            font-weight: 700;
            padding: 0.7rem 1rem;
            box-shadow: 0 8px 18px rgba(249,115,22,0.22);
        }
        .gobite-hero {
            background: linear-gradient(135deg, #fff7ed 0%, #ffe4e6 45%, #f8fafc 100%);
            border: 1px solid rgba(249,115,22,0.18);
            border-radius: 24px;
            padding: 1.5rem 1.6rem;
            margin-bottom: 1rem;
        }
        .gobite-hero h2 {
            margin: 0;
            color: #111827;
            font-size: 2.1rem;
            line-height: 1.2;
        }
        .gobite-pill {
            display: inline-block;
            background: #fff;
            border: 1px solid rgba(249,115,22,0.2);
            color: #c2410c;
            border-radius: 999px;
            padding: 0.35rem 0.8rem;
            font-size: 0.75rem;
            font-weight: 700;
            letter-spacing: 0.04em;
            text-transform: uppercase;
            margin-bottom: 0.75rem;
        }
        .checkout-card {
            background: linear-gradient(180deg, #ffffff 0%, #fff7ed 100%);
            border: 1px solid rgba(249,115,22,0.18);
            border-radius: 20px;
            padding: 1rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.session_state.setdefault("user_id", None)
    owner_email = (os.getenv("OWNER_EMAIL") or "owner@gobite.com").strip().lower()
    st.title("🛵 GoBite")
    st.caption("Fresh food delivered faster")
    if engine is not None:
        st.caption(f"Database: {os.getenv('DB_HOST')} ({os.getenv('DB_NAME')})")
    else:
        st.warning("Database config is missing. Add DB_HOST, DB_USER, DB_NAME, and DB_PASSWORD in your .env to enable login and ordering.")

    if engine is None:
        st.stop()

    if not st.session_state.user_id:
        a, b, c = st.tabs(["Customer login", "Owner login", "Sign up"])
        with a:
            with st.form("login"):
                email = st.text_input("Email")
                password = st.text_input("Password", type="password")
                if st.form_submit_button("Login"):
                    with engine.connect() as conn:
                        user = conn.execute(text("SELECT * FROM users WHERE email=:email"), {"email": email}).mappings().first()
                    if user and verify_password(password, user["password"]):
                        st.session_state.user_id = user["id"]
                        st.rerun()
                    st.error("Invalid login")
        with b:
            st.markdown(
                """
                <div class="gobite-owner-gate">
                    <div class="secure-label">Secure owner access</div>
                    <div style="margin-top:0.9rem; display:flex; align-items:center; justify-content:space-between; gap:1rem; flex-wrap:wrap;">
                        <div>
                            <div style="font-size:1.4rem; font-weight:800; color:#fff;">Operations portal</div>
                            <div style="margin-top:0.25rem; color:#fed7aa; font-weight:600;">Use the owner email and password to unlock the dashboard.</div>
                        </div>
                        <div class="gobite-admin-badge">Owner only</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            with st.form("owner_login"):
                owner_input = st.text_input("Owner email", value=os.getenv("OWNER_EMAIL", "owner@gobite.com"))
                owner_password = st.text_input("Password", type="password")
                if st.form_submit_button("Access admin"):
                    if owner_input.strip().lower() != owner_email:
                        st.error("This email is not registered as the owner.")
                    else:
                        with engine.connect() as conn:
                            user = conn.execute(text("SELECT * FROM users WHERE email=:email"), {"email": owner_input.strip()}).mappings().first()
                        if user and verify_password(owner_password, user["password"]):
                            st.session_state.user_id = user["id"]
                            st.rerun()
                        st.error("Invalid owner credentials")
        with c:
            with st.form("signup"):
                name = st.text_input("Name")
                email = st.text_input("Email", key="signup_email")
                password = st.text_input("Password", type="password", key="signup_password")
                if st.form_submit_button("Create account"):
                    if not name.strip() or not email.strip() or len(password) < 6:
                        st.error("Please enter a valid name, email, and password of at least 6 characters.")
                    else:
                        try:
                            with engine.begin() as conn:
                                conn.execute(text("INSERT INTO users(name,email,password) VALUES(:name,:email,:password)"), {"name": name.strip(), "email": email.strip(), "password": hash_password(password)})
                            st.success("Account created")
                        except Exception:
                            st.error("Email already exists")
    else:
        with engine.connect() as conn:
            user = conn.execute(text("SELECT * FROM users WHERE id=:id"), {"id": st.session_state.user_id}).mappings().first()
            order = conn.execute(text("SELECT * FROM orders WHERE user_id=:id ORDER BY id DESC LIMIT 1"), {"id": st.session_state.user_id}).mappings().first()
            order_history = conn.execute(text("SELECT * FROM orders WHERE user_id=:id ORDER BY created_at DESC LIMIT 5"), {"id": st.session_state.user_id}).mappings().all()
            all_orders = conn.execute(text("SELECT * FROM orders ORDER BY created_at DESC LIMIT 20")).mappings().all()
        hotels = nearby_hotels(user["address"]) if user["address"] else {}

        with st.sidebar:
            st.markdown(
                """
                <div class="gobite-sidebar-box">
                    <div style="font-size:0.72rem; text-transform:uppercase; letter-spacing:0.12em; color:#fbbf24; margin-bottom:0.4rem;">GoBite</div>
                    <div style="font-size:1.5rem; font-weight:800;">Fresh. Fast. Local.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.markdown(f"**Welcome, {user['name']}**")
            if st.button("Logout", use_container_width=True):
                st.session_state.user_id = None
                st.session_state.checkout_requested = False
                st.rerun()

        left, right = st.columns([2, 1])
        with left:
            st.markdown(
                """
                <div class="gobite-hero">
                    <div class="gobite-pill">Now delivering</div>
                    <h2>Order your favorites in minutes.</h2>
                    <p style="margin:0.7rem 0 0; color:#374151; font-size:1rem;">Discover local restaurants, track delivery in real time, and keep everything running smoothly from one premium experience.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with right:
            st.metric("Open orders", len(all_orders))
            st.metric("Owner access", "Enabled" if (user.get("email", "").strip().lower() == owner_email) else "Standard")

        is_owner = (user.get("email", "").strip().lower() == owner_email)
        nav_options = determine_user_navigation(user.get("email"), owner_email)
        page = st.sidebar.radio("Navigation", nav_options, index=0)

        if page == "Profile":
            st.subheader("Profile")
            address = st.text_input("Delivery address", value=user["address"] or "")
            if st.button("Save location") and address:
                lat, lng = geocode(address)
                with engine.begin() as conn:
                    conn.execute(text("UPDATE users SET address=:address, lat=:lat, lng=:lng WHERE id=:id"), {"address": address, "lat": lat, "lng": lng, "id": user["id"]})
                st.rerun()
            if user["lat"] and user["lng"]:
                pins = [{"lat": user["lat"], "lon": user["lng"]}] + [{"lat": h["lat"], "lon": h["lon"]} for h in hotels.values()]
                st.map(pd.DataFrame(pins), zoom=12)

        elif page == "Orders":
            st.subheader("Order history")
            history_rows = summarize_order_history(order_history)
            if history_rows:
                for row in history_rows:
                    st.write(f"{row['restaurant']} | {row['status']} | Rs {row['total']} | {row['created_at']}")
                    st.caption(row["items"])
            else:
                st.info("No previous orders yet.")

        elif page == "Tracking":
            if order:
                status = live_status(order["created_at"])
                if status != order["status"]:
                    with engine.begin() as conn:
                        conn.execute(text("UPDATE orders SET status=:status WHERE id=:id"), {"status": status, "id": order["id"]})
                st.subheader("Live order status")
                driver_lat = user["lat"] if user["lat"] else 12.9716
                driver_lon = user["lng"] if user["lng"] else 77.5946
                restaurant_lat = driver_lat + 0.004
                restaurant_lon = driver_lon + 0.006
                route_distance = estimate_delivery_distance_km((driver_lat, driver_lon), (restaurant_lat, restaurant_lon))
                traffic_factor = 1.3 if status in {"Out for Delivery", "Preparing"} else 1.0
                etad = calculate_eta_minutes(route_distance, traffic_factor=traffic_factor)
                steps = delivery_status_steps(status)
                cols = st.columns(len(steps))
                for idx, step in enumerate(steps):
                    with cols[idx]:
                        state = "✅" if step["completed"] else "●" if step["active"] else "○"
                        st.markdown(f"{state} {step['name']}")
                st.progress({"Placed": .25, "Preparing": .5, "Out for Delivery": .75, "Delivered": 1}[status], text=f"{status} • ETA {etad} mins")
                st.write(order["restaurant"])
                st.write(order["items"])
                st.write(f"Total: Rs {int(order['total'])}")

                route_points = generate_delivery_route((driver_lat, driver_lon), (restaurant_lat, restaurant_lon), points=5)
                driver_map = pd.DataFrame([
                    {"lat": lat, "lon": lon, "type": "driver" if idx == 0 else "route"}
                    for idx, (lat, lon) in enumerate(route_points)
                ])
                st.subheader("Driver tracking map")
                st.map(driver_map, zoom=12)
                if status in {"Preparing", "Out for Delivery"}:
                    st.caption(f"Delivery route: {len(route_points)} checkpoints • Approx. {route_distance:.1f} km")
                st.subheader("Bill")
                st.code(bill(order, user))
                st.download_button("Download bill", bill(order, user), file_name="gobite_bill.pdf")
                if st.button("Refresh status"):
                    st.rerun()
            else:
                st.info("No active order to track yet.")

        elif page == "Admin":
            if not is_owner:
                st.info("Admin dashboard is restricted to the owner account only.")
            else:
                st.markdown(
                    """
                    <div class="admin-topbar">
                        <div style="display:flex; justify-content:space-between; align-items:center; gap:1rem; flex-wrap:wrap;">
                            <div>
                                <div style="font-size:0.72rem; letter-spacing:0.12em; text-transform:uppercase; color:#fbbf24;">Operations center</div>
                                <div style="font-size:1.5rem; font-weight:800;">Restaurant admin panel</div>
                            </div>
                            <div class="gobite-admin-badge">Live</div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                dashboard = summarize_admin_dashboard(all_orders)
                pending_orders = sum(1 for order in all_orders if order.get("status") != "Delivered")
                today_revenue = sum(int(float(order.get("total", 0) or 0)) for order in all_orders)
                st.markdown(
                    f"""
                    <div class="admin-metric-strip">
                        <div class="admin-metric-pill">
                            <div class="small">Today</div>
                            <div class="big">Rs {today_revenue}</div>
                        </div>
                        <div class="admin-metric-pill">
                            <div class="small">Pending</div>
                            <div class="big">{pending_orders}</div>
                        </div>
                        <div class="admin-metric-pill">
                            <div class="small">Delivered</div>
                            <div class="big">{dashboard['status_counts']['Delivered']}</div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.markdown('<div class="admin-alert">⚠️ Monitor active orders and delivery flow before peak hours.</div>', unsafe_allow_html=True)
                quick_actions = st.columns(4)
                with quick_actions[0]:
                    if st.button("Dispatch queue", use_container_width=True):
                        st.info("Dispatch queue opened.")
                with quick_actions[1]:
                    if st.button("Kitchen sync", use_container_width=True):
                        st.info("Kitchen sync started.")
                with quick_actions[2]:
                    if st.button("Driver assign", use_container_width=True):
                        st.info("Driver assignment check started.")
                with quick_actions[3]:
                    if st.button("Alerts", use_container_width=True):
                        st.info("Alerts refreshed.")
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.markdown(f'<div class="admin-kpi"><div class="label">Revenue</div><div class="value">Rs {dashboard["revenue"]}</div></div>', unsafe_allow_html=True)
                with c2:
                    st.markdown(f'<div class="admin-kpi"><div class="label">Open orders</div><div class="value">{dashboard["open_orders"]}</div></div>', unsafe_allow_html=True)
                with c3:
                    st.markdown(f'<div class="admin-kpi"><div class="label">Delivered</div><div class="value">{dashboard["status_counts"]["Delivered"]}</div></div>', unsafe_allow_html=True)

                st.markdown(
                    """
                    <div style="margin:1rem 0 0.5rem; display:flex; gap:0.75rem; flex-wrap:wrap;">
                        <span style="background:#f59e0b; color:#111827; padding:0.35rem 0.7rem; border-radius:999px; font-size:0.75rem; font-weight:700;">Placed</span>
                        <span style="background:#f97316; color:white; padding:0.35rem 0.7rem; border-radius:999px; font-size:0.75rem; font-weight:700;">Preparing</span>
                        <span style="background:#ef4444; color:white; padding:0.35rem 0.7rem; border-radius:999px; font-size:0.75rem; font-weight:700;">Out for Delivery</span>
                        <span style="background:#22c55e; color:#052e16; padding:0.35rem 0.7rem; border-radius:999px; font-size:0.75rem; font-weight:700;">Delivered</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                st.subheader("Live orders")
                if all_orders:
                    live_df = pd.DataFrame([
                        {
                            "Order": row.get("id"),
                            "Restaurant": row.get("restaurant"),
                            "Items": row.get("items", ""),
                            "Status": row.get("status", "Placed"),
                            "Total": f"Rs {int(float(row.get('total', 0) or 0))}",
                            "Time": row.get("created_at"),
                        }
                        for row in all_orders[:10]
                    ])
                    st.dataframe(live_df, use_container_width=True, hide_index=True)
                else:
                    st.info("No live orders yet.")

                st.write("Status counts")
                st.json(dashboard["status_counts"])

                active_cards = build_active_delivery_cards([row for row in all_orders if row.get("status") != "Delivered"])
                if active_cards:
                    st.subheader("Active deliveries")
                    cols = st.columns(len(active_cards))
                    for idx, card in enumerate(active_cards):
                        with cols[idx]:
                            color = {"gray": "#94a3b8", "orange": "#f59e0b", "red": "#ef4444", "green": "#22c55e"}[card["color"]]
                            st.markdown(
                                f"""
                                <div style="padding:14px; border-radius:14px; background:{color}; color:white; min-height:140px;">
                                    <b>#{card['id']}</b><br>
                                    <span>{card['restaurant']}</span><br>
                                    <span>{card['status']}</span><br>
                                    <span>Rs {card['total']}</span>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )

                timeline = build_order_timeline(all_orders)
                st.subheader("Delivery timeline board")
                for status, items in timeline.items():
                    with st.container():
                        st.caption(status)
                        if not items:
                            st.write("No orders")
                        else:
                            for item in items:
                                st.write(f"#{item['id']} • {item['restaurant']} • Rs {item['total']}")

                driver_points = build_active_driver_map(all_orders)
                if driver_points:
                    st.subheader("Active driver map")
                    driver_df = pd.DataFrame(driver_points)
                    st.map(driver_df[["lat", "lon"]], zoom=12)

                order_filters = st.columns(2)
                with order_filters[0]:
                    filter_status = st.selectbox("Filter status", ["All", "Placed", "Preparing", "Out for Delivery", "Delivered"])
                with order_filters[1]:
                    restaurants = ["All"] + sorted({row.get("restaurant") for row in all_orders if row.get("restaurant")})
                    filter_restaurant = st.selectbox("Filter restaurant", restaurants)
                filtered_orders = filter_dashboard_orders(all_orders, status=filter_status, restaurant=filter_restaurant)
                if filtered_orders:
                    st.dataframe(pd.DataFrame(filtered_orders), use_container_width=True)
                else:
                    st.info("No orders match the current filters.")

                if filtered_orders:
                    selected_order_id = st.selectbox("Choose order to update", [row["id"] for row in filtered_orders], format_func=lambda oid: f"Order #{oid}")
                    selected_order = next((row for row in filtered_orders if row["id"] == selected_order_id), filtered_orders[0])
                    restaurant_statuses = ["Placed", "Preparing", "Out for Delivery", "Delivered"]
                    selected_order_status = st.selectbox("Update order status", restaurant_statuses, index=restaurant_statuses.index(selected_order.get("status", "Placed")))
                    if st.button("Apply status update", use_container_width=True):
                        with engine.begin() as conn:
                            conn.execute(text("UPDATE orders SET status=:status WHERE id=:id"), {"status": selected_order_status, "id": selected_order_id})
                        st.success(f"Order #{selected_order_id} updated to {selected_order_status}")
                        st.rerun()

        else:
            if hotels:
                st.subheader("Restaurants")
                cuisine_options = ["All"] + sorted({hotel["cuisine"] for hotel in hotels.values()})
                query = st.text_input("Search restaurant or cuisine", placeholder="Try dosa, pizza, biryani")
                cuisine = st.selectbox("Filter by cuisine", cuisine_options)
                sort_by = st.selectbox("Sort by", ["rating", "name"])
                filtered_hotels = filter_hotels(hotels, query=query, cuisine=cuisine, sort_by=sort_by)

                if not filtered_hotels:
                    st.info("No restaurants match your filters right now.")
                else:
                    st.write(f"Showing {len(filtered_hotels)} restaurant(s)")
                    for name, hotel in filtered_hotels.items():
                        st.write(f"{name} | {hotel['cuisine']} | {hotel['rating']} stars")
                    restaurant = st.selectbox("Choose hotel", list(filtered_hotels))
                    st.subheader("Menu")
                    cart = {}
                    for dish in filtered_hotels[restaurant]["menu"]:
                        price = max(80, int(dish.get("caloriesPerServing", 200) / 2))
                        qty = st.number_input(f"{dish['name']} - Rs {price}", 0, 10, 0, 1, key=f"{restaurant}_{dish['name']}")
                        if qty:
                            cart[dish["name"]] = {"qty": qty, "price": price}

                    subtotal, delivery_fee, total = compute_order_totals(cart, delivery_fee=35)
                    if cart:
                        st.subheader("Cart summary")
                        for name, info in cart.items():
                            st.write(f"{name} x{info['qty']} — Rs {info['qty'] * info['price']}")
                        st.write(f"Subtotal: Rs {subtotal}")
                        st.write(f"Delivery fee: Rs {delivery_fee}")
                        st.write(f"Total: Rs {total}")

                        if not st.session_state.checkout_requested:
                            if st.button("Proceed to checkout"):
                                st.session_state.checkout_requested = True
                                st.rerun()
                        else:
                            st.markdown("<div class='checkout-card'>", unsafe_allow_html=True)
                            st.subheader("Checkout")
                            payment_method = st.radio("Payment method", ["UPI", "Card", "Cash on Delivery"], horizontal=True)
                            eta = calculate_eta_minutes(4.5)
                            st.write(f"Delivering from: {restaurant}")
                            st.write(f"Delivery address: {user['address'] or 'Add a delivery address in Profile'}")
                            st.write(f"Estimated delivery: {eta} mins")
                            st.write("Items")
                            for name, info in cart.items():
                                st.write(f"- {name} x{info['qty']} — Rs {info['qty'] * info['price']}")
                            st.write(f"Subtotal: Rs {subtotal}")
                            st.write(f"Delivery fee: Rs {delivery_fee}")
                            st.markdown(f"<h4 style='margin:0.5rem 0;'>Total: Rs {total}</h4>", unsafe_allow_html=True)
                            if st.button("Place order"):
                                order_items = ", ".join(f"{info['qty']} x {name}" for name, info in cart.items())
                                with engine.begin() as conn:
                                    conn.execute(text("INSERT INTO orders(user_id,restaurant,items,total,status) VALUES(:user_id,:restaurant,:items,:total,'Placed')"), {"user_id": user["id"], "restaurant": restaurant, "items": order_items, "total": total})
                                st.session_state.checkout_requested = False
                                st.success(f"Order placed successfully from {restaurant} via {payment_method}.")
                                st.rerun()
                            if st.button("Cancel checkout"):
                                st.session_state.checkout_requested = False
                                st.rerun()
                            st.markdown("</div>", unsafe_allow_html=True)
            elif user["address"]:
                st.info("No live hotels found for this location right now.")


if __name__ == "__main__":
    main()
