# Tarify — Price Tracker

Tarify is a containerized web app that monitors product prices across e-commerce sites, stores historical price data, and sends Telegram alerts when prices drop. Built as a portfolio project to practice web scraping, background job scheduling, and containerized deployment.

## Key features

- Add products to monitor by target URL
- Scheduled background scraper checks prices automatically
- Full price history stored in PostgreSQL
- Telegram bot alerts on price drops
- CSV export of price history

## Tech stack

- **Backend:** Python 3.12, FastAPI, Uvicorn
- **Database:** PostgreSQL
- **Scheduling:** APScheduler
- **Scraping:** BeautifulSoup, Requests
- **Notifications:** Telegram Bot API
- **Deployment:** Docker, Docker Compose

## Running locally

Requirements: Docker and Docker Compose installed.

```bash
git clone https://github.com/CarlosGranados-devs/tarify-price-tracker.git
cd tarify-price-tracker
cp .env.example .env
# fill in your own Telegram bot token and DB credentials in .env
docker-compose up --build
```

The app will be available at `http://localhost:8000`.

## What I learned

Building Tarify helped me practice designing a resilient scraping pipeline, working with scheduled background jobs, integrating a third-party notification API, and containerizing a full-stack app for deployment.

## License

MIT