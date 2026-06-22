from typing import Dict, List
from collections import Counter

HOLLAND_TYPES = ["R", "I", "A", "S", "E", "C"]


def calculate_holland(answers: List[Dict[str, int]], question_map: Dict[int, List[str]] = None) -> Dict:
    """
    answers: list of {question_num: int, score: int 1-5}
    question_map: optional dict of question_num -> [holland_type] from DB theme_tags.
                  If provided, scores are aggregated by theme_tags (more robust than
                  relying on fixed question order). Falls back to fixed order if map
                  is missing or a question has no theme_tags.
    """
    scores = {t: 0 for t in HOLLAND_TYPES}
    used_fallback = False

    for ans in answers:
        qn = ans["question_num"]
        score = ans["score"]
        types_from_map = question_map.get(qn, []) if question_map else []
        # Support either single-letter tags like ["R"] or legacy multi-type tags
        htypes = [t.upper() for t in types_from_map if t.upper() in HOLLAND_TYPES]
        if not htypes:
            # Fallback to fixed order R1..R10, I1..I10, ...
            type_index = (qn - 1) // 10
            if 0 <= type_index < 6:
                htypes = [HOLLAND_TYPES[type_index]]
                used_fallback = True
        for htype in htypes:
            scores[htype] += score

    sorted_types = sorted(scores.items(), key=lambda x: (-x[1], HOLLAND_TYPES.index(x[0])))
    code = "".join([t for t, _ in sorted_types[:3]])

    # Data quality: differentiation between highest and lowest score
    score_values = list(scores.values())
    differentiation = max(score_values) - min(score_values) if score_values else 0
    is_flat = differentiation <= 10  # 60-point scale; <=10 means very flat profile

    return {
        "scores": scores,
        "code": code,
        "sorted": sorted_types,
        "differentiation": differentiation,
        "is_flat": is_flat,
        "used_fallback": used_fallback,
    }


def get_type_description(holland_type: str) -> Dict[str, str]:
    descriptions = {
        "R": {"name": "现实型", "en": "Realistic", "env": "户外、车间、实验室", "feature": "动手操作、技术实践、解决具体问题"},
        "I": {"name": "研究型", "en": "Investigative", "env": "图书馆、实验室、研究室", "feature": "分析研究、探索原理、独立思考"},
        "A": {"name": "艺术型", "en": "Artistic", "env": "工作室、舞台、创作空间", "feature": "创意表达、原创设计、自由灵活"},
        "S": {"name": "社会型", "en": "Social", "env": "教室、诊所、咨询室", "feature": "帮助他人、人际互动、教学辅导"},
        "E": {"name": "企业型", "en": "Enterprising", "env": "办公室、商场、会议室", "feature": "领导影响、说服他人、商业成就"},
        "C": {"name": "常规型", "en": "Conventional", "env": "办公室、数据中心、档案室", "feature": "秩序规则、数据处理、稳定可靠"},
    }
    return descriptions.get(holland_type, {})
