"""
响应质量检测 / Response Quality Detection

检测 Holland 与 Gallup 测评中疑似乱答、敷衍或规律性作答的模式，
不依赖前端时间戳，仅根据答案分布与序列特征判断。
"""
from __future__ import annotations

import math
from collections import Counter
from typing import Dict, List, Optional


def _shannon_entropy(values: List[int]) -> float:
    """计算离散序列的香农熵（以 2 为底，单位 bit）。"""
    if not values:
        return 0.0
    counter = Counter(values)
    total = len(values)
    entropy = 0.0
    for count in counter.values():
        if count == 0:
            continue
        p = count / total
        entropy -= p * math.log2(p)
    return entropy


def _max_run_length(values: List[int]) -> int:
    """计算最长连续相同值长度。"""
    if not values:
        return 0
    max_run = 1
    current = 1
    for i in range(1, len(values)):
        if values[i] == values[i - 1]:
            current += 1
            max_run = max(max_run, current)
        else:
            current = 1
    return max_run


def _alternating_ratio(values: List[int]) -> float:
    """
    检测 A-B-A-B 或 1-5-1-5 等严格交替模式占比。
    认为相邻三项中「前后相等且与中间不同」的模式为一次交替。
    """
    if len(values) < 3:
        return 0.0
    n = len(values) - 2
    alt = 0
    for i in range(n):
        a, b, c = values[i], values[i + 1], values[i + 2]
        # 形如 x, y, x 且 x != y
        if a == c and a != b:
            alt += 1
    return alt / n


def _stddev(values: List[int]) -> float:
    """计算样本标准差。"""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
    return math.sqrt(variance)


def evaluate_holland_quality(answers: List[Dict[str, int]]) -> Dict:
    """
    评估 Holland 测评作答质量。

    输入：list of {"question_num": int, "score": int 1-5}
    返回：{
        "score": float 0-1,
        "flags": List[str],
        "risk_level": "low" | "medium" | "high",
        "message_zh": str,
        "message_en": str,
        "details": Dict
    }
    """
    scores = [a["score"] for a in answers]
    if not scores:
        return _empty_result()

    counter = Counter(scores)
    total = len(scores)
    most_common_count = counter.most_common(1)[0][1]
    straight_line_ratio = most_common_count / total
    variance = _stddev(scores)
    alt_ratio = _alternating_ratio(scores)
    max_run = _max_run_length(scores)
    entropy = _shannon_entropy(scores)

    flags = []
    # 60 题 1-5 量表中，正常偏态 profile 也可能有 50% 左右落在同一分值；
    # 将阈值提高到 0.65，减少高 S/A 或低 R/I/C 等真实偏态轮廓的误报。
    if straight_line_ratio >= 0.65:
        flags.append("straight_line")
    if variance < 0.7:
        flags.append("low_variance")
    if alt_ratio >= 0.35 and entropy < 1.8:
        flags.append("alternating_pattern")
    if entropy < 1.2 and total >= 30:
        flags.append("low_entropy")
    if max_run >= 15:
        flags.append("long_run")

    score = _holland_score_from_flags(flags, variance, entropy)
    risk_level = _risk_level(score)
    message_zh, message_en = _holland_message(flags, score)

    return {
        "score": round(score, 2),
        "flags": flags,
        "risk_level": risk_level,
        "message_zh": message_zh,
        "message_en": message_en,
        "details": {
            "variance": round(variance, 3),
            "entropy": round(entropy, 3),
            "straight_line_ratio": round(straight_line_ratio, 3),
            "alternating_ratio": round(alt_ratio, 3),
            "max_run": max_run,
        },
    }


def evaluate_gallup_quality(answers: List[Dict[str, int]]) -> Dict:
    """
    评估 Gallup 测评作答质量。

    输入：list of {"question_num": int, "choice": int -2..2}
    返回：同 evaluate_holland_quality
    """
    choices = [a["choice"] for a in answers]
    if not choices:
        return _empty_result()

    total = len(choices)
    counter = Counter(choices)
    neutral_count = counter.get(0, 0)
    neutral_rate = neutral_count / total

    positive_count = sum(1 for c in choices if c > 0)
    negative_count = sum(1 for c in choices if c < 0)
    one_side_ratio = max(positive_count, negative_count) / total

    # 极端交替：-2 与 +2 相邻出现
    extreme_alternations = 0
    for i in range(1, len(choices)):
        pair = (choices[i - 1], choices[i])
        if sorted(pair) == [-2, 2]:
            extreme_alternations += 1
    extreme_alt_ratio = extreme_alternations / (total - 1) if total > 1 else 0.0

    entropy = _shannon_entropy(choices)
    max_run = _max_run_length(choices)
    alt_ratio = _alternating_ratio(choices)

    flags = []
    if neutral_rate >= 0.3:
        flags.append("neutral_rate")
    if one_side_ratio >= 0.8:
        flags.append("one_side_bias")
    if extreme_alt_ratio >= 0.25:
        flags.append("extreme_alternation")
    if entropy < 1.2 and total >= 100:
        flags.append("low_entropy")
    if max_run >= 15:
        flags.append("long_run")
    if alt_ratio >= 0.25:
        flags.append("alternating_pattern")

    score = _gallup_score_from_flags(flags, neutral_rate, one_side_ratio, extreme_alt_ratio, entropy)
    risk_level = _risk_level(score)
    message_zh, message_en = _gallup_message(flags, score)

    return {
        "score": round(score, 2),
        "flags": flags,
        "risk_level": risk_level,
        "message_zh": message_zh,
        "message_en": message_en,
        "details": {
            "entropy": round(entropy, 3),
            "neutral_rate": round(neutral_rate, 3),
            "one_side_ratio": round(one_side_ratio, 3),
            "extreme_alternation_ratio": round(extreme_alt_ratio, 3),
            "alternating_ratio": round(alt_ratio, 3),
            "max_run": max_run,
        },
    }


def _empty_result() -> Dict:
    return {
        "score": 0.0,
        "flags": [],
        "risk_level": "low",
        "message_zh": "未检测到作答数据。/ No answer data detected.",
        "message_en": "No answer data detected.",
        "details": {},
    }


def _risk_level(score: float) -> str:
    if score >= 0.75:
        return "low"
    if score >= 0.45:
        return "medium"
    return "high"


def _holland_score_from_flags(flags: List[str], variance: float, entropy: float) -> float:
    """Holland 质量分：1.0 最好，0.0 最差。"""
    score = 1.0
    if "straight_line" in flags:
        score -= 0.45
    if "low_variance" in flags:
        score -= 0.25
    if "alternating_pattern" in flags:
        score -= 0.25
    if "long_run" in flags:
        score -= 0.2
    if "low_entropy" in flags:
        score -= 0.15

    # 方差越小、熵越低，额外扣分
    if variance < 0.5:
        score -= 0.15
    if entropy < 1.0:
        score -= 0.1

    return max(0.0, min(1.0, score))


def _gallup_score_from_flags(
    flags: List[str],
    neutral_rate: float,
    one_side_ratio: float,
    extreme_alt_ratio: float,
    entropy: float,
) -> float:
    """Gallup 质量分：1.0 最好，0.0 最差。"""
    score = 1.0
    if "neutral_rate" in flags:
        score -= 0.35
    if "one_side_bias" in flags:
        score -= 0.3
    if "extreme_alternation" in flags:
        score -= 0.3
    if "long_run" in flags:
        score -= 0.2
    if "alternating_pattern" in flags:
        score -= 0.2
    if "low_entropy" in flags:
        score -= 0.15

    # 越严重额外扣分
    if neutral_rate >= 0.5:
        score -= 0.15
    if one_side_ratio >= 0.9:
        score -= 0.15
    if extreme_alt_ratio >= 0.4:
        score -= 0.15
    if entropy < 0.9:
        score -= 0.1

    return max(0.0, min(1.0, score))


def _holland_message(flags: List[str], score: float) -> tuple:
    if not flags or score >= 0.75:
        return (
            "作答模式正常，结果可信度较高。",
            "Response pattern looks normal; results are relatively reliable.",
        )

    if "straight_line" in flags:
        return (
            "检测到大量相同答案，疑似直线作答或敷衍，建议重新认真测评。",
            "Many identical answers detected (possible straight-lining or rushing). Please retake carefully.",
        )
    if "alternating_pattern" in flags:
        return (
            "答案呈现明显交替规律，可能存在乱答或机器作答。",
            "Your answers show a clear alternating pattern, which may indicate random or automated responding.",
        )
    if "low_variance" in flags:
        return (
            "答案波动较小，可能所有题目感受相近或存在敷衍倾向。",
            "Low variance detected: answers are clustered closely; consider whether you responded thoughtfully.",
        )
    if "long_run" in flags:
        return (
            "出现较长连续相同答案，建议检查是否有未认真审题的情况。",
            "A long run of identical answers was detected; please check whether items were read carefully.",
        )

    return (
        "作答质量存在一定疑问，建议结合报告谨慎解读。",
        "Some response quality concerns were detected; please interpret the report with caution.",
    )


def _gallup_message(flags: List[str], score: float) -> tuple:
    if not flags or score >= 0.75:
        return (
            "作答模式正常，结果可信度较高。",
            "Response pattern looks normal; results are relatively reliable.",
        )

    if "neutral_rate" in flags and "one_side_bias" in flags:
        return (
            "中立选项过多且明显偏向一侧，作答模式异常，建议重新测评。",
            "Too many neutral choices combined with strong one-sided bias; response pattern is unusual. Please retake.",
        )
    if "neutral_rate" in flags:
        return (
            "中立选项过多，可能未做明确选择，建议认真重新作答。",
            "Too many neutral choices detected; please retake and make clearer selections.",
        )
    if "one_side_bias" in flags:
        return (
            "答案明显偏向 A 侧或 B 侧，可能存在理解偏差或敷衍。",
            "Responses are strongly biased toward one side; possible misunderstanding or rushing.",
        )
    if "extreme_alternation" in flags:
        return (
            "检测到极端选项频繁交替，疑似乱答。",
            "Frequent alternation between extreme options detected; possible random responding.",
        )
    if "alternating_pattern" in flags:
        return (
            "答案呈现规律性交替，建议检查是否认真作答。",
            "A regular alternating pattern was detected; please verify that you responded thoughtfully.",
        )
    if "long_run" in flags:
        return (
            "出现较长连续相同选择，建议复核作答过程。",
            "A long run of identical choices was detected; please review your response process.",
        )

    return (
        "作答质量存在一定疑问，建议结合报告谨慎解读。",
        "Some response quality concerns were detected; please interpret the report with caution.",
    )
