"""Multi-round simulation of assessment platform usage."""
import requests
import json
import random
from datetime import datetime
from collections import Counter

BASE = "http://127.0.0.1:8000"


def register(username, password, display_name, role="student"):
    r = requests.post(f"{BASE}/api/auth/register", json={
        "username": username,
        "password": password,
        "display_name": display_name,
        "role": role,
    })
    return r


def login(username, password, role="student"):
    r = requests.post(f"{BASE}/api/auth/login", json={
        "username": username,
        "password": password,
        "role": role,
    })
    return r.json() if r.status_code == 200 else r.text


def get_questions(token, assessment_type):
    r = requests.get(f"{BASE}/api/assessments/questions", params={"assessment_type": assessment_type},
                     headers={"Authorization": f"Bearer {token}"})
    return r.json() if r.status_code == 200 else r.text


def submit_holland(token, answers):
    r = requests.post(f"{BASE}/api/assessments/holland", json={"answers": answers},
                      headers={"Authorization": f"Bearer {token}"})
    return r.json() if r.status_code == 200 else r.text


def submit_gallup(token, answers):
    r = requests.post(f"{BASE}/api/assessments/gallup", json={"answers": answers},
                      headers={"Authorization": f"Bearer {token}"})
    return r.json() if r.status_code == 200 else r.text


def get_student_report(token):
    r = requests.get(f"{BASE}/api/reports/student", headers={"Authorization": f"Bearer {token}"})
    return r.json() if r.status_code == 200 else r.text


def get_professional_report(token, student_id):
    r = requests.get(f"{BASE}/api/reports/professional/{student_id}", headers={"Authorization": f"Bearer {token}"})
    return r.json() if r.status_code == 200 else r.text


def ensure_user(username, password, display_name):
    r = login(username, password)
    if isinstance(r, dict) and "access_token" in r:
        return r
    rr = register(username, password, display_name)
    if rr.status_code != 200:
        print(f"Register failed for {username}: {rr.status_code} {rr.text}")
    return login(username, password)


def make_holland_answers_radar(token, bias):
    qs = get_questions(token, "holland")
    answers = []
    for q in qs:
        themes = q.get("theme_tags") or []
        target = 3
        for t, score in bias.items():
            if t.upper() in [x.upper() for x in themes]:
                target = score
                break
        val = max(1, min(5, round(random.gauss(target, 0.8))))
        answers.append({"question_num": q["question_num"], "score": val})
    return answers


def make_gallup_answers_bias(token, top_themes):
    qs = get_questions(token, "gallup")
    answers = []
    for q in qs:
        a_themes = set((q.get("theme_tags") or []))
        b_themes = set((q.get("b_side_themes") or []))
        a_overlap = len(a_themes & set(top_themes))
        b_overlap = len(b_themes & set(top_themes))
        if a_overlap > b_overlap:
            base = 2
        elif a_overlap < b_overlap:
            base = -2
        else:
            base = 0
        val = max(-2, min(2, round(random.gauss(base, 0.7))))
        answers.append({"question_num": q["question_num"], "choice": val})
    return answers


def make_gallup_answers_random(n_questions=180):
    return [{"question_num": i + 1, "choice": random.randint(-2, 2)} for i in range(n_questions)]


def make_holland_answers_random(n_questions=60):
    return [{"question_num": i + 1, "score": random.randint(1, 5)} for i in range(n_questions)]


def run_round(round_num, username, password, display_name, holland_bias, gallup_top_themes=None, label=""):
    print(f"\n=== Round {round_num}: {label} ({username}) ===")
    user = ensure_user(username, password, display_name)
    if not isinstance(user, dict) or "access_token" not in user:
        print("Login/register failed", user)
        return None
    token = user["access_token"]

    hol_answers = make_holland_answers_radar(token, holland_bias)
    hol_result = submit_holland(token, hol_answers)
    print("Holland result:", json.dumps(hol_result, ensure_ascii=False, indent=2))

    if gallup_top_themes:
        gal_answers = make_gallup_answers_bias(token, gallup_top_themes)
    else:
        gal_answers = make_gallup_answers_random()
    gal_result = submit_gallup(token, gal_answers)
    print("Gallup result:", json.dumps(gal_result, ensure_ascii=False, indent=2))

    stu_report = get_student_report(token)
    if isinstance(stu_report, dict):
        print("Student careers count:", len(stu_report.get("careers", [])))
        print("Student actions count:", len(stu_report.get("actions", [])))
    else:
        print("Student report error:", stu_report)

    teacher = login("teacher", "teacher123", "teacher")
    prof_report = None
    if isinstance(teacher, dict) and "access_token" in teacher:
        prof_report = get_professional_report(teacher["access_token"], user["user_id"])
        if isinstance(prof_report, dict):
            print("Professional careers count:", len(prof_report.get("careers", [])))
            print("Tension:", prof_report.get("tension"))
        else:
            print("Professional report error:", prof_report)
    else:
        print("Teacher login failed:", teacher)

    return {
        "round": round_num,
        "label": label,
        "username": username,
        "user_id": user.get("user_id"),
        "holland_result": hol_result,
        "gallup_result": gal_result,
        "student_report": stu_report,
        "professional_report": prof_report,
    }


if __name__ == "__main__":
    random.seed(42)
    rounds = []

    rounds.append(run_round(
        1, "sim_student_ria", "pass123", "RIA学生",
        {"R": 5, "I": 5, "A": 4, "S": 2, "E": 1, "C": 2},
        gallup_top_themes=["Achiever", "Analytical", "Deliberative", "Intellection", "Restorative"],
        label="强 RIA + 分析型 Gallup"
    ))

    rounds.append(run_round(
        2, "sim_student_sec", "pass123", "SEC学生",
        {"S": 5, "E": 5, "C": 4, "R": 1, "I": 2, "A": 2},
        gallup_top_themes=["Activator", "Command", "Communication", "Relator", "Woo"],
        label="强 SEC + 影响力 Gallup"
    ))

    rounds.append(run_round(
        3, "sim_student_random", "pass123", "随机学生",
        {"R": 3, "I": 3, "A": 3, "S": 3, "E": 3, "C": 3},
        gallup_top_themes=None,
        label="随机作答"
    ))

    rounds.append(run_round(
        4, "sim_student_c_only", "pass123", "C dominant",
        {"C": 5, "R": 2, "I": 2, "A": 2, "S": 2, "E": 2},
        gallup_top_themes=["Discipline", "Consistency", "Focus", "Arranger", "Responsibility"],
        label="C 独高 + 执行型 Gallup"
    ))

    rounds.append(run_round(
        5, "sim_student_all5", "pass123", "全5学生",
        {"R": 5, "I": 5, "A": 5, "S": 5, "E": 5, "C": 5},
        gallup_top_themes=None,
        label="霍兰德全满分"
    ))

    out_path = "/Users/pengpeng/Desktop/KIMI/测评研究/06-website/simulation_raw_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(rounds, f, ensure_ascii=False, indent=2)

    print("\n=== Summary ===")
    for r in rounds:
        if not r:
            continue
        hol = r["holland_result"]
        gal = r["gallup_result"]
        stu = r["student_report"]
        prof = r["professional_report"]
        print(f"Round {r['round']} {r['label']}: Holland={hol.get('holland_code') if isinstance(hol, dict) else 'ERR'}, "
              f"GallupDomain={gal.get('gallup_domain') if isinstance(gal, dict) else 'ERR'}, "
              f"StudentCareers={len(stu.get('careers', [])) if isinstance(stu, dict) else 'ERR'}, "
              f"ProfCareers={len(prof.get('careers', [])) if isinstance(prof, dict) else 'ERR'}")
    print(f"\nRaw results saved to {out_path}")
