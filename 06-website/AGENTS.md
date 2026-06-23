# Agent 指令：06-website 网站同步规范

本文件对 `06-website/` 目录下的网站（尤其是 `assessment-platform/` 在线测评平台）生效。

## 1. 核心原则

任何对网站代码、数据文件、报告模板、测评逻辑、数据模型、API 或职业-专业映射的修改，都必须在改动完成后同步到设计文档 `06-website/website-implementation-plan-v2.md`。

## 2. 必须同步的场景

修改以下文件或逻辑后，请检查并更新设计文档的对应章节：

| 修改内容 | 需更新的设计文档章节 |
|---------|---------------------|
| `backend/app/models.py` | 第 6 节 数据模型 |
| `backend/app/services/holland.py` | 第 7.1 节 Holland 计分 |
| `backend/app/services/gallup.py` | 第 7.2 节 Gallup 计分 |
| `backend/app/import_data.py` 或 `data/processed/*.json` / `*.md` | 第 6 节、第 7 节、第 10 节 数据导入与初始化 |
| `backend/app/services/report.py` 中报告结构、HTML 样式、双语文本 | 第 9 节 报告设计 |
| `backend/app/services/report.py` 中 `get_career_recommendations` | 第 8 节 职业-专业映射策略 |
| `backend/app/routers/*.py`（新增/删除/修改端点） | 附录 A：API 端点 |
| `frontend/src/views/*.vue`（新增页面、重大交互变更） | 第 5 节 信息架构与页面结构 |
| 新增/删除前端路由 | 第 5 节 |
| 新增/删除数据文件 | 第 10 节 |

## 3. 同步格式

1. 在 `website-implementation-plan-v2.md` 的“附录 C：变更日志 | Changelog”中新增一行，包含：
   - 日期（`YYYY-MM-DD`）
   - 版本号（如 v2.1）
   - 改动摘要（中英文均可，但需清晰）
   - 影响文件列表

2. 如果改动涉及迭代里程碑，在“第 11 节 迭代说明 | Iteration Notes”中补充一个小节。

3. 如果改动改变了用户可见功能，请同时检查 `assessment-platform/README.md` 是否需要更新。

## 4. 禁止行为

- 不要只修改代码而不更新本文档。
- 不要在设计文档中保留与代码明显矛盾的描述。
- 不要删除历史变更日志；如需废弃某功能，追加说明即可。

## 5. 快速检查清单

每次提交前自问：

- [ ] 我是否修改了 `assessment-platform/` 下的代码或数据？
- [ ] 如果是，`website-implementation-plan-v2.md` 是否已同步？
- [ ] 变更日志中是否新增了一条记录？
- [ ] 相关样例报告（`sample-report-*.md`）是否仍然与实现一致？

---

*本文件与 `website-implementation-plan-v2.md` 共同维护，确保设计文档与代码实现保持一致。*
