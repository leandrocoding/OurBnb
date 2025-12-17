# Ourbnb

A collaborative trip planning app where groups vote on Airbnb listings to find the perfect accommodation together.

## The Problem

Planning group trips is hard. Everyone has different preferences, budgets, and must-haves. Ourbnb lets each group member set their own filters and vote on listings, then ranks options based on collective preferences.

## How It Works

1. Create a group with your travel dates and destinations
2. Invite friends via the group link
3. Each person sets their filters (price, bedrooms, amenities)
4. Swipe through listings and vote (veto, dislike, like)
5. View the real-time leaderboard showing the group's top picks

## Architecture

| Component | Tech Stack | Port |
|-----------|------------|------|
| Frontend | Next.js + TypeScript | 3000 |
| Backend | Python + FastAPI | 8080 |
| Microservice | Python + FastAPI | 8081 |
| Database | PostgreSQL | 5432 |
| Queue | Redis + Celery | 6379 |

The **Airbnb API microservice** is a standalone service that scrapes Airbnb listings. It's versioned (`/v1/`) and includes OpenAPI docs at `/v1/docs`.

## Quick Start

```bash
# Copy env file
cp .env.example .env

# Start all services
docker-compose up
```

Frontend: http://localhost  
Backend API: http://localhost/api  
Microservice: http://localhost:8081  
Microservice Docs: http://localhost:8081/v1/docs

## Deployment

Push to GitLab to trigger automatic deployment via CI/CD. The app deploys to:
- Frontend/Backend: `https://group-p11.webdev-25.ivia.isginf.ch/`
- Microservice: `https://api.group-p11.webdev-25.ivia.isginf.ch/`

It is currently also hosted on https://ourbnb.ch 
## Project Structure

```
├── frontend/          # Next.js frontend
├── backend/           # FastAPI main backend
├── microservice/      # Airbnb API microservice
├── scraper-worker/    # Celery worker for background scraping
├── db/                # Database schema
└── helm/              # Kubernetes deployment configs
```

## Data Source

Listings are scraped live from Airbnb based on user search criteria. The scraper-worker handles background fetching while the microservice provides a REST API for on-demand searches.

## Team

Vincent Franz
David Gärtner
Leandro Zazzi
Marco De Franceschi