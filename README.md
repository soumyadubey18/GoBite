# GoBite

<div align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Streamlit-1.0%2B-FF4B4B?logo=streamlit&logoColor=white" alt="Streamlit" />
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License" />
</div>

<p align="center">
  <strong>GoBite</strong> is a modern food delivery and restaurant operations app built with Python and Streamlit.
</p>

GoBite helps users discover nearby restaurants, place food orders, track delivery progress, and gives the owner a dedicated admin dashboard to manage active orders and status updates.

## Demo Flow

1. Sign up or log in as a customer.
2. Save a delivery address to see nearby restaurants.
3. Browse restaurants, filter by cuisine, and add items to a cart.
4. Place an order with payment and ETA details.
5. Track the delivery timeline and route map.
6. Log in with the owner account to access the admin dashboard and update order status.

## Features

- Customer signup and login
- Delivery address saving with geolocation
- Restaurant search and cuisine filtering
- Menu browsing and cart management
- ETA estimation using route distance and traffic assumptions
- Live order status timeline and route tracking
- Owner-only admin dashboard with multi-order controls
- MySQL-backed persistence for orders and users

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

Create a `.env` file inside `gobite/` with:

```env
DB_HOST=your_host
DB_PORT=3306
DB_USER=your_user
DB_NAME=your_database
DB_PASSWORD=your_password
OWNER_EMAIL=owner@gobite.com
RAPIDAPI_KEY=your_key
RAPIDAPI_GEO_HOST=forward-reverse-geocoding.p.rapidapi.com
```

> The admin dashboard is restricted to the account whose email matches `OWNER_EMAIL`.

### 3) Run the app

```bash
streamlit run gobite/app.py
```

## Screenshots

Add project screenshots here as you capture them:

- Customer home and restaurant browsing
- Cart and checkout flow
- Live delivery tracking screen
- Owner admin dashboard

Example layout:

```md
## Screenshots

### Customer Flow
![Customer Flow](docs/screenshots/customer-flow.png)

### Owner Admin
![Owner Admin](docs/screenshots/admin-dashboard.png)
```

## Testing

```bash
python -m pytest -q
```

## Releases

Current release:

- v1.0.0 — initial public release of GoBite

Create a release tag locally with:

```bash
git tag -a v1.0.0 -m "GoBite v1.0.0"
git push origin v1.0.0
```

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss the proposal.
