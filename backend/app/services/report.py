from typing import List, Dict, Any
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

def _build_data_quality_notes(holland_quality: Dict[str, Any] = None, gallup_coverage: Dict[str, Any] = None) -> List[str]:
    """根据 Holland 区分度与 Gallup B 侧覆盖率生成数据质量提示。"""
    notes = []

    if holland_quality and holland_quality.get("is_flat"):
        notes.append(
            "你的 Holland 得分区分度较低（各类型分数接近），三码可能不能清晰代表你的兴趣偏好，建议结合日常经历进一步验证。/ "
            "Your Holland scores show low differentiation (types are close together), so the three-letter code may not clearly represent your interests. Validate against your daily experiences."
        )

    if gallup_coverage:
        b_ratio = gallup_coverage.get("b_side_ratio", 0)
        if b_ratio < 0.5:
            notes.append(
                f"当前 Gallup 测评的 B 侧主题映射覆盖率为 {b_ratio*100:.1f}%，B 侧陈述对才干计分的贡献有限，优势结果主要反映 A 侧偏好，请谨慎解读。/ "
                f"The current Gallup B-side theme mapping coverage is {b_ratio*100:.1f}%, so B-side statements contribute little to theme scoring. Strengths results mainly reflect A-side preferences; interpret cautiously."
            )
        elif b_ratio < 0.8:
            notes.append(
                f"当前 Gallup 测评的 B 侧主题映射覆盖率为 {b_ratio*100:.1f}%，优势结果基本可用，但部分反向陈述未参与计分。/ "
                f"The current Gallup B-side theme mapping coverage is {b_ratio*100:.1f}%. Strengths results are usable, but some reverse statements are not yet scored."
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
    status = assessment.status or {}
    gallup_coverage = status.get("gallup_coverage")
    holland_quality = status.get("holland_quality")

    # Career recommendations (student version: 3-5 directions)
    careers = get_career_recommendations(db, holland_code, gallup_domain, limit=5)

    # Data quality notes
    data_quality_notes = _build_data_quality_notes(holland_quality, gallup_coverage)

    # Actions (personalized based on Holland code and Gallup domain)
    actions = _build_personalized_actions(holland_code, gallup_domain)

    report_html = _build_student_html(
        student_name=student_name,
        holland_code=holland_code,
        holland_scores=holland_scores,
        gallup_domain=gallup_domain,
        careers=careers,
        actions=actions,
        data_quality_notes=data_quality_notes,
    )

    return {
        "student_name": student_name,
        "holland_code": holland_code,
        "holland_scores": holland_scores,
        "gallup_top5": gallup_top5,
        "gallup_domain": gallup_domain,
        "careers": careers,
        "actions": actions,
        "report_html": report_html,
        "data_quality_notes": data_quality_notes,
        "gallup_coverage": gallup_coverage,
        "holland_quality": holland_quality,
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

    top5_details = []
    for theme in gallup_top5:
        desc = db.query(models.ThemeDescription).filter(
            models.ThemeDescription.theme_name == theme
        ).first()
        top5_details.append({
            "theme": theme,
            "theme_en": desc.theme_name_en if desc else "",
            "domain": desc.domain if desc else "",
            "definition": desc.standard_definition if desc else "",
            "feature": desc.feature if desc else "",
            "application": desc.application if desc else "",
            "blind_spots": desc.blind_spots if desc else "",
        })

    # Domain distribution from top5
    domain_distribution = {}
    for d in top5_details:
        domain_distribution[d["domain"]] = domain_distribution.get(d["domain"], 0) + 1

    # Tension
    tension = analyze_tension(holland_code, gallup_domain)

    careers = get_career_recommendations(db, holland_code, gallup_domain)

    status = assessment.status or {}
    gallup_coverage = status.get("gallup_coverage")
    holland_quality = status.get("holland_quality")
    data_quality_notes = _build_data_quality_notes(holland_quality, gallup_coverage)

    report_html = _build_professional_html(
        db=db,
        student_name=student_name,
        holland_code=holland_code,
        holland_scores=holland_scores,
        gallup_domain=gallup_domain,
        gallup_secondary_domain=gallup_secondary_domain,
        domain_distribution=domain_distribution,
        top5_details=top5_details,
        gallup_top10=gallup_top10,
        tension=tension,
        careers=careers,
        data_quality_notes=data_quality_notes,
    )

    return {
        "student_name": student_name,
        "holland_scores": holland_scores,
        "holland_code": holland_code,
        "gallup_top5": top5_details,
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
.kz-report table { width: 100%; border-collapse: collapse; margin: 14px 0; font-size: 14px; }
.kz-report th, .kz-report td { border: 1px solid #e5e7eb; padding: 10px 12px; text-align: left; vertical-align: top; }
.kz-report th { background: #f3f4f6; font-weight: 600; color: #374151; }
.kz-report tr:nth-child(even) { background: #f9fafb; }
.kz-report .kz-tag { display: inline-block; padding: 3px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; margin-left: 6px; }
.kz-report .kz-tag-steady { background: #d1fae5; color: #065f46; }
.kz-report .kz-tag-explore { background: #fef3c7; color: #92400e; }
.kz-report .kz-tag-challenge { background: #fee2e2; color: #991b1b; }
.kz-report .kz-matrix-dominant { background: #dbeafe; font-weight: 700; }
.kz-report .kz-matrix-secondary { background: #fef3c7; }
.kz-report .kz-matrix-tertiary { background: #f3f4f6; }
.kz-report .kz-matrix-header { background: #1e40af; color: #fff; font-weight: 600; }
.kz-report .kz-small { color: #6b7280; font-size: 13px; }
.kz-report .kz-en { color: #6b7280; font-style: italic; }
.kz-report ul.kz-list { padding-left: 22px; }
.kz-report ul.kz-list li { margin: 8px 0; }
.kz-report .kz-answer-line { display: inline-block; min-width: 160px; border-bottom: 1px solid #9ca3af; }
.kz-report .kz-stage-badge { display: inline-block; padding: 2px 10px; border-radius: 12px; background: #ede9fe; color: #5b21b6; font-size: 13px; font-weight: 600; }
.kz-report .kz-print-header { display: flex; justify-content: space-between; align-items: center; gap: 16px; }
.kz-report .kz-print-btn { background: #2563eb; color: #fff; padding: 8px 16px; border-radius: 6px; font-size: 14px; cursor: pointer; border: none; }
.kz-report .kz-print-btn:hover { background: #1d4ed8; }
@media print {
  .kz-report .kz-print-btn { display: none; }
  .kz-report { max-width: 100%; }
  .kz-report h2 { page-break-after: avoid; }
  .kz-report table { page-break-inside: avoid; }
  .kz-report .kz-card, .kz-report .kz-highlight, .kz-report .kz-tip, .kz-report .kz-warning { page-break-inside: avoid; }
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


def _build_cross_matrix(db: Session, holland_code: str, gallup_domain: str) -> Dict[str, Dict[str, List[str]]]:
    """构建 6×4 兴趣×优势交叉矩阵。返回 matrix[riasec][domain_en] = [职业名, ...]。"""
    rows = db.query(models.CareerMajorMapping).all()
    matrix = {r: {d: [] for d in DOMAIN_ZH_TO_EN.values()} for r in ["R", "I", "A", "S", "E", "C"]}
    for r in rows:
        ri = (r.riasec_primary or "").upper()
        cs = r.cs_domain or ""
        if ri in matrix and cs in matrix[ri]:
            matrix[ri][cs].append(r.career_name)
    return matrix


def _matrix_marker(
    ri: str,
    domain_en: str,
    holland_code: str,
    gallup_domain: str,
    gallup_secondary_domain: str = "",
) -> tuple:
    """返回单元格的标记（css 类，前缀符号）。

    使用真正的 Gallup 主要优势领域与次要优势领域，而不是把所有非主导领域都视为次要。
    """
    if not holland_code:
        return "", ""
    first = holland_code[0].upper()
    second = holland_code[1].upper() if len(holland_code) > 1 else ""
    third = holland_code[2].upper() if len(holland_code) > 2 else ""

    leading = _domain_en(gallup_domain)
    secondary = _domain_en(gallup_secondary_domain)

    # 主导交叉象限：Holland 第一码 × 主导优势领域
    if ri == first and domain_en == leading:
        return "kz-matrix-dominant", ""
    # 次要交叉象限：Holland 第二码 × 主导优势领域，或 Holland 第一码 × 次要优势领域
    if (ri == second and domain_en == leading) or (ri == first and domain_en == secondary):
        return "kz-matrix-secondary", "⭐ "
    # 第三码相关象限：Holland 第三码 × 主导优势领域
    if ri == third and domain_en == leading:
        return "kz-matrix-tertiary", "○ "
    return "", ""


def _build_student_html(
    student_name: str,
    holland_code: str,
    holland_scores: Dict[str, int],
    gallup_domain: str,
    careers: List[Dict[str, Any]],
    actions: List[str],
    data_quality_notes: List[str],
) -> str:
    safe = _safe_entry_points(careers)
    major_tiers = _build_major_tiers(careers)
    core_majors = major_tiers["core"]

    holland_result = f"<strong>{holland_code}</strong> — {_type_name(holland_code[0]) if holland_code else '未指定 / Not specified'}" if holland_code else "未指定 / Not specified"
    domain_en = _domain_en(gallup_domain)
    style = _strength_style(domain_en) if gallup_domain else "未指定 / Not specified"

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

    return f"""
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

<div class="kz-warning">
  <strong>数据质量提示 / Data Quality Notes</strong>
  <ul class="kz-list">
    {quality_items}
  </ul>
</div>

<h2>1. 我的核心结果 | My Core Results</h2>
<table>
  <tr><th>维度 / Dimension</th><th>结果 / Result</th></tr>
  <tr><td>Holland 三码 / Holland Code</td><td>{holland_result}</td></tr>
  <tr><td>优势领域 / Leading Strength Domain</td><td>{_escape_html(gallup_domain or '未指定 / Not specified')}</td></tr>
  <tr><td>优势风格 / Strengths Style</td><td>{_escape_html(style)}</td></tr>
</table>

<h2>2. 稳妥入口职业 | Safe Entry Points</h2>
<p>如果你更关注就业稳定性和现实可行性，以下方向是不错的起点。</p>
<p class="kz-en">If you prioritize employment stability and practical entry paths, these roles are good starting points.</p>
<table>
  <tr><th>职业 / Career</th><th>标签 / Tag</th><th>相关专业 / Related Majors</th></tr>
  {safe_rows if safe_rows else '<tr><td colspan="3">暂无 / None</td></tr>'}
</table>

<h2>3. 核心推荐专业 | Core Recommended Majors</h2>
<table>
  <tr><th>专业 / Major</th><th>国内可报说明 / Domestic Note</th><th>海外方向（以英国为例）/ Overseas Example (UK)</th></tr>
  {major_rows}
</table>

<h2>4. 三个下一步行动 | Three Next Steps</h2>
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
    top5_details: List[Dict[str, Any]],
    gallup_top10: List[str],
    tension: str,
    careers: List[Dict[str, Any]],
    data_quality_notes: List[str],
) -> str:
    safe = _safe_entry_points(careers)
    major_tiers = _build_major_tiers(careers)
    career_tiers = _build_career_tiers(careers, holland_code, gallup_domain)
    matrix = _build_cross_matrix(db, holland_code, gallup_domain)

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
<h2>一、我的兴趣舞台 | My Interest Stage</h2>
<p>你的 Holland 三码是 <strong>{holland_code}</strong>，三个字母分别代表你最感兴趣、次感兴趣和第三感兴趣的工作舞台。</p>
<p class="kz-en">Your Holland code is <strong>{holland_code}</strong>. The three letters represent your strongest, second-strongest, and third-strongest areas of work interest.</p>
<table>
  <tr><th>排名 / Rank</th><th>类型 / Type</th><th>舞台标签 / Stage Tag</th><th>含义 / Meaning</th></tr>
  {interest_stage_rows}
</table>
"""

    # 3. Strengths style
    top5_rows = ""
    for idx, t in enumerate(top5_details, 1):
        top5_rows += f"""
        <tr>
          <td>{idx}</td>
          <td>{_escape_html(t['theme'])} / {_escape_html(t['theme_en'])}</td>
          <td>{_escape_html(t['domain'])} / {DOMAIN_ZH_TO_EN.get(t['domain'], t['domain'])}</td>
          <td>{_escape_html(t['definition'][:120] if t['definition'] else '')}</td>
        </tr>"""

    domain_dist_items = ""
    for d, count in sorted(domain_distribution.items(), key=lambda x: -x[1]):
        domain_dist_items += f"<li>{_escape_html(d)} / {DOMAIN_ZH_TO_EN.get(d, d)}：{count}</li>"

    strengths_section = f"""
<h2>二、我的优势风格 | My Strengths Style</h2>
<p>你的 Gallup CliftonStrengths Top 10 主题按排名加权后，<strong>{_escape_html(gallup_domain or '未指定')}</strong> 领域得分最高，是最能代表你稳定工作方式的领域；<strong>{_escape_html(gallup_secondary_domain or '未指定')}</strong> 为次要领域。这意味着你最自然的工作方式是 <strong>{_escape_html(strength_style)}</strong>。</p>
<p class="kz-en">When your Gallup CliftonStrengths Top 10 themes are weighted by rank, <strong>{domain_en}</strong> scores highest as your leading domain and <strong>{secondary_domain_en}</strong> is your secondary domain. Your most natural way of working is as an <strong>{_strength_style(domain_en).split(' / ')[1] if ' / ' in _strength_style(domain_en) else domain_en}</strong>.</p>
<div class="kz-card">
  <p><strong>{_escape_html(gallup_domain or '未指定')} / {domain_en}</strong>：{_escape_html(_domain_description(domain_en))}</p>
</div>
<h3>Top 5 才干主题 | Your Top 5 Themes</h3>
<table>
  <tr><th>排名 / Rank</th><th>主题 / Theme</th><th>领域 / Domain</th><th>一句话定义 / One-Liner</th></tr>
  {top5_rows}
</table>
<p><strong>领域分布 / Domain Distribution</strong>：</p>
<ul class="kz-list">
  {domain_dist_items}
</ul>
"""

    # 4. Cross-matrix
    matrix_html = _build_matrix_html(matrix, holland_code, gallup_domain, gallup_secondary_domain)
    cross_section = f"""
<h2>三、兴趣 × 优势交叉矩阵 | Interest × Strengths Cross-Matrix</h2>
<p>下方矩阵展示了 6 种 RIASEC 兴趣类型与 4 大 CliftonStrengths 优势领域的交叉组合。标注规则：</p>
<ul class="kz-list">
  <li><strong>粗体 / Bold</strong> = 你的主导交叉象限（Holland 第一码 × 主导优势领域）</li>
  <li>⭐ = 你的次要交叉象限（Holland 第二码 × 主导优势领域，或 Holland 第一码 × 次要优势领域）</li>
  <li>○ = 你的第三码相关象限（Holland 第三码 × 主导优势领域）</li>
</ul>
<p class="kz-en"><em>Bold = dominant intersection (1st Holland letter × leading domain); ⭐ = secondary intersection (2nd Holland letter × leading domain, or 1st Holland letter × secondary domain); ○ = tertiary-code related intersection (3rd Holland letter × leading domain).</em></p>
{matrix_html}
<p><strong>你的交叉点 / Your Intersection</strong>：{_type_name(dominant_type) if dominant_type else '未指定'} × {_escape_html(gallup_domain or '未指定')} / {dominant_type_name.split('（')[1].replace('）','') if '（' in dominant_type_name else dominant_type} × {domain_en}</p>
<p><strong>次要交叉点 / Secondary Intersection</strong>：{_type_name(dominant_type) if dominant_type else '未指定'} × {_escape_html(gallup_secondary_domain or '未指定')} / {dominant_type_name.split('（')[1].replace('）','') if '（' in dominant_type_name else dominant_type} × {secondary_domain_en}</p>
"""

    # 5. Recommended majors
    majors_section = _build_majors_html(major_tiers)

    # 6. Career paths
    careers_section = _build_career_tiers_html(career_tiers)

    # 7. Employment market placeholder
    market_section = _build_market_html()

    # 8. Evidence levels
    evidence_section = _build_evidence_html()

    # 9. Integration
    consistency_text = _holland_consistency(holland_code)
    integration_section = f"""
<h2>八、兴趣-优势整合分析 | Interest-Strengths Integration</h2>
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

    # 10. Action tracking
    action_section = _build_action_html()

    # 11. Next steps
    next_steps = """
<h2>十、下一步行动 | Next Steps</h2>
<ol class="kz-list">
  <li><strong>阅读学生一页纸摘要 / Read student one-pager</strong>：快速抓住核心结论。</li>
  <li><strong>选择 1-2 个稳妥入口职业 / Pick 1-2 safe entry points</strong>：在招聘网站查找真实岗位描述。</li>
  <li><strong>了解 2-3 个核心专业 / Explore 2-3 core majors</strong>：查看目标院校的国内招生目录或海外 Programme 页面。</li>
  <li><strong>完成一次职业访谈 / Do one career interview</strong>：记录到「行动跟踪模块」。</li>
  <li><strong>与测评师讨论 / Discuss with a counselor</strong>：带着报告参加一对一职业咨询。</li>
</ol>
"""

    # Appendix
    appendix = _build_appendix_html(holland_scores, holland_code, top5_details, gallup_domain)

    quality_items = ""
    for note in data_quality_notes:
        quality_items += f"<li>{_escape_html(note)}</li>"

    return f"""
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

<div class="kz-warning">
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
{market_section}
{evidence_section}
{integration_section}
{action_section}
{next_steps}
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


def _build_matrix_html(
    matrix: Dict[str, Dict[str, List[str]]],
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
            cell_careers = matrix.get(ri, {}).get(dom, [])[:4]
            cell_text = "、".join(cell_careers) if cell_careers else "—"
            row += f'<td class="{cls}">{prefix}{_escape_html(cell_text)}</td>'
        rows += f"<tr>{row}</tr>"
    return f"<table>{header}{rows}</table>"


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
<h2>四、推荐申请专业 | Recommended Majors</h2>
<p>以下专业根据推荐职业路径分层整理。<strong>核心专业</strong>建议优先了解；<strong>拓展专业</strong>可作为备选或第二专业方向；<strong>可关注专业</strong>适合作为长期兴趣跟踪。</p>
<p class="kz-en"><em>Majors are organized by priority. <strong>Core</strong> majors are the top priorities; <strong>Expand</strong> majors are alternatives or second-field options; <strong>Watch</strong> majors are for long-term interest tracking.</em></p>

<h3>4.1 核心专业 | Core Majors</h3>
<table>
  <tr><th>专业 / Major</th><th>国内可报说明 / Domestic Note</th><th>海外方向（以英国为例）/ Overseas Example (UK)</th></tr>
  {_major_table_rows(major_tiers['core'])}
</table>

<h3>4.2 拓展专业 | Expand Majors</h3>
<table>
  <tr><th>专业 / Major</th><th>国内可报说明 / Domestic Note</th><th>海外方向（以英国为例）/ Overseas Example (UK)</th></tr>
  {_major_table_rows(major_tiers['expand'])}
</table>

<h3>4.3 可关注专业 | Watch Majors</h3>
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
<h2>五、推荐职业路径 | Recommended Career Paths</h2>
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

<h3>5.1 高适配路径 | High Fit</h3>
<table>
  <tr><th>职业 / Career</th><th>标签 / Tag</th><th>主要工作 / What They Do</th><th>相关专业 / Related Majors</th></tr>
  {_career_table_rows(career_tiers['high'], mode='fit')}
</table>

<h3>5.2 中适配路径 | Moderate Fit</h3>
<table>
  <tr><th>职业 / Career</th><th>标签 / Tag</th><th>主要工作 / What They Do</th><th>相关专业 / Related Majors</th></tr>
  {_career_table_rows(career_tiers['moderate'], mode='fit')}
</table>

<h3>5.3 就业友好备选 | Employment-Friendly Alternatives</h3>
<table>
  <tr><th>职业 / Career</th><th>标签 / Tag</th><th>为何作为备选 / Why This Alternative</th><th>相关专业 / Related Majors</th></tr>
  {_career_table_rows(career_tiers['alternative'])}
</table>
"""


def _build_market_html() -> str:
    return """
<h2>六、就业市场参考 | Employment Market Reference</h2>
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
<h2>七、证据等级说明与科学性建设 | Evidence Levels & Scientific Roadmap</h2>
<h3>7.1 当前证据等级定义 | Current Evidence Level Definitions</h3>
<table>
  <tr><th>等级 / Level</th><th>含义 / Meaning</th><th>当前应用情况 / Current Application</th></tr>
  <tr><td><strong>A</strong></td><td>大样本实证研究或长期追踪数据支持</td><td>当前暂无，需通过用户毕业去向追踪积累</td></tr>
  <tr><td><strong>B</strong></td><td>小样本研究、专家评审或行业调研支持</td><td>当前暂无，可通过行业专家访谈与毕业生反馈逐步建立</td></tr>
  <tr><td><strong>C</strong></td><td>理论推导与现有文献综述支持</td><td>当前大部分职业-专业映射属于此等级</td></tr>
  <tr><td><strong>D</strong></td><td>基于个案经验或初步假设</td><td>少量映射属于此等级</td></tr>
</table>

<h3>7.2 如何积累 A/B 级证据 | How to Build A/B-Level Evidence</h3>
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
<h2>九、行动跟踪模块 | Action Tracking Module</h2>
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
    top5_details: List[Dict[str, Any]],
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
    for t in top5_details:
        narrative += f"""
        <h4>{_escape_html(t['theme'])} / {_escape_html(t['theme_en'])}（{_escape_html(t['domain'])} / {DOMAIN_ZH_TO_EN.get(t['domain'], t['domain'])}）</h4>
        <p><strong>标准定义 / Standard Definition</strong>：{_escape_html(t['definition'] or '')}</p>
        <p><strong>特征 / Feature</strong>：{_escape_html(t['feature'] or '')}</p>
        <p><strong>应用 / Application</strong>：{_escape_html(t['application'] or '')}</p>
        <p><strong>盲点 / Blind Spots</strong>：{_escape_html(t['blind_spots'] or '')}</p>
        <hr style="border:0;border-top:1px solid #e5e7eb;margin:16px 0;">
        """

    domain_en = _domain_en(gallup_domain)
    leading_count = sum(1 for t in top5_details if _domain_en(t['domain']) == domain_en) if gallup_domain else 0

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
<div class="kz-warning">
  <strong>说明 / Note</strong>：以下主题详细描述中的“标准定义”已提供中文，“特征 / Feature”“应用 / Application”“盲点 / Blind Spots” 目前仍为英文素材。我们已经为每个主题补充了双语一句话定义（见 Top 5 表格），并会在后续版本中完成全部 narrative 的标准化翻译。如果你现在需要中文解读，建议优先参考 Top 5 表格中的一句话定义。
  <br><span class="kz-en">The "Standard Definition" below is in Chinese, while Feature / Application / Blind Spots remain in English source material. A bilingual one-liner has been added for each theme (see Top 5 table), and full narrative translation will be standardized in a future release. For Chinese interpretation now, prioritize the one-liner definitions in the Top 5 table.</span>
</div>
{narrative}
<p><strong>主导领域分析 / Leading Domain Analysis</strong>：Top 5 中 {_escape_html(gallup_domain or '未指定')} / {domain_en} 领域占 {leading_count} 项，说明该生在行动方式上偏向 <strong>{_strength_style(domain_en) if gallup_domain else '未指定 / Not specified'}</strong>。</p>
<p class="kz-en"><em>In your Top 5, {domain_en} accounts for {leading_count} themes, indicating a natural tendency toward {_strength_style(domain_en).split(' / ')[1] if gallup_domain and ' / ' in _strength_style(domain_en) else domain_en}.</em></p>

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
