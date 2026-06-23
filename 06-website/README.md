# 研究成果展示网站 / Research Website

## 简介 / Introduction

本目录包含项目的静态网站文件，用于展示盖洛普-霍兰德职业测评整合研究的成果。

## 文件结构 / File Structure

```
06-website/
├── index.html        # 首页
├── gallup.html       # 盖洛普 CliftonStrengths 信效度
├── holland.html      # 霍兰德 RIASEC 信效度
├── tag.html          # TAG 标注系统
├── integration.html  # 整合思路与验证
├── system.html       # 双维度评价体系
├── about.html        # 关于本项目
└── style.css         # 共享样式表
```

## 本地查看 / Local Viewing

### 方法一：直接打开
在浏览器中直接打开 `index.html` 文件即可查看。

### 方法二：使用 Python 本地服务器（推荐）
```bash
cd 06-website
python -m http.server 8000
```
然后在浏览器中访问：http://localhost:8000

## 更新说明 / Update Notes

- 网站内容为研究文档的简化展示版本；
- 完整研究文档位于项目其他目录中；
- 网站使用纯 HTML/CSS，无需构建工具。

---

*最后更新 / Last Updated*: 2026-06-17
