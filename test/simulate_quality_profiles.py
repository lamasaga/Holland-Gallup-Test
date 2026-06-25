"""
模拟低质量作答，验证乱答检测机制是否生效。
生成 6 组异常作答：Holland 直线/交替/低方差，Gallup 中立/单边/极端交替。
"""
from __future__ import annotations

import json
import os
import random
from datetime import datetime, timezone
from typing import List

import requests

BASE = os.environ.get("ASSESSMENT_API_BASE", "http://127.0.0.1:8000")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "quality_simulations")

TEACHER = {"username": "teacher", "password": "teacher123"}

PROFILES = [
    {"id": "holland_straight", "label": "Holland 全部选 3", "username": "sim_quality_straight", "password": "Test@1234!", "display_name": "直线作答者"},
    {"id": "holland_alternating", "label": "Holland 1-5 交替", "username": "sim_quality_alt", "password": "Test@1234!", "display_name": "交替作答者"},
    {"id": "holland_lowvar", "label": "Holland 低方差", "username": "sim_quality_lowvar", "password": "Test@1234!", "display_name": "低方差作答者"},
    {"id": "gallup_neutral", "label": "Gallup 全中立", "username": "sim_quality_neutral", "password": "Test@1234!", "display_name": "全中立作答者"},
    {"id": "gallup_oneside", "label": "Gallup 单边偏向", "username": "sim_quality_oneside", "password": "Test@1234!", "display_name": "单边偏向者"},
    {"id": "gallup_extreme_alt", "label": "Gallup 极端交替", "username": "sim_quality_extreme", "password": "Test@1234!", "display_name": "极端交替者"},
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


def make_holland_straight(questions: List[dict], score: int = 3) -> List[dict]:
    return [{"question_num": q["question_num"], "score": score} for q in questions]


def make_holland_alternating(questions: List[dict]) -> List[dict]:
    return [{"question_num": q["question_num"], "score": 1 if i % 2 == 0 else 5} for i, q in enumerate(questions)]


def make_holland_lowvar(questions: List[dict]) -> List[dict]:
    # 90% 选 3，10% 选 2 或 4
    return [
        {"question_num": q["question_num"], "score": random.choice([2, 3, 3, 3, 3, 3, 3, 3, 3, 4])}
        for q in questions
    ]


def make_gallup_neutral(questions: List[dict]) -> List[dict]:
    return [{"question_num": q["question_num"], "choice": 0} for q in questions]


def make_gallup_oneside(questions: List[dict], positive: bool = True) -> List[dict]:
    choice = 2 if positive else -2
    return [{"question_num": q["question_num"], "choice": choice} for q in questions]


def make_gallup_extreme_alt(questions: List[dict]) -> List[dict]:
    return [{"question_num": q["question_num"], "choice": -2 if i % 2 == 0 else 2} for i, q in enumerate(questions)]


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

    pid = profile["id"]
    if pid == "holland_straight":
        hol_answers = make_holland_straight(hol_qs, score=3)
        gal_answers = make_gallup_oneside(gal_qs, positive=True)
    elif pid == "holland_alternating":
        hol_answers = make_holland_alternating(hol_qs)
        gal_answers = make_gallup_oneside(gal_qs, positive=True)
    elif pid == "holland_lowvar":
        hol_answers = make_holland_lowvar(hol_qs)
        gal_answers = make_gallup_oneside(gal_qs, positive=True)
    elif pid == "gallup_neutral":
        hol_answers = make_holland_straight(hol_qs, score=3)
        gal_answers = make_gallup_neutral(gal_qs)
    elif pid == "gallup_oneside":
        hol_answers = make_holland_straight(hol_qs, score=3)
        gal_answers = make_gallup_oneside(gal_qs, positive=True)
    elif pid == "gallup_extreme_alt":
        hol_answers = make_holland_straight(hol_qs, score=3)
        gal_answers = make_gallup_extreme_alt(gal_qs)
    else:
        raise ValueError(pid)

    hol_result = submit_holland(token, hol_answers)
    gal_result = submit_gallup(token, gal_answers)

    stu_report = get_student_report(token)

    save(os.path.join(out, "answers_holland.json"), {"answers": hol_answers})
    save(os.path.join(out, "answers_gallup.json"), {"answers": gal_answers})
    save(os.path.join(out, "student_report.json"), stu_report)
    if stu_report.get("report_html"):
        save(os.path.join(out, "student_report.html"), stu_report["report_html"])

    summary = {
        "profile": profile["label"],
        "username": profile["username"],
        "password": profile["password"],
        "display_name": profile["display_name"],
        "user_id": user_id,
        "holland_code": hol_result.get("holland_code"),
        "holland_quality": hol_result.get("holland_quality"),
        "gallup_domain": gal_result.get("gallup_domain"),
        "gallup_quality": gal_result.get("gallup_quality"),
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
        hq = summary["holland_quality"]
        gq = summary["gallup_quality"]
        print(f"  → Holland: risk={hq['response_quality']['risk_level']}, flags={hq['response_quality']['flags']}")
        print(f"  → Gallup:  risk={gq['response_quality']['risk_level']}, flags={gq['response_quality']['flags']}")
        print(f"  → Notes:   {summary['data_quality_notes']}")

    print("\n" + "=" * 80)
    print("低质量模拟结果汇总")
    print("=" * 80)
    for r in results:
        print(f"\n【{r['profile']}】{r['display_name']} ({r['username']})")
        hq = r["holland_quality"]["response_quality"]
        gq = r["gallup_quality"]["response_quality"]
        print(f"  Holland: risk={hq['risk_level']}, flags={hq['flags']}, score={hq['score']}")
        print(f"  Gallup:  risk={gq['risk_level']}, flags={gq['flags']}, score={gq['score']}")
        print(f"  报告提示: {r['data_quality_notes']}")

    save(os.path.join(OUTPUT_DIR, "comparison.json"), {"results": results, "generated_at": datetime.now(timezone.utc).isoformat()})
    print(f"\n全部报告已保存到: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
