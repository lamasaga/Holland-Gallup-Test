import sys
sys.path.insert(0, "/Users/pengpeng/Desktop/KIMI/测评研究/06-website/assessment-platform/backend")

from app.services.report import _build_student_html

html = _build_student_html(
    student_name="测试学生 / Test Student",
    holland_code="IAS",
    holland_scores={"R": 12, "I": 28, "A": 32, "S": 25, "E": 15, "C": 10},
    gallup_domain="战略思维",
    gallup_secondary_domain="执行力",
    gallup_top5=["理念", "战略", "学习", "成就", "专注"],
    careers=[
        {
            "career_name": "产品设计师",
            "evidence_level": "B",
            "description": "结合创造力与用户体验思维",
            "tags": ["创意", "设计"],
            "related_majors": ["工业设计", "交互设计"],
        }
    ],
    actions=["尝试一次设计思维工作坊", "采访一位产品经理", "整理自己的作品集"],
    data_quality_notes=["Holland 测评完成率 100%", "Gallup 测评完成率 100%"],
    tension="低 / Low",
)

output_path = "/Users/pengpeng/Desktop/KIMI/测评研究/06-website/assessment-platform/backend/test_student_report_visuals.html"
with open(output_path, "w", encoding="utf-8") as f:
    f.write(html)

print(f"Report saved to: {output_path}")
