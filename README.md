# GoBite

GoBite is a food delivery and restaurant admin app built with Python and Streamlit. It lets users browse nearby restaurants, place orders, track delivery status, and gives restaurant/admin users a dashboard to manage active orders and delivery progress.

## Features

- User signup and login
- Delivery address saving and geolocation
- Restaurant search and cuisine filtering
- Cart and checkout flow
- ETA estimation based on route distance and traffic
- Live order status updates
- Restaurant/admin dashboard with multi-order controls
- Delivery route tracking view

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
└── .git
```

## Setup

1. Open a terminal in the project root.
2. Create a virtual environment if needed.
3. Install dependencies:

```bash
pip install -r gobite/requirements.txt
```

4. Configure environment variables in `gobite/.env`.

Example:

```env
DB_HOST=your_host
DB_PORT=3306
DB_USER=your_user
DB_NAME=your_database
DB_PASSWORD=your_password
RAPIDAPI_KEY=your_key
RAPIDAPI_GEO_HOST=forward-reverse-geocoding.p.rapidapi.com
```

5. Run the app:

```bash
streamlit run gobite/app.py
```

## Testing

Run the test suite with:

```bash
python -m pytest -q
```

## Git

This repository is initialized with Git and configured for GoBite branding.

## License

This project is for learning and demo purposes.
