# RIASEC × CliftonStrengths 在线测评平台

基于 `website-implementation-plan.md` 搭建的双维度职业测评系统。

## 技术栈

- 前端：Vue 3 + Vue Router + Pinia + Axios + Vite
- 后端：Python + FastAPI + SQLAlchemy + SQLite
- 数据：Holland RIASEC 60 题、Gallup 180 题迫选版、78 条职业-专业映射、34 主题素材库

## 项目结构

```
assessment-platform/
├── backend/              # FastAPI 后端
│   ├── app/
│   │   ├── main.py       # 应用入口
│   │   ├── models.py     # 数据库模型
│   │   ├── schemas.py    # Pydantic 数据模型
│   │   ├── auth.py       # JWT 认证
│   │   ├── database.py   # 数据库连接
│   │   ├── routers/      # API 路由
│   │   ├── services/     # 业务逻辑
│   │   └── import_data.py # 数据导入脚本
│   ├── data/             # SQLite 数据库
│   └── requirements.txt
└── frontend/             # Vue 前端
    ├── src/
    │   ├── api/          # API 封装
    │   ├── components/   # 组件
    │   ├── router/       # 路由配置
    │   ├── stores/       # Pinia 状态
    │   └── views/        # 页面
    └── package.json
```

## 快速启动

### 1. 启动后端

```bash
cd assessment-platform/backend
source venv/bin/activate
python -m uvicorn app.main:app --port 8000
```

后端地址：`http://127.0.0.1:8000`

### 2. 启动前端

```bash
cd assessment-platform/frontend
npm run dev
```

前端地址：`http://localhost:5173/`

## 演示账号

- 学生：`student` / `student123`
- 老师：`teacher` / `teacher123`

## 功能模块

### 学生端
- 登录后进入仪表盘，查看 Holland / Gallup 测评进度
- 完成 Holland 60 题兴趣测评
- 完成 Gallup 180 题优势测评
- 双测评完成后查看学生版报告

### 老师端
- 查看所有学生测评完成情况
- 为已完成双测评的学生生成专业版报告
- 可切换查看学生版与专业版报告

## 数据说明

- 首次运行时会自动创建 SQLite 数据库并导入题目与映射数据。
- 如需重新导入数据，可删除 `backend/data/assessment.db` 后重新运行后端，或手动执行：
  ```bash
  python -m app.import_data
  ```

## 注意事项

- 当前 Gallup 计分基于 `gallup_questions_students_association.md` 中的关键词启发式主题映射，非 Gallup 官方算法，仅供探索性分析。
- 职业-专业映射为理论参考，不可用于高利害决策。
- 正式商用 Gallup 完整版 177 对陈述需获得 Gallup 官方授权。
