#!/usr/bin/env python3
"""Check gallup_180_questions_list.md for A/B scenario reversals.

Heuristic: A scenario should contain distinctive keywords from A statement,
and B scenario should contain distinctive keywords from B statement.
We flag a question when the scenario parts appear to align with the
opposite statement.
"""
import re
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MD_PATH = os.path.join(BASE_DIR, "research", "测评研究", "data", "processed", "gallup_180_questions_list.md")


def parse_questions(path: str):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = re.compile(
        r"### 第 (\d+) 题\n+\*\*A:\*\*\s*(.+?)\n+\*\*B:\*\*\s*(.+?)\n+\n+💡 \*\*场景提示\*\*：(.+?)\n+\n+非常认同A",
        re.DOTALL,
    )
    questions = {}
    for num_str, a, b, scenario in pattern.findall(content):
        n = int(num_str.strip())
        questions[n] = {
            "a": a.strip(),
            "b": b.strip(),
            "scenario": scenario.strip(),
        }
    return questions


def split_scenario(scenario: str):
    """Split scenario into A-part and B-part."""
    # Remove prefix.
    body = re.sub(r"^.*A 对应的情境[:：]\s*", "", scenario, flags=re.DOTALL)
    # The final question is the last sentence ending with ？; remove it.
    q_idx = body.rfind("？")
    if q_idx >= 0:
        body = body[:q_idx]
    parts = re.split(r"\s*B 对应的情境[:：]\s*", body, maxsplit=1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return None, None


def extract_keywords(text: str) -> set:
    """Extract meaningful Chinese keywords (length >= 2) from text."""
    # Remove punctuation and whitespace.
    text = re.sub(r"[，。、；：？！\"''（）【】《》\s]", "", text)
    # Extract 2-5 character chunks that are likely meaningful.
    # Simpler: just take all 2-char substrings.
    return set(text[i:i+2] for i in range(len(text) - 1))


def keyword_overlap(statement: str, scenario: str) -> int:
    """Count how many 2-char keywords from statement appear in scenario."""
    kw = extract_keywords(statement)
    if not kw:
        return 0
    return sum(1 for k in kw if k in scenario)


def main():
    questions = parse_questions(MD_PATH)
    print(f"Parsed {len(questions)} questions.\n")

    known_reversed = {22, 23, 24, 25, 26, 28, 31, 32, 35}
    flagged = []

    for n in sorted(questions):
        q = questions[n]
        a_scenario, b_scenario = split_scenario(q["scenario"])
        if not a_scenario or not b_scenario:
            print(f"[warn] Q{n}: cannot split scenario")
            continue

        a_kw_in_a = keyword_overlap(q["a"], a_scenario)
        a_kw_in_b = keyword_overlap(q["a"], b_scenario)
        b_kw_in_a = keyword_overlap(q["b"], a_scenario)
        b_kw_in_b = keyword_overlap(q["b"], b_scenario)

        # A scenario should have at least as many A keywords as B keywords,
        # and B scenario should have at least as many B keywords as A keywords.
        a_ok = a_kw_in_a >= a_kw_in_b
        b_ok = b_kw_in_b >= b_kw_in_a

        if not (a_ok and b_ok):
            flagged.append({
                "num": n,
                "a": q["a"],
                "b": q["b"],
                "a_scenario": a_scenario,
                "b_scenario": b_scenario,
                "scores": (a_kw_in_a, a_kw_in_b, b_kw_in_a, b_kw_in_b),
                "known": n in known_reversed,
            })

    print(f"Flagged {len(flagged)} potential reversal(s):\n")
    for item in flagged:
        print(f"Q{item['num']} {'(KNOWN)' if item['known'] else '(SUSPECT)'}")
        print(f"  A: {item['a']}")
        print(f"  B: {item['b']}")
        print(f"  A-scenario: {item['a_scenario']}")
        print(f"  B-scenario: {item['b_scenario']}")
        print(f"  keyword counts (a_kw_in_a, a_kw_in_b, b_kw_in_a, b_kw_in_b): {item['scores']}")
        print()


if __name__ == "__main__":
    main()
