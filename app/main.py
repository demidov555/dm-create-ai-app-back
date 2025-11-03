import socketio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import projects, messages
from .db.main import db
from app.sockets import sio_app
from dotenv import load_dotenv

load_dotenv()

# Инициализация FastAPI
app = FastAPI()

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Socket.IO endpoint
app.mount("/socket.io", sio_app)

# Подключение маршрутов FastAPI
app.include_router(projects.router)
app.include_router(messages.router)


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
