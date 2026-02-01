from fastapi import FastAPI
from app.api.v1.router import api_router
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(title="AIESEC Egypt CRM API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite default
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    """Root endpoint - returns API information"""
    return {
        "message": "AIESEC Egypt CRM API",
        "version": "v1",
        "docs": "/docs",
        "health": "/api/v1/health"
    }


app.include_router(api_router, prefix="/api/v1")
