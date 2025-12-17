"""
Airbnb API Microservice

A standalone REST API for searching and retrieving Airbnb listing data.
This service provides programmatic access to Airbnb search functionality.
"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_versioning import version, VersionedFastAPI
from starlette.middleware import Middleware

from routes.search import router as search_router
from routes.listing import router as listing_router

# CORS configuration
origins = os.getenv(
    "CORS_ORIGINS", 
    "http://localhost:3000,http://127.0.0.1:3000,http://localhost:8081"
).split(",")

cors_middleware = Middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# FastAPI configuration
fastapi_args = {
    "version": "1.0.0",
    "middleware": [cors_middleware],
}

# Create the FastAPI application
app = FastAPI(
    title="Airbnb API",
    description="""
## Airbnb API Microservice

A standalone REST API for searching and retrieving Airbnb listing data.

### Features

- **Search Listings**: Search for Airbnb listings by location, dates, and filters
- **Get Listing Details**: Retrieve detailed information about specific listings
- **Filter Options**: Query available amenities and room types for filtering

### Rate Limiting

This API performs live web scraping, so please use it responsibly:
- Limit search requests to avoid overloading
- Use pagination sparingly (max_pages: 1-3 recommended)
- Consider caching results on your end

### Authentication

Currently, this API does not require authentication.
    """,
    **fastapi_args
)

# Include routers
app.include_router(search_router)
app.include_router(listing_router)

# Apply versioning
app = VersionedFastAPI(
    app,
    **fastapi_args,
    version_format='{major}',
    prefix_format='/v{major}',
    enable_latest=True,
    docs_url=None,  # Disable root /docs so we can redirect to /v1/docs
    redoc_url=None,  # Disable root /redoc as well
)


##################################################################
# UNVERSIONED ENDPOINTS                                          #
# The following endpoints are declared after VersionedFastAPI()  #
##################################################################

from fastapi.responses import RedirectResponse


@app.get("/health", tags=["Monitoring"])
async def health():
    """Health check endpoint for monitoring and load balancers."""
    return {
        "status": "ok",
        "service": "airbnb-api",
        "version": "1.0.0"
    }


@app.get("/docs", include_in_schema=False)
async def docs_redirect():
    """Redirect /docs to /v1/docs where the API documentation lives."""
    return RedirectResponse(url="/v1/docs")


@app.get("/", tags=["Info"])
async def root():
    # """Root endpoint with API information."""
    """Redirect /docs to /v1/docs where the API documentation lives."""
    return RedirectResponse(url="/v1/docs")

