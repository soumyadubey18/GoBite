from gobite.app import (
    build_active_delivery_cards,
    build_active_driver_map,
    build_order_timeline,
    calculate_eta_minutes,
    compute_order_totals,
    delivery_status_steps,
    determine_user_navigation,
    estimate_delivery_distance_km,
    filter_dashboard_orders,
    filter_hotels,
    generate_delivery_route,
    hash_password,
    summarize_admin_dashboard,
    summarize_order_history,
    verify_password,
)


def test_hash_password_is_not_plain_text():
    hashed = hash_password("secret123")
    assert hashed != "secret123"
    assert hashed.startswith("pbkdf2_sha256$")
    assert len(hashed.split("$")) == 4


def test_verify_password_accepts_hashed_and_legacy_values():
    hashed = hash_password("secret123")
    assert verify_password("secret123", hashed)
    assert verify_password("secret123", "secret123")


def test_compute_order_totals_includes_subtotal_fee_and_total():
    cart = {
        "Masala Dosa": {"qty": 2, "price": 120},
        "Filter Coffee": {"qty": 1, "price": 60},
    }
    subtotal, delivery_fee, total = compute_order_totals(cart, delivery_fee=35)
    assert subtotal == 300
    assert delivery_fee == 35
    assert total == 335


def test_summarize_order_history_returns_clean_rows():
    history = [
        {"id": 7, "restaurant": "Aroma Bites", "items": "2 x Masala Dosa, 1 x Tea", "total": 320.0, "status": "Preparing", "created_at": "2026-09-01 12:00:00"},
        {"id": 8, "restaurant": "Saffron Bowl", "items": "1 x Biryani", "total": 220.0, "status": "Delivered", "created_at": "2026-09-01 13:00:00"},
    ]
    rows = summarize_order_history(history)
    assert rows[0]["restaurant"] == "Aroma Bites"
    assert rows[1]["total"] == 220
    assert rows[0]["status"] == "Preparing"


def test_filter_hotels_searches_and_sorts():
    hotels = {
        "Aroma Bites": {"cuisine": "Indian", "rating": 4.8},
        "Pizza Palace": {"cuisine": "Italian", "rating": 4.5},
        "Saffron Grill": {"cuisine": "Pakistani", "rating": 4.9},
    }
    filtered = filter_hotels(hotels, query="pizza", cuisine="All", sort_by="rating")
    assert list(filtered.keys()) == ["Pizza Palace"]

    indian = filter_hotels(hotels, query="", cuisine="Indian", sort_by="rating")
    assert list(indian.keys()) == ["Aroma Bites"]


def test_determine_user_navigation_shows_admin_only_for_owner():
    owner_nav = determine_user_navigation("owner@gobite.com", "owner@gobite.com")
    customer_nav = determine_user_navigation("user@example.com", "owner@gobite.com")

    assert owner_nav == ["Home", "Orders", "Tracking", "Profile", "Admin"]
    assert customer_nav == ["Home", "Orders", "Tracking", "Profile"]


def test_calculate_eta_minutes_and_dashboard_summary():
    eta = calculate_eta_minutes(4.5, 3)
    assert eta >= 25
    assert eta <= 60

    orders = [
        {"status": "Placed", "total": 250},
        {"status": "Preparing", "total": 420},
        {"status": "Delivered", "total": 190},
        {"status": "Out for Delivery", "total": 300},
    ]
    summary = summarize_admin_dashboard(orders)
    assert summary["revenue"] == 1160
    assert summary["status_counts"]["Preparing"] == 1
    assert summary["open_orders"] == 3


def test_delivery_status_steps_mark_active_and_completed_states():
    steps = delivery_status_steps("Out for Delivery")
    assert [step["name"] for step in steps] == ["Placed", "Preparing", "Out for Delivery", "Delivered"]
    assert steps[2]["active"] is True
    assert steps[0]["completed"] is True
    assert steps[3]["completed"] is False


def test_generate_delivery_route_returns_points_between_locations():
    route = generate_delivery_route((12.9716, 77.5946), (12.9816, 77.6046), 3)
    assert len(route) == 3
    assert route[0][0] == 12.9716
    assert route[-1][0] == 12.9816


def test_calculate_eta_uses_distance_and_traffic_multiplier():
    eta_low = calculate_eta_minutes(4.5, traffic_factor=1.0)
    eta_high = calculate_eta_minutes(4.5, traffic_factor=1.8)
    assert eta_high > eta_low
    assert estimate_delivery_distance_km((12.9716, 77.5946), (12.9816, 77.6046)) > 0


def test_filter_dashboard_orders_supports_status_and_restaurant_filters():
    orders = [
        {"id": 1, "restaurant": "Aroma Bites", "status": "Preparing", "total": 250},
        {"id": 2, "restaurant": "Pizza Palace", "status": "Out for Delivery", "total": 430},
        {"id": 3, "restaurant": "Aroma Bites", "status": "Delivered", "total": 180},
    ]
    filtered = filter_dashboard_orders(orders, status="Preparing", restaurant="Aroma Bites")
    assert len(filtered) == 1
    assert filtered[0]["id"] == 1


def test_build_active_delivery_cards_and_timeline():
    orders = [
        {"id": 101, "restaurant": "Aroma Bites", "status": "Preparing", "total": 250, "created_at": "2026-09-01 12:00:00"},
        {"id": 102, "restaurant": "Pizza Palace", "status": "Out for Delivery", "total": 430, "created_at": "2026-09-01 12:10:00"},
    ]
    cards = build_active_delivery_cards(orders)
    assert cards[0]["restaurant"] == "Aroma Bites"
    assert cards[0]["color"] in {"orange", "red", "green"}
    timeline = build_order_timeline(orders)
    assert timeline["Preparing"][0]["id"] == 101
    assert timeline["Out for Delivery"][0]["id"] == 102


def test_build_active_driver_map_returns_active_positions():
    orders = [
        {"id": 201, "restaurant": "Aroma Bites", "status": "Out for Delivery", "total": 320},
        {"id": 202, "restaurant": "Pizza Palace", "status": "Preparing", "total": 290},
    ]
    driver_map = build_active_driver_map(orders)
    assert len(driver_map) == 2
    assert driver_map[0]["status"] == "Out for Delivery"
