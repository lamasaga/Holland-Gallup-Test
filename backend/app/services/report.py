import json
import os
from typing import List, Dict, Any, Optional
from sqlalchemy import case
from sqlalchemy.orm import Session
from app import models
from app.services.holland import get_type_description


# ---------------------------------------------------------------------------
# 常量 / Constants
# ---------------------------------------------------------------------------

DOMAIN_ZH_TO_EN = {
    "执行力": "Executing",
    "影响力": "Influencing",
    "关系建立": "Relationship Building",
    "战略思维": "Strategic Thinking",
}

DOMAIN_EN_TO_ZH = {v: k for k, v in DOMAIN_ZH_TO_EN.items()}

RIASEC_STAGE_TAGS = {
    "R": ("实践行动派", "Hands-On Doer"),
    "I": ("探索思考派", "Curious Investigator"),
    "A": ("创意表达派", "Creative Expresser"),
    "S": ("人际关怀派", "People Helper"),
    "E": ("领导影响派", "Impact Driver"),
    "C": ("秩序组织派", "Order Organizer"),
}

STRENGTH_STYLE = {
    "Executing": ("实干完成型", "Efficient Executor"),
    "Influencing": ("推动影响型", "Influential Mobilizer"),
    "Relationship Building": ("关系连接型", "Relationship Builder"),
    "Strategic Thinking": ("战略思考型", "Strategic Thinker"),
}

RIASEC_MEANING = {
    "R": ("喜欢使用工具、机器或体力技能解决实际问题，重视具体成果。", "You enjoy working with tools, machines, or physical skills to solve practical problems."),
    "I": ("喜欢观察、学习、研究、分析、评估和解决问题，重视独立思考和知识探索。", "You enjoy observing, learning, researching, analyzing, evaluating, and solving problems."),
    "A": ("喜欢艺术、设计、音乐、写作或表演，重视自我表达、创造力和审美体验。", "You enjoy art, design, music, writing, or performance, and value self-expression and creativity."),
    "S": ("喜欢与人互动、帮助他人、教导或治疗，重视人际关系与社会贡献。", "You enjoy interacting with, helping, teaching, or treating people, and value social contribution."),
    "E": ("喜欢领导、说服、组织资源以实现目标，重视影响力与商业成就。", "You enjoy leading, persuading, and organizing resources to achieve goals, and value influence and achievement."),
    "C": ("喜欢处理数据、文件、细节和规范化流程，重视准确性、条理性和稳定性。", "You prefer working with data, documents, details, and standardized processes."),
}


# ---------------------------------------------------------------------------
# 数据质量与个性化内容 / Data quality & personalization
# ---------------------------------------------------------------------------

def _build_data_quality_notes(
    holland_quality: Dict[str, Any] = None,
    gallup_coverage: Dict[str, Any] = None,
    gallup_quality: Dict[str, Any] = None,
) -> List[str]:
    """根据 Holland 区分度、Gallup 映射覆盖率与作答响应质量生成数据质量提示。"""
    notes = []

    # Holland 响应质量
    if holland_quality:
        if holland_quality.get("is_flat"):
            notes.append(
                "你的 Holland 得分区分度较低（各类型分数接近），三码可能不能清晰代表你的兴趣偏好，建议结合日常经历进一步验证。/ "
                "Your Holland scores show low differentiation (types are close together), so the three-letter code may not clearly represent your interests. Validate against your daily experiences."
            )
        rq = holland_quality.get("response_quality") or {}
        if rq.get("risk_level") in ("medium", "high") and rq.get("message_zh"):
            notes.append(f"{rq['message_zh']} / {rq.get('message_en', '')}".strip())

    # Gallup 响应质量
    if gallup_quality:
        rq = gallup_quality.get("response_quality") or {}
        if rq.get("risk_level") in ("medium", "high") and rq.get("message_zh"):
            notes.append(f"{rq['message_zh']} / {rq.get('message_en', '')}".strip())

    if gallup_coverage:
        b_ratio = gallup_coverage.get("b_side_ratio", 0)
        dual_ratio = gallup_coverage.get("dual_side_ratio", 0)
        themes_scored = gallup_coverage.get("themes_scored", 0)
        if b_ratio < 0.5:
            notes.append(
                f"当前 Gallup 模拟量表的 B 侧主题映射覆盖率为 {b_ratio*100:.1f}%，B 侧陈述对才干计分的贡献有限，优势结果主要反映 A 侧偏好，请谨慎解读。/ "
                f"The Gallup simulation B-side theme mapping coverage is {b_ratio*100:.1f}%, so B-side statements contribute little to theme scoring. Strengths results mainly reflect A-side preferences; interpret cautiously."
            )
        elif b_ratio < 0.9:
            notes.append(
                f"当前 Gallup 模拟量表的 A/B 侧映射基本可用（B 侧覆盖率 {b_ratio*100:.1f}%，双侧同时计分 {dual_ratio*100:.1f}%），但仍为启发式映射，非官方 CliftonStrengths 算法。/ "
                f"Gallup simulation mapping is mostly usable (B-side {b_ratio*100:.1f}%, dual-side {dual_ratio*100:.1f}%), but remains heuristic—not the official CliftonStrengths algorithm."
            )
        else:
            notes.append(
                f"Gallup 模拟量表 A/B 双侧映射已完整（双侧计分题 {dual_ratio*100:.1f}%，{themes_scored}/34 个主题参与计分）。结果为探索性参考，非官方 CliftonStrengths 报告。/ "
                f"Gallup simulation has full A/B mapping (dual-side {dual_ratio*100:.1f}%, {themes_scored}/34 themes scored). Results are for exploration—not an official CliftonStrengths report."
            )

    if not notes:
        notes.append(
            "当前数据质量良好，可作为探索参考。/ "
            "Data quality is good; use this as an exploration reference."
        )

    return notes


def _build_personalized_actions(holland_code: str, gallup_domain: str) -> List[str]:
    """根据 Holland 首码与 Gallup 领域生成个性化的下一步行动。"""
    if not holland_code:
        return [
            "了解一个稳妥入口职业：搜索该岗位的真实工作内容和薪资范围。/ Explore one safe-entry role and its typical daily work.",
            "选择一个核心专业：查看 2-3 所目标院校的相关专业课程设置。/ Look up 2-3 target institutions' programmes for one core major.",
            "做一次职业访谈：找一位从业者聊 30 分钟，了解ta的真实一天。/ Conduct a 30-minute informational interview with someone in that field.",
        ]

    first = holland_code[0].upper()
    domain_zh = gallup_domain or ""

    action_map = {
        "R": [
            "找一个动手项目体验：例如维修、组装、实验或户外实践，观察自己是否乐在其中。/ Find a hands-on project (repair, assembly, experiment, or outdoor activity) to see if you enjoy it.",
            "调研一个技术类专业：查看该专业的实验/实习比例和就业去向。/ Research a technical major, focusing on lab/practice ratios and graduate destinations.",
            "访谈一位工程师/技师：了解他们典型的一天和核心技能。/ Interview an engineer or technician about their typical day and core skills.",
        ],
        "I": [
            "精读一篇你感兴趣领域的学术论文或深度报道，记录你最有好奇心的 3 个问题。/ Read an academic paper or in-depth article in an area of interest and note 3 questions it raises.",
            "了解一个研究型专业：关注它的课程设置、实验室资源和升学路径。/ Explore a research-oriented major, focusing on curriculum, lab resources, and graduate paths.",
            "约一位研究员或分析师做职业访谈：询问他们如何保持深度学习。/ Interview a researcher or analyst about how they maintain deep learning.",
        ],
        "A": [
            "完成一个小型创作作品：写作、绘画、设计或视频，并收集反馈。/ Create a small piece (writing, drawing, design, or video) and gather feedback.",
            "调研一个创意类专业：对比国内外院校的课程差异和作品集要求。/ Research a creative major, comparing curricula and portfolio requirements across institutions.",
            "访谈一位创意从业者：了解自由职业与稳定岗位之间的取舍。/ Interview a creative professional about the trade-offs between freelance and stable roles.",
        ],
        "S": [
            "参加一次志愿或辅导活动：观察自己在帮助他人时的能量变化。/ Take part in a volunteer or tutoring activity and observe your energy level.",
            "了解一个社会服务类专业：如教育、心理、社会工作、护理等。/ Explore a social-service major such as education, psychology, social work, or nursing.",
            "访谈一位教师/社工/咨询师：了解职业倦怠与成就感的来源。/ Interview a teacher, social worker, or counselor about burnout and sources of fulfillment.",
        ],
        "E": [
            "组织一次小型活动或项目：体验策划、说服与协调的过程。/ Organize a small event or project to experience planning, persuasion, and coordination.",
            "调研一个商科或管理类专业：关注实习、案例竞赛和校友网络。/ Research a business or management major, focusing on internships, case competitions, and alumni networks.",
            "访谈一位创业者或销售管理者：了解他们如何面对拒绝与竞争。/ Interview an entrepreneur or sales manager about handling rejection and competition.",
        ],
        "C": [
            "整理一个复杂数据集或档案：体验分类、核对与流程化的工作。/ Organize a complex dataset or archive to experience categorization, verification, and process work.",
            "了解一个数据处理或行政管理类专业：如会计、审计、信息系统等。/ Explore a data-processing or administrative major such as accounting, auditing, or information systems.",
            "访谈一位财务/行政/质量管理人员：了解他们对准确性和细节的要求。/ Interview a finance, administration, or quality manager about their demands for accuracy and detail.",
        ],
    }

    base_actions = action_map.get(first, action_map["R"])

    # Add a Gallup-domain specific action if domain is present
    if domain_zh:
        domain_action_map = {
            "执行力": "设定一个小目标并记录完成过程，观察你的执行节奏。/ Set a small goal and track your completion process to observe your execution rhythm.",
            "影响力": "准备一次 3 分钟的观点分享，练习清晰表达与说服。/ Prepare a 3-minute point of view sharing to practice clear expression and persuasion.",
            "关系建立": "主动与一位新朋友或久未联系的朋友深聊 30 分钟。/ Have a 30-minute deep conversation with a new or old friend.",
            "战略思维": "针对一个你关心的话题，写一份 500 字的未来趋势分析。/ Write a 500-word future-trend analysis on a topic you care about.",
        }
        domain_action = domain_action_map.get(domain_zh)
        if domain_action:
            return [base_actions[0], base_actions[1], domain_action]

    return base_actions


# ---------------------------------------------------------------------------
# 入口函数 / Entry functions
# ---------------------------------------------------------------------------

def get_student_name(db: Session, user_id: str) -> str:
    user = db.query(models.User).filter(models.User.id == user_id).first()
    return user.display_name or user.username if user else "未知"


def generate_student_report(db: Session, user_id: str) -> Dict[str, Any]:
    assessment = db.query(models.AssessmentStatus).filter(
        models.AssessmentStatus.user_id == user_id
    ).first()
    if not assessment:
        raise ValueError("Assessment not found")

    student_name = get_student_name(db, user_id)
    holland_code = assessment.holland_code or ""
    holland_scores = assessment.holland_scores or {}
    gallup_top5 = assessment.gallup_top5 or []
    gallup_domain = assessment.gallup_domain or ""
    gallup_secondary_domain = assessment.gallup_secondary_domain or ""
    status = assessment.status or {}
    gallup_coverage = status.get("gallup_coverage")
    holland_quality = status.get("holland_quality")

    # Career recommendations (student version: 3-5 directions)
    careers = get_career_recommendations(db, holland_code, gallup_domain, limit=5)

    # Data quality notes
    data_quality_notes = _build_data_quality_notes(holland_quality, gallup_coverage, status.get("gallup_quality"))

    # Tension & personalized actions
    tension = analyze_tension(holland_code, gallup_domain)
    actions = _build_personalized_actions(holland_code, gallup_domain)

    report_html = _build_student_html(
        student_name=student_name,
        holland_code=holland_code,
        holland_scores=holland_scores,
        gallup_domain=gallup_domain,
        gallup_secondary_domain=gallup_secondary_domain,
        gallup_top5=gallup_top5,
        careers=careers,
        actions=actions,
        data_quality_notes=data_quality_notes,
        tension=tension,
    )

    return {
        "student_name": student_name,
        "holland_code": holland_code,
        "holland_scores": holland_scores,
        "gallup_top5": gallup_top5,
        "gallup_domain": gallup_domain,
        "gallup_secondary_domain": gallup_secondary_domain,
        "careers": careers,
        "actions": actions,
        "tension": tension,
        "report_html": report_html,
        "data_quality_notes": data_quality_notes,
        "gallup_coverage": gallup_coverage,
        "holland_quality": holland_quality,
        "gallup_quality": status.get("gallup_quality"),
    }


def generate_professional_report(db: Session, user_id: str) -> Dict[str, Any]:
    assessment = db.query(models.AssessmentStatus).filter(
        models.AssessmentStatus.user_id == user_id
    ).first()
    if not assessment:
        raise ValueError("Assessment not found")

    student_name = get_student_name(db, user_id)
    holland_scores = assessment.holland_scores or {}
    holland_code = assessment.holland_code or ""
    gallup_top5 = assessment.gallup_top5 or []
    gallup_top10 = assessment.gallup_top10 or []
    gallup_domain = assessment.gallup_domain or ""
    gallup_secondary_domain = assessment.gallup_secondary_domain or ""
    gallup_scores = assessment.gallup_scores or {}

    # Build details for Top 10 themes (Top 5 will get detailed narrative, 6-10 concise list)
    top10_details = []
    for theme in gallup_top10:
        desc = db.query(models.ThemeDescription).filter(
            models.ThemeDescription.theme_name == theme
        ).first()
        top10_details.append({
            "theme": theme,
            "theme_en": desc.theme_name_en if desc else "",
            "domain": desc.domain if desc else "",
            "definition_zh": desc.standard_definition_zh if desc else "",
            "definition_en": desc.standard_definition_en if desc else "",
            "feature_zh": desc.feature_zh if desc else "",
            "feature_en": desc.feature_en if desc else "",
            "description_zh": desc.description_zh if desc else "",
            "description_en": desc.description_en if desc else "",
            "application_zh": desc.application_zh if desc else "",
            "application_en": desc.application_en if desc else "",
            "blind_spots_zh": desc.blind_spots_zh if desc else "",
            "blind_spots_en": desc.blind_spots_en if desc else "",
        })

    # Domain distribution from top10 for consistency with "Top 10 weighted by rank" narrative
    domain_distribution = {}
    for d in top10_details:
        domain_distribution[d["domain"]] = domain_distribution.get(d["domain"], 0) + 1

    # Tension
    tension = analyze_tension(holland_code, gallup_domain)

    careers = get_career_recommendations(db, holland_code, gallup_domain)

    status = assessment.status or {}
    gallup_coverage = status.get("gallup_coverage")
    holland_quality = status.get("holland_quality")
    data_quality_notes = _build_data_quality_notes(holland_quality, gallup_coverage, status.get("gallup_quality"))

    report_html = _build_professional_html(
        db=db,
        student_name=student_name,
        holland_code=holland_code,
        holland_scores=holland_scores,
        gallup_domain=gallup_domain,
        gallup_secondary_domain=gallup_secondary_domain,
        domain_distribution=domain_distribution,
        top10_details=top10_details,
        gallup_top10=gallup_top10,
        tension=tension,
        careers=careers,
        data_quality_notes=data_quality_notes,
    )

    return {
        "student_name": student_name,
        "holland_scores": holland_scores,
        "holland_code": holland_code,
        "gallup_top5": top10_details[:5],
        "gallup_top10": gallup_top10,
        "gallup_domain": gallup_domain,
        "gallup_secondary_domain": gallup_secondary_domain,
        "domain_distribution": domain_distribution,
        "tension": tension,
        "careers": careers,
        "evidence_note": "本报告基于 Holland RIASEC 与 Gallup CliftonStrengths 的整合框架生成，职业-专业映射为理论参考，不可用于高利害决策。/ This report is generated from an integrated Holland RIASEC and Gallup CliftonStrengths framework. Career-major mappings are for reference only and should not be used for high-stakes decisions.",
        "report_html": report_html,
        "data_quality_notes": data_quality_notes,
        "gallup_coverage": gallup_coverage,
        "holland_quality": holland_quality,
        "gallup_quality": status.get("gallup_quality"),
    }


# ---------------------------------------------------------------------------
# HTML 生成器 / HTML builders
# ---------------------------------------------------------------------------

def _escape_html(text: str) -> str:
    if text is None:
        return ""
    return (str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))


def _css() -> str:
    """返回报告专用样式，类名以 .kz-report 为前缀避免污染页面。"""
    return """
<style>
.kz-report { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; color: #1f2937; line-height: 1.7; max-width: 960px; margin: 0 auto; }
.kz-report h1 { font-size: 28px; font-weight: 700; color: #111827; margin: 0 0 12px 0; }
.kz-report h2 { font-size: 22px; font-weight: 700; color: #1e40af; margin: 32px 0 14px 0; padding-bottom: 8px; border-bottom: 2px solid #dbeafe; }
.kz-report h3 { font-size: 18px; font-weight: 700; color: #1f2937; margin: 24px 0 10px 0; }
.kz-report h4 { font-size: 16px; font-weight: 700; color: #374151; margin: 18px 0 8px 0; }
.kz-report p { margin: 8px 0; }
.kz-report .kz-meta { background: #f8fafc; border-left: 4px solid #2563eb; padding: 14px 18px; margin: 16px 0; border-radius: 6px; }
.kz-report .kz-meta p { margin: 4px 0; }
.kz-report .kz-card { background: #ffffff; border: 1px solid #e5e7eb; border-radius: 10px; padding: 20px 24px; margin: 16px 0; box-shadow: 0 1px 2px rgba(0,0,0,0.04); }
.kz-report .kz-highlight { background: #eff6ff; border-left: 4px solid #3b82f6; padding: 14px 18px; border-radius: 6px; margin: 14px 0; }
.kz-report .kz-tip { background: #f0fdf4; border-left: 4px solid #22c55e; padding: 12px 16px; border-radius: 6px; margin: 14px 0; color: #166534; }
.kz-report .kz-warning { background: #fffbeb; border-left: 4px solid #f59e0b; padding: 12px 16px; border-radius: 6px; margin: 14px 0; color: #92400e; }
.kz-report .kz-info { background: #eff6ff; border-left: 4px solid #3b82f6; padding: 12px 16px; border-radius: 6px; margin: 14px 0; color: #1e40af; }
.kz-report table { width: 100%; border-collapse: collapse; margin: 14px 0; font-size: 14px; }
.kz-report th, .kz-report td { border: 1px solid #e5e7eb; padding: 10px 12px; text-align: left; vertical-align: top; }
.kz-report th { background: #f3f4f6; font-weight: 600; color: #374151; }
.kz-report tr:nth-child(even) { background: #f9fafb; }
.kz-report .kz-tag { display: inline-block; padding: 3px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; margin-left: 6px; }
.kz-report .kz-tag-steady { background: #d1fae5; color: #065f46; }
.kz-report .kz-tag-explore { background: #fef3c7; color: #92400e; }
.kz-report .kz-tag-challenge { background: #fee2e2; color: #991b1b; }
.kz-report .kz-matrix-dominant { background: #dbeafe; border: 3px solid #1d4ed8 !important; font-weight: 700; box-shadow: inset 0 0 0 1px #93c5fd; }
.kz-report .kz-matrix-secondary { background: #fffbeb; border: 2px dashed #d97706 !important; }
.kz-report .kz-matrix-tertiary { background: #f5f3ff; border: 2px dotted #7c3aed !important; }
.kz-report .kz-matrix-header { background: #1e40af; color: #fff; font-weight: 600; }
.kz-report .kz-matrix-badge { display: inline-block; font-size: 11px; font-weight: 700; padding: 3px 8px; border-radius: 4px; margin-bottom: 6px; line-height: 1.3; }
.kz-report .kz-matrix-badge-dominant { background: #1d4ed8; color: #fff; }
.kz-report .kz-matrix-badge-secondary { background: #d97706; color: #fff; }
.kz-report .kz-matrix-badge-tertiary { background: #7c3aed; color: #fff; }
.kz-report .kz-matrix-legend { display: flex; flex-wrap: wrap; gap: 12px; margin: 16px 0; }
.kz-report .kz-matrix-legend-item { flex: 1; min-width: 200px; padding: 12px 14px; border-radius: 8px; font-size: 13px; line-height: 1.5; }
.kz-report .kz-matrix-legend-dominant { border: 3px solid #1d4ed8; background: #eff6ff; }
.kz-report .kz-matrix-legend-secondary { border: 2px dashed #d97706; background: #fffbeb; }
.kz-report .kz-matrix-legend-tertiary { border: 2px dotted #7c3aed; background: #f5f3ff; }
.kz-report .kz-matrix-legend-item strong { display: block; margin-bottom: 4px; font-size: 14px; }
.kz-report .kz-matrix-domain-title { font-weight: 700; font-size: 13px; line-height: 1.4; }
.kz-report .kz-matrix-table td { font-size: 12px; line-height: 1.35; padding: 8px 10px; }
.kz-report .kz-matrix-table th { font-size: 12px; padding: 8px 10px; }
.kz-report .kz-intersection-detail { margin-top: 28px; }
.kz-report .kz-intersection-detail > h3 { font-size: 18px; color: #1e40af; margin: 0 0 8px 0; padding-bottom: 8px; border-bottom: 2px solid #dbeafe; }
.kz-report .kz-intersection-intro { color: #4b5563; font-size: 14px; line-height: 1.65; margin: 0 0 20px 0; }
.kz-report .kz-intersection-tier { margin-bottom: 24px; }
.kz-report .kz-intersection-tier-header { display: flex; align-items: flex-start; gap: 14px; margin-bottom: 14px; padding: 14px 16px; border-radius: 10px; }
.kz-report .kz-intersection-tier-primary .kz-intersection-tier-header { background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%); border: 1px solid #93c5fd; }
.kz-report .kz-intersection-tier-secondary .kz-intersection-tier-header { background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%); border: 1px solid #fcd34d; }
.kz-report .kz-intersection-tier-tertiary .kz-intersection-tier-header { background: linear-gradient(135deg, #f5f3ff 0%, #ede9fe 100%); border: 1px solid #c4b5fd; }
.kz-report .kz-intersection-tier-badge { flex-shrink: 0; display: inline-block; padding: 6px 14px; border-radius: 20px; font-size: 13px; font-weight: 700; color: #fff; }
.kz-report .kz-intersection-tier-primary .kz-intersection-tier-badge { background: #1d4ed8; }
.kz-report .kz-intersection-tier-secondary .kz-intersection-tier-badge { background: #d97706; }
.kz-report .kz-intersection-tier-tertiary .kz-intersection-tier-badge { background: #7c3aed; }
.kz-report .kz-intersection-tier-desc { margin: 0; font-size: 14px; line-height: 1.65; color: #374151; }
.kz-report .kz-intersection-cards { display: grid; gap: 14px; }
.kz-report .kz-intersection-card { background: #fff; border: 1px solid #e5e7eb; border-radius: 12px; padding: 18px 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
.kz-report .kz-intersection-tier-primary .kz-intersection-card { border-left: 4px solid #1d4ed8; }
.kz-report .kz-intersection-tier-secondary .kz-intersection-card { border-left: 4px solid #d97706; }
.kz-report .kz-intersection-tier-tertiary .kz-intersection-card { border-left: 4px solid #7c3aed; }
.kz-report .kz-intersection-card-title { font-size: 16px; font-weight: 700; color: #111827; margin: 0 0 6px 0; }
.kz-report .kz-intersection-card-tagline { font-size: 14px; color: #1e40af; font-style: italic; margin: 0 0 12px 0; line-height: 1.5; }
.kz-report .kz-intersection-card-body { font-size: 14px; line-height: 1.7; color: #374151; margin: 0 0 14px 0; }
.kz-report .kz-intersection-meta { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; margin-top: 12px; padding-top: 12px; border-top: 1px dashed #e5e7eb; }
.kz-report .kz-intersection-meta-item { font-size: 12px; line-height: 1.5; }
.kz-report .kz-intersection-meta-item strong { display: block; font-size: 11px; text-transform: uppercase; letter-spacing: 0.03em; color: #6b7280; margin-bottom: 3px; font-weight: 600; }
.kz-report .kz-intersection-prompt { margin-top: 12px; padding: 10px 14px; background: #f0fdf4; border-radius: 8px; font-size: 13px; color: #166534; line-height: 1.55; }
.kz-report .kz-ethics { background: #f0f9ff; border: 1px solid #bae6fd; border-left: 4px solid #0284c7; padding: 14px 18px; border-radius: 8px; margin: 16px 0; color: #0c4a6e; }
.kz-report .kz-synthesis { background: linear-gradient(135deg, #eff6ff 0%, #f0fdf4 100%); border: 1px solid #bfdbfe; border-radius: 10px; padding: 20px 24px; margin: 20px 0; }
.kz-report .kz-synthesis h3 { margin-top: 0; color: #1e40af; }
.kz-report .kz-synthesis-advice { background: #fff; border-radius: 8px; padding: 14px 18px; margin: 12px 0; border-left: 4px solid #22c55e; }
.kz-report .kz-small { color: #6b7280; font-size: 13px; }
.kz-report .kz-en { color: #6b7280; font-style: italic; }
.kz-report ul.kz-list { padding-left: 22px; }
.kz-report ul.kz-list li { margin: 8px 0; }
.kz-report .kz-answer-line { display: inline-block; min-width: 160px; border-bottom: 1px solid #9ca3af; }
.kz-report .kz-stage-badge { display: inline-block; padding: 2px 10px; border-radius: 12px; background: #ede9fe; color: #5b21b6; font-size: 13px; font-weight: 600; }
.kz-report .kz-print-header { display: flex; justify-content: space-between; align-items: center; gap: 16px; }
.kz-report .kz-print-btn { background: #2563eb; color: #fff; padding: 8px 16px; border-radius: 6px; font-size: 14px; cursor: pointer; border: none; }
.kz-report .kz-print-btn:hover { background: #1d4ed8; }

/* 学生版报告可视化 / Student report visuals */
.kz-report .kz-type-card { background: #fff; border-radius: 12px; padding: 24px 28px; margin: 20px 0; box-shadow: 0 4px 12px rgba(0,0,0,0.06); text-align: center; }
.kz-report .kz-type-badges { display: flex; justify-content: center; align-items: center; gap: 14px; margin-bottom: 14px; flex-wrap: wrap; }
.kz-report .kz-type-badge { display: inline-flex; align-items: center; justify-content: center; min-width: 80px; padding: 10px 20px; border-radius: 10px; color: #fff; font-size: 22px; font-weight: 800; letter-spacing: 1px; box-shadow: 0 2px 6px rgba(0,0,0,0.12); }
.kz-report .kz-type-plus { font-size: 24px; font-weight: 700; color: #9ca3af; }
.kz-report .kz-type-summary { font-size: 16px; color: #374151; line-height: 1.6; }
.kz-report .kz-type-summary .kz-en { font-size: 14px; }
.kz-report .kz-chart-card { background: #fff; border: 1px solid #e5e7eb; border-radius: 10px; padding: 18px 22px; margin: 16px 0; box-shadow: 0 1px 2px rgba(0,0,0,0.04); }
.kz-report .kz-chart-title { font-size: 15px; font-weight: 700; color: #1f2937; margin: 0 0 14px 0; }
.kz-report .kz-chart-subtitle { font-size: 13px; color: #6b7280; margin: -10px 0 14px 0; }
.kz-report .kz-domain-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 10px 0; }
.kz-report .kz-domain-block { border-radius: 10px; padding: 16px 10px; text-align: center; position: relative; min-height: 90px; display: flex; flex-direction: column; justify-content: center; }
.kz-report .kz-domain-name { font-size: 15px; font-weight: 700; color: #1f2937; }
.kz-report .kz-domain-en { font-size: 11px; color: #6b7280; margin-top: 4px; }
.kz-report .kz-domain-badge { position: absolute; top: 8px; right: 8px; font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 10px; }
.kz-report .kz-domain-primary { background: #1f2937; color: #fff; }
.kz-report .kz-domain-secondary { background: #fff; color: #1f2937; border: 1px solid #1f2937; }
.kz-report .kz-top5-pills { display: flex; flex-wrap: wrap; gap: 10px; margin: 12px 0; }
.kz-report .kz-top5-pill { display: inline-flex; align-items: center; gap: 6px; padding: 7px 14px; border-radius: 20px; font-size: 14px; font-weight: 600; }
.kz-report .kz-top5-rank { display: inline-flex; align-items: center; justify-content: center; width: 18px; height: 18px; border-radius: 50%; background: rgba(255,255,255,0.85); font-size: 11px; font-weight: 700; }
.kz-report .kz-illustration-row { display: flex; flex-wrap: wrap; gap: 16px; margin: 16px 0; }
.kz-report .kz-illustration-card { flex: 1; min-width: 140px; max-width: 220px; background: #fff; border: 1px solid #e5e7eb; border-radius: 12px; padding: 16px; text-align: center; box-shadow: 0 1px 2px rgba(0,0,0,0.04); }
.kz-report .kz-illustration-card svg { width: 100%; height: auto; display: block; }
.kz-report .kz-illustration-label { font-size: 13px; font-weight: 600; color: #374151; margin-top: 10px; }
.kz-report .kz-illustration-en { font-size: 11px; color: #6b7280; font-style: italic; }
.kz-report .kz-hero-illustration { background: linear-gradient(135deg, #f8fafc 0%, #eff6ff 100%); border: 1px solid #dbeafe; border-radius: 12px; padding: 20px; margin: 16px 0; display: flex; flex-wrap: wrap; align-items: center; gap: 20px; }
.kz-report .kz-hero-illustration svg { width: 160px; height: 120px; flex-shrink: 0; }
.kz-report .kz-hero-text { flex: 1; min-width: 200px; }
.kz-report .kz-hero-text p { margin: 6px 0; }
@media (max-width: 640px) {
  .kz-report { max-width: 100%; padding: 0 8px; overflow-x: auto; }
  .kz-report h1 { font-size: 22px; }
  .kz-report h2 { font-size: 18px; }
  .kz-report h3 { font-size: 16px; }
  .kz-report h4 { font-size: 14px; }
  .kz-report p, .kz-report li, .kz-report td, .kz-report th { font-size: 13px; }
  .kz-report .kz-meta, .kz-report .kz-card, .kz-report .kz-highlight, .kz-report .kz-tip, .kz-report .kz-warning { padding: 12px 14px; }
  .kz-report table { font-size: 12px; }
  .kz-report th, .kz-report td { padding: 8px 10px; }
  .kz-report .kz-matrix-table { min-width: 560px; }
  .kz-report .kz-domain-grid { grid-template-columns: repeat(2, 1fr); }
  .kz-report .kz-type-badge { font-size: 18px; padding: 8px 14px; }
  .kz-report .kz-hero-illustration { flex-direction: column; text-align: center; }
  .kz-report .kz-hero-illustration svg { width: 140px; height: 105px; }
  .kz-report .kz-illustration-row { flex-direction: column; align-items: center; }
  .kz-report .kz-illustration-card { max-width: 100%; width: 100%; }
  .kz-report .kz-top5-pill { font-size: 13px; padding: 6px 12px; }
  .kz-report .kz-type-card { padding: 18px 20px; }
  .kz-report .kz-print-header { flex-direction: column; align-items: flex-start; gap: 10px; }
  .kz-report .kz-print-btn { align-self: flex-start; }
}
.kz-report { counter-reset: kz-section; }
.kz-report h2.kz-section { counter-increment: kz-section; counter-reset: kz-subsection; }
.kz-report h2.kz-section::before { content: counter(kz-section, simp-chinese-informal) "、"; font-weight: 700; color: inherit; }
.kz-report h3.kz-subsection { counter-increment: kz-subsection; }
.kz-report h3.kz-subsection::before { content: counter(kz-section) "." counter(kz-subsection) " "; font-weight: 700; color: inherit; }
.kz-report .kz-screen-only { }
@media print {
  .kz-report .kz-print-btn { display: none; }
  .kz-report { max-width: 100%; }
  .kz-report h2 { page-break-after: avoid; }
  .kz-report table { page-break-inside: avoid; }
  .kz-report .kz-card, .kz-report .kz-highlight, .kz-report .kz-tip, .kz-report .kz-warning, .kz-report .kz-type-card, .kz-report .kz-chart-card, .kz-report .kz-domain-block, .kz-report .kz-illustration-card, .kz-report .kz-hero-illustration { page-break-inside: avoid; }
  .kz-report .kz-screen-only { display: none !important; }
  .kz-report .kz-screen-only h2.kz-section { counter-increment: none; counter-reset: none; }
}
</style>
"""


def _stage_tag(letter: str) -> str:
    zh, en = RIASEC_STAGE_TAGS.get(letter, ("", ""))
    return f"{zh} / {en}" if zh else ""


def _strength_style(domain_en: str) -> str:
    zh, en = STRENGTH_STYLE.get(domain_en, ("", ""))
    return f"{zh} / {en}" if zh else domain_en


def _domain_en(domain_zh: str) -> str:
    return DOMAIN_ZH_TO_EN.get(domain_zh, domain_zh)


def _type_name(letter: str) -> str:
    desc = get_type_description(letter)
    if desc:
        return f"{desc['name']}（{desc['en']}）"
    return letter


def _type_name_en(letter: str) -> str:
    desc = get_type_description(letter)
    return desc.get("en", letter) if desc else letter


def _safe_entry_points(careers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """选取 evidence_level 为 C 或以上、描述较具体的稳妥入口职业（最多 2 个）。"""
    candidates = []
    for c in careers:
        ev = c.get("evidence_level") or "D"
        if ev in ("A", "B", "C"):
            desc = c.get("description") or ""
            # 描述长度作为“具体”的启发式指标
            candidates.append((len(desc), c))
    candidates.sort(key=lambda x: -x[0])
    return [c for _, c in candidates[:2]]


def _career_tag(career: Dict[str, Any]) -> tuple:
    """返回（标签中文，标签英文，CSS 类）。
    优先使用职业映射数据中的人工标注 career_tag；缺失时回退到关键词启发式。"""
    explicit_tag = career.get("career_tag")
    if explicit_tag == "steady":
        return "稳就业型", "Steady Employment", "kz-tag-steady"
    if explicit_tag == "explore":
        return "探索型", "Explore-oriented", "kz-tag-explore"
    if explicit_tag == "challenge":
        return "高挑战型", "High Challenge", "kz-tag-challenge"

    name = (career.get("career_name") or "").lower()
    desc = (career.get("description") or "").lower()
    ev = career.get("evidence_level") or "D"
    text = name + " " + desc

    explore_keywords = ["研究", "创意", "艺术", "设计", "写作", "学术", "探索", "创新", "实验", "自由"]
    challenge_keywords = ["管理", "创业", "总监", "高管", "合伙人", "投资", "竞争", "领导", "战略", "顾问"]
    steady_keywords = ["技师", "工程师", "研究员", "分析师", "专员", "编辑", "教师", "护士", "社工", "行政", "会计", "审计"]

    if any(k in text for k in explore_keywords) and ev in ("A", "B", "C"):
        return "探索型", "Explore-oriented", "kz-tag-explore"
    if any(k in text for k in challenge_keywords):
        return "高挑战型", "High Challenge", "kz-tag-challenge"
    if ev in ("A", "B", "C") or any(k in text for k in steady_keywords):
        return "稳就业型", "Steady Employment", "kz-tag-steady"
    return "探索型", "Explore-oriented", "kz-tag-explore"


def _build_major_tiers(careers: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """将推荐职业的相关专业去重后按匹配度分为 Core / Expand / Watch 三层。"""
    # 计算每个专业的最高匹配分
    major_best = {}
    for c in careers:
        score = c.get("match_score", 0)
        ev = c.get("evidence_level") or "D"
        rank = {"A": 4, "B": 3, "C": 2, "D": 1}.get(ev, 0)
        priority = score + rank * 2
        for m in c.get("related_majors") or []:
            m = str(m).strip()
            if not m:
                continue
            if m not in major_best or major_best[m]["priority"] < priority:
                major_best[m] = {"priority": priority, "score": score, "evidence": ev}

    sorted_majors = sorted(major_best.items(), key=lambda x: -x[1]["priority"])

    # 分层：Core 8 / Expand 8 / Watch 6
    core = [{"name": m, "info": info} for m, info in sorted_majors[:8]]
    expand = [{"name": m, "info": info} for m, info in sorted_majors[8:16]]
    watch = [{"name": m, "info": info} for m, info in sorted_majors[16:22]]

    return {"core": core, "expand": expand, "watch": watch}


def _build_career_tiers(careers: List[Dict[str, Any]], holland_code: str, gallup_domain: str) -> Dict[str, List[Dict[str, Any]]]:
    """把推荐职业分为高适配、中适配、就业友好备选三层，并按职业名去重。"""
    if not holland_code:
        deduped = _deduplicate_careers_by_name(careers)
        return {"high": deduped[:3], "moderate": deduped[3:6], "alternative": deduped[6:]}

    domain_en = _domain_en(gallup_domain)
    first = holland_code[0].upper()
    rest = holland_code[1:].upper() if len(holland_code) > 1 else ""

    high, moderate, alternative = [], [], []
    seen_names = set()

    def add_unique(target_list, career):
        name = career.get("career_name")
        if name and name not in seen_names:
            seen_names.add(name)
            target_list.append(career)

    for c in careers:
        ri = (c.get("riasec_primary") or "").upper()
        cs = c.get("cs_domain") or ""
        if ri == first and cs == domain_en:
            add_unique(high, c)
        elif ri == first or ri in rest or cs == domain_en:
            add_unique(moderate, c)
        else:
            add_unique(alternative, c)

    # 保证每一层都有内容：若高适配为空，从前几个补入
    if not high and careers:
        for c in careers:
            add_unique(high, c)
        moderate = [c for c in careers if c.get("career_name") not in seen_names]
    if not moderate and alternative:
        for c in alternative:
            add_unique(moderate, c)
        alternative = [c for c in alternative if c.get("career_name") not in seen_names]

    return {"high": high, "moderate": moderate, "alternative": alternative}


def _deduplicate_careers_by_name(careers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    result = []
    for c in careers:
        name = c.get("career_name")
        if name and name not in seen:
            seen.add(name)
            result.append(c)
    return result


_MATRIX_DOMAINS_CACHE: Optional[Dict[str, Dict[str, Optional[Dict[str, Any]]]]] = None


def _matrix_domains_path() -> str:
    """定位 24 格职业范畴 JSON（与 import_data 数据目录一致）。"""
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    candidates = [
        os.path.join(base, "research", "测评研究", "data", "processed", "riasec_gallup_matrix_24_domains.json"),
        os.path.join(base, "data", "processed", "riasec_gallup_matrix_24_domains.json"),
    ]
    return next((p for p in candidates if os.path.isfile(p)), candidates[0])


def _load_matrix_domains() -> Dict[str, Dict[str, Optional[Dict[str, Any]]]]:
    """加载 24 格职业范畴定义。返回 matrix[riasec][domain_en] = cell_dict | None。"""
    global _MATRIX_DOMAINS_CACHE
    if _MATRIX_DOMAINS_CACHE is not None:
        return _MATRIX_DOMAINS_CACHE

    matrix = {r: {d: None for d in DOMAIN_ZH_TO_EN.values()} for r in ["R", "I", "A", "S", "E", "C"]}
    path = _matrix_domains_path()
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for cell in data.get("cells", []):
            ri = (cell.get("riasec") or "").upper()
            dom = cell.get("gallup_domain_en") or ""
            if ri in matrix and dom in matrix[ri]:
                matrix[ri][dom] = cell
    _MATRIX_DOMAINS_CACHE = matrix
    return matrix


def _matrix_intersection_tier(
    ri: str,
    domain_en: str,
    holland_code: str,
    gallup_domain: str,
    gallup_secondary_domain: str = "",
) -> str:
    """判定单元格与用户结果的交叉层级：dominant | secondary | tertiary | 空。"""
    if not holland_code:
        return ""
    first = holland_code[0].upper()
    second = holland_code[1].upper() if len(holland_code) > 1 else ""
    third = holland_code[2].upper() if len(holland_code) > 2 else ""

    leading = _domain_en(gallup_domain)
    secondary = _domain_en(gallup_secondary_domain)
    has_secondary_gallup = bool(secondary and secondary != leading)

    if ri == first and domain_en == leading:
        return "dominant"
    if has_secondary_gallup:
        if ri == first and domain_en == secondary:
            return "secondary"
        if second and ri == second and domain_en == leading:
            return "secondary"
        if second and ri == second and domain_en == secondary:
            return "tertiary"
    if third and ri == third and domain_en == leading:
        return "tertiary"
    return ""


def _matrix_marker(
    ri: str,
    domain_en: str,
    holland_code: str,
    gallup_domain: str,
    gallup_secondary_domain: str = "",
) -> tuple:
    """返回单元格 CSS 类。三级视觉权重：主导 > 次要 > 第三交叉（仅边框着色，不显示圈号徽章）。"""
    tier = _matrix_intersection_tier(ri, domain_en, holland_code, gallup_domain, gallup_secondary_domain)
    css_map = {
        "dominant": "kz-matrix-dominant",
        "secondary": "kz-matrix-secondary",
        "tertiary": "kz-matrix-tertiary",
    }
    return css_map.get(tier, ""), ""


def _matrix_legend_html() -> str:
    """矩阵三级图例：描述性引导，弱化公式感。"""
    return """
<div class="kz-matrix-legend">
  <div class="kz-matrix-legend-item kz-matrix-legend-dominant">
    <strong>主导交叉 / Primary</strong>
    当你最强烈的兴趣舞台，遇上最自然擅长的做事方式，一个特别值得率先投入的方向便会浮现——不妨从这里开始验证自己的热情与能力。
    <br><span class="kz-en">Where your strongest interest stage meets your most natural working style — a direction worth exploring first.</span>
  </div>
  <div class="kz-matrix-legend-item kz-matrix-legend-secondary">
    <strong>次要交叉 / Secondary</strong>
    兴趣与才干以另一种配比相遇时，会照亮若干值得并行留意的拓展面——它们未必是主航道，却可能藏着你尚未充分尝试的潜能。
    <br><span class="kz-en">Alternative pairings of interest and strength that reveal expansion paths and untapped potential.</span>
  </div>
  <div class="kz-matrix-legend-item kz-matrix-legend-tertiary">
    <strong>第三交叉 / Third</strong>
    在三码与双领域的交汇处，还有一些更轻柔、更长期的线索——适合作为背景关注，在主业之外慢慢积累体验与见识。
    <br><span class="kz-en">Gentler, longer-term clues at the edges of your profile — worth keeping on your radar over time.</span>
  </div>
</div>
"""


def _tier_guidance(tier: str) -> tuple:
    """返回某交叉层级的描述性引导（中、英）。"""
    guidance = {
        "dominant": (
            "这是你当前最值得优先投入精力的方向。不妨问自己：在这个范畴里，哪些具体活动曾让你忘记时间？哪些经历让你感到「这就是我擅长的事」？",
            "Your top-priority direction. Ask yourself: which activities in this domain made you lose track of time? When did you feel 'this is what I'm good at'?",
        ),
        "secondary": (
            "这些交叉为你打开了另一种可能的组合方式。它们适合作为并行探索的支线——不必立刻做出选择，但值得在课程、社团或短期项目中轻轻试探。",
            "These intersections open alternative combinations worth exploring in parallel — try them lightly through courses, clubs, or short projects.",
        ),
        "tertiary": (
            "这些线索处于你兴趣与优势谱系的边缘地带，不必急于定义，却值得长期留意。随着阅历增长，它们有时会意外成为新的突破口。",
            "These clues sit at the edges of your profile — no rush to define them, but worth tracking as experience grows; they may become unexpected breakthroughs.",
        ),
    }
    return guidance.get(tier, ("", ""))


def _intersection_prompt(tier: str) -> tuple:
    """返回单格探索提示（中、英）。"""
    prompts = {
        "dominant": (
            "💡 试着找一个与此范畴相关的小项目或体验，记录你在其中的能量变化。",
            "💡 Try a small project in this domain and note how your energy shifts.",
        ),
        "secondary": (
            "💡 可以把它当作「第二战场」——在主业之外，每周留出一小块时间做相关尝试。",
            "💡 Treat this as a 'second front' — set aside a small weekly slice for related experiments.",
        ),
        "tertiary": (
            "💡 不必立刻行动，但可以把相关领域加入你的阅读清单或关注列表，保持开放。",
            "💡 No immediate action needed — add related topics to your reading list and stay open.",
        ),
    }
    return prompts.get(tier, ("", ""))


def _collect_tier_coordinates(
    tier: str,
    holland_code: str,
    gallup_domain: str,
    gallup_secondary_domain: str = "",
) -> List[tuple]:
    """收集某层级对应的 (riasec, domain_en) 坐标列表。"""
    if not holland_code:
        return []
    first = holland_code[0].upper()
    second = holland_code[1].upper() if len(holland_code) > 1 else ""
    third = holland_code[2].upper() if len(holland_code) > 2 else ""
    leading = _domain_en(gallup_domain)
    secondary = _domain_en(gallup_secondary_domain)
    has_secondary = bool(secondary and secondary != leading)

    if tier == "dominant":
        return [(first, leading)]
    if tier == "secondary":
        coords = []
        if has_secondary:
            coords.append((first, secondary))
        if second:
            coords.append((second, leading))
        return coords
    if tier == "tertiary":
        coords = []
        if has_secondary and second:
            coords.append((second, secondary))
        if third:
            coords.append((third, leading))
        return coords
    return []


def _secondary_intersection_summary(
    holland_code: str,
    gallup_domain: str,
    gallup_secondary_domain: str = "",
) -> tuple:
    """生成次要交叉点的中英文摘要。"""
    coords = _collect_tier_coordinates("secondary", holland_code, gallup_domain, gallup_secondary_domain)
    if not coords:
        return "未指定", "Not specified"
    zh_parts = []
    en_parts = []
    for ri, dom in coords:
        dom_zh = DOMAIN_EN_TO_ZH.get(dom, dom)
        zh_parts.append(f"{_type_name(ri)} × {dom_zh}")
        en_parts.append(f"{ri} × {dom}")
    return "，".join(zh_parts), ", ".join(en_parts)


def _third_intersection_summary(
    holland_code: str,
    gallup_domain: str,
    gallup_secondary_domain: str = "",
) -> tuple:
    """生成第三交叉点的中英文摘要。"""
    coords = _collect_tier_coordinates("tertiary", holland_code, gallup_domain, gallup_secondary_domain)
    if not coords:
        return "未指定", "Not specified"
    zh_parts = []
    en_parts = []
    for ri, dom in coords:
        dom_zh = DOMAIN_EN_TO_ZH.get(dom, dom)
        zh_parts.append(f"{_type_name(ri)} × {dom_zh}")
        en_parts.append(f"{ri} × {dom}")
    return "，".join(zh_parts), ", ".join(en_parts)


def _matrix_ethics_notice() -> str:
    """交叉矩阵伦理说明：强调探索性、非诊断性。"""
    return """
<div class="kz-ethics">
  <p><strong>关于本矩阵的说明 / About This Matrix</strong></p>
  <p>本框架是一个<strong>辅助你探索兴趣与潜能交集</strong>的工具，而非对你下结论的标签。矩阵中的每一格代表一种<strong>职业范畴</strong>（方向层），是根据 Holland 兴趣舞台与 Gallup 工作方式的理论整合而定义；报告后文的「推荐职业路径」则提供具体岗位线索。请把结果当作<strong>对话与行动的起点</strong>，通过课程体验、实习、访谈和项目实践来验证。</p>
  <p class="kz-en"><em>This matrix is an <strong>exploration aid</strong>, not a diagnostic label. Each cell represents an <strong>occupational domain</strong> (direction layer) defined by the integration of Holland interest stage and Gallup working style; specific job suggestions appear later in the career paths section. Use these insights as a starting point for conversation and action; validate them through real experiences, internships, interviews, and projects.</em></p>
</div>
"""


def _build_student_synthesis(
    student_name: str,
    holland_code: str,
    holland_scores: Dict[str, int],
    gallup_domain: str,
    gallup_secondary_domain: str,
    gallup_top5: List[str],
    careers: List[Dict[str, Any]],
    tension: str,
) -> str:
    """为学生版报告生成综合解读与个性化建议。"""
    dominant = holland_code[0].upper() if holland_code else ""
    second = holland_code[1].upper() if len(holland_code) > 1 else ""
    third = holland_code[2].upper() if len(holland_code) > 2 else ""
    domain_en = _domain_en(gallup_domain)
    strength_style = _strength_style(domain_en) if gallup_domain else "未指定 / Not specified"
    stage_tag = _stage_tag(dominant) if dominant else ""
    consistency = _holland_consistency(holland_code)
    overall_fit = _overall_fit(holland_code, domain_en) if holland_code and gallup_domain else ""

    top_career_names = [c.get("career_name") for c in (careers or [])[:3] if c.get("career_name")]
    career_hint = "、".join(top_career_names) if top_career_names else "见下方推荐列表"
    top5_text = "、".join(gallup_top5[:5]) if gallup_top5 else "待完成 Gallup 测评后显示"

    interest_lines = []
    for rank, letter in enumerate(holland_code.upper(), 1):
        zh_meaning = RIASEC_MEANING.get(letter, ("", ""))[0]
        rank_label = {1: "最感兴趣", 2: "次感兴趣", 3: "第三感兴趣"}.get(rank, "")
        interest_lines.append(f"<li><strong>{letter}</strong>（{_type_name(letter)}）— {rank_label}：{_escape_html(zh_meaning)}</li>")
    interest_list = "\n".join(interest_lines)

    advice_items = _build_student_advice(holland_code, gallup_domain, gallup_secondary_domain, overall_fit)
    advice_html = "".join(f"<li>{_escape_html(a)}</li>" for a in advice_items)

    return f"""
<div class="kz-synthesis">
  <h3>综合解读与给你的建议 | Summary & Recommendations</h3>
  <p><strong>{_escape_html(student_name)}</strong>，你好。以下是对你本次双维度测评的综合解读——帮你把「喜欢做什么」和「擅长怎么做」放在一起看。</p>
  <p class="kz-en"><em>Hello <strong>{_escape_html(student_name)}</strong>. This section integrates what you enjoy doing with how you naturally work best.</em></p>

  <h4>你是谁：兴趣舞台 + 优势风格 | Who You Are</h4>
  <p>你的 Holland 三码是 <strong>{holland_code or '—'}</strong>，兴趣舞台标签为 <strong>{_escape_html(stage_tag)}</strong>；Gallup 主导优势领域是 <strong>{_escape_html(gallup_domain or '未指定')}</strong>（次要领域：{_escape_html(gallup_secondary_domain or '未指定')}），工作风格偏向 <strong>{_escape_html(strength_style)}</strong>。</p>
  <p>Top 5 才干主题：{_escape_html(top5_text)}</p>
  <ul class="kz-list">
    {interest_list}
  </ul>

  <h4>兴趣与优势如何配合 | How Interests & Strengths Fit</h4>
  <p>{_escape_html(tension)}</p>
  <p><strong>整体契合度 / Overall Fit</strong>：{_escape_html(overall_fit)}</p>
  <p class="kz-small">{_escape_html(consistency)}</p>

  <div class="kz-synthesis-advice">
    <p><strong>给你的三条建议 / Three Recommendations for You</strong></p>
    <ol class="kz-list">
      {advice_html}
    </ol>
  </div>

  <p>结合以上解读，当前最值得你留意的探索方向包括：<strong>{_escape_html(career_hint)}</strong>。请从下方「稳妥入口职业」和「核心推荐专业」中挑选 1–2 个，用真实体验去验证——喜欢不等于适合，适合也需要在实践中确认。</p>
  <p class="kz-en"><em>Based on this profile, directions worth exploring include: <strong>{_escape_html(career_hint)}</strong>. Pick 1–2 from the safe-entry careers and core majors below, and validate through real experience.</em></p>

  <div class="kz-ethics">
    <p><strong>重要提醒 / Important Reminder</strong>：本报告是<strong>探索与自我发现的辅助工具</strong>，不能替代你的判断，也不能限制你的可能性。测评结果会随经历与成长而变化——请带着好奇而非焦虑阅读，并与信任的老师、家长或咨询师讨论你的下一步。</p>
    <p class="kz-en"><em>This report is an <strong>exploration aid</strong>, not a verdict on who you must become. Results can evolve with experience—read with curiosity, not anxiety, and discuss your next steps with trusted adults or counselors.</em></p>
  </div>
</div>
"""


def _build_student_advice(
    holland_code: str,
    gallup_domain: str,
    gallup_secondary_domain: str,
    overall_fit: str,
) -> List[str]:
    """根据测评结果生成三条学生向建议（中英双语）。"""
    if not holland_code:
        return [
            "先完成 Holland 与 Gallup 两项测评，再阅读综合建议。/ Complete both assessments before reading the synthesis.",
            "找一位你信任的人，聊聊你最近最有成就感的三件事。/ Talk with someone you trust about three recent moments you felt proud of.",
            "不要急于选专业，先用一个周末做一件你好奇的小事并记录感受。/ Don't rush into a major—try one small thing you're curious about this weekend and note how it feels.",
        ]

    first = holland_code[0].upper()
    stage_advice = {
        "R": "优先安排能动手、能出具体成果的体验（维修、实验、户外项目等），观察你是否真的享受。/ Prioritize hands-on experiences with tangible outcomes and notice whether you genuinely enjoy them.",
        "I": "选一个你好奇的话题，做一次深度调研或小型研究，记录你最想继续追问的问题。/ Pick a topic you are curious about, do a small research dive, and note what questions you still want to pursue.",
        "A": "完成一件小型创作（设计、写作、音乐、视频等）并收集他人反馈，感受创作过程是否让你充满能量。/ Create a small piece of work and gather feedback—notice whether the creative process energizes you.",
        "S": "参与一次助人或陪伴活动（辅导、志愿、倾听朋友），留意你在互动中的感受与消耗。/ Join a helping or mentoring activity and notice how you feel during and after the interaction.",
        "E": "主导或参与一个小型项目（活动、社团、售卖、演讲），体验说服与推动的过程。/ Lead or join a small project to experience persuasion, coordination, and momentum.",
        "C": "尝试整理一份复杂资料或完成一项需要细致核对的事务，观察你对流程与准确性的感受。/ Try organizing complex information or completing detail-heavy work and observe how you feel about process and accuracy.",
    }
    domain_advice = {
        "执行力": "把大目标拆成可执行的小步骤，用一周时间跟踪完成率——你的优势在「把事做完」。/ Break big goals into small steps and track completion for a week—your strength is getting things done.",
        "影响力": "练习用 3 分钟清晰表达一个观点，并观察听众的反应——你的优势在「推动他人行动」。/ Practice expressing one idea clearly in 3 minutes and observe how others respond—your strength is mobilizing action.",
        "关系建立": "主动与一位你欣赏的人深聊，记录你们建立信任的过程——你的优势在「连接人与信任」。/ Have a deep conversation with someone you admire and notice how trust builds—your strength is connecting people.",
        "战略思维": "针对你关心的方向写一份简短的趋势分析或问题清单——你的优势在「看见模式与方向」。/ Write a short trend analysis or question list on a topic you care about—your strength is seeing patterns and direction.",
    }
    fit_advice = (
        "你的兴趣与优势整体一致，可以较大胆地在主导交叉方向上投入时间；仍建议用实习或项目做小范围验证。/ Your interests and strengths align well—feel confident investing time in your primary intersection, but still validate through projects or internships."
        if "高度一致" in overall_fit or "High alignment" in overall_fit
        else "你的兴趣与优势存在差异或张力，不必强行统一——寻找能把两者结合起来的具体场景（如跨学科项目、复合岗位）。/ Your interests and strengths show tension—don't force them to match; look for roles or projects that combine both."
    )

    return [
        stage_advice.get(first, stage_advice["R"]),
        domain_advice.get(gallup_domain, domain_advice.get(gallup_secondary_domain, "回顾你的 Top 5 主题，找出最常出现的工作场景并刻意练习。/ Review your Top 5 themes and practice the work situations where they show up most.")),
        fit_advice,
    ]


# ---------------------------------------------------------------------------
# 学生版报告可视化 / Student report visuals
# ---------------------------------------------------------------------------

_RIASEC_COLORS = {
    "R": "#ef4444",
    "I": "#3b82f6",
    "A": "#8b5cf6",
    "S": "#22c55e",
    "E": "#f59e0b",
    "C": "#6b7280",
}

_RIASEC_BG_COLORS = {
    "R": "#fee2e2",
    "I": "#dbeafe",
    "A": "#ede9fe",
    "S": "#dcfce7",
    "E": "#fef3c7",
    "C": "#f3f4f6",
}

_DOMAIN_COLORS = {
    "执行力": "#ef4444",
    "影响力": "#f59e0b",
    "关系建立": "#22c55e",
    "战略思维": "#3b82f6",
}

_DOMAIN_BG_COLORS = {
    "执行力": "#fee2e2",
    "影响力": "#fef3c7",
    "关系建立": "#dcfce7",
    "战略思维": "#dbeafe",
}

# ---------------------------------------------------------------------------
# 报告主题插画 / Report illustrations (inline SVG)
# ---------------------------------------------------------------------------

_RIASEC_SVGS = {
    "R": """<svg viewBox="0 0 160 120" xmlns="http://www.w3.org/2000/svg">
      <rect width="160" height="120" rx="12" fill="#fee2e2"/>
      <circle cx="80" cy="60" r="28" fill="#ef4444" opacity="0.15"/>
      <path d="M62 55 L78 71 L112 37" stroke="#ef4444" stroke-width="6" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
      <circle cx="105" cy="80" r="14" fill="none" stroke="#ef4444" stroke-width="5"/>
      <circle cx="105" cy="80" r="6" fill="#ef4444"/>
      <rect x="48" y="78" width="26" height="8" rx="2" fill="#ef4444" transform="rotate(-45 61 82)"/>
    </svg>""",
    "I": """<svg viewBox="0 0 160 120" xmlns="http://www.w3.org/2000/svg">
      <rect width="160" height="120" rx="12" fill="#dbeafe"/>
      <circle cx="80" cy="60" r="28" fill="#3b82f6" opacity="0.15"/>
      <path d="M70 85 L70 50" stroke="#3b82f6" stroke-width="5" stroke-linecap="round"/>
      <path d="M58 40 L82 40 L82 50 L58 50 Z" fill="#3b82f6"/>
      <circle cx="80" cy="32" r="4" fill="#3b82f6"/>
      <circle cx="105" cy="55" r="8" fill="none" stroke="#3b82f6" stroke-width="3"/>
      <circle cx="118" cy="42" r="5" fill="none" stroke="#3b82f6" stroke-width="3"/>
      <circle cx="118" cy="68" r="5" fill="none" stroke="#3b82f6" stroke-width="3"/>
    </svg>""",
    "A": """<svg viewBox="0 0 160 120" xmlns="http://www.w3.org/2000/svg">
      <rect width="160" height="120" rx="12" fill="#ede9fe"/>
      <circle cx="80" cy="60" r="28" fill="#8b5cf6" opacity="0.15"/>
      <ellipse cx="65" cy="70" rx="14" ry="10" fill="none" stroke="#8b5cf6" stroke-width="4"/>
      <path d="M51 70 L65 55 L72 62 L79 52" stroke="#8b5cf6" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
      <path d="M92 48 L100 80 L95 80 L87 48 Z" fill="#8b5cf6"/>
      <path d="M82 55 Q95 45 108 55" stroke="#8b5cf6" stroke-width="3" fill="none" stroke-linecap="round"/>
      <circle cx="113" cy="52" r="3" fill="#8b5cf6"/>
    </svg>""",
    "S": """<svg viewBox="0 0 160 120" xmlns="http://www.w3.org/2000/svg">
      <rect width="160" height="120" rx="12" fill="#dcfce7"/>
      <circle cx="80" cy="60" r="28" fill="#22c55e" opacity="0.15"/>
      <circle cx="62" cy="55" r="12" fill="#22c55e"/>
      <circle cx="98" cy="55" r="12" fill="#22c55e"/>
      <path d="M74 70 Q80 78 86 70" stroke="#22c55e" stroke-width="3" fill="none" stroke-linecap="round"/>
      <path d="M55 82 Q80 100 105 82" stroke="#22c55e" stroke-width="4" fill="none" stroke-linecap="round"/>
      <circle cx="80" cy="92" r="5" fill="#22c55e"/>
    </svg>""",
    "E": """<svg viewBox="0 0 160 120" xmlns="http://www.w3.org/2000/svg">
      <rect width="160" height="120" rx="12" fill="#fef3c7"/>
      <circle cx="80" cy="60" r="28" fill="#f59e0b" opacity="0.15"/>
      <rect x="55" y="75" width="50" height="8" rx="2" fill="#f59e0b"/>
      <rect x="60" y="50" width="8" height="25" rx="2" fill="#f59e0b"/>
      <rect x="75" y="40" width="8" height="35" rx="2" fill="#f59e0b"/>
      <rect x="90" y="55" width="8" height="20" rx="2" fill="#f59e0b"/>
      <path d="M110 45 L120 35 L120 55 Z" fill="#f59e0b"/>
      <circle cx="125" cy="45" r="8" fill="none" stroke="#f59e0b" stroke-width="3"/>
    </svg>""",
    "C": """<svg viewBox="0 0 160 120" xmlns="http://www.w3.org/2000/svg">
      <rect width="160" height="120" rx="12" fill="#f3f4f6"/>
      <circle cx="80" cy="60" r="28" fill="#6b7280" opacity="0.15"/>
      <rect x="52" y="42" width="36" height="48" rx="4" fill="none" stroke="#6b7280" stroke-width="4"/>
      <rect x="60" y="52" width="20" height="4" rx="1" fill="#6b7280"/>
      <rect x="60" y="60" width="20" height="4" rx="1" fill="#6b7280"/>
      <rect x="60" y="68" width="14" height="4" rx="1" fill="#6b7280"/>
      <path d="M95 50 L125 50" stroke="#6b7280" stroke-width="3" stroke-linecap="round"/>
      <path d="M95 60 L118 60" stroke="#6b7280" stroke-width="3" stroke-linecap="round"/>
      <path d="M95 70 L115 70" stroke="#6b7280" stroke-width="3" stroke-linecap="round"/>
    </svg>""",
}

_DOMAIN_SVGS = {
    "执行力": """<svg viewBox="0 0 160 120" xmlns="http://www.w3.org/2000/svg">
      <rect width="160" height="120" rx="12" fill="#fee2e2"/>
      <circle cx="80" cy="60" r="28" fill="#ef4444" opacity="0.15"/>
      <path d="M55 65 L75 85 L105 45" stroke="#ef4444" stroke-width="7" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
      <rect x="100" y="35" width="20" height="28" rx="2" fill="none" stroke="#ef4444" stroke-width="4"/>
      <path d="M105 45 L112 52 L120 40" stroke="#ef4444" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>""",
    "影响力": """<svg viewBox="0 0 160 120" xmlns="http://www.w3.org/2000/svg">
      <rect width="160" height="120" rx="12" fill="#fef3c7"/>
      <circle cx="80" cy="60" r="28" fill="#f59e0b" opacity="0.15"/>
      <path d="M52 55 L52 75 L68 70 L68 50 Z" fill="#f59e0b"/>
      <path d="M68 55 L95 48" stroke="#f59e0b" stroke-width="4" stroke-linecap="round"/>
      <path d="M95 35 L95 65" stroke="#f59e0b" stroke-width="4" stroke-linecap="round"/>
      <ellipse cx="95" cy="50" rx="10" ry="18" fill="none" stroke="#f59e0b" stroke-width="3"/>
      <circle cx="115" cy="50" r="12" fill="none" stroke="#f59e0b" stroke-width="3"/>
    </svg>""",
    "关系建立": """<svg viewBox="0 0 160 120" xmlns="http://www.w3.org/2000/svg">
      <rect width="160" height="120" rx="12" fill="#dcfce7"/>
      <circle cx="80" cy="60" r="28" fill="#22c55e" opacity="0.15"/>
      <circle cx="62" cy="52" r="10" fill="#22c55e"/>
      <circle cx="98" cy="52" r="10" fill="#22c55e"/>
      <path d="M70 62 Q80 72 90 62" stroke="#22c55e" stroke-width="4" fill="none" stroke-linecap="round"/>
      <circle cx="62" cy="52" r="14" fill="none" stroke="#22c55e" stroke-width="2" opacity="0.5"/>
      <circle cx="98" cy="52" r="14" fill="none" stroke="#22c55e" stroke-width="2" opacity="0.5"/>
      <path d="M50 70 Q80 95 110 70" stroke="#22c55e" stroke-width="3" fill="none" stroke-linecap="round" opacity="0.6"/>
    </svg>""",
    "战略思维": """<svg viewBox="0 0 160 120" xmlns="http://www.w3.org/2000/svg">
      <rect width="160" height="120" rx="12" fill="#dbeafe"/>
      <circle cx="80" cy="60" r="28" fill="#3b82f6" opacity="0.15"/>
      <path d="M65 75 Q80 40 95 75" stroke="#3b82f6" stroke-width="4" fill="none" stroke-linecap="round"/>
      <circle cx="80" cy="55" r="14" fill="none" stroke="#3b82f6" stroke-width="4"/>
      <path d="M80 48 L80 55 L86 55" stroke="#3b82f6" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
      <circle cx="105" cy="45" r="6" fill="#3b82f6"/>
      <circle cx="55" cy="50" r="4" fill="#3b82f6"/>
      <circle cx="110" cy="70" r="4" fill="#3b82f6"/>
    </svg>""",
}

_THEME_DOMAINS = {
    "成就": "执行力", "统筹": "执行力", "信仰": "执行力", "公平": "执行力",
    "审慎": "执行力", "纪律": "执行力", "专注": "执行力", "责任": "执行力", "排难": "执行力",
    "行动": "影响力", "统率": "影响力", "沟通": "影响力", "竞争": "影响力",
    "完美": "影响力", "自信": "影响力", "追求": "影响力", "取悦": "影响力",
    "适应": "关系建立", "关联": "关系建立", "伯乐": "关系建立", "体谅": "关系建立",
    "和谐": "关系建立", "包容": "关系建立", "个别": "关系建立", "积极": "关系建立", "交往": "关系建立",
    "思维": "战略思维", "理念": "战略思维", "学习": "战略思维", "分析": "战略思维",
    "回顾": "战略思维", "战略": "战略思维", "前瞻": "战略思维", "搜集": "战略思维",
}


def _holland_bar_chart(holland_scores: Dict[str, int]) -> str:
    """生成 RIASEC 分数水平条形图（SVG）。"""
    if not holland_scores:
        return ""

    max_score = max(holland_scores.values()) or 1
    letters = ["R", "I", "A", "S", "E", "C"]
    labels = {
        "R": "现实型 R",
        "I": "研究型 I",
        "A": "艺术型 A",
        "S": "社会型 S",
        "E": "企业型 E",
        "C": "常规型 C",
    }

    bar_height = 22
    gap = 12
    left_margin = 70
    right_margin = 50
    chart_width = 420
    bar_max_width = chart_width - left_margin - right_margin
    total_height = len(letters) * (bar_height + gap) + 20

    svg = f'<svg width="100%" height="{total_height}" viewBox="0 0 {chart_width} {total_height}" xmlns="http://www.w3.org/2000/svg">'
    for i, letter in enumerate(letters):
        score = holland_scores.get(letter, 0)
        bar_width = (score / max_score) * bar_max_width
        y = 10 + i * (bar_height + gap)
        color = _RIASEC_COLORS.get(letter, "#9ca3af")
        bg_color = _RIASEC_BG_COLORS.get(letter, "#f3f4f6")

        # Background track.
        svg += f'<rect x="{left_margin}" y="{y}" width="{bar_max_width}" height="{bar_height}" rx="11" fill="{bg_color}"/>'
        # Score bar.
        svg += f'<rect x="{left_margin}" y="{y}" width="{bar_width}" height="{bar_height}" rx="11" fill="{color}"/>'
        # Label.
        svg += f'<text x="{left_margin - 10}" y="{y + bar_height/2 + 5}" text-anchor="end" font-size="13" font-weight="600" fill="#374151">{labels[letter]}</text>'
        # Score number.
        svg += f'<text x="{left_margin + bar_width + 8}" y="{y + bar_height/2 + 5}" font-size="12" font-weight="600" fill="#374151">{score}</text>'

    svg += "</svg>"
    return svg


def _gallup_domain_blocks(gallup_domain: str, gallup_secondary_domain: str) -> str:
    """生成 Gallup 四大领域可视化方块。"""
    domains = ["执行力", "影响力", "关系建立", "战略思维"]
    html = '<div class="kz-domain-grid">'
    for d in domains:
        is_primary = d == gallup_domain
        is_secondary = d == gallup_secondary_domain
        color = _DOMAIN_COLORS.get(d, "#9ca3af")
        bg = _DOMAIN_BG_COLORS.get(d, "#f3f4f6")
        badge = ""
        if is_primary:
            badge = '<span class="kz-domain-badge kz-domain-primary">主导</span>'
        elif is_secondary:
            badge = '<span class="kz-domain-badge kz-domain-secondary">次要</span>'

        html += f'''
        <div class="kz-domain-block" style="background:{bg}; border-top: 4px solid {color};">
          <div class="kz-domain-name">{d}</div>
          <div class="kz-domain-en">{_domain_en(d)}</div>
          {badge}
        </div>
        '''
    html += '</div>'
    return html


def _top5_theme_pills(gallup_top5: List[str]) -> str:
    """生成 Top 5 主题彩色胶囊。"""
    if not gallup_top5:
        return ""
    html = '<div class="kz-top5-pills">'
    for i, theme in enumerate(gallup_top5[:5], 1):
        domain = _THEME_DOMAINS.get(theme, "")
        color = _DOMAIN_COLORS.get(domain, "#6b7280")
        html += f'''
        <div class="kz-top5-pill" style="background:{color}20; border: 1px solid {color}; color:{color};">
          <span class="kz-top5-rank">{i}</span>
          <span class="kz-top5-name">{_escape_html(theme)}</span>
        </div>
        '''
    html += '</div>'
    return html


def _type_badge_card(holland_code: str, gallup_domain: str, style: str) -> str:
    """生成顶部类型徽章卡片（MBTI 风格）。"""
    if not holland_code:
        return ""

    primary_color = _RIASEC_COLORS.get(holland_code[0].upper(), "#2563eb")
    domain_color = _DOMAIN_COLORS.get(gallup_domain, "#6b7280")

    stage_tag = _stage_tag(holland_code[0].upper()) if holland_code else ""
    stage_tag_en = RIASEC_STAGE_TAGS.get(holland_code[0].upper(), ("", ""))[1] if holland_code else ""
    style_parts = style.split(" / ", 1)
    style_zh = style_parts[0]
    style_en = style_parts[1] if len(style_parts) > 1 else style

    return f'''
    <div class="kz-type-card" style="border-left: 6px solid {primary_color};">
      <div class="kz-type-badges">
        <span class="kz-type-badge kz-holland-badge" style="background:{primary_color};">{holland_code}</span>
        <span class="kz-type-plus">+</span>
        <span class="kz-type-badge" style="background:{domain_color};">{_escape_html(gallup_domain or '未指定')}</span>
      </div>
      <div class="kz-type-summary">
        <strong>{_escape_html(stage_tag)}</strong> × <strong>{_escape_html(style_zh)}</strong>
        <br><span class="kz-en">{stage_tag_en} × {_escape_html(style_en)}</span>
      </div>
    </div>
    '''


def _report_illustration(holland_first_letter: str, gallup_domain: str, mode: str = "combined") -> str:
    """生成报告主题插画（内联 SVG）。mode: combined / holland / domain"""
    letter = (holland_first_letter or "R").upper()
    holland_svg = _RIASEC_SVGS.get(letter, _RIASEC_SVGS["R"])
    domain_svg = _DOMAIN_SVGS.get(gallup_domain, _DOMAIN_SVGS.get("执行力", ""))

    if mode == "holland":
        stage_zh, stage_en = RIASEC_STAGE_TAGS.get(letter, ("", ""))
        return f'''
        <div class="kz-illustration-card">
          {holland_svg}
          <div class="kz-illustration-label">{_escape_html(stage_zh)}</div>
          <div class="kz-illustration-en">{_escape_html(stage_en)}</div>
        </div>
        '''

    if mode == "domain":
        domain_en = _domain_en(gallup_domain) if gallup_domain else ""
        return f'''
        <div class="kz-illustration-card">
          {domain_svg}
          <div class="kz-illustration-label">{_escape_html(gallup_domain or '')}</div>
          <div class="kz-illustration-en">{_escape_html(domain_en)}</div>
        </div>
        '''

    # combined: side-by-side hero with short text
    stage_zh, stage_en = RIASEC_STAGE_TAGS.get(letter, ("", ""))
    domain_en = _domain_en(gallup_domain) if gallup_domain else ""
    return f'''
    <div class="kz-hero-illustration">
      <div class="kz-illustration-row" style="margin:0;">
        <div class="kz-illustration-card" style="max-width:180px;">
          {holland_svg}
          <div class="kz-illustration-label">{_escape_html(stage_zh)}</div>
          <div class="kz-illustration-en">{_escape_html(stage_en)}</div>
        </div>
        <div class="kz-illustration-card" style="max-width:180px;">
          {domain_svg}
          <div class="kz-illustration-label">{_escape_html(gallup_domain or '')}</div>
          <div class="kz-illustration-en">{_escape_html(domain_en)}</div>
        </div>
      </div>
      <div class="kz-hero-text">
        <p><strong>你的组合画像 / Your Profile</strong></p>
        <p>兴趣舞台：{_escape_html(stage_zh)}（{stage_en}）；优势领域：{_escape_html(gallup_domain or '未指定')} / {_escape_html(domain_en)}。</p>
        <p class="kz-en">Interest stage: {stage_en}; Leading strength domain: {domain_en or 'Not specified'}.</p>
      </div>
    </div>
    '''


def _build_student_html(
    student_name: str,
    holland_code: str,
    holland_scores: Dict[str, int],
    gallup_domain: str,
    gallup_secondary_domain: str,
    gallup_top5: List[str],
    careers: List[Dict[str, Any]],
    actions: List[str],
    data_quality_notes: List[str],
    tension: str,
) -> str:
    safe = _safe_entry_points(careers)
    major_tiers = _build_major_tiers(careers)
    core_majors = major_tiers["core"]

    holland_result = f"<strong>{holland_code}</strong> — {_type_name(holland_code[0]) if holland_code else '未指定 / Not specified'}" if holland_code else "未指定 / Not specified"
    domain_en = _domain_en(gallup_domain)
    style = _strength_style(domain_en) if gallup_domain else "未指定 / Not specified"

    type_card = _type_badge_card(holland_code, gallup_domain, style)
    holland_chart = _holland_bar_chart(holland_scores)
    domain_blocks = _gallup_domain_blocks(gallup_domain, gallup_secondary_domain)
    top5_pills = _top5_theme_pills(gallup_top5)
    hero_illustration = _report_illustration(holland_code[0] if holland_code else "", gallup_domain, mode="combined")
    career_illustration = _report_illustration(holland_code[0] if holland_code else "", gallup_domain, mode="holland")

    safe_rows = ""
    for c in safe:
        tag_zh, tag_en, tag_cls = _career_tag(c)
        safe_rows += f"""
        <tr>
          <td>{_escape_html(c['career_name'])}</td>
          <td><span class="kz-tag {tag_cls}">{tag_zh} / {tag_en}</span></td>
          <td>{_escape_html('、'.join(c.get('related_majors') or []))}</td>
        </tr>"""

    major_rows = _major_table_rows(core_majors[:8])

    action_items = ""
    for a in actions:
        action_items += f"<li>{_escape_html(a)}</li>"

    quality_items = ""
    for note in data_quality_notes:
        quality_items += f"<li>{_escape_html(note)}</li>"

    synthesis_html = _build_student_synthesis(
        student_name=student_name,
        holland_code=holland_code,
        holland_scores=holland_scores,
        gallup_domain=gallup_domain,
        gallup_secondary_domain=gallup_secondary_domain,
        gallup_top5=gallup_top5,
        careers=careers,
        tension=tension,
    )

    return f"""
<meta charset="UTF-8">
<div class="kz-report">
{_css()}
<div class="kz-print-header">
  <h1>学生一页纸测评摘要 | Student One-Page Summary</h1>
  <button class="kz-print-btn" onclick="window.print()">🖨️ 打印 / Print</button>
</div>
<div class="kz-meta">
  <p><strong>姓名 / Name</strong>：{_escape_html(student_name)}</p>
  <p><strong>Holland 三码 / Holland Code</strong>：{holland_result}</p>
  <p><strong>优势领域 / Leading Strength Domain</strong>：{_escape_html(gallup_domain or '未指定 / Not specified')}</p>
  <p><strong>优势风格 / Strengths Style</strong>：{_escape_html(style)}</p>
</div>

<div class="kz-warning kz-screen-only">
  <strong>数据质量提示 / Data Quality Notes</strong>
  <ul class="kz-list">
    {quality_items}
  </ul>
</div>

{synthesis_html}

{type_card}

{hero_illustration}

<h2>1. 我的测评画像 | My Profile</h2>

<div class="kz-chart-card">
  <div class="kz-chart-title">Holland 兴趣六维得分 | RIASEC Scores</div>
  <div class="kz-chart-subtitle">分数越高，代表该类型越能描述你的兴趣倾向 / Higher scores mean stronger alignment with that interest type.</div>
  {holland_chart}
</div>

<div class="kz-chart-card">
  <div class="kz-chart-title">Gallup 优势领域 | CliftonStrengths Domains</div>
  <div class="kz-chart-subtitle">主导领域是你最自然的工作方式，次要领域是其次 / Your leading domain is your most natural way of working.</div>
  {domain_blocks}
</div>

<div class="kz-chart-card">
  <div class="kz-chart-title">Top 5 才干主题 | My Top 5 Themes</div>
  <div class="kz-chart-subtitle">颜色代表该主题所属的优势领域 / Colors show which domain each theme belongs to.</div>
  {top5_pills}
</div>

<h2>2. 我的核心结果 | My Core Results</h2>
<table>
  <tr><th>维度 / Dimension</th><th>结果 / Result</th></tr>
  <tr><td>Holland 三码 / Holland Code</td><td>{holland_result}</td></tr>
  <tr><td>优势领域 / Leading Strength Domain</td><td>{_escape_html(gallup_domain or '未指定 / Not specified')}</td></tr>
  <tr><td>优势风格 / Strengths Style</td><td>{_escape_html(style)}</td></tr>
</table>

{career_illustration}

<h2>3. 稳妥入口职业 | Safe Entry Points</h2>
<p>如果你更关注就业稳定性和现实可行性，以下方向是不错的起点。</p>
<p class="kz-en">If you prioritize employment stability and practical entry paths, these roles are good starting points.</p>
<table>
  <tr><th>职业 / Career</th><th>标签 / Tag</th><th>相关专业 / Related Majors</th></tr>
  {safe_rows if safe_rows else '<tr><td colspan="3">暂无 / None</td></tr>'}
</table>

<h2>4. 核心推荐专业 | Core Recommended Majors</h2>
<table>
  <tr><th>专业 / Major</th><th>国内可报说明 / Domestic Note</th><th>海外方向（以英国为例）/ Overseas Example (UK)</th></tr>
  {major_rows}
</table>

<h2>5. 三个下一步行动 | Three Next Steps</h2>
<ul class="kz-list">
  {action_items}
</ul>

<div class="kz-tip">
  📄 <strong>完整报告 / Full Report</strong>：请查看专业版报告获取 RIASEC 剖面、主题叙事、交叉矩阵与详细专业映射。
  <br><span class="kz-en">See the professional report for RIASEC profile, theme narrative, cross-matrix, and detailed major mappings.</span>
</div>
</div>
"""


def _build_professional_html(
    db: Session,
    student_name: str,
    holland_code: str,
    holland_scores: Dict[str, int],
    gallup_domain: str,
    gallup_secondary_domain: str,
    domain_distribution: Dict[str, int],
    top10_details: List[Dict[str, Any]],
    gallup_top10: List[str],
    tension: str,
    careers: List[Dict[str, Any]],
    data_quality_notes: List[str],
) -> str:
    safe = _safe_entry_points(careers)
    major_tiers = _build_major_tiers(careers)
    career_tiers = _build_career_tiers(careers, holland_code, gallup_domain)
    matrix = _load_matrix_domains()

    domain_en = _domain_en(gallup_domain)
    secondary_domain_en = _domain_en(gallup_secondary_domain)
    secondary_domain_en = _domain_en(gallup_secondary_domain)
    dominant_type = holland_code[0].upper() if holland_code else ""
    dominant_type_name = _type_name(dominant_type) if dominant_type else "未指定 / Not specified"
    strength_style = _strength_style(domain_en) if gallup_domain else "未指定 / Not specified"

    # 1. Report overview
    overview = f"""
<h2>报告概览 | Report at a Glance</h2>
<div class="kz-highlight">
  <p><strong>你是独一无二的存在。本报告基于你的 Holland RIASEC 兴趣测评与 Gallup CliftonStrengths 优势测评，帮助你了解自己的兴趣舞台、优势风格，以及两者交叉后的职业与专业探索方向。</strong></p>
  <p class="kz-en"><em>You are uniquely wired. This report integrates your Holland RIASEC interest profile and Gallup CliftonStrengths talent profile to help you understand your preferred stage, natural strengths style, and intersecting career and major directions.</em></p>
</div>
<table>
  <tr><th>维度 / Dimension</th><th>结果 / Result</th></tr>
  <tr><td>Holland 三码 / Holland Code</td><td><strong>{holland_code}</strong> — {dominant_type_name}</td></tr>
  <tr><td>主导兴趣舞台 / Dominant Stage</td><td>{_escape_html(_stage_tag(dominant_type)) if dominant_type else '未指定 / Not specified'}</td></tr>
  <tr><td>CliftonStrengths 主导领域 / Leading Domain</td><td>{_escape_html(gallup_domain or '未指定 / Not specified')} / {domain_en}</td></tr>
  <tr><td>CliftonStrengths 次要领域 / Secondary Domain</td><td>{_escape_html(gallup_secondary_domain or '未指定 / Not specified')} / {secondary_domain_en}</td></tr>
  <tr><td>优势风格 / Strengths Style</td><td>{_escape_html(strength_style)}</td></tr>
</table>

<h3>🎯 稳妥入口职业 | Safe Entry Points</h3>
<p>如果你更关注就业稳定性和现实可行性，以下方向是不错的起点。这些岗位需求稳定、入行路径清晰，适合作为长期探索的「安全基地」。</p>
<p class="kz-en">If you prioritize employment stability and practical entry paths, these roles are good starting points with clear demand and accessible entry routes.</p>
<table>
  <tr><th>职业 / Career</th><th>为何稳妥 / Why Steady</th><th>相关专业 / Related Majors</th></tr>
  {_safe_rows(safe)}
</table>
<div class="kz-tip">
  💡 <strong>提示 / Tip</strong>：即使你的高适配方向看起来偏创意或研究，也可以从「稳妥入口」开始积累经验，再逐步转向理想方向。
  <br><span class="kz-en">Even if your best-fit directions seem creative or research-oriented, you can start from safe entry points and gradually move toward your ideal path.</span>
</div>
"""

    # 2. Interest stage
    interest_stage_rows = ""
    for rank, letter in enumerate(holland_code.upper(), 1):
        zh, en = RIASEC_MEANING.get(letter, ("", ""))
        interest_stage_rows += f"""
        <tr>
          <td>{rank}</td>
          <td>{letter} — {_type_name(letter)}</td>
          <td><span class="kz-stage-badge">{_stage_tag(letter)}</span></td>
          <td>{_escape_html(zh)}<br><span class="kz-en">{_escape_html(en)}</span></td>
        </tr>"""

    interest_section = f"""
<h2 class="kz-section">我的兴趣舞台 | My Interest Stage</h2>
<p>你的 Holland 三码是 <strong>{holland_code}</strong>，三个字母分别代表你最感兴趣、次感兴趣和第三感兴趣的工作舞台。</p>
<p class="kz-en">Your Holland code is <strong>{holland_code}</strong>. The three letters represent your strongest, second-strongest, and third-strongest areas of work interest.</p>
<table>
  <tr><th>排名 / Rank</th><th>类型 / Type</th><th>舞台标签 / Stage Tag</th><th>含义 / Meaning</th></tr>
  {interest_stage_rows}
</table>
"""

    # 3. Strengths style
    top5_rows = ""
    for idx, t in enumerate(top10_details[:5], 1):
        one_liner = ""
        if t.get('definition_zh'):
            one_liner += _escape_html(t['definition_zh'])
        if t.get('definition_en'):
            if one_liner:
                one_liner += "<br><span class='kz-en'>"
            one_liner += _escape_html(t['definition_en'])
            if t.get('definition_zh'):
                one_liner += "</span>"
        top5_rows += f"""
        <tr>
          <td>{idx}</td>
          <td>{_escape_html(t['theme'])} / {_escape_html(t['theme_en'])}</td>
          <td>{_escape_html(t['domain'])} / {DOMAIN_ZH_TO_EN.get(t['domain'], t['domain'])}</td>
          <td>{one_liner}</td>
        </tr>"""

    top10_rows = ""
    for idx, t in enumerate(top10_details, 1):
        top10_rows += f"""
        <tr>
          <td>{idx}</td>
          <td>{_escape_html(t['theme'])} / {_escape_html(t['theme_en'])}</td>
          <td>{_escape_html(t['domain'])} / {DOMAIN_ZH_TO_EN.get(t['domain'], t['domain'])}</td>
        </tr>"""

    domain_dist_items = ""
    for d, count in sorted(domain_distribution.items(), key=lambda x: -x[1]):
        domain_dist_items += f"<li>{_escape_html(d)} / {DOMAIN_ZH_TO_EN.get(d, d)}：{count}</li>"

    strengths_section = f"""
<h2 class="kz-section">我的优势风格 | My Strengths Style</h2>
<p>你的 Gallup CliftonStrengths Top 10 主题按排名加权后，<strong>{_escape_html(gallup_domain or '未指定')}</strong> 领域得分最高，是最能代表你稳定工作方式的领域；<strong>{_escape_html(gallup_secondary_domain or '未指定')}</strong> 为次要领域。这意味着你最自然的工作方式是 <strong>{_escape_html(strength_style)}</strong>。</p>
<p class="kz-en">When your Gallup CliftonStrengths Top 10 themes are weighted by rank, <strong>{domain_en}</strong> scores highest as your leading domain and <strong>{secondary_domain_en}</strong> is your secondary domain. Your most natural way of working is as an <strong>{_strength_style(domain_en).split(' / ')[1] if ' / ' in _strength_style(domain_en) else domain_en}</strong>.</p>
<div class="kz-card">
  <p><strong>{_escape_html(gallup_domain or '未指定')} / {domain_en}</strong>：{_escape_html(_domain_description(domain_en))}</p>
</div>
<h3>Top 10 主题一览 | Top 10 Themes at a Glance</h3>
<table>
  <tr><th>排名 / Rank</th><th>主题 / Theme</th><th>领域 / Domain</th></tr>
  {top10_rows}
</table>
<h3>Top 5 才干主题详细解读 | Your Top 5 Themes in Detail</h3>
<p>以下是对你最突出的 5 个才干主题的详细解读。第 6–10 名主题已列在上方一览表中，作为延伸线索。/ Detailed narratives are provided for your top 5 themes. Themes 6–10 are listed above as extended clues.</p>
<table>
  <tr><th>排名 / Rank</th><th>主题 / Theme</th><th>领域 / Domain</th><th>一句话定义 / One-Liner</th></tr>
  {top5_rows}
</table>
<p><strong>Top 10 领域分布 / Domain Distribution (Top 10)</strong>：</p>
<ul class="kz-list">
  {domain_dist_items}
</ul>
"""

    # 4. Cross-matrix
    matrix_html = _build_matrix_html(matrix, holland_code, gallup_domain, gallup_secondary_domain)
    cross_section = f"""
<h2 class="kz-section">兴趣 × 优势交叉矩阵 | Interest × Strengths Cross-Matrix</h2>
{_matrix_ethics_notice()}
<p>下方矩阵展示了 6 种 RIASEC 兴趣类型与 4 大 CliftonStrengths 优势领域交叉形成的 <strong>24 种职业范畴</strong>。表格中每格仅标注范畴名称；带色边框的格子与你结果相关——边框越实、颜色越深，关联越强。具体解读见矩阵下方。</p>
<p class="kz-en"><em>The matrix shows <strong>24 occupational domains</strong>. Each cell lists only the domain name; colored borders mark relevance to your results. See detailed interpretation below the matrix.</em></p>
{_matrix_legend_html()}
{matrix_html}
{_build_matrix_intersection_html(matrix, holland_code, gallup_domain, gallup_secondary_domain)}
"""

    # 5. Recommended majors
    majors_section = _build_majors_html(major_tiers)

    # 6. Career paths
    careers_section = _build_career_tiers_html(career_tiers)

    # 7. Integration (placed before screen-only blocks so print numbering stays continuous)
    consistency_text = _holland_consistency(holland_code)
    integration_section = f"""
<h2 class="kz-section">兴趣-优势整合分析 | Interest-Strengths Integration</h2>
<ul class="kz-list">
  <li><strong>主导兴趣 / Dominant Interest</strong>：{_type_name(dominant_type) if dominant_type else '未指定 / Not specified'}</li>
  <li><strong>主导优势 / Dominant Strength</strong>：{_escape_html(gallup_domain or '未指定 / Not specified')} / {domain_en}</li>
  <li><strong>整体契合度 / Overall Fit</strong>：{_escape_html(_overall_fit(holland_code, domain_en))}</li>
</ul>
<div class="kz-card">
  <p><strong>张力分析 / Tension Analysis</strong>：{_escape_html(tension)}</p>
</div>
<div class="kz-tip">
  <strong>一致性提示 / Consistency</strong>：{consistency_text}
</div>
"""

    # 8. Employment market placeholder
    market_section = _build_market_html()

    # 9. Evidence levels
    evidence_section = _build_evidence_html()

    # 10. Action tracking
    action_section = _build_action_html()

    # 11. Next steps
    next_steps = """
<h2 class="kz-section">下一步行动 | Next Steps</h2>
<ol class="kz-list">
  <li><strong>阅读学生一页纸摘要 / Read student one-pager</strong>：快速抓住核心结论。</li>
  <li><strong>选择 1-2 个稳妥入口职业 / Pick 1-2 safe entry points</strong>：在招聘网站查找真实岗位描述。</li>
  <li><strong>了解 2-3 个核心专业 / Explore 2-3 core majors</strong>：查看目标院校的国内招生目录或海外 Programme 页面。</li>
  <li><strong>完成一次职业访谈 / Do one career interview</strong>：记录到「行动跟踪模块」。</li>
  <li><strong>与测评师讨论 / Discuss with a counselor</strong>：带着报告参加一对一职业咨询。</li>
</ol>
"""

    # Appendix
    appendix = _build_appendix_html(holland_scores, holland_code, top10_details, gallup_domain)

    quality_items = ""
    for note in data_quality_notes:
        quality_items += f"<li>{_escape_html(note)}</li>"

    return f"""
<meta charset="UTF-8">
<div class="kz-report">
{_css()}
<div class="kz-print-header">
  <h1>双维度测评报告（专业详细版）| Dual-Dimension Assessment Report (Professional Edition)</h1>
  <button class="kz-print-btn" onclick="window.print()">🖨️ 打印 / Print</button>
</div>
<div class="kz-meta">
  <p><strong>姓名 / Name</strong>：{_escape_html(student_name)}</p>
  <p><strong>测评日期 / Date</strong>：以系统记录为准 / As recorded by system</p>
  <p><strong>目标申请方向 / Target Region</strong>：未指定 / Not specified</p>
</div>

<div class="kz-warning kz-screen-only">
  <strong>数据质量提示 / Data Quality Notes</strong>
  <ul class="kz-list">
    {quality_items}
  </ul>
</div>

{overview}
{interest_section}
{strengths_section}
{cross_section}
{majors_section}
{careers_section}
{integration_section}
<div class="kz-screen-only">
{market_section}
{evidence_section}
{action_section}
{next_steps}
</div>
{appendix}
</div>
"""


def _safe_rows(safe: List[Dict[str, Any]]) -> str:
    if not safe:
        return '<tr><td colspan="3">暂无 / None</td></tr>'
    rows = ""
    for c in safe:
        rows += f"""
        <tr>
          <td>{_escape_html(c['career_name'])}</td>
          <td>{_escape_html(c.get('description') or '')}</td>
          <td>{_escape_html('、'.join(c.get('related_majors') or []))}</td>
        </tr>"""
    return rows


def _domain_description(domain_en: str) -> str:
    descriptions = {
        "Executing": "喜欢按计划把事情做完、负责到底，善于把想法化为现实。/ You make things happen and turn ideas into reality.",
        "Influencing": "善于表达观点、说服他人、推动行动，乐于在团队中发声。/ You express ideas, persuade others, and mobilize action.",
        "Relationship Building": "重视连接、信任和团队协作，善于让不同的人走到一起。/ You value connection, trust, and teamwork, bringing people together.",
        "Strategic Thinking": "喜欢分析、想象、规划未来，善于在复杂信息中找到方向。/ You analyze, imagine, and plan, finding direction in complexity.",
    }
    return descriptions.get(domain_en, "")


def _format_matrix_cell_html(cell: Optional[Dict[str, Any]]) -> str:
    """矩阵单元格仅显示范畴名称（黑体概括）。"""
    if not cell:
        return "—"
    name = cell.get("name_zh") or ""
    return f'<div class="kz-matrix-domain-title">{_escape_html(name)}</div>'


def _format_intersection_card_html(cell: Dict[str, Any], tier: str) -> str:
    """生成单格详细解读卡片。"""
    name = cell.get("name_zh") or ""
    tagline = cell.get("tagline_zh") or ""
    integration = cell.get("integration_zh") or ""
    interests = "、".join(cell.get("onet_basic_interests_zh") or [])
    clusters = "、".join(cell.get("tag_clusters_zh") or [])
    themes = "、".join(cell.get("gallup_themes") or [])
    prompt_zh, prompt_en = _intersection_prompt(tier)

    meta_html = ""
    if interests or clusters or themes:
        meta_items = []
        if interests:
            meta_items.append(f'<div class="kz-intersection-meta-item"><strong>兴趣线索 / Interests</strong>{_escape_html(interests)}</div>')
        if clusters:
            meta_items.append(f'<div class="kz-intersection-meta-item"><strong>方向集群 / Clusters</strong>{_escape_html(clusters)}</div>')
        if themes:
            meta_items.append(f'<div class="kz-intersection-meta-item"><strong>才干主题 / Themes</strong>{_escape_html(themes)}</div>')
        meta_html = f'<div class="kz-intersection-meta">{"".join(meta_items)}</div>'

    return f"""
<div class="kz-intersection-card">
  <p class="kz-intersection-card-title">{_escape_html(name)}</p>
  {f'<p class="kz-intersection-card-tagline">{_escape_html(tagline)}</p>' if tagline else ''}
  <p class="kz-intersection-card-body">{_escape_html(integration)}</p>
  {meta_html}
  <div class="kz-intersection-prompt">{_escape_html(prompt_zh)}<br><span class="kz-en">{_escape_html(prompt_en)}</span></div>
</div>"""


def _build_matrix_intersection_html(
    matrix: Dict[str, Dict[str, Optional[Dict[str, Any]]]],
    holland_code: str,
    gallup_domain: str,
    gallup_secondary_domain: str = "",
) -> str:
    """为与用户结果相关的交叉格生成分组详细解读。"""
    if not holland_code:
        return ""

    tier_config = [
        ("dominant", "primary", "主导交叉 / Primary"),
        ("secondary", "secondary", "次要交叉 / Secondary"),
        ("tertiary", "tertiary", "第三交叉 / Third"),
    ]

    sections = []
    for tier_key, css_tier, label in tier_config:
        coords = _collect_tier_coordinates(tier_key, holland_code, gallup_domain, gallup_secondary_domain)
        if not coords:
            continue
        cards = []
        seen_ids = set()
        for ri, dom_en in coords:
            cell = (matrix.get(ri) or {}).get(dom_en)
            if not cell:
                continue
            cid = cell.get("id") or f"{ri}-{dom_en}"
            if cid in seen_ids:
                continue
            seen_ids.add(cid)
            cards.append(_format_intersection_card_html(cell, tier_key))
        if not cards:
            continue

        guide_zh, guide_en = _tier_guidance(tier_key)
        sections.append(f"""
<div class="kz-intersection-tier kz-intersection-tier-{css_tier}">
  <div class="kz-intersection-tier-header">
    <span class="kz-intersection-tier-badge">{_escape_html(label.split(' / ')[0])}</span>
    <p class="kz-intersection-tier-desc">{_escape_html(guide_zh)}<br><span class="kz-en">{_escape_html(guide_en)}</span></p>
  </div>
  <div class="kz-intersection-cards">{''.join(cards)}</div>
</div>""")

    if not sections:
        return ""

    return f"""
<div class="kz-intersection-detail">
  <h3>你的交叉解读 | Your Intersection Profile</h3>
  <p class="kz-intersection-intro">矩阵中标色边框的格子，对应你测评结果中兴趣与优势的不同交汇方式。下方按层级展开具体范畴——帮助你从「方向感」走向「可尝试的行动线索」。</p>
  <p class="kz-intersection-intro kz-en"><em>Colored cells in the matrix mark how your interests and strengths intersect. The sections below expand each domain — moving from direction to actionable exploration clues.</em></p>
  {''.join(sections)}
</div>"""


def _build_matrix_html(
    matrix: Dict[str, Dict[str, Optional[Dict[str, Any]]]],
    holland_code: str,
    gallup_domain: str,
    gallup_secondary_domain: str = "",
) -> str:
    domains = ["Strategic Thinking", "Executing", "Influencing", "Relationship Building"]
    domain_headers = {
        "Strategic Thinking": "战略思维 / Strategic Thinking",
        "Executing": "执行力 / Executing",
        "Influencing": "影响力 / Influencing",
        "Relationship Building": "关系建立 / Relationship Building",
    }
    header = "<tr><th class=\"kz-matrix-header\">RIASEC \\ 领域 / Domain</th>" + "".join(f'<th class="kz-matrix-header">{domain_headers[d]}</th>' for d in domains) + "</tr>"
    rows = ""
    for ri in ["R", "I", "A", "S", "E", "C"]:
        row = f"<th>{ri} / {_type_name_en(ri)}</th>"
        for dom in domains:
            cls, prefix = _matrix_marker(ri, dom, holland_code, gallup_domain, gallup_secondary_domain)
            cell = (matrix.get(ri) or {}).get(dom)
            cell_html = _format_matrix_cell_html(cell)
            row += f'<td class="{cls}">{prefix}{cell_html}</td>'
        rows += f"<tr>{row}</tr>"
    return f'<table class="kz-matrix-table">{header}{rows}</table>'


def _major_table_rows(majors: List[Dict[str, Any]]) -> str:
    if not majors:
        return '<tr><td colspan="3">暂无 / None</td></tr>'
    rows = ""
    for m in majors:
        name = m['name']
        # Generate a simple domestic note based on major name keywords
        domestic_note = _major_domestic_note(name)
        rows += f"""
        <tr>
          <td>{_escape_html(name)}</td>
          <td>{_escape_html(domestic_note)}</td>
          <td>建议按具体院校查询 / Check programme titles</td>
        </tr>"""
    return rows


def _major_domestic_note(major: str) -> str:
    """根据专业名称生成简单的国内可报说明。"""
    notes = []
    if "工程" in major:
        notes.append("工学门类")
    if "科学" in major or "技术" in major:
        notes.append("理学/工学")
    if "经济" in major or "金融" in major or "财务" in major or "会计" in major:
        notes.append("经济学/管理学")
    if "教育" in major or "教师" in major or "心理" in major:
        notes.append("教育学/理学")
    if "艺术" in major or "设计" in major or "创意" in major:
        notes.append("艺术学")
    if "社会" in major or "行政" in major:
        notes.append("法学/管理学")
    if "医学" in major or "护理" in major or "生物" in major:
        notes.append("医学/理学")
    if "计算机" in major or "软件" in major or "数据" in major:
        notes.append("工学（计算机类）")
    if not notes:
        notes.append("按具体院校招生目录查询")
    return " / ".join(notes)


def _build_majors_html(major_tiers: Dict[str, List[Dict[str, Any]]]) -> str:
    return f"""
<h2 class="kz-section">推荐申请专业 | Recommended Majors</h2>
<p>以下专业根据推荐职业路径分层整理。<strong>核心专业</strong>建议优先了解；<strong>拓展专业</strong>可作为备选或第二专业方向；<strong>可关注专业</strong>适合作为长期兴趣跟踪。</p>
<p class="kz-en"><em>Majors are organized by priority. <strong>Core</strong> majors are the top priorities; <strong>Expand</strong> majors are alternatives or second-field options; <strong>Watch</strong> majors are for long-term interest tracking.</em></p>

<h3 class="kz-subsection">核心专业 | Core Majors</h3>
<table>
  <tr><th>专业 / Major</th><th>国内可报说明 / Domestic Note</th><th>海外方向（以英国为例）/ Overseas Example (UK)</th></tr>
  {_major_table_rows(major_tiers['core'])}
</table>

<h3 class="kz-subsection">拓展专业 | Expand Majors</h3>
<table>
  <tr><th>专业 / Major</th><th>国内可报说明 / Domestic Note</th><th>海外方向（以英国为例）/ Overseas Example (UK)</th></tr>
  {_major_table_rows(major_tiers['expand'])}
</table>

<h3 class="kz-subsection">可关注专业 | Watch Majors</h3>
<table>
  <tr><th>专业 / Major</th><th>国内可报说明 / Domestic Note</th><th>海外方向（以英国为例）/ Overseas Example (UK)</th></tr>
  {_major_table_rows(major_tiers['watch'])}
</table>

<div class="kz-warning">
  ⚠️ <strong>提醒 / Reminder</strong>：推荐专业仅为参考路径。国内路径需对照教育部本科专业目录与各省招生计划；海外路径需以目标院校官网 Programme/Course 名称为准。
  <br><span class="kz-en">Recommended majors are reference paths. For domestic applications, verify against the Ministry of Education catalog and provincial enrollment plans. For overseas applications, confirm programme titles on target university websites.</span>
</div>
"""


def _career_table_rows(careers: List[Dict[str, Any]], mode: str = "fit") -> str:
    if not careers:
        return '<tr><td colspan="4">暂无 / None</td></tr>'
    rows = ""
    for c in careers:
        tag_zh, tag_en, tag_cls = _career_tag(c)
        why = c.get("description") or ""
        rows += f"""
        <tr>
          <td>{_escape_html(c['career_name'])}</td>
          <td><span class="kz-tag {tag_cls}">{tag_zh} / {tag_en}</span></td>
          <td>{_escape_html(why)}</td>
          <td>{_escape_html('、'.join(c.get('related_majors') or []))}</td>
        </tr>"""
    return rows


def _build_career_tiers_html(career_tiers: Dict[str, List[Dict[str, Any]]]) -> str:
    return f"""
<h2 class="kz-section">推荐职业路径 | Recommended Career Paths</h2>
<p>以下推荐分为三个层级：</p>
<ol class="kz-list">
  <li><strong>高适配路径 / High Fit</strong>：与你的主导兴趣和主导优势精确匹配。</li>
  <li><strong>中适配路径 / Moderate Fit</strong>：与你的主导兴趣或主导优势部分匹配，可作为拓展方向。</li>
  <li><strong>就业友好备选 / Employment-Friendly Alternatives</strong>：即使你对某些高适配方向存有顾虑，这些方向也能让你在现实就业市场中找到稳定入口。</li>
</ol>
<p class="kz-en"><em>Recommendations are divided into three tiers. Each career is tagged with <strong>Steady Employment</strong>, <strong>Explore-oriented</strong>, or <strong>High Challenge</strong> to help you choose.</em></p>

<div class="kz-card">
  <p><strong>标签说明 / Tag Guide</strong>：</p>
  <ul class="kz-list">
    <li><span class="kz-tag kz-tag-steady">稳就业型 / Steady Employment</span>：岗位需求稳定，入行路径清晰。</li>
    <li><span class="kz-tag kz-tag-explore">探索型 / Explore-oriented</span>：需要更多尝试和积累，适合作为长期方向。</li>
    <li><span class="kz-tag kz-tag-challenge">高挑战型 / High Challenge</span>：竞争激烈或需要长期资源积累，适合有强烈动机的人。</li>
  </ul>
</div>

<h3 class="kz-subsection">高适配路径 | High Fit</h3>
<table>
  <tr><th>职业 / Career</th><th>标签 / Tag</th><th>主要工作 / What They Do</th><th>相关专业 / Related Majors</th></tr>
  {_career_table_rows(career_tiers['high'], mode='fit')}
</table>

<h3 class="kz-subsection">中适配路径 | Moderate Fit</h3>
<table>
  <tr><th>职业 / Career</th><th>标签 / Tag</th><th>主要工作 / What They Do</th><th>相关专业 / Related Majors</th></tr>
  {_career_table_rows(career_tiers['moderate'], mode='fit')}
</table>

<h3 class="kz-subsection">就业友好备选 | Employment-Friendly Alternatives</h3>
<table>
  <tr><th>职业 / Career</th><th>标签 / Tag</th><th>为何作为备选 / Why This Alternative</th><th>相关专业 / Related Majors</th></tr>
  {_career_table_rows(career_tiers['alternative'])}
</table>
"""


def _build_market_html() -> str:
    return """
<h2 class="kz-section">就业市场参考 | Employment Market Reference</h2>
<div class="kz-tip">
  <strong>数据建设中 / Data Under Construction</strong>：本模块计划接入第三方就业数据源（招聘平台、行业报告、校友追踪），为每个推荐职业补充平均起薪、岗位需求、学历要求、热门城市与发展路径。当前版本暂以框架形式呈现，具体数值请以目标院校就业报告和招聘平台实时数据为准。
  <br><span class="kz-en">This module will integrate third-party employment data (job platforms, industry reports, alumni tracking) to add entry salary, job demand, education requirements, top cities, and career paths for each recommended role. Current version shows the framework only; please verify specific figures against university employment reports and live job platforms.</span>
</div>
<table>
  <tr><th>数据项 / Data Item</th><th>说明 / Description</th><th>参考来源 / Potential Source</th></tr>
  <tr><td>平均起薪 / Entry Salary</td><td>应届生或初级岗位的中位数起薪</td><td>麦可思、智联招聘、BOSS直聘</td></tr>
  <tr><td>岗位需求量 / Job Demand</td><td>近一年招聘发布数量与增长趋势</td><td>智联招聘、前程无忧、猎聘</td></tr>
  <tr><td>学历要求 / Education Requirement</td><td>本科/硕士/博士占比</td><td>教育部就业质量报告、招聘平台</td></tr>
  <tr><td>热门城市 / Top Cities</td><td>岗位分布集中的城市或地区</td><td>BOSS直聘、猎聘城市报告</td></tr>
  <tr><td>发展路径 / Career Path</td><td>3-5 年、5-10 年的典型晋升方向</td><td>行业报告、校友访谈</td></tr>
</table>
"""


def _build_evidence_html() -> str:
    return """
<h2 class="kz-section">证据等级说明与科学性建设 | Evidence Levels & Scientific Roadmap</h2>
<h3 class="kz-subsection">当前证据等级定义 | Current Evidence Level Definitions</h3>
<table>
  <tr><th>等级 / Level</th><th>含义 / Meaning</th><th>当前应用情况 / Current Application</th></tr>
  <tr><td><strong>A</strong></td><td>大样本实证研究或长期追踪数据支持</td><td>当前暂无，需通过用户毕业去向追踪积累</td></tr>
  <tr><td><strong>B</strong></td><td>小样本研究、专家评审或行业调研支持</td><td>当前暂无，可通过行业专家访谈与毕业生反馈逐步建立</td></tr>
  <tr><td><strong>C</strong></td><td>理论推导与现有文献综述支持</td><td>当前大部分职业-专业映射属于此等级</td></tr>
  <tr><td><strong>D</strong></td><td>基于个案经验或初步假设</td><td>少量映射属于此等级</td></tr>
</table>

<h3 class="kz-subsection">如何积累 A/B 级证据 | How to Build A/B-Level Evidence</h3>
<ol class="kz-list">
  <li><strong>毕业生追踪研究 / Graduate tracking studies</strong>：对使用本工具的用户进行 1 年、3 年、5 年跟踪，记录其专业选择与职业满意度。
    <br><span class="kz-en">Follow users at 1, 3, and 5 years to record major choices and career satisfaction.</span></li>
  <li><strong>行业专家评议 / Expert review</strong>：邀请各职业领域的资深从业者对推荐匹配度进行 1-5 分评分。
    <br><span class="kz-en">Invite senior practitioners to rate the fit of recommendations.</span></li>
  <li><strong>用人单位调研 / Employer surveys</strong>：收集招聘方对相关专业毕业生的能力匹配评价。
    <br><span class="kz-en">Collect hiring managers' assessments of graduates from related majors.</span></li>
  <li><strong>纵向对照实验 / Longitudinal controlled experiments</strong>：对比使用本工具与未使用本工具的学生在专业选择清晰度、就业对口率上的差异。
    <br><span class="kz-en">Compare students who used the tool versus those who did not.</span></li>
</ol>
"""


def _build_action_html() -> str:
    return """
<h2 class="kz-section">行动跟踪模块 | Action Tracking Module</h2>
<p>本模块帮助你把报告结论转化为具体行动并记录进展。若使用在线版工具，可自动保存打卡与复盘。</p>
<p class="kz-en">This module helps turn report insights into concrete actions and track progress. The online version can automatically save check-ins and reflections.</p>

<h3>行动 1：职业访谈记录 | Career Interview Log</h3>
<table>
  <tr><th>项目 / Item</th><th>内容 / Content</th></tr>
  <tr><td>访谈对象 / Interviewee</td><td><span class="kz-answer-line"></span></td></tr>
  <tr><td>职业 / Career</td><td><span class="kz-answer-line"></span></td></tr>
  <tr><td>访谈日期 / Date</td><td><span class="kz-answer-line"></span></td></tr>
  <tr><td>三个关键发现 / Key Insights</td><td>1. <span class="kz-answer-line"></span><br>2. <span class="kz-answer-line"></span><br>3. <span class="kz-answer-line"></span></td></tr>
  <tr><td>我喜欢 / What I Liked</td><td><span class="kz-answer-line"></span></td></tr>
  <tr><td>我担心 / What Concerned Me</td><td><span class="kz-answer-line"></span></td></tr>
  <tr><td>下一步 / Next Step</td><td><span class="kz-answer-line"></span></td></tr>
</table>

<h3>行动 2：专业体验记录 | Major Exploration Log</h3>
<table>
  <tr><th>项目 / Item</th><th>内容 / Content</th></tr>
  <tr><td>体验专业 / Major</td><td><span class="kz-answer-line"></span></td></tr>
  <tr><td>体验方式 / Activity</td><td>□ 线上课程 / Online course &nbsp; □ 校园开放日 / Open day &nbsp; □ 旁听课程 / Audit &nbsp; □ 实习 / Internship</td></tr>
  <tr><td>体验时间 / Date</td><td><span class="kz-answer-line"></span></td></tr>
  <tr><td>感受 / Reflection</td><td><span class="kz-answer-line"></span></td></tr>
  <tr><td>是否愿意继续探索 / Continue?</td><td>□ 是 / Yes &nbsp; □ 否 / No &nbsp; □ 再试试 / Maybe</td></tr>
</table>

<h3>行动 3：月度复盘 | Monthly Review</h3>
<table>
  <tr><th>问题 / Question</th><th>我的回答 / My Answer</th></tr>
  <tr><td>这个月我尝试了哪些方向？ / What did I try this month?</td><td><span class="kz-answer-line"></span></td></tr>
  <tr><td>哪些方向让我更有能量？ / What energized me?</td><td><span class="kz-answer-line"></span></td></tr>
  <tr><td>哪些方向让我感觉不适合？ / What felt like a poor fit?</td><td><span class="kz-answer-line"></span></td></tr>
  <tr><td>下个月我要聚焦什么？ / What will I focus on next month?</td><td><span class="kz-answer-line"></span></td></tr>
</table>
"""


def _overall_fit(holland_code: str, gallup_domain_en: str) -> str:
    """基于 Holland 三码与 Gallup 领域的综合契合度。"""
    mapping = {
        "R": "Executing",
        "I": "Strategic Thinking",
        "A": "Strategic Thinking",
        "S": "Relationship Building",
        "E": "Influencing",
        "C": "Executing",
    }
    expected_list = [mapping.get(l.upper()) for l in holland_code if l.upper() in mapping]
    if gallup_domain_en in expected_list:
        return "兴趣与优势高度一致 / High alignment"
    task_domains = {"Executing", "Strategic Thinking"}
    people_domains = {"Relationship Building", "Influencing"}
    if (gallup_domain_en in task_domains and any(d in task_domains for d in expected_list)) or \
       (gallup_domain_en in people_domains and any(d in people_domains for d in expected_list)):
        return "兴趣与优势可互补 / Complementary"
    return "兴趣与优势存在张力，需项目验证 / Tension to explore through projects"


# Hexagon adjacency: adjacent types are most consistent; opposite types are least consistent
_HEXAGON_ADJACENCY = {
    "R": {"I", "C"},
    "I": {"R", "A"},
    "A": {"I", "S"},
    "S": {"A", "E"},
    "E": {"S", "C"},
    "C": {"E", "R"},
}


def _holland_consistency(holland_code: str) -> str:
    """根据三码在六边形上的相邻关系，返回动态一致性提示（中英双语）。"""
    letters = [l.upper() for l in holland_code if l.upper() in _HEXAGON_ADJACENCY]
    if len(letters) < 3:
        return "Holland 代码不完整，无法评估一致性。/ Holland code is incomplete."

    first, second, third = letters[0], letters[1], letters[2]
    adjacent_pairs = sum(
        1 for a, b in [(first, second), (second, third), (first, third)]
        if b in _HEXAGON_ADJACENCY.get(a, set())
    )

    if adjacent_pairs >= 2:
        return (
            "三码在六边形上相对集中，兴趣轮廓较为清晰。/ "
            "Your three-letter code is relatively consistent on the hexagon."
        )
    elif adjacent_pairs == 1:
        return (
            "三码在六边形上有一定跨度，兴趣范围较广，可重点关注能将多面向结合的方向。/ "
            "Your three-letter code spans a moderate range on the hexagon; consider directions that integrate multiple interests."
        )
    else:
        return (
            "三码在六边形上跨度较大，兴趣可能较为多元，建议通过具体体验进一步澄清主次偏好。/ "
            "Your three-letter code spans widely on the hexagon; your interests may be diverse. Clarify priorities through hands-on exploration."
        )


def _build_appendix_html(
    holland_scores: Dict[str, int],
    holland_code: str,
    top10_details: List[Dict[str, Any]],
    gallup_domain: str,
) -> str:
    # RIASEC profile
    score_rows = ""
    pairs = [("R", "现实型", "Realistic"), ("I", "研究型", "Investigative"),
             ("A", "艺术型", "Artistic"), ("S", "社会型", "Social"),
             ("E", "企业型", "Enterprising"), ("C", "常规型", "Conventional")]
    for i in range(0, 6, 2):
        l1, n1, e1 = pairs[i]
        l2, n2, e2 = pairs[i+1]
        s1 = holland_scores.get(l1, 0)
        s2 = holland_scores.get(l2, 0)
        score_rows += f"""
        <tr>
          <td>{l1} {n1} / {e1}</td><td>{s1}</td>
          <td>{l2} {n2} / {e2}</td><td>{s2}</td>
        </tr>"""

    scores_list = [holland_scores.get(k, 0) for k in ["R", "I", "A", "S", "E", "C"]]
    diff = max(scores_list) - min(scores_list) if scores_list else 0

    # Theme narrative
    narrative = ""
    def _bilingual_block(label: str, zh: str, en: str) -> str:
        html = f"<p><strong>{label}</strong>"
        if zh:
            html += f"：{_escape_html(zh)}"
        if en:
            if zh:
                html += "<br>"
            html += f"<span class='kz-en'>{_escape_html(en)}</span>"
        html += "</p>"
        return html

    for t in top10_details:
        narrative += f"""
        <h4>{_escape_html(t['theme'])} / {_escape_html(t['theme_en'])}（{_escape_html(t['domain'])} / {DOMAIN_ZH_TO_EN.get(t['domain'], t['domain'])}）</h4>
        {_bilingual_block('标准定义 / Standard Definition', t.get('definition_zh', ''), t.get('definition_en', ''))}
        {_bilingual_block('特征 / Feature', t.get('feature_zh', ''), t.get('feature_en', ''))}
        {_bilingual_block('应用 / Application', t.get('application_zh', ''), t.get('application_en', ''))}
        {_bilingual_block('盲点 / Blind Spots', t.get('blind_spots_zh', ''), t.get('blind_spots_en', ''))}
        <hr style="border:0;border-top:1px solid #e5e7eb;margin:16px 0;">
        """

    domain_en = _domain_en(gallup_domain)
    leading_count = sum(1 for t in top10_details if _domain_en(t['domain']) == domain_en) if gallup_domain else 0

    return f"""
<h2>附录：专业版解读 | Appendix: Professional Interpretation</h2>
<h3>A. RIASEC 剖面 | RIASEC Profile</h3>
<table>
  <tr><th>类型 / Type</th><th>得分 / Score</th><th>类型 / Type</th><th>得分 / Score</th></tr>
  {score_rows}
</table>
<ul class="kz-list">
  <li><strong>三码 / Code</strong>：{holland_code or '未指定 / Not specified'}</li>
  <li><strong>区分度提示 / Differentiation Note</strong>：最高与最低分相差 {diff} 分，兴趣轮廓{('清晰' if diff >= 30 else '较为平缓')}。</li>
  <li><span class="kz-en"><strong>Differentiation Note</strong>：The gap between highest and lowest scores is {diff}; your interest profile is {('well-differentiated' if diff >= 30 else 'relatively flat')}.</span></li>
</ul>

<h3>B. 主题叙事 | Theme Narrative</h3>
<div class="kz-info">
  <strong>说明 / Note</strong>：以下主题叙事已提供中英双语对照：中文翻译优先保留本土教练式表达，英文保留 Gallup CliftonStrengths 原有表述风格。每个主题依次列出标准定义、特征、应用建议与盲点。
  <br><span class="kz-en">The theme narratives below are presented in bilingual format: Chinese translations retain a local coaching style, while English preserves the original Gallup CliftonStrengths tone. Each theme includes its standard definition, feature, application tips, and blind spots.</span>
</div>
{narrative}
<p><strong>主导领域分析 / Leading Domain Analysis</strong>：Top 10 中 {_escape_html(gallup_domain or '未指定')} / {domain_en} 领域占 {leading_count} 项，说明该生在行动方式上偏向 <strong>{_strength_style(domain_en) if gallup_domain else '未指定 / Not specified'}</strong>。</p>
<p class="kz-en"><em>In your Top 10, {domain_en} accounts for {leading_count} themes, indicating a natural tendency toward {_strength_style(domain_en).split(' / ')[1] if gallup_domain and ' / ' in _strength_style(domain_en) else domain_en}.</em></p>

<h3>C. 伦理与边界声明 | Ethics & Boundaries</h3>
<ul class="kz-list">
  <li>本报告基于理论推导与模拟数据，未经过实证验证，仅用于职业探索参考。/ <span class="kz-en">This report is based on theoretical integration and simulated data, not empirically validated. It is for career exploration reference only.</span></li>
  <li>不用于选拔、分班、评奖等高利害决策。/ <span class="kz-en">Not for high-stakes decisions such as selection, placement, or awards.</span></li>
  <li>不替代专业心理咨询或临床评估。/ <span class="kz-en">Not a substitute for professional psychological counseling or clinical assessment.</span></li>
  <li>职业建议仅为可能性探索，需结合能力、价值观、市场需求综合判断。/ <span class="kz-en">Career suggestions are possibilities to explore; final decisions require integrating ability, values, and market demand.</span></li>
</ul>
"""


# ---------------------------------------------------------------------------
# 职业推荐与张力分析（保持原有逻辑不变）
# ---------------------------------------------------------------------------

def _career_match_score(career, code_letter: str, gallup_domain_en: str, evidence_bonus: Dict[str, int]) -> int:
    """为单个职业按指定 Holland 字母计算匹配分。"""
    score = 0
    if career.riasec_primary == code_letter:
        score += 10
    if gallup_domain_en and career.cs_domain == gallup_domain_en:
        score += 2
    score += evidence_bonus.get(career.evidence_level or "D", 0)
    return score


def get_career_recommendations(
    db: Session,
    holland_code: str,
    cs_domain: str,
    limit: int = 8
) -> List[Dict[str, Any]]:
    """
    以 Holland 三字母代码为核心，尽可能扩大职业映射范围：
    - 主码、次码、第三码分别取一定数量的候选，避免全部被主码占据；
    - Gallup 优势领域仅作为排序修正（+2 分），不用于过滤；
    - 证据等级高的职业额外加分，优先展示；
    - 按职业名去重，避免同一职业在多个层级重复出现。
    """
    domain_en = {
        "执行力": "Executing",
        "影响力": "Influencing",
        "关系建立": "Relationship Building",
        "战略思维": "Strategic Thinking",
    }
    evidence_bonus = {"A": 3, "B": 2, "C": 1, "D": 0}
    gallup_domain_en = domain_en.get(cs_domain, cs_domain)

    code_letters = list(holland_code.upper()) if holland_code else []
    # 每个 Holland 字母取前 N 个，保证三码都有机会出现；主码不过度挤占
    per_letter_limits = [3, 3, 2][:len(code_letters)] if code_letters else []

    selected = {}  # id -> (score, career)
    for letter, cap in zip(code_letters, per_letter_limits):
        rows = db.query(models.CareerMajorMapping).filter(
            models.CareerMajorMapping.riasec_primary == letter
        ).all()
        scored = sorted(
            [(_career_match_score(r, letter, gallup_domain_en, evidence_bonus), r) for r in rows],
            key=lambda x: -x[0]
        )
        for score, r in scored[:cap]:
            if r.id not in selected or selected[r.id][0] < score:
                selected[r.id] = (score, r)

    # 按匹配分排序，返回前 limit 个；同时按职业名去重
    ranked = sorted(selected.values(), key=lambda x: -x[0])
    seen_names = set()
    deduped = []
    for score, r in ranked:
        if r.career_name not in seen_names:
            seen_names.add(r.career_name)
            deduped.append((score, r))

    return [{
        "career_name": r.career_name,
        "description": r.description,
        "related_majors": r.related_majors,
        "evidence_level": r.evidence_level,
        "riasec_primary": r.riasec_primary,
        "cs_domain": r.cs_domain,
        "match_score": score,
        "career_tag": r.career_tag,
    } for score, r in deduped[:limit]]


def analyze_tension(holland_code: str, gallup_domain: str) -> str:
    """
    Tension analysis considering all three RIASEC letters, not just the first.
    基于 RIASEC 三码与 Gallup 领域的映射关系，生成中英双语张力说明。
    """
    letter_to_domain = {
        "R": "Executing",
        "I": "Strategic Thinking",
        "A": "Strategic Thinking",
        "S": "Relationship Building",
        "E": "Influencing",
        "C": "Executing",
    }
    domain_en = {
        "执行力": "Executing",
        "影响力": "Influencing",
        "关系建立": "Relationship Building",
        "战略思维": "Strategic Thinking",
    }
    actual = domain_en.get(gallup_domain, gallup_domain)
    letters = [l.upper() for l in holland_code if l.upper() in letter_to_domain]
    expected_list = [letter_to_domain[l] for l in letters]

    if not letters:
        return (
            "缺少 Holland 代码，无法评估兴趣与优势的张力。/ "
            "Holland code is missing; cannot assess interest-strength tension."
        )

    if actual in expected_list:
        primary = letters[expected_list.index(actual)]
        return (
            f"你的 Gallup 主导领域（{gallup_domain}）与 Holland 三码中的 {primary} 型高度一致，"
            f"说明你在相关方向上拥有内外双重能量支撑。"
            f" / Your leading Gallup domain ({gallup_domain}) aligns strongly with the {primary} type in your Holland code, "
            f"giving you both internal motivation and natural ability in related directions."
        )

    # Check if actual is in the same quadrant group as any expected domain
    task_domains = {"Executing", "Strategic Thinking"}
    people_domains = {"Relationship Building", "Influencing"}
    if (actual in task_domains and any(d in task_domains for d in expected_list)) or \
       (actual in people_domains and any(d in people_domains for d in expected_list)):
        return (
            f"你的优势领域（{gallup_domain}）与 Holland 兴趣舞台（{holland_code}）偏向不同但可互补，"
            f"建议关注能将两者结合的职业路径。"
            f" / Your strength domain ({gallup_domain}) and interest stage ({holland_code}) differ but can complement each other. "
            f"Look for career paths that integrate both."
        )

    return (
        f"你的优势领域（{gallup_domain}）与 Holland 兴趣舞台（{holland_code}）存在一定张力，"
        f"建议通过具体项目体验来验证真实偏好，避免过早定性。"
        f" / Your strength domain ({gallup_domain}) and interest stage ({holland_code}) show some tension. "
        f"Validate your real preferences through concrete projects before committing too early."
    )
