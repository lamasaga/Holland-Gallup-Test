#!/usr/bin/env python3
"""Fix known A/B scenario reversals in gallup_180_questions_list.md."""
import re
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MD_PATH = os.path.join(BASE_DIR, "research", "测评研究", "data", "processed", "gallup_180_questions_list.md")

# Questions where A/B scenario descriptions are reversed.
KNOWN_REVERSED = {22, 23, 24, 25, 26, 28, 31, 32, 35}


def swap_scenario_parts(scenario: str) -> str:
    """Swap 'A 对应的情境：X。B 对应的情境：Y。' to 'A 对应的情境：Y。B 对应的情境：X。'"""
    pattern = re.compile(
        r"(A 对应的情境[:：]\s*)(.+?)(\s*B 对应的情境[:：]\s*)(.+?)(\s*你更)",
        re.DOTALL,
    )

    def repl(m):
        return f"{m.group(1)}{m.group(4)}{m.group(3)}{m.group(2)}{m.group(5)}"

    return pattern.sub(repl, scenario)


def main():
    with open(MD_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = re.compile(
        r"(### 第 (\d+) 题\n+\*\*A:\*\*\s*.+?\n+\*\*B:\*\*\s*.+?\n+\n+💡 \*\*场景提示\*\*：)(.+?)(\n+\n+非常认同A)",
        re.DOTALL,
    )

    def repl_block(m):
        header = m.group(1)
        num = int(m.group(2))
        scenario = m.group(3)
        footer = m.group(4)
        if num in KNOWN_REVERSED:
            new_scenario = swap_scenario_parts(scenario)
            print(f"Fixed Q{num}")
            return header + new_scenario + footer
        return m.group(0)

    new_content = pattern.sub(repl_block, content)

    with open(MD_PATH, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"\nUpdated {MD_PATH}")


if __name__ == "__main__":
    main()
