import os
import threading
from datetime import datetime
from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from bloodhub.core.config import settings
from bloodhub.core.database import Base, get_db, DatabaseSession
from bloodhub.models.models import create_all
from bloodhub.api.auth import router as auth_router
from bloodhub.api.donors import router as donors_router
from bloodhub.api.requests import router as requests_router
from bloodhub.api.dispatch import router as dispatch_router
from bloodhub.api.centers import router as centers_router
from bloodhub.api.admin import router as admin_router
from bloodhub.api.events import router as events_router
from bloodhub.api.simulator import router as simulator_router

# Initialize database schema tables
create_all()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Autonomous Blood Donation Coordination Platform (Ride-Hailing Style Dispatch Model)"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(donors_router, prefix=settings.API_V1_STR)
app.include_router(requests_router, prefix=settings.API_V1_STR)
app.include_router(dispatch_router, prefix=settings.API_V1_STR)
app.include_router(centers_router, prefix=settings.API_V1_STR)
app.include_router(admin_router, prefix=settings.API_V1_STR)
app.include_router(events_router, prefix=settings.API_V1_STR)
app.include_router(simulator_router, prefix=settings.API_V1_STR)

# Frontend Static and HTML Route mounting
FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
STATIC_DIR = os.path.join(FRONTEND_DIR, "static")

if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/health", tags=["Health"])
def health_check(db: DatabaseSession = Depends(get_db)):
    try:
        db.execute("SELECT 1")
        db_status = "connected"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "database": db_status,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/", include_in_schema=False)
def index_page():
    path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(path):
        return FileResponse(path)
    return {"message": "Welcome to Blood Hub API"}

@app.get("/donor", include_in_schema=False)
def donor_page():
    path = os.path.join(FRONTEND_DIR, "donor.html")
    if os.path.exists(path):
        return FileResponse(path)
    return {"message": "Donor page"}

@app.get("/requester", include_in_schema=False)
def requester_page():
    path = os.path.join(FRONTEND_DIR, "requester.html")
    if os.path.exists(path):
        return FileResponse(path)
    return {"message": "Requester page"}

@app.get("/admin", include_in_schema=False)
def admin_page():
    path = os.path.join(FRONTEND_DIR, "admin.html")
    if os.path.exists(path):
        return FileResponse(path)
    return {"message": "Admin dashboard"}

@app.get("/simulator", include_in_schema=False)
def simulator_page():
    path = os.path.join(FRONTEND_DIR, "simulator.html")
    if os.path.exists(path):
        return FileResponse(path)
    return {"message": "Simulator page"}
