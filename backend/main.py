from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routes import upload, chat, session, student

app = FastAPI(
    title="Lecture Companion API",
    description="Multi-agent system for student support",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router, prefix="/upload", tags=["Upload"])
app.include_router(chat.router, prefix="/chat", tags=["Chat"])
app.include_router(session.router, prefix="/session", tags=["Session"])
app.include_router(student.router, prefix="/student", tags=["Student"])

@app.get("/")
def root():
    return {"status": "Lecture Companion API is running"}