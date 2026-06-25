"""
基于大五人格维度模拟 4 组 RIASEC × Gallup 测评，写入数据库并导出报告。
平台本身不是大五测评，这里借用大五维度快速生成差异化的测试人格。
"""
from __future__ import annotations

import json
import os
import random
import sys
from datetime import datetime, timezone
from typing import Dict, List, Set

import requests

BASE = os.environ.get("ASSESSMENT_API_BASE", "http://127.0.0.1:8000")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "bigfive_simulations")

TEACHER = {"username": "teacher", "password": "teacher123"}

# 4 个大五-inspired 人格档案
PROFILES = [
    {
        "id": "openness",
        "label": "高开放性 · 创新型探索者",
        "username": "sim_openness_01",
        "password": "Sim@1234!",
        "display_name": "陈启思",
        "holland_bias": {"I": 4.4, "A": 4.2, "S": 3.0, "E": 2.5, "R": 2.2, "C": 1.8},
        "gallup_favored": {"理念", "思维", "战略", "学习", "前瞻", "搜集", "分析"},
        "gallup_disfavored": {"纪律", "审慎", "成就", "专注", "排难", "和谐", "交往"},
        "strict": False,
    },
    {
        "id": "conscientiousness",
        "label": "高尽责性 · 严谨实干者",
        "username": "sim_conscientious_01",
        "password": "Sim@1234!",
        "display_name": "王守规",
        "holland_bias": {"C": 4.5, "R": 4.0, "I": 3.5, "E": 2.0, "S": 1.8, "A": 1.5},
        "gallup_favored": {"纪律", "责任", "审慎", "成就", "专注", "统筹", "公平"},
        "gallup_disfavored": {"适应", "积极", "取悦", "沟通", "理念", "前瞻", "行动"},
        "strict": True,
    },
    {
        "id": "extraversion",
        "label": "高外向性 · 社交影响者",
        "username": "sim_extraversion_01",
        "password": "Sim@1234!",
        "display_name": "刘朗行",
        "holland_bias": {"E": 4.5, "S": 4.0, "A": 3.2, "R": 2.0, "I": 1.8, "C": 1.6},
        "gallup_favored": {"沟通", "统率", "竞争", "追求", "自信", "行动", "取悦"},
        "gallup_disfavored": {"思维", "分析", "审慎", "学习", "体谅", "和谐", "包容"},
        "strict": False,
    },
    {
        "id": "agreeableness",
        "label": "高宜人性 · 亲和协调者",
        "username": "sim_agreeable_01",
        "password": "Sim@1234!",
        "display_name": "林暖语",
        "holland_bias": {"S": 4.4, "A": 3.8, "R": 2.5, "E": 2.2, "I": 2.0, "C": 2.0},
        "gallup_favored": {"体谅", "和谐", "包容", "伯乐", "关联", "交往", "积极"},
        "gallup_disfavored": {"竞争", "统率", "完美", "批判", "审慎", "分析", "自信"},
        "strict": False,
    },
]


def _api(method: str, path: str, token: str | None = None, **kwargs):
    headers = kwargs.pop("headers", {})
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return requests.request(method, f"{BASE}{path}", headers=headers, timeout=120, **kwargs)


def ensure_user(profile: dict) -> dict:
    payload = {"username": profile["username"], "password": profile["password"], "role": "student"}
    r = _api("POST", "/api/auth/login", json=payload)
    if r.status_code == 200:
        return r.json()
    reg = {
        "username": profile["username"],
        "password": profile["password"],
        "display_name": profile["display_name"],
        "school": "模拟测试",
        "grade": "测试",
    }
    r = _api("POST", "/api/auth/register", json=reg)
    if r.status_code not in (200, 201):
        raise RuntimeError(f"注册失败 {profile['username']}: {r.status_code} {r.text}")
    r = _api("POST", "/api/auth/login", json=payload)
    r.raise_for_status()
    return r.json()


def get_questions(token: str, assessment_type: str) -> List[dict]:
    r = _api("GET", "/api/assessments/questions", token, params={"assessment_type": assessment_type})
    r.raise_for_status()
    return r.json()


def _theme_weight(themes: Set[str], favored: Set[str], disfavored: Set[str]) -> float:
    w = 0.0
    for t in themes:
        if t in favored:
            w += 1.0
        if t in disfavored:
            w -= 1.0
    return w


def make_holland_answers(questions: List[dict], bias: Dict[str, float], strict: bool) -> List[dict]:
    answers = []
    for q in questions:
        themes = [t.upper() for t in (q.get("theme_tags") or [])]
        target = 3.0
        for t, score in bias.items():
            if t in themes:
                target = score
                break
        noise = random.gauss(0, 0.35)
        val = round(target + noise)
        if strict:
            val = min(val, 4)
        val = max(1, min(5, val))
        answers.append({"question_num": q["question_num"], "score": val})
    return answers


def make_gallup_answers(questions: List[dict], favored: Set[str], disfavored: Set[str], strict: bool) -> List[dict]:
    answers = []
    for q in questions:
        a_themes = set(q.get("theme_tags") or [])
        b_themes = set(q.get("b_side_themes") or [])
        a_w = _theme_weight(a_themes, favored, disfavored)
        b_w = _theme_weight(b_themes, favored, disfavored)
        diff = a_w - b_w + random.gauss(0, 0.25)

        if diff > 0.6:
            base = 2 if not strict else 1
        elif diff > 0.15:
            base = 1
        elif diff < -0.6:
            base = -2 if not strict else -1
        elif diff < -0.15:
            base = -1
        else:
            base = 0

        choice = max(-2, min(2, base))
        answers.append({"question_num": q["question_num"], "choice": choice})
    return answers


def submit_holland(token: str, answers: List[dict]) -> dict:
    r = _api("POST", "/api/assessments/holland", token, json={"answers": answers})
    if r.status_code != 200:
        raise RuntimeError(f"Holland 提交失败: {r.status_code} {r.text}")
    return r.json()


def submit_gallup(token: str, answers: List[dict]) -> dict:
    r = _api("POST", "/api/assessments/gallup", token, json={"answers": answers})
    if r.status_code != 200:
        raise RuntimeError(f"Gallup 提交失败: {r.status_code} {r.text}")
    return r.json()


def get_student_report(token: str) -> dict:
    r = _api("GET", "/api/reports/student", token)
    r.raise_for_status()
    return r.json()


def teacher_login() -> dict:
    r = _api("POST", "/api/auth/login", json={**TEACHER, "role": "teacher"})
    r.raise_for_status()
    return r.json()


def get_professional_report(teacher_token: str, student_id: str) -> dict:
    r = _api("GET", f"/api/reports/professional/{student_id}", teacher_token)
    r.raise_for_status()
    return r.json()


def save(path: str, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if isinstance(data, str):
        with open(path, "w", encoding="utf-8") as f:
            f.write(data)
    else:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


def run_profile(profile: dict, teacher_token: str) -> dict:
    random.seed(hash(profile["username"]) % 2**32)
    out = os.path.join(OUTPUT_DIR, profile["id"])

    user = ensure_user(profile)
    token = user["access_token"]
    user_id = user["user_id"]

    hol_qs = get_questions(token, "holland")
    gal_qs = get_questions(token, "gallup")

    hol_answers = make_holland_answers(hol_qs, profile["holland_bias"], profile["strict"])
    gal_answers = make_gallup_answers(gal_qs, profile["gallup_favored"], profile["gallup_disfavored"], profile["strict"])

    hol_result = submit_holland(token, hol_answers)
    gal_result = submit_gallup(token, gal_answers)

    stu_report = get_student_report(token)
    pro_report = get_professional_report(teacher_token, user_id)

    save(os.path.join(out, "answers_holland.json"), {"answers": hol_answers})
    save(os.path.join(out, "answers_gallup.json"), {"answers": gal_answers})
    save(os.path.join(out, "student_report.json"), stu_report)
    save(os.path.join(out, "professional_report.json"), pro_report)
    if stu_report.get("report_html"):
        save(os.path.join(out, "student_report.html"), stu_report["report_html"])
    if pro_report.get("report_html"):
        save(os.path.join(out, "professional_report.html"), pro_report["report_html"])

    summary = {
        "profile": profile["label"],
        "username": profile["username"],
        "password": profile["password"],
        "display_name": profile["display_name"],
        "user_id": user_id,
        "holland_code": hol_result.get("holland_code"),
        "holland_scores": hol_result.get("holland_scores"),
        "gallup_domain": gal_result.get("gallup_domain"),
        "gallup_secondary_domain": gal_result.get("gallup_secondary_domain"),
        "gallup_top5": gal_result.get("gallup_top5"),
        "student_careers": [c.get("career_name") for c in (stu_report.get("careers") or [])],
        "professional_careers": [c.get("career_name") for c in (pro_report.get("careers") or [])],
        "tension": pro_report.get("tension"),
        "data_quality_notes": stu_report.get("data_quality_notes", []),
    }
    save(os.path.join(out, "summary.json"), summary)
    return summary


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    teacher = teacher_login()
    teacher_token = teacher["access_token"]

    results = []
    for profile in PROFILES:
        print(f"Running {profile['label']}...")
        summary = run_profile(profile, teacher_token)
        results.append(summary)
        print(f"  → Holland: {summary['holland_code']}, Gallup: {summary['gallup_domain']}, Top5: {summary['gallup_top5']}")

    # Print comparison table
    print("\n" + "="*80)
    print("模拟结果汇总")
    print("="*80)
    for r in results:
        print(f"\n【{r['profile']}】{r['display_name']} ({r['username']})")
        print(f"  Holland: {r['holland_code']} | Scores: {r['holland_scores']}")
        print(f"  Gallup:  {r['gallup_domain']} / {r['gallup_secondary_domain']}")
        print(f"  Top 5:   {r['gallup_top5']}")
        print(f"  学生版职业: {r['student_careers'][:5]}")
        print(f"  专业版职业: {r['professional_careers'][:5]}")
        print(f"  张力: {r['tension']}")
        print(f"  质量提示: {r['data_quality_notes']}")

    save(os.path.join(OUTPUT_DIR, "comparison.json"), {"results": results, "generated_at": datetime.now(timezone.utc).isoformat()})
    print(f"\n全部报告已保存到: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
