from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.routers import auth, assessments, reports, teacher

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="RIASEC × CliftonStrengths 在线测评平台",
    description="双维度职业测评工具",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:8080", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(assessments.router)
app.include_router(reports.router)
app.include_router(teacher.router)


@app.get("/")
def root():
    return {"message": "Assessment Platform API"}
