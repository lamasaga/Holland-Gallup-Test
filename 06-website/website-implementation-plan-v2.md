# 在线测评工具实施计划 v2.0 | Online Assessment Tool Implementation Plan v2.0

> **版本 / Version**: 2.0  
> **定位 / Positioning**: 基于既有研究成果（RIASEC × CliftonStrengths 双维度评价体系）的在线测评平台迭代版。本版本在 v1.0 架构基础上，完成了 Gallup 题目映射补全、A/B 侧主题计分、情景化提示、职业映射扩大以及学生版/专业版报告模板化。  
> **范围 / Scope**: 涵盖学生端与老师端双端口、分次测评、HTML 化报告生成、职业-专业映射、数据导入与本地部署。

---

## 1. 迭代总览 | Iteration Overview

### 1.1 相对 v1.0 的主要改进

| 改进项                  | 说明                                                                                   | 对应代码/文件                                                                                               |
| -------------------- | ------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------- |
| Holland 情景化提示        | 60 题每题补充一个具体生活/学习场景，降低抽象理解成本。                                                        | `data/processed/holland_scenarios.json`                                                               |
| Gallup 情景去选项         | 修复场景提示误把选项文字（非常认同 A…）一起展示的问题。                                                        | `backend/app/import_data.py`                                                                          |
| Gallup 180 题 A 侧映射补全 | 原 117 题有主题归属，现 A 侧主题覆盖 177/180 题（3 题仍缺失）。                                            | `data/processed/gallup_missing_mapping.json`                                                          |
| Gallup B 侧主题机制       | 支持 B 侧主题计分，但实际数据覆盖率仅 26/180 题（14.4%），大部分 B 侧陈述未映射到主题。                                | `data/processed/gallup_missing_mapping.json`, `backend/app/import_data.py`                            |
| A/B 侧主题计分            | 每道题可配置 A 侧主题（选 A 加分）与 B 侧主题（选 B 加分），支持反向陈述。                                          | `backend/app/models.py`, `backend/app/services/gallup.py`                                             |
| 职业映射扩大               | 从仅匹配 Holland 主码，改为同时匹配主/次/第三码；Gallup 领域仅作排序修正。                                       | `backend/app/services/report.py`                                                                      |
| 报告模板化                | 学生版与专业版报告完全按照 `sample-report-student.md` / `sample-report-professional.md` 渲染为 HTML。 | `backend/app/services/report.py`                                                                      |
| 中英双语                 | 报告固定标题、说明、表格列头均使用中 / 英文双语。                                                           | `backend/app/services/report.py`                                                                      |
| 防快速连点                | Holland / Gallup 答题页增加定时器清理，避免快速双击导致跳题。                                              | `frontend/src/views/HollandAssessment.vue`, `frontend/src/views/GallupAssessment.vue`                 |
| 错误提示优化               | 后端校验错误从 `[object Object]` 改为可读文本。                                                    | `frontend/src/views/HollandAssessment.vue`, `frontend/src/views/GallupAssessment.vue`                 |
| 后端提交校验               | Holland / Gallup 提交时校验题数与题号范围，防止 API 被绕过。                                            | `backend/app/routers/assessments.py`                                                                  |
| 数据质量提示               | 报告根据 Holland 区分度、Gallup B 侧覆盖率自动生成质量提示。                                              | `backend/app/services/report.py`, `backend/app/routers/assessments.py`                                |
| 报告去重与标签              | 推荐职业按名称去重；职业标签从数据中读取，减少关键词误判。                                                        | `backend/app/services/report.py`, `backend/app/models.py`, `data/processed/career_major_mapping.json` |
| 动态张力/一致性             | 张力分析综合 Holland 三码；一致性提示根据六边形相邻关系动态计算。                                                | `backend/app/services/report.py`                                                                      |
| 答题交互增强               | 题号导航、自动跳转开关、提交前回顾弹窗、未答题跳转。                                                           | `frontend/src/views/HollandAssessment.vue`, `frontend/src/views/GallupAssessment.vue`                 |
| 仪表盘增强                | 学生仪表盘显示 Holland 分数、Top 5 主题；重新测评需确认。                                                 | `frontend/src/views/StudentDashboard.vue`                                                             |
| 老师工作台增强              | 支持按姓名、完成状态、Holland 代码搜索筛选，可导出 CSV。                                                   | `frontend/src/views/TeacherDashboard.vue`                                                             |
| 报告打印按钮               | 学生版与专业版报告内嵌打印按钮与打印优化样式。                                                              | `backend/app/services/report.py`                                                                      |
| 404 语义修复             | 老师访问不存在学生时返回 404 而非 400。                                                             | `backend/app/routers/reports.py`                                                                      |

### 1.2 当前已实现的报告模块

- **学生一页纸摘要**：核心结果、稳妥入口职业、核心推荐专业、三个下一步行动。
- **专业详细版报告**：报告概览、兴趣舞台、优势风格、6×4 交叉矩阵、推荐专业（Core / Expand / Watch 三层）、推荐职业路径（高/中/就业友好备选 + 标签）、就业市场占位、证据等级说明、兴趣-优势整合分析、行动跟踪模块、下一步行动、附录（RIASEC 剖面、主题叙事、伦理声明）。

---

## 2. 项目目标 | Project Objectives

1. 搭建支持 **学生端** 与 **老师端** 双角色登录的在线测评平台。
2. 学生可 **分两次完成** Holland RIASEC 兴趣测评与 Gallup CliftonStrengths 优势测评。
3. 老师可查看学生完成情况，并为单个学生生成 **学生版** 与 **专业版** 双版本解读报告。
4. 报告核心任务是建立 **测评结果 → 未来职业方向 → 可申请专业** 的映射关系，并支持 **多对多、尽可能广的映射**。
5. 报告输出为 **HTML**，固定文本保持 **中英双语**，便于后续扩展为 PDF 导出。

---

## 3. 技术栈 | Tech Stack

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3 + Vue Router + Pinia + Axios + Vite |
| 后端 | Python 3.9 + FastAPI 0.111 + SQLAlchemy 2.0 + Pydantic |
| 数据库 | SQLite（`backend/data/assessment.db`） |
| 认证 | JWT（python-jose + passlib + bcrypt 4.0.1） |
| 测试 | Puppeteer（e2e） |
| 数据导入 | Markdown / JSON 解析脚本 |

---

## 4. 目录结构 | Project Structure

```
06-website/
├── README.md                               # 静态成果网站说明
├── about.html                              # 项目说明与伦理声明
├── website-implementation-plan.md          # v1.0 实施计划（原始）
├── website-implementation-plan-v2.md       # 本文件：v2.0 迭代后设计文档
├── sample-report-professional.md         # 专业版报告样例
├── sample-report-student.md              # 学生版报告样例
├── report-improvement-issues.md          # 报告改进问题清单
└── assessment-platform/                    # 在线测评平台
    ├── README.md
    ├── backend/
    │   ├── app/
    │   │   ├── main.py
    │   │   ├── models.py
    │   │   ├── schemas.py
    │   │   ├── auth.py
    │   │   ├── database.py
    │   │   ├── import_data.py
    │   │   ├── routers/
    │   │   │   ├── auth.py
    │   │   │   ├── assessments.py
    │   │   │   ├── reports.py
    │   │   │   └── teacher.py
    │   │   └── services/
    │   │       ├── holland.py
    │   │       ├── gallup.py
    │   │       └── report.py
    │   ├── data/assessment.db
    │   └── requirements.txt
    └── frontend/
        ├── src/
        │   ├── api/index.js
        │   ├── router/index.js
        │   ├── stores/auth.js
        │   └── views/
        │       ├── Login.vue
        │       ├── StudentDashboard.vue
        │       ├── HollandAssessment.vue
        │       ├── GallupAssessment.vue
        │       ├── StudentReport.vue
        │       ├── TeacherDashboard.vue
        │       └── TeacherReport.vue
        └── e2e-full.cjs
```

---

## 5. 信息架构与页面结构 | Information Architecture

```
/
├── /login                  # 登录页（角色选择 + 账号密码）
├── /student
│   ├── /dashboard          # 学生仪表盘
│   ├── /holland            # Holland RIASEC 测评页
│   ├── /gallup             # Gallup CliftonStrengths 测评页
│   └── /report             # 学生版报告页
├── /teacher
│   ├── /dashboard          # 老师工作台（学生列表）
│   └── /report/:studentId  # 单个学生双版本报告页
└── /about                  # 项目说明与伦理声明（静态 HTML）
```

---

## 6. 数据模型 | Data Model

### 6.1 用户表 users

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID string | 主键 |
| username | string | 用户名/学号 |
| display_name | string | 显示名称 |
| role | enum | `student` / `teacher` |
| password_hash | string | bcrypt 加密 |
| created_at | timestamp | 创建时间 |

### 6.2 测评状态表 assessments

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID string | 主键 |
| user_id | UUID string | 关联用户 |
| holland_done | int | 0/1 |
| holland_scores | JSON | `{R,I,A,S,E,C}` |
| holland_code | string | 三字母代码 |
| gallup_done | int | 0/1 |
| gallup_top5 | JSON | 主题名列表 |
| gallup_top10 | JSON | 主题名列表 |
| gallup_domain | string | 主导领域中文 |
| gallup_scores | JSON | 34 主题 raw score |
| status | JSON | 扩展字段 |
| completed_at | timestamp | 完成时间 |
| updated_at | timestamp | 更新时间 |

### 6.3 题目表 questions

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID string | 主键 |
| assessment_type | string | `holland` / `gallup` |
| question_num | int | 题号 |
| statement_a | text | A 陈述 |
| statement_b | text | B 陈述（Holland 为 null） |
| scenario_hint | text | 情景提示 |
| theme_tags | JSON | A 侧主题列表 |
| b_side_themes | JSON | B 侧主题列表 |

### 6.4 职业-专业映射表 career_major_mapping

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID string | 主键 |
| career_name | string | 职业名称 |
| riasec_primary | string | 主要 RIASEC 类型（R/I/A/S/E/C） |
| cs_domain | string | CliftonStrengths 领域英文 |
| related_majors | JSON | 相关专业列表 |
| evidence_level | string | A/B/C/D |
| description | text | 工作内容说明 |

### 6.5 主题素材表 theme_descriptions

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID string | 主键 |
| theme_name | string | 中文主题名 |
| theme_name_en | string | 英文主题名 |
| domain | string | 领域中文 |
| standard_definition | text | 中文标准定义 |
| feature | text | 特征（可能含英文素材） |
| description | text | 描述 |
| application | text | 应用建议 |
| blind_spots | text | 盲点 |

---

## 7. 测评流程与计分 | Assessment Flow & Scoring

### 7.1 Holland RIASEC

- 60 题，每类型 10 题。
- 选项 1-5 分（很不喜欢 → 非常喜欢）。
- 同类型得分相加，取 Top 3 构成三字母代码（同分按 R→I→A→S→E→C 顺序）。

### 7.2 Gallup CliftonStrengths（180 题迫选版）

- 每题 A/B 两个陈述，五个选项：非常认同 A (+2)、比较认同 A (+1)、两者居中 (0)、比较认同 B (-1)、非常认同 B (-2)。
- 每道题可配置 `theme_tags`（A 侧主题）与 `b_side_themes`（B 侧主题）。
- 计分：A 侧主题 `+ choice`，B 侧主题 `- choice`。
- 累加得到 34 主题 raw score，取 Top 5 / Top 10。
- Top 5 按领域统计，数量最多的领域为 `gallup_domain`。

### 7.3 题目映射来源

- Holland：代码硬编码 60 条陈述 + `holland_scenarios.json` 情景。
- Gallup：
  - 原始映射来自 `gallup_questions_students_association.md`（严格解析，不包含示例题目编号），仅提供 A 侧主题。
  - 缺失 63 题由 `gallup_missing_mapping.json` 补全 A 侧主题；该文件含少量 B 侧主题，但 154/180 题（85.6%）的 B 侧主题仍为空。
  - "适应"主题的题目在 `import_data.py` 中硬编码为 B 侧，未进入数据文件。

---

## 8. 职业-专业映射策略 | Career-Major Mapping Strategy

目标：**以 Holland 兴趣为主，Gallup 优势为辅，尽量扩大推荐范围**。

1. 对 Holland 三码的每个字母分别取候选职业：
   - 主码取前 3 个；
   - 次码取前 3 个；
   - 第三码取前 2 个。
2. 每个职业的匹配分 = 10（主码命中）+ Gallup 领域匹配 +2 + 证据等级加分（A=3, B=2, C=1, D=0）。
3. 合并去重后按匹配分排序，返回前 N 个：
   - 学生版：5 个；
   - 专业版：8 个。
4. 推荐专业从返回职业的相关专业中聚合，按出现频次/匹配度分为：
   - Core（核心专业，最多 8 个）
   - Expand（拓展专业，最多 8 个）
   - Watch（可关注专业，最多 6 个）

---

## 9. 报告设计 | Report Design

### 9.1 学生版报告

- 文件：`sample-report-student.md`
- 形式：一页纸摘要
- 模块：
  1. 我的核心结果
  2. 稳妥入口职业
  3. 核心推荐专业
  4. 三个下一步行动

### 9.2 专业版报告

- 文件：`sample-report-professional.md`
- 形式：详细 HTML 报告（`report_html`）
- 模块：报告概览、稳妥入口职业、兴趣舞台、优势风格、兴趣×优势交叉矩阵、推荐申请专业、推荐职业路径、就业市场参考、证据等级说明、兴趣-优势整合分析、行动跟踪模块、下一步行动、附录。
- 所有固定标题与说明为中英双语；素材性文本保留原文并附加“素材语言说明”。

### 9.3 报告渲染方式

- 后端 `report.py` 生成完整 HTML 字符串，通过 `report_html` 字段返回。
- 前端 `StudentReport.vue` 与 `TeacherReport.vue` 使用 `v-html` 渲染。
- HTML 内嵌 `.kz-report` 命名空间样式，避免污染全局。

---

## 10. 数据导入与初始化 | Data Import & Initialization

后端启动时 `Base.metadata.create_all()` 自动建表。
首次访问相关接口时调用 `import_data.py` 中的函数导入：

| 数据 | 来源文件 |
|------|---------|
| Holland 60 题 | `backend/app/import_data.py` 硬编码 + `data/processed/holland_scenarios.json` |
| Gallup 180 题 | `data/processed/gallup_180_questions_list.md` |
| Gallup 主题映射 | `data/processed/gallup_questions_students_association.md` + `data/processed/gallup_missing_mapping.json` |
| 职业-专业映射 | `data/processed/career_major_mapping.json` |
| 主题素材 | `data/processed/cliftonstrengths_report_materials.json` |
| 演示账号 | `backend/app/import_data.py` 中硬编码 |

如需重新导入，删除 `backend/data/assessment.db` 后重启后端，或运行：

```bash
cd assessment-platform/backend
source venv/bin/activate
python -m app.import_data
```

---

## 11. 迭代说明 | Iteration Notes

### 11.1 第一次迭代：基础平台搭建
- 完成前后端项目结构、登录认证、Holland / Gallup 测评页面、基础报告。

### 11.2 第二次迭代：题目与映射补全
- 补充 Holland 情景提示。
- 修复 Gallup 情景提示误含选项文字的问题。
- 补全 Gallup 180 题映射到 34 主题，并支持 A/B 侧主题计分。

### 11.3 第三次迭代：报告与职业映射优化
- 重构职业推荐逻辑，扩大映射范围。
- 按照 sample-report 模板生成 HTML 版学生版与专业版报告。
- 实现中英双语固定文本，处理素材语言混杂问题。
- 优化答题交互（防快速连点、错误提示）。

### 11.4 第四次迭代：模拟测试问题修复（v2.0.2）
- 后端增加 Holland / Gallup 提交校验与 404 语义修复。
- 报告增加数据质量提示、职业去重、动态张力/一致性分析、职业标签字段。
- 学生仪表盘展示 Holland 分数与 Gallup Top 5；老师工作台增加搜索/筛选/导出。
- 答题页增加题号导航、自动跳转开关、提交前回顾。
- 报告内嵌打印按钮与打印优化样式。

### 11.5 已知限制与后续任务

| 限制/任务 | 说明 | 状态 |
|----------|------|------|
| Gallup 官方算法 | 当前为 180 题迫选简化计分，非官方算法。 | 需官方授权后替换 |
| 主题 narrative 全翻译 | 素材库中 feature/application/blind_spots 部分仍为英文。 | 已加说明，待后续翻译 |
| 就业市场数据 | 当前为占位表格，未接入真实数据源。 | 待接入第三方数据 |
| PDF 导出 | 当前仅支持浏览器打印/另存为 PDF。 | 二期功能 |
| 目标申请地区 | 当前未收集用户目标地区，报告中显示“未指定”。 | 二期前端扩展 |
| Gallup B 侧主题映射 | 154/180 题 B 侧主题为空，导致 B 侧陈述未参与计分，优势结果可能失真。 | 高优先级：需补齐 B 侧映射或改用单维度计分 |

---

## 12. 同步机制 | Synchronization Mechanism

为保证本设计文档与代码实现持续一致，后续对 `assessment-platform/` 的修改需同步更新本文档：

1. **每次修改后**，检查本文档中以下章节是否需要更新：
   - 数据模型（第 6 节）
   - 测评流程与计分（第 7 节）
   - 职业-专业映射策略（第 8 节）
   - 报告设计（第 9 节）
   - 迭代说明（第 11 节）
   - 附录 A：API 端点
   - 附录 C：变更日志

2. **新增功能**时，在“迭代说明”中补充一行；在“附录 C：变更日志”中记录日期、改动摘要、影响文件。

3. **修改数据文件**（如新增题目映射、调整职业映射）时，同步更新“数据导入与初始化”表格。

4. 具体执行要求见同目录 `AGENTS.md`。

---

## 13. 模拟测试问题清单 | Simulation Test Findings

> 本节记录 2026-06-22 前后通过 API + 前端代码审查进行的多轮模拟测试所发现的问题。**注：以下 P0/P1/P2 级别问题已在 v2.0.2 修复批次中处理；P3 与数据依赖项（如主题 narrative 全翻译、完整 B 侧映射）列为长期任务。** 测试脚本与原始结果保存在：
> - `/Users/pengpeng/Desktop/KIMI/测评研究/06-website/assessment-platform/test_simulation.py`
> - `/Users/pengpeng/Desktop/KIMI/测评研究/06-website/assessment-platform/test_edge_cases.py`
> - `/Users/pengpeng/Desktop/KIMI/测评研究/06-website/simulation_raw_results.json`
> - `/Users/pengpeng/Desktop/KIMI/测评研究/06-website/simulation_run.log`

### 13.1 测试方法

- **多轮正例模拟**：构造 5 组不同 Holland / Gallup 倾向的模拟学生账号，完成完整测评并查看学生版与专业版报告。
- **边界用例测试**：重复注册、错误角色登录、不完整提交、非法分数、提前查看报告、老师查看未完成学生、重复作答、越权访问、空映射检查等。
- **前端代码审查**：检查答题流程、仪表盘、报告页交互与状态管理。

### 13.2 关键数据问题（高优先级）

| 问题 | 现象 | 影响 | 建议修复 |
|------|------|------|---------|
| **Gallup B 侧主题覆盖率极低** | 180 题中仅 26 题有 B 侧主题，154 题（85.6%）为空。 | B 侧陈述未参与计分，优势结果主要由 A 侧正向选择决定，可能严重失真。 | 补齐 180 题 B 侧主题映射；或在数据补齐前，在报告中明确标注“B 侧映射未完成，结果仅供参考”。 |
| **Gallup A 侧主题仍有 3 题缺失** | 题号 97、119、127 的 `theme_tags` 为空。 | 这 3 题选择不会对任何主题产生贡献，降低测评有效性。 | 补全这 3 题的 A 侧主题。 |
| **B 侧映射数据源单一且缺失严重** | `gallup_missing_mapping.json` 仅 63 条记录，其中绝大部分 `b` 为空；`import_data.py` 把“适应”硬编码为 B 侧。 | 数据与代码耦合，维护困难；B 侧计分能力名存实亡。 | 将 B 侧映射统一纳入数据文件，补充每道题的 B 侧主题。 |

### 13.3 计分与算法问题

| 问题 | 现象 | 影响 | 建议修复 |
|------|------|------|---------|
| **Holland 计分依赖固定题序** | `calculate_holland` 按 `(qn-1)//10` 推断类型，未校验 `theme_tags`。 | 若题目顺序或 `theme_tags` 与代码不一致，结果会错。 | 使用 `theme_tags` 作为计分依据，或增加一致性校验。 |
| **Gallup 领域判定不稳定** | 仅按 Top 5 主题数量取最多领域，未处理平局；模拟中 intended 领域常与实际不符。 | 兴趣-优势“张力”结论可能不可靠。 | 引入 Top 10 或 raw score 加权；平局时给出提示。 |
| **Holland 全满分时三码任意** | 所有分数相同时三码按 R→I→A→S→E→C 固定为 `RIA`。 | 学生可能得到误导性代码。 | 增加“区分度过低”提示，报告里说明。 |
| **重复作答无历史记录** | 再次提交会静默覆盖数据库中的分数，无版本、无审计。 | 学生/老师无法追溯变化，也不利于研究验证。 | 增加 `assessment_history` 表或至少记录 `updated_at` 与变更日志。 |
| **Holland 允许不完整提交** | 提交 1 题也能成功并生成三码。 | 前端虽校验 60 题，但 API 不校验，存在被绕过的风险。 | 后端增加答案数量与题号范围校验。 |

### 13.4 报告内容问题

| 问题 | 现象 | 影响 | 建议修复 |
|------|------|------|---------|
| **推荐职业数量固定** | 学生版永远 5 个，专业版永远 8 个，不随数据质量变化。 | 数据不足时仍会硬凑，显得不自然。 | 当可推荐职业不足时给出提示，并允许少于上限。 |
| **职业分层出现重复** | Round 4 专业版“项目经理”出现两次（分别属于 R 和 E 主码）。 | 报告不专业，学生困惑。 | 去重时以职业名为 key，避免同一职业在多层级/多字母下重复。 |
| **张力分析只取首码** | `analyze_tension` 仅对比 Holland 第一码与 Gallup 领域。 | 忽略次码、第三码与领域的匹配关系，结论过于简化。 | 综合三码与 Top 5 领域分布进行张力分析。 |
| **主题 narrative 仍为英文素材** | 专业版附录 B 的 feature/application/blind_spots 中英混杂。 | 影响中文用户阅读体验。 | 完成主题 narrative 的标准化翻译。 |
| **就业市场占位模块** | 专业版“就业市场参考”直接声明为占位模块。 | 报告完整性受损。 | 接入真实数据或暂时折叠该模块。 |
| **专业表格重复列内容** | “推荐申请专业”表格的“国内可报说明”列直接复制专业名称。 | 信息价值低。 | 补充具体说明，如学科门类、典型院系。 |
| **学生版行动不个性化** | 永远是固定的 3 条通用建议。 | 与学生结果关联弱。 | 根据 Holland 代码和 Gallup 领域动态生成行动建议。 |
| **“一致性提示”为静态文本** | `_overall_fit` 下方固定显示“三码在六边形上相对集中”。 | 当三码分散时会给出错误暗示。 | 根据三码在六边形上的实际距离动态计算。 |
| **标签分类依赖关键词启发式** | `_career_tag` 通过关键词匹配决定“稳就业/探索/高挑战”，可能误判。 | 例如“管理顾问”含“管理”被标为“高挑战型”。 | 在职业映射数据中增加 `career_tag` 字段，人工标注。 |

### 13.5 前端交互问题

| 问题 | 现象 | 影响 | 建议修复 |
|------|------|------|---------|
| **自动跳转无法关闭** | 选择答案后 200ms 自动下一题，无设置项。 | 部分用户可能来不及确认或误触。 | 增加“自动下一题”开关，默认开启但可关闭。 |
| **无题目导航与进度总览** | 只能上一题/下一题逐题进行，不能跳到任意题或查看已答题分布。 | 60/180 题时回顾与检查成本高。 | 增加题号面板、进度条、未答题提示。 |
| **提交前无确认/回顾页** | 答完最后一题直接提交，无汇总检查。 | 容易漏答或误提交。 | 增加提交前确认页，列出未答题。 |
| **报告页无打印/导出按钮** | 报告通过 `v-html` 渲染，依赖浏览器打印。 | 用户体验不闭环。 | 增加“打印/PDF”按钮，并优化打印样式。 |
| **学生仪表盘信息过少** | 完成后仅显示领域，不显示 Top 5 主题、Holland 分数等。 | 学生无法快速回顾核心结果。 | 在仪表盘展示核心结果摘要。 |
| **老师工作台无搜索/筛选** | 学生多时需要滚动查找。 | 可用性差。 | 增加按姓名、Holland 代码、完成状态筛选。 |
| **无数据导出** | 老师无法批量导出学生结果。 | 不利于后续咨询与研究。 | 增加 CSV/Excel 导出功能。 |
| **重复作答无确认** | 学生再次进入已完成的测评会直接覆盖。 | 可能误操作丢失历史结果。 | 再次进入时提示“已完成，是否重新测评”。 |
| **移动端 A/B 布局风险** | Gallup 题目使用 `grid-template-columns: 1fr 1fr`，小屏可能挤压。 | 移动端体验未经验证。 | 增加响应式布局测试与调整。 |

### 13.6 API / 后端问题

| 问题 | 现象 | 影响 | 建议修复 |
|------|------|------|---------|
| **不存在学生返回 400 而非 404** | 老师访问不存在 studentId 时提示“Student has not completed both assessments”。 | 语义错误，调试困难。 | 先判断用户是否存在，再判断测评完成状态。 |
| **缺少限流与审计日志** | 无接口限流，无报告查看日志。 | 存在滥用风险，也无法追溯老师查看行为。 | 增加基本限流与访问日志表。 |
| **后端未校验 Holland 题数** | 见 13.3。 | API 可被绕过。 | 后端校验。 |
| **专业版与学生版报告独立加载** | `TeacherReport.vue` 同时请求两个报告，任一失败即 alert。 | 一个接口失败会导致整个页面不可用。 | 改为独立加载、独立错误提示。 |

### 13.7 本轮测试结果速览

| 轮次 | 标签 | Holland 三码 | Gallup 领域 | 学生版职业数 | 专业版职业数 | 主要观察 |
|------|------|-------------|------------|-------------|-------------|---------|
| 1 | 强 RIA + 分析型 Gallup | RIA | 关系建立 | 5 | 8 | 预期“战略思维”，实际“关系建立”；推荐职业多与 R/I/A + Relationship Building 组合。 |
| 2 | 强 SEC + 影响力 Gallup | SEC | 战略思维 | 5 | 8 | 预期“影响力”，实际“战略思维”；张力提示模板化。 |
| 3 | 随机作答 | ACI | 影响力 | 5 | 8 | 随机数据仍能生成完整报告，缺乏数据质量警告。 |
| 4 | C 独高 + 执行型 Gallup | CRE | 执行力 | 5 | 8 | 领域与兴趣匹配，但“项目经理”在报告中重复出现。 |
| 5 | Holland 全满分 | RIA | 关系建立 | 5 | 8 | 全满分被固定编码为 RIA，未提示区分度过低。 |

### 13.8 修复优先级建议

1. **P0（阻塞上线）**：补齐 Gallup B 侧主题映射，或临时在报告中声明 B 侧映射未完成；修复重复职业问题。
2. **P1（严重影响体验）**：后端校验 Holland/Gallup 题数；报告增加数据质量提示；修复“不存在学生返回 400”问题。
3. **P2（优化体验）**：仪表盘展示 Top 5；老师工作台搜索筛选；提交前回顾页；自动跳转开关。
4. **P3（长期建设）**：主题 narrative 全翻译；就业市场数据接入；PDF 导出；测评历史版本。

### 13.9 v2.0.2 修复状态 | Fix Status in v2.0.2

| 原问题 | 修复方式 | 状态 |
|--------|---------|------|
| Gallup B 侧映射覆盖率仅 14.4% | 移除 `import_data.py` 硬编码；在报告中显式提示 B 侧覆盖率；将“适应”B 侧映射移入数据文件。 | 部分修复（数据待补齐） |
| 推荐职业重复 | `get_career_recommendations` 与 `_build_career_tiers` 按职业名去重。 | 已修复 |
| 后端未校验题数 | `submit_holland` / `submit_gallup` 校验 60/180 题及题号范围。 | 已修复 |
| 不存在学生返回 400 | `reports.py` 增加 `_require_student_exists`，返回 404。 | 已修复 |
| 无数据质量提示 | 新增 `_build_data_quality_notes`，报告顶部显示区分度低 / B 侧覆盖率低提示。 | 已修复 |
| Holland 计分依赖固定题序 | `calculate_holland` 优先使用 `theme_tags`，回退到固定题序。 | 已修复 |
| Gallup 领域判定不稳定 | 使用 Top 10 加权 + raw score 平局打破。 | 已修复 |
| 张力分析只取首码 | `analyze_tension` 综合 Holland 三码与 Gallup 领域。 | 已修复 |
| 一致性提示静态 | `_holland_consistency` 根据六边形相邻关系动态计算。 | 已修复 |
| 职业标签关键词误判 | `career_major_mapping.json` 增加 `career_tag` 字段，`_career_tag` 优先读取。 | 已修复 |
| 专业表格重复列 | `_major_table_rows` 根据专业名生成国内可报说明，不再复制名称。 | 已修复 |
| 学生版行动不个性化 | `_build_personalized_actions` 根据 Holland 首码 + Gallup 领域生成。 | 已修复 |
| 仪表盘信息少 | `StudentDashboard.vue` 显示分数、Top 5，重新测评需确认。 | 已修复 |
| 老师工作台无筛选 | `TeacherDashboard.vue` 增加搜索、状态筛选、Holland 代码筛选、CSV 导出。 | 已修复 |
| 答题无导航/回顾 | 增加题号面板、自动跳转开关、提交前回顾弹窗、未答题跳转。 | 已修复 |
| 报告无打印按钮 | 学生版与专业版 HTML 增加 `window.print()` 按钮与 `@media print` 样式。 | 已修复 |
| 就业市场占位模块 | 文案改为“数据建设中”，说明后续接入计划与当前参考方式。 | 已优化 |
| 主题 narrative 中英混杂 | 附录 B 说明更清晰，提示优先参考 Top 5 双语一句话定义。 | 已优化 |

---

## 附录 A：API 端点 | API Endpoints

| 方法 | 端点 | 说明 | 权限 |
|------|------|------|------|
| POST | `/api/auth/register` | 注册 | 公开 |
| POST | `/api/auth/login` | 登录 | 公开 |
| GET | `/api/auth/me` | 当前用户 | 登录 |
| GET | `/api/assessments/questions?assessment_type=` | 获取题目 | 登录 |
| GET | `/api/assessments/progress` | 测评进度 | 登录 |
| POST | `/api/assessments/holland` | 提交 Holland | 学生 |
| POST | `/api/assessments/gallup` | 提交 Gallup | 学生 |
| GET | `/api/reports/student` | 学生版报告 | 学生本人 |
| GET | `/api/reports/student/:studentId` | 学生版报告（老师查看） | 老师 |
| GET | `/api/reports/professional/:studentId` | 专业版报告 | 老师 |
| GET | `/api/teacher/students` | 学生列表 | 老师 |

## 附录 B：设计文档 ↔ 代码对应表 | Design-to-Code Mapping

| 设计章节 | 主要代码文件 |
|---------|-------------|
| 数据模型 | `backend/app/models.py` |
| Holland 计分 | `backend/app/services/holland.py` |
| Gallup 计分 | `backend/app/services/gallup.py` |
| 报告生成 | `backend/app/services/report.py` |
| 职业推荐 | `backend/app/services/report.py` 中 `get_career_recommendations` |
| API 路由 | `backend/app/routers/*.py` |
| 前端页面 | `frontend/src/views/*.vue` |
| 数据导入 | `backend/app/import_data.py` |
| 报告样例 | `sample-report-student.md`, `sample-report-professional.md` |
| 改进问题清单 | `report-improvement-issues.md` |

## 附录 C：变更日志 | Changelog

| 日期 | 版本 | 改动摘要 | 影响文件 |
|------|------|---------|---------|
| 2026-06-18 | v1.0 | 初始实施计划 | `website-implementation-plan.md` |
| 2026-06-22 | v2.0 | 补全 Gallup 映射、A/B 侧计分、情景化、报告模板化、中英双语、职业映射扩大 | `website-implementation-plan-v2.md`, `backend/app/services/report.py`, `backend/app/services/gallup.py`, `backend/app/import_data.py`, `frontend/src/views/*.vue`, 数据 JSON 文件 |
| 2026-06-22 | v2.0.1 | 多轮模拟测试与问题整理：发现 Gallup B 侧映射覆盖率仅 14.4%、推荐职业重复、报告静态文本等 30+ 项问题 | `website-implementation-plan-v2.md`（新增第 13 节）、测试脚本与日志文件 |
| 2026-06-22 | v2.0.2 | 修复第 13 节中 P0/P1/P2 问题：后端校验、404 语义、数据质量提示、报告去重、动态张力/一致性、职业标签字段、仪表盘信息、老师搜索筛选、答题导航与回顾、打印按钮、重新测评确认 | `backend/app/services/*.py`, `backend/app/routers/*.py`, `backend/app/models.py`, `backend/app/schemas.py`, `backend/app/import_data.py`, `frontend/src/views/*.vue`, `data/processed/career_major_mapping.json`, `data/processed/gallup_missing_mapping.json` |

---

*本文件由开发 agent 根据当前代码实现与样例报告整理。后续修改请同步更新。*
