import os

from fastapi import FastAPI

from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, Base, migrate_schema

from app.routers import auth, assessments, reports, teacher, admin



Base.metadata.create_all(bind=engine)

migrate_schema()



_default_origins = "http://localhost:5173,http://localhost:5175,http://127.0.0.1:5173,http://127.0.0.1:5175"

_cors_origins = [

    o.strip()

    for o in os.environ.get("CORS_ORIGINS", _default_origins).split(",")

    if o.strip()

]



app = FastAPI(

    title="RIASEC × CliftonStrengths 在线测评平台",

    description="双维度职业测评工具",

    version="1.1.0"

)



app.add_middleware(

    CORSMiddleware,

    allow_origins=_cors_origins,

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],

)



app.include_router(auth.router)

app.include_router(assessments.router)

app.include_router(reports.router)

app.include_router(teacher.router)

app.include_router(admin.router)



@app.on_event("startup")

def seed_data_on_startup():

    """

    启动时自动导入题库、职业映射和 34 项才干主题描述。

    这些导入都是幂等的，不会重复写入；默认演示账号只在用户表为空时创建。

    避免把本地 SQLite 数据库提交到仓库，同时保证线上部署后报告与本地一致。

    """

    from app.import_data import (

        import_holland_questions,

        import_gallup_questions,

        import_career_mapping,

        import_theme_descriptions,

        create_default_users,

    )

    from app.database import SessionLocal

    from app import models



    db = SessionLocal()

    try:

        import_holland_questions(db)

        import_gallup_questions(db)

        import_career_mapping(db)

        import_theme_descriptions(db)

        if db.query(models.User).first() is None:

            create_default_users(db)

    finally:

        db.close()



@app.get("/")

def root():

    return {"message": "Assessment Platform API", "version": "1.1.0"}


