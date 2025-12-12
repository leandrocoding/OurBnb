# Airbnb API Microservice

A standalone REST API for searching and retrieving Airbnb listing data. This microservice provides programmatic access to Airbnb search functionality without requiring direct database integration.

## Features

- **Search Listings**: Search for Airbnb listings by location, dates, and filters
- **Get Listing Details**: Retrieve detailed information about specific listings
- **Filter Options**: Query available amenities and room types for filtering
- **Versioned API**: API versioning with `/v1/` prefix
- **OpenAPI Documentation**: Auto-generated Swagger UI at `/docs`

## Quick Start

### Using Docker Compose

From the project root directory:

```bash
docker-compose up airbnb-api
```

The API will be available at `http://localhost:8081`

### Local Development

```bash
cd airbnb-api
pip install uv
uv pip install -e .
cd src
uvicorn main:app --reload --port 8081
```

## API Endpoints

### Health & Info

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API information and available endpoints |
| `/health` | GET | Health check for monitoring |
| `/docs` | GET | Swagger UI documentation |

### Search (v1)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/search` | POST | Search for Airbnb listings |
| `/v1/search/amenities` | GET | List available amenity filters |
| `/v1/search/room-types` | GET | List available room type filters |

### Listing (v1)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/listing/{room_id}` | GET | Get detailed listing information |

## Usage Examples

### Search for Listings

```bash
curl -X POST "http://localhost:8081/v1/search" \
  -H "Content-Type: application/json" \
  -d '{
    "location": "Paris",
    "checkin": "2025-06-01",
    "checkout": "2025-06-05",
    "adults": 2,
    "min_price": 50,
    "max_price": 300,
    "amenities": ["wifi", "kitchen"],
    "room_type": "entire_home",
    "max_pages": 1
  }'
```

### Get Listing Details

```bash
curl "http://localhost:8081/v1/listing/12345678"
```

### List Available Amenities

```bash
curl "http://localhost:8081/v1/search/amenities"
```

### List Room Types

```bash
curl "http://localhost:8081/v1/search/room-types"
```

## Search Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `location` | string | Yes | Location to search (e.g., "Paris", "Tokyo") |
| `checkin` | date | Yes | Check-in date (YYYY-MM-DD) |
| `checkout` | date | Yes | Check-out date (YYYY-MM-DD) |
| `adults` | int | No | Number of adults (default: 1) |
| `children` | int | No | Number of children (default: 0) |
| `infants` | int | No | Number of infants (default: 0) |
| `pets` | int | No | Number of pets (default: 0) |
| `min_price` | int | No | Minimum price per night |
| `max_price` | int | No | Maximum price per night |
| `min_bedrooms` | int | No | Minimum number of bedrooms |
| `min_beds` | int | No | Minimum number of beds |
| `min_bathrooms` | int | No | Minimum number of bathrooms |
| `room_type` | enum | No | "entire_home" or "private_room" |
| `amenities` | array | No | List of amenity filters |
| `max_pages` | int | No | Pages to scrape (1-10, default: 1) |

## Available Amenities

- `wifi` - WiFi
- `kitchen` - Kitchen
- `washer` - Washer
- `dedicated_workspace` - Dedicated Workspace
- `tv` - TV
- `pool` - Pool
- `hot_tub` - Hot Tub
- `free_parking` - Free Parking
- `ev_charger` - EV Charger
- `crib` - Crib
- `king_bed` - King Bed
- `gym` - Gym
- `bbq_grill` - BBQ Grill
- `breakfast` - Breakfast
- `indoor_fireplace` - Indoor Fireplace
- `smoking_allowed` - Smoking Allowed
- `smoke_alarm` - Smoke Alarm
- `carbon_monoxide_alarm` - Carbon Monoxide Alarm

## Response Format

### Search Response

```json
{
  "success": true,
  "location": "Paris",
  "checkin": "2025-06-01",
  "checkout": "2025-06-05",
  "total_results": 18,
  "listings": [
    {
      "id": "12345678",
      "title": "Cozy apartment in the heart of Paris",
      "price_text": "CHF 150",
      "price_per_night": 150,
      "rating": "4.85 (123)",
      "images": ["https://..."],
      "url": "https://www.airbnb.ch/rooms/12345678"
    }
  ]
}
```

### Listing Response

```json
{
  "success": true,
  "room_id": "12345678",
  "basic_info": {
    "title": "Cozy apartment",
    "property_type": "Apartment",
    "person_capacity": 4
  },
  "host": {
    "name": "John",
    "is_superhost": true
  },
  "amenities": [...],
  "reviews": {
    "overall_rating": 4.85,
    "total_count": 123
  },
  "location": {
    "name": "Paris, France",
    "lat": 48.8566,
    "lng": 2.3522
  },
  "photos": [...]
}
```

## Rate Limiting & Anti-Blocking

This API performs live web scraping. Airbnb may block requests if they detect automated access.

### Without Proxies
- **Low volume (< 50 requests/day)**: Generally safe for development/testing
- **Medium volume (50-200 requests/day)**: Risk of temporary blocks (CAPTCHAs, 429 errors)
- **High volume (200+ requests/day)**: High risk of IP blocks

### With Rotating Proxies
- Roughly 3x capacity per proxy before detection
- Better resilience - if one IP gets blocked, others continue
- **Recommended**: 3 proxies can handle ~150-500 requests/day

### Configuring Proxies

Set the `PROXY_URLS` environment variable with comma-separated proxy URLs. For proxies with authentication (like tinyproxy with BasicAuth), include credentials in the URL:

```bash
# Format: http://username:password@host:port
PROXY_URLS="http://user:pass@proxy1.example.com:8888,http://user:pass@proxy2.example.com:8888"

# Without authentication
PROXY_URLS="http://proxy1.example.com:8888,http://proxy2.example.com:8888"
```

In Docker Compose:
```yaml
microservice:
  environment:
    PROXY_URLS: "http://user:pass@proxy1:8888,http://user:pass@proxy2:8888"
```

**Note:** Proxy configuration is only enabled for Docker Compose deployments. The Helm/Kubernetes deployment does not use proxies by default.

### Check Proxy Status

```bash
curl "http://localhost:8081/v1/search/proxy-status"
```

### Best Practices

- Limit concurrent requests
- Use `max_pages: 1-3` for faster responses
- Consider caching results on your end
- Add delays between requests in automated scripts
- Monitor the `/v1/search/proxy-status` endpoint

## Architecture

This microservice reuses the scraping logic from `scraper-worker` without modifying it. The scraper code is mounted as a read-only volume in development and copied during production builds.

```
airbnb-api/
├── Dockerfile
├── pyproject.toml
├── README.md
└── src/
    ├── main.py          # FastAPI application
    ├── models/
    │   ├── __init__.py
    │   └── schemas.py   # Pydantic models
    ├── routes/
    │   ├── __init__.py
    │   ├── search.py    # Search endpoints
    │   └── listing.py   # Listing endpoints
    └── scraper/
        ├── __init__.py
        └── core.py      # Wrapper for scraper-worker
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CORS_ORIGINS` | `http://localhost:3000,...` | Comma-separated list of allowed origins |
| `PROXY_URLS` | *(empty)* | Comma-separated proxy URLs (supports `user:pass@host:port` for auth) |

## License

This project is for educational purposes only. Use responsibly and in compliance with Airbnb's terms of service.
