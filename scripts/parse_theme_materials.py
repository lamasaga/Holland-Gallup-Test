#!/usr/bin/env python3
"""Parse cliftonstrengths_report_materials.md and generate populated JSON."""
import json
import os
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "research", "测评研究", "data", "processed")
MD_PATH = os.path.join(DATA_DIR, "cliftonstrengths_report_materials.md")
JSON_PATH = os.path.join(DATA_DIR, "cliftonstrengths_report_materials.json")

# Map Chinese theme names to English Gallup theme names.
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


def parse_md(path: str):
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    # Split by theme sections: "## N. 主题名（领域）"
    theme_blocks = re.split(r"\n## \d+\.\s+", text)
    # First block is header/intro, skip it.
    themes = {}
    for block in theme_blocks[1:]:
        lines = block.splitlines()
        if not lines:
            continue

        # First line: "主题名（领域）" or "主题名（领域）\n..."
        header = lines[0].strip()
        m = re.match(r"(.+?)（(.+?)）", header)
        if not m:
            print(f"[warn] Cannot parse header: {header[:80]}")
            continue

        theme_name = m.group(1).strip()
        domain_zh = m.group(2).strip()

        # Join remaining lines and parse sections.
        body = "\n".join(lines[1:])

        sections = {}
        # Match bold section headers in Chinese.
        # Sections may contain English text with newlines; we stop at the next bold header.
        pattern = re.compile(
            r"\*\*(标准定义|才干特征|才干描述|如何应用优势|注意盲点)\*\*[:：]\s*(.*?)(?=\n\*\*(标准定义|才干特征|才干描述|如何应用优势|注意盲点)\*\*|$)",
            re.DOTALL,
        )
        for match in pattern.finditer(body):
            key = match.group(1)
            value = match.group(2).strip()
            # Normalize whitespace.
            value = re.sub(r"\s+", " ", value)
            sections[key] = value

        themes[theme_name] = {
            "name_en": THEME_EN.get(theme_name, ""),
            "domain": domain_zh,
            "standard_definition": sections.get("标准定义", ""),
            "feature": sections.get("才干特征", ""),
            "description": sections.get("才干描述", ""),
            "application": sections.get("如何应用优势", ""),
            "blind_spots": sections.get("注意盲点", ""),
        }

    return themes


def main():
    themes = parse_md(MD_PATH)
    print(f"Parsed {len(themes)} themes from markdown.")

    # Load existing JSON to preserve any extra fields (just in case).
    existing = {}
    if os.path.exists(JSON_PATH):
        with open(JSON_PATH, "r", encoding="utf-8") as f:
            existing = json.load(f)

    # Merge parsed content into existing structure.
    for theme_name, item in themes.items():
        if theme_name in existing:
            existing[theme_name].update(item)
        else:
            existing[theme_name] = item

    # Reorder to match THEME_EN order for stability.
    ordered = {}
    for name in THEME_EN:
        if name in existing:
            ordered[name] = existing[name]
    # Add any extras at the end.
    for name, item in existing.items():
        if name not in ordered:
            ordered[name] = item

    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(ordered, f, ensure_ascii=False, indent=2)

    print(f"Written populated JSON to {JSON_PATH}")

    # Print a quick validation summary.
    empty_count = 0
    for name, item in ordered.items():
        for field in ["standard_definition", "feature", "description", "application", "blind_spots"]:
            if not item.get(field):
                print(f"[empty] {name}.{field}")
                empty_count += 1
    if empty_count == 0:
        print("All 34 themes have complete content for all fields.")
    else:
        print(f"Total empty fields: {empty_count}")


if __name__ == "__main__":
    main()
