from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.logger.console_logger import error, success
from app.routes import projects, messages, auth, agents
from app.db.main import db
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(projects.router)
app.include_router(messages.router)
app.include_router(auth.router)
app.include_router(agents.router)


@app.on_event("startup")
async def startup_event():
    try:
        test_query = "SELECT cluster_name FROM system.local"
        row = db.get_session().execute(test_query).one()
        success(f"✅ DB status OK on startup: Cluster - {row.cluster_name}")
    except Exception as e:
        error(f"❌ DB status check failed on startup: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    error("🛑 Shutting down FastAPI application...")
    db.close()
