import json
import os
import re
import sys
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine, Base
from app import models

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(os.path.dirname(BASE_DIR), "..", "..", "data", "processed")
# Adjust because backend is at 06-website/assessment-platform/backend, data is at data/processed
# Relative path: backend/../../data/processed
DATA_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "..", "..", "data", "processed"))


def parse_gallup_180_questions(md_path: str):
    """Parse gallup_180_questions_list.md into list of question dicts."""
    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Split by question headers like "### 第 1 题"
    # Stop before the options line (starts with 非常认同A) or section divider
    pattern = re.compile(
        r"###\s*第\s*(\d+)\s*题\s*\n+"
        r"\*\*A:\*\*\s*(.+?)\s*\n+"
        r"\*\*B:\*\*\s*(.+?)\s*\n+"
        r"💡\s*\*\*场景提示\*\*：\s*(.+?)"
        r"(?=\n\s*非常认同A|\n+---|\n+###|$)",
        re.DOTALL
    )
    matches = pattern.findall(content)
    
    questions = []
    for num_str, a, b, scenario in matches:
        questions.append({
            "question_num": int(num_str.strip()),
            "statement_a": a.strip(),
            "statement_b": b.strip(),
            "scenario_hint": scenario.strip(),
            "theme_tags": [],  # will be filled from association file
        })
    return questions


def parse_gallup_theme_association(md_path: str):
    """Parse gallup_questions_students_association.md to get theme -> question nums mapping."""
    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    mapping = {}
    # Split by theme headers like "### 专注 Focus"
    sections = re.split(r"###\s+(.+?)\s*\n", content)
    
    current_theme = None
    for i, section in enumerate(sections):
        if i == 0:
            continue
        if i % 2 == 1:
            # This is the theme header
            current_theme = section.strip().split()[0]  # take Chinese name
        else:
            # This is the content
            if current_theme:
                match = re.search(r"题目编号：\s*([\d,\s]+?)(?=\n\s*\n|\*\*示例题目\*\*|###|$)", section, re.DOTALL)
                if match:
                    nums = [int(n.strip()) for n in match.group(1).replace("\n", " ").split(",") if n.strip().isdigit()]
                    mapping[current_theme] = nums
    
    # 补全 Adaptability（适应）主题的映射
    # 原 association 文件中缺失该主题，基于主题定义和题目内容人工分配
    # 选择最贴合“活在当下、灵活应变、顺其自然”特征的题目
    if "适应" not in mapping:
        mapping["适应"] = [21, 50, 57, 74]
    
    return mapping


def import_holland_questions(db: Session):
    """Create Holland 60 questions in DB."""
    existing = db.query(models.Question).filter(models.Question.assessment_type == "holland").count()
    if existing > 0:
        print(f"Holland questions already imported: {existing}")
        return
    
    scenarios_path = os.path.join(DATA_DIR, "holland_scenarios.json")
    with open(scenarios_path, "r", encoding="utf-8") as f:
        scenarios = json.load(f)
    
    type_texts = {
        "R": "修理或组装机械设备/在户外或车间进行实际操作/使用工具、仪器或运动器材/建造、种植或修理东西/解决具体的技术或机械问题/操作机器或驾驶车辆/进行体育运动或体能活动/从事农业、园艺或养殖工作/安装或维修电器设备/绘制机械图或建筑图".split("/"),
        "I": "阅读科学或学术类文章/做实验、分析数据或研究问题/探索事物背后的原理和规律/使用数学、统计或计算机工具/独立深入思考复杂问题/观察自然现象并寻找解释/撰写研究报告或学术论文/学习新的科学理论或技术/解决逻辑推理或智力谜题/在实验室里进行精确测量".split("/"),
        "A": "绘画、写作、音乐或表演/设计有创意和美感的作品/提出新颖独特的想法/在自由灵活的环境中工作/通过艺术形式表达情感或观点/欣赏电影、戏剧、展览或音乐会/尝试新的创作材料或表现手法/为品牌或产品设计视觉形象/编写故事、剧本或诗歌/参与即兴表演或创意工作坊".split("/"),
        "S": "帮助他人解决问题或成长/教学、培训或辅导他人/倾听他人的困扰并提供支持/组织团队活动或志愿服务/与人深入交流、建立信任关系/照顾病人、儿童或老年人/调解人际冲突、促进和谐/参与社区服务或公益活动/在团体中扮演协调者角色/向他人解释复杂的概念或流程".split("/"),
        "E": "领导团队或项目管理/说服他人接受某个观点或产品/创业、销售或谈判/在竞争中争取胜利和成果/发表演讲、组织活动或影响公众/制定商业计划或营销策略/承担风险以追求更大回报/竞选学生干部或社团负责人/管理预算、资源或供应链/在众人面前自信地表达观点".split("/"),
        "C": "整理数据、制作表格或档案/按照明确流程完成任务/处理账目、文件或审计工作/确保工作准确无误、井井有条/使用办公软件和信息系统处理事务/核对数字、检查细节、发现错误/建立分类系统或数据库/编写规范、手册或操作指南/管理日程、会议或行政事务/按照清单逐项完成重复性工作".split("/"),
    }
    
    qnum = 1
    for htype in ["R", "I", "A", "S", "E", "C"]:
        for text in type_texts[htype]:
            q = models.Question(
                assessment_type="holland",
                question_num=qnum,
                statement_a=text,
                statement_b=None,
                scenario_hint=scenarios[qnum - 1],
                theme_tags=[htype]
            )
            db.add(q)
            qnum += 1
    db.commit()
    print(f"Imported {qnum - 1} Holland questions")


def import_gallup_questions(db: Session):
    md_path = os.path.join(DATA_DIR, "gallup_180_questions_list.md")
    assoc_path = os.path.join(DATA_DIR, "gallup_questions_students_association.md")
    missing_path = os.path.join(DATA_DIR, "gallup_missing_mapping.json")

    questions = parse_gallup_180_questions(md_path)
    mapping = parse_gallup_theme_association(assoc_path)

    # A-side and B-side themes per question
    q_to_a = {q["question_num"]: [] for q in questions}
    q_to_b = {q["question_num"]: [] for q in questions}

    # The association file gives A-side themes
    for theme, nums in mapping.items():
        for n in nums:
            if theme not in q_to_a.get(n, []):
                q_to_a.setdefault(n, []).append(theme)

    # Merge missing-question mapping
    if os.path.exists(missing_path):
        with open(missing_path, "r", encoding="utf-8") as f:
            missing = json.load(f)
        for num_str, sides in missing.items():
            n = int(num_str)
            for t in sides.get("a", []):
                if t not in q_to_a.get(n, []):
                    q_to_a.setdefault(n, []).append(t)
            for t in sides.get("b", []):
                if t not in q_to_b.get(n, []):
                    q_to_b.setdefault(n, []).append(t)

    existing = db.query(models.Question).filter(models.Question.assessment_type == "gallup").count()
    if existing > 0:
        print(f"Gallup questions already imported: {existing}")
        return

    for q in questions:
        db_q = models.Question(
            assessment_type="gallup",
            question_num=q["question_num"],
            statement_a=q["statement_a"],
            statement_b=q["statement_b"],
            scenario_hint=q["scenario_hint"],
            theme_tags=q_to_a.get(q["question_num"], []),
            b_side_themes=q_to_b.get(q["question_num"], [])
        )
        db.add(db_q)
    db.commit()
    print(f"Imported {len(questions)} Gallup questions")


def import_career_mapping(db: Session):
    path = os.path.join(DATA_DIR, "career_major_mapping.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    existing = db.query(models.CareerMajorMapping).count()
    if existing > 0:
        print(f"Career mapping already imported: {existing}")
        return
    
    for item in data:
        cm = models.CareerMajorMapping(
            career_name=item["career_name"],
            riasec_primary=item["riasec_primary"],
            cs_domain=item["cs_domain"],
            related_majors=item.get("related_majors", []),
            evidence_level=item.get("evidence_level"),
            description=item.get("description"),
            career_tag=item.get("career_tag")
        )
        db.add(cm)
    db.commit()
    print(f"Imported {len(data)} career-major mappings")


def import_theme_descriptions(db: Session):
    path = os.path.join(DATA_DIR, "cliftonstrengths_report_materials.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    existing = db.query(models.ThemeDescription).count()
    if existing > 0:
        print(f"Theme descriptions already imported: {existing}")
        return
    
    from app.services.gallup import THEME_EN
    
    for theme_name, item in data.items():
        td = models.ThemeDescription(
            theme_name=theme_name,
            theme_name_en=THEME_EN.get(theme_name, item.get("name_en", "")),
            domain=item.get("domain", ""),
            standard_definition=item.get("standard_definition", ""),
            feature=item.get("feature", ""),
            description=item.get("description", ""),
            application=item.get("application", ""),
            blind_spots=item.get("blind_spots", "")
        )
        db.add(td)
    db.commit()
    print(f"Imported {len(data)} theme descriptions")


def create_default_users(db: Session):
    from app.auth import get_password_hash
    
    # Create teacher if not exists
    teacher = db.query(models.User).filter(models.User.username == "teacher").first()
    if not teacher:
        teacher = models.User(
            username="teacher",
            display_name="演示老师",
            role=models.UserRole.teacher,
            password_hash=get_password_hash("teacher123")
        )
        db.add(teacher)
        print("Created default teacher: teacher / teacher123")
    
    # Create demo student
    student = db.query(models.User).filter(models.User.username == "student").first()
    if not student:
        student = models.User(
            username="student",
            display_name="演示学生",
            role=models.UserRole.student,
            password_hash=get_password_hash("student123")
        )
        db.add(student)
        print("Created default student: student / student123")
    
    db.commit()


def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        print(f"Using data directory: {DATA_DIR}")
        import_holland_questions(db)
        import_gallup_questions(db)
        import_career_mapping(db)
        import_theme_descriptions(db)
        create_default_users(db)
        print("Data import completed.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
