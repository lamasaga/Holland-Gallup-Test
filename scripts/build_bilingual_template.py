#!/usr/bin/env python3
"""Build a clean bilingual template JSON from the markdown source."""
import json
import os
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "research", "测评研究", "data", "processed")
MD_PATH = os.path.join(DATA_DIR, "cliftonstrengths_report_materials.md")
JSON_PATH = os.path.join(DATA_DIR, "cliftonstrengths_report_materials.json")
TEMPLATE_PATH = os.path.join(DATA_DIR, "cliftonstrengths_report_materials.bilingual_template.json")

THEME_EN = {
    "成就": "Achiever",
    "统筹": "Arranger",
    "信仰": "Belief",
    "公平": "Consistency",
    "审慎": "Deliberative",
    "纪律": "Discipline",
    "专注": "Focus",
    "责任": "Responsibility",
    "排难": "Restorative",
    "行动": "Activator",
    "统率": "Command",
    "沟通": "Communication",
    "竞争": "Competition",
    "完美": "Maximizer",
    "自信": "Self-Assurance",
    "追求": "Significance",
    "取悦": "Woo",
    "适应": "Adaptability",
    "关联": "Connectedness",
    "伯乐": "Developer",
    "体谅": "Empathy",
    "和谐": "Harmony",
    "包容": "Includer",
    "个别": "Individualization",
    "积极": "Positivity",
    "交往": "Relator",
    "思维": "Intellection",
    "理念": "Ideation",
    "学习": "Learner",
    "分析": "Analytical",
    "回顾": "Context",
    "战略": "Strategic",
    "前瞻": "Futuristic",
    "搜集": "Input",
}

DOMAIN_EN = {
    "执行力": "Executing",
    "影响力": "Influencing",
    "关系建立": "Relationship Building",
    "战略思维": "Strategic Thinking",
}


def parse_md(path: str):
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    # Normalize line endings and remove the trailing source/anchor artifacts.
    # Split by theme sections.
    theme_blocks = re.split(r"\n## \d+\.\s+", text)
    themes = {}
    for block in theme_blocks[1:]:
        lines = block.splitlines()
        if not lines:
            continue

        header = lines[0].strip()
        m = re.match(r"(.+?)（(.+?)）", header)
        if not m:
            print(f"[warn] Cannot parse header: {header[:80]}")
            continue

        theme_name = m.group(1).strip()
        domain_zh = m.group(2).strip()
        body = "\n".join(lines[1:])

        # Trim after the source line / next anchor if present.
        body = re.split(r"\n\*来源：Strengths Navigator", body)[0]
        body = re.split(r"\n---\s*\n\s*<a id=", body)[0]

        sections = {}
        pattern = re.compile(
            r"\*\*(标准定义|才干特征|才干描述|如何应用优势|注意盲点)\*\*[:：]\s*(.*?)(?=\n\*\*(标准定义|才干特征|才干描述|如何应用优势|注意盲点)\*\*|$)",
            re.DOTALL,
        )
        for match in pattern.finditer(body):
            key = match.group(1)
            value = match.group(2).strip()
            value = re.sub(r"\s+", " ", value)
            sections[key] = value

        themes[theme_name] = {
            "name_en": THEME_EN.get(theme_name, ""),
            "domain": domain_zh,
            "domain_en": DOMAIN_EN.get(domain_zh, ""),
            "standard_definition": sections.get("标准定义", ""),
            "feature": sections.get("才干特征", ""),
            "description": sections.get("才干描述", ""),
            "application": sections.get("如何应用优势", ""),
            "blind_spots": sections.get("注意盲点", ""),
        }

    return themes


def detect_language(text: str) -> str:
    """Heuristic: if more than half the words are Latin script, treat as English."""
    if not text:
        return "unknown"
    latin = len(re.findall(r"[a-zA-Z]", text))
    non_latin = len(re.findall(r"[^\x00-\x7F]", text))
    return "en" if latin > non_latin else "zh"


def build_template():
    themes = parse_md(MD_PATH)
    print(f"Parsed {len(themes)} themes.")

    bilingual = {}
    for name in THEME_EN:
        if name not in themes:
            print(f"[warn] Theme missing from markdown: {name}")
            continue

        item = themes[name]
        bilingual[name] = {
            "domain": item["domain"],
            "domain_en": item["domain_en"],
            "name_en": item["name_en"],
            "standard_definition_zh": item["standard_definition"] if detect_language(item["standard_definition"]) == "zh" else "",
            "standard_definition_en": item["standard_definition"] if detect_language(item["standard_definition"]) == "en" else "",
            "feature_zh": item["feature"] if detect_language(item["feature"]) == "zh" else "",
            "feature_en": item["feature"] if detect_language(item["feature"]) == "en" else "",
            "description_zh": item["description"] if detect_language(item["description"]) == "zh" else "",
            "description_en": item["description"] if detect_language(item["description"]) == "en" else "",
            "application_zh": item["application"] if detect_language(item["application"]) == "zh" else "",
            "application_en": item["application"] if detect_language(item["application"]) == "en" else "",
            "blind_spots_zh": item["blind_spots"] if detect_language(item["blind_spots"]) == "zh" else "",
            "blind_spots_en": item["blind_spots"] if detect_language(item["blind_spots"]) == "en" else "",
        }

    with open(TEMPLATE_PATH, "w", encoding="utf-8") as f:
        json.dump(bilingual, f, ensure_ascii=False, indent=2)

    print(f"Written bilingual template to {TEMPLATE_PATH}")

    # Print missing translations summary.
    missing = []
    for name, item in bilingual.items():
        for field in ["standard_definition_zh", "standard_definition_en",
                      "feature_zh", "feature_en", "description_zh", "description_en",
                      "application_zh", "application_en", "blind_spots_zh", "blind_spots_en"]:
            if not item.get(field):
                missing.append(f"{name}.{field}")

    print(f"Missing fields: {len(missing)}")
    for m in missing[:20]:
        print(f"  - {m}")
    if len(missing) > 20:
        print(f"  ... and {len(missing) - 20} more")


if __name__ == "__main__":
    build_template()
