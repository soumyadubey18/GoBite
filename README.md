# GoBite

GoBite is a modern food delivery and restaurant operations app built with Python and Streamlit. It helps users discover nearby restaurants, place orders, track live delivery status, and gives restaurant/admin teams a dashboard to manage active orders and fulfillment.

## Overview

This project demonstrates a complete delivery workflow in a compact, easy-to-run Streamlit app:

- customer signup/login
- save delivery address and geolocation
- restaurant discovery and filtering
- cart and checkout flow
- ETA estimation using route distance and traffic assumptions
- live order tracking and order history
- admin dashboard with multi-order status management

## Features

- User authentication with secure password hashing
- Delivery location saving via geocoding
- Restaurant search and cuisine filtering
- Menu browsing and cart management
- Order placement with payment selection and ETA feedback
- Live status timeline and route-inspired tracking card
- Admin dashboard with status filters and per-order updates
- MySQL-backed order persistence

## Tech Stack

- Python
- Streamlit
- SQLAlchemy
- MySQL
- Pandas
- Requests
- python-dotenv

## Project Structure

```text
GoBite/
├── gobite/
│   ├── app.py
│   ├── README.md
│   ├── requirements.txt
│   └── .env
├── tests/
│   └── test_app_logic.py
├── .gitignore
├── README.md
├── LICENSE
└── .git
```

## Getting Started

### 1) Install dependencies

```bash
pip install -r gobite/requirements.txt
```

### 2) Configure environment variables

Create a `.env` file in the `gobite` folder with values like:

```env
DB_HOST=your_host
DB_PORT=3306
DB_USER=your_user
DB_NAME=your_database
DB_PASSWORD=your_password
RAPIDAPI_KEY=your_key
RAPIDAPI_GEO_HOST=forward-reverse-geocoding.p.rapidapi.com
```

### 3) Run the app

```bash
streamlit run gobite/app.py
```

## Testing

```bash
python -m pytest -q
```

## Screenshots

Add project screenshots to this section once you have UI captures ready:

- Customer dashboard
- Restaurant list and filters
- Cart/checkout flow
- Admin order management panel
- Delivery tracking view

Example layout:

```md
## Screenshots

### Customer Home
![Customer Home](docs/screenshots/customer-home.png)

### Admin Dashboard
![Admin Dashboard](docs/screenshots/admin-dashboard.png)
```

## Releases

Current release:

- v1.0.0 — initial public release of GoBite

To create a Git tag locally:

```bash
git tag -a v1.0.0 -m "GoBite v1.0.0"
git push origin v1.0.0
```

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss the proposed update.
