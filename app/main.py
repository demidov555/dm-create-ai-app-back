from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import projects
from .db.main import db
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE",
                   "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(projects.router)


@app.on_event("startup")
async def startup_event():
    try:
        test_query = "SELECT cluster_name FROM system.local"
        row = db.get_session().execute(test_query).one()
        print(f"✅ DB status OK on startup: Cluster - {row.cluster_name}")
    except Exception as e:
        print(f"❌ DB status check failed on startup: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    print("🛑 Shutting down FastAPI application...")
    db.close()
