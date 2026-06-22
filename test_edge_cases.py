"""Edge case and UX issue detection for assessment platform."""
import requests
import json

BASE = "http://127.0.0.1:8000"


def login(username, password, role="student"):
    r = requests.post(f"{BASE}/api/auth/login", json={"username": username, "password": password, "role": role})
    return r.status_code, r.json() if r.status_code == 200 else r.text


def register(username, password, display_name, role="student"):
    r = requests.post(f"{BASE}/api/auth/register", json={"username": username, "password": password, "display_name": display_name, "role": role})
    return r.status_code, r.json() if r.status_code == 200 else r.text


def get_questions(token, atype):
    r = requests.get(f"{BASE}/api/assessments/questions", params={"assessment_type": atype}, headers={"Authorization": f"Bearer {token}"})
    return r.status_code, r.json() if r.status_code == 200 else r.text


def submit_holland(token, answers):
    r = requests.post(f"{BASE}/api/assessments/holland", json={"answers": answers}, headers={"Authorization": f"Bearer {token}"})
    return r.status_code, r.json() if r.status_code == 200 else r.text


def submit_gallup(token, answers):
    r = requests.post(f"{BASE}/api/assessments/gallup", json={"answers": answers}, headers={"Authorization": f"Bearer {token}"})
    return r.status_code, r.json() if r.status_code == 200 else r.text


def get_student_report(token):
    r = requests.get(f"{BASE}/api/reports/student", headers={"Authorization": f"Bearer {token}"})
    return r.status_code, r.json() if r.status_code == 200 else r.text


def get_professional_report(token, student_id):
    r = requests.get(f"{BASE}/api/reports/professional/{student_id}", headers={"Authorization": f"Bearer {token}"})
    return r.status_code, r.json() if r.status_code == 200 else r.text


def get_progress(token):
    r = requests.get(f"{BASE}/api/assessments/progress", headers={"Authorization": f"Bearer {token}"})
    return r.status_code, r.json() if r.status_code == 200 else r.text


print("=== Edge Case Tests ===\n")

# 1. Duplicate registration
print("1. Duplicate registration")
sc, body = register("edge_dup_001", "pass123", "Dup User")
print(f"   First register: {sc}")
sc2, body2 = register("edge_dup_001", "pass123", "Dup User")
print(f"   Second register: {sc2} -> {body2}")

# 2. Login with wrong role
print("\n2. Login with wrong role (student creds as teacher)")
sc, body = login("student", "student123", "teacher")
print(f"   Status: {sc} -> {body}")

# 3. Submit incomplete Holland
print("\n3. Submit incomplete Holland (missing answers)")
sc, body = login("edge_incomplete", "pass123")
if sc != 200:
    register("edge_incomplete", "pass123", "Incomplete")
    sc, body = login("edge_incomplete", "pass123")
token = body["access_token"]
sc2, body2 = submit_holland(token, [{"question_num": 1, "score": 5}])
print(f"   Status: {sc2} -> {body2}")

# 4. Submit Holland with invalid score
print("\n4. Submit Holland with invalid score (score=0)")
sc, body = submit_holland(token, [{"question_num": 1, "score": 0}])
print(f"   Status: {sc} -> {body}")

# 5. Submit Gallup with invalid choice
print("\n5. Submit Gallup with invalid choice (choice=3)")
sc, body = submit_gallup(token, [{"question_num": 1, "choice": 3}])
print(f"   Status: {sc} -> {body}")

# 6. Get report before completing assessments
print("\n6. Get student report before completing assessments")
sc, body = get_student_report(token)
print(f"   Status: {sc} -> {body}")

# 7. Teacher tries to view report of incomplete student
print("\n7. Teacher view report of incomplete student")
sc, body = login("teacher", "teacher123", "teacher")
teacher_token = body["access_token"]
# Need user id of edge_incomplete
me_resp = requests.get(f"{BASE}/api/auth/me", headers={"Authorization": f"Bearer {token}"})
user_id = me_resp.json()["id"]
sc2, body2 = get_professional_report(teacher_token, user_id)
print(f"   Status: {sc2} -> {body2}")

# 8. Retake assessment after completion
print("\n8. Retake assessment after completion")
sc, body = login("edge_retake", "pass123")
if sc != 200:
    register("edge_retake", "pass123", "Retake")
    sc, body = login("edge_retake", "pass123")
token = body["access_token"]
qs = get_questions(token, "holland")[1]
hol_answers = [{"question_num": q["question_num"], "score": 3} for q in qs]
submit_holland(token, hol_answers)
qs2 = get_questions(token, "gallup")[1]
gal_answers = [{"question_num": q["question_num"], "choice": 0} for q in qs2]
submit_gallup(token, gal_answers)
progress1 = get_progress(token)[1]
print(f"   After first completion: {progress1}")
# Now submit again with different answers
hol_answers2 = [{"question_num": q["question_num"], "score": 5 if i < 10 else (1 if i < 20 else 3)} for i, q in enumerate(qs)]
sc2, body2 = submit_holland(token, hol_answers2)
print(f"   Retake Holland status: {sc2} -> {body2}")
gal_answers2 = [{"question_num": q["question_num"], "choice": 2 if i < 30 else -2} for i, q in enumerate(qs2)]
sc3, body3 = submit_gallup(token, gal_answers2)
print(f"   Retake Gallup status: {sc3} -> {body3}")
progress2 = get_progress(token)[1]
print(f"   After retake: {progress2}")

# 9. Professional report for non-existent student
print("\n9. Teacher view report for non-existent student ID")
sc, body = get_professional_report(teacher_token, "nonexistent_user_12345")
print(f"   Status: {sc} -> {body}")

# 10. Access protected endpoint without token
print("\n10. Access protected endpoint without token")
r = requests.get(f"{BASE}/api/assessments/progress")
print(f"   Status: {r.status_code} -> {r.text}")

# 11. Gallup question count
print("\n11. Question counts")
sc, qs = get_questions(teacher_token, "gallup")
print(f"   Gallup questions: {len(qs) if sc == 200 else 'ERR'}")
sc, qs = get_questions(teacher_token, "holland")
print(f"   Holland questions: {len(qs) if sc == 200 else 'ERR'}")

# 12. Check if any Gallup question has empty theme_tags or b_side_themes
print("\n12. Gallup questions with empty theme mappings")
sc, qs = get_questions(teacher_token, "gallup")
empty_a = sum(1 for q in qs if not q.get("theme_tags"))
empty_b = sum(1 for q in qs if not q.get("b_side_themes"))
print(f"   Empty A-side themes: {empty_a}, Empty B-side themes: {empty_b}")

# 13. Check Holland questions with empty theme_tags
print("\n13. Holland questions with empty theme_tags")
sc, qs = get_questions(teacher_token, "holland")
empty = sum(1 for q in qs if not q.get("theme_tags"))
print(f"   Empty theme_tags: {empty}")
