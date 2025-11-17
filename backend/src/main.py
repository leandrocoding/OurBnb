import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware import Middleware

from routes.dummy import router as dummy_router

origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")

cors_middleware = Middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app = FastAPI(
    title="FWE'25 Backend API",
    version="1.0.0",
    middleware=[cors_middleware]
)

app.include_router(dummy_router)


@app.get("/health", tags=["Monitoring"])
async def health():
    return {"status": "ok"}
