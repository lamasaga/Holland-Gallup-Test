#!/usr/bin/env python3
"""Merge translation files into the main cliftonstrengths_report_materials.json."""
import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "research", "测评研究", "data", "processed")
TEMPLATE_PATH = os.path.join(DATA_DIR, "cliftonstrengths_report_materials.bilingual_template.json")
JSON_PATH = os.path.join(DATA_DIR, "cliftonstrengths_report_materials.json")

TRANSLATION_FILES = [
    "translations_executing_zh.json",
    "translations_influencing_zh.json",
    "translations_relationship_en.json",
    "translations_strategic_en.json",
]


def main():
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    for filename in TRANSLATION_FILES:
        path = os.path.join(DATA_DIR, filename)
        if not os.path.exists(path):
            print(f"[warn] Translation file not found: {path}")
            continue
        with open(path, "r", encoding="utf-8") as f:
            translations = json.load(f)
        for theme_name, fields in translations.items():
            if theme_name not in data:
                print(f"[warn] Unknown theme in {filename}: {theme_name}")
                continue
            data[theme_name].update(fields)

    # Validation: ensure every theme has all 10 narrative fields populated.
    all_fields = [
        "standard_definition_zh", "standard_definition_en",
        "feature_zh", "feature_en",
        "description_zh", "description_en",
        "application_zh", "application_en",
        "blind_spots_zh", "blind_spots_en",
    ]
    missing = []
    for theme_name, item in data.items():
        for field in all_fields:
            if not item.get(field):
                missing.append(f"{theme_name}.{field}")

    if missing:
        print(f"[warn] Still missing {len(missing)} fields:")
        for m in missing[:20]:
            print(f"  - {m}")
        if len(missing) > 20:
            print(f"  ... and {len(missing) - 20} more")
    else:
        print("All 34 themes have complete bilingual narrative content.")

    # Preserve original flat fields for backward compatibility if needed.
    # We keep only the bilingual fields plus domain/name_en.
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Written merged bilingual JSON to {JSON_PATH}")


if __name__ == "__main__":
    main()
