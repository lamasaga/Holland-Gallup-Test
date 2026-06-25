#!/usr/bin/env python3
"""Sync bilingual cliftonstrengths_report_materials.json into SQLite DB.

This script drops and recreates the theme_descriptions table to align with
models.ThemeDescription schema, then imports the latest JSON content.
"""
import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
sys.path.insert(0, BACKEND_DIR)

from app.database import engine
from app.database import SessionLocal
from app import models

DATA_DIR = os.path.join(BASE_DIR, "research", "测评研究", "data", "processed")
JSON_PATH = os.path.join(DATA_DIR, "cliftonstrengths_report_materials.json")

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


def main():
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Drop and recreate table to match current schema.
    print("Recreating theme_descriptions table...")
    models.Base.metadata.tables["theme_descriptions"].drop(engine)
    models.Base.metadata.tables["theme_descriptions"].create(engine)

    db = SessionLocal()
    try:
        for theme_name, item in data.items():
            record = models.ThemeDescription(
                theme_name=theme_name,
                theme_name_en=item.get("name_en") or THEME_EN.get(theme_name, ""),
                domain=item.get("domain", ""),
                standard_definition_zh=item.get("standard_definition_zh", ""),
                standard_definition_en=item.get("standard_definition_en", ""),
                feature_zh=item.get("feature_zh", ""),
                feature_en=item.get("feature_en", ""),
                description_zh=item.get("description_zh", ""),
                description_en=item.get("description_en", ""),
                application_zh=item.get("application_zh", ""),
                application_en=item.get("application_en", ""),
                blind_spots_zh=item.get("blind_spots_zh", ""),
                blind_spots_en=item.get("blind_spots_en", ""),
            )
            db.add(record)
        db.commit()
        print(f"Imported {len(data)} theme descriptions.")

        # Validation.
        total = db.query(models.ThemeDescription).count()
        empty = (
            db.query(models.ThemeDescription)
            .filter(
                (models.ThemeDescription.standard_definition_zh == None)
                | (models.ThemeDescription.standard_definition_zh == "")
                | (models.ThemeDescription.standard_definition_en == None)
                | (models.ThemeDescription.standard_definition_en == "")
                | (models.ThemeDescription.feature_zh == None)
                | (models.ThemeDescription.feature_zh == "")
                | (models.ThemeDescription.feature_en == None)
                | (models.ThemeDescription.feature_en == "")
                | (models.ThemeDescription.application_zh == None)
                | (models.ThemeDescription.application_zh == "")
                | (models.ThemeDescription.application_en == None)
                | (models.ThemeDescription.application_en == "")
                | (models.ThemeDescription.blind_spots_zh == None)
                | (models.ThemeDescription.blind_spots_zh == "")
                | (models.ThemeDescription.blind_spots_en == None)
                | (models.ThemeDescription.blind_spots_en == "")
            )
            .count()
        )
        print(f"Total ThemeDescription records: {total}")
        print(f"Records with any empty bilingual field: {empty}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
