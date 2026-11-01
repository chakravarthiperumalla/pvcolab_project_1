"""Turn stored roadmap data into Markdown (used for module quizzes, PDF export and email)."""
from .models import Day, Quiz, Roadmap


def _numbered(items: list[str]) -> str:
    return "\n".join(f"{i}. {q}" for i, q in enumerate(items, start=1)) or "_None_"


def day_to_markdown(day_number: int, title: str, c: dict) -> str:
    p, a = c["practice"], c["assignment"]
    return f"""## Day {day_number}: {title}

**Goal:** {c['goal']}

### Theory
{c['theory']}

### Examples
{c['examples']}

### Real-World Use Case
{c['real_world_use_case']}

### Common Mistakes
{c['common_mistakes']}

### Summary
{c['summary']}

### Practice

**MCQs**

{_numbered(p['mcqs'])}

**Coding Questions**

{_numbered(p['coding_questions'])}

**Debugging Questions**

{_numbered(p['debugging_questions'])}

**Interview Questions**

{_numbered(p['interview_questions'])}

### Assignment

**Mini Assignment:** {a['mini_assignment']}

**Homework:** {a['homework']}

**Challenge:** {a['challenge']}

**Hints:** {a['hints']}

**Expected Output:** {a['expected_output']}
"""


def quiz_to_markdown(q: Quiz) -> str:
    lines = [f"## Module {q.module_number} Quiz (Days {q.day_range})", ""]
    for i, item in enumerate(q.questions or [], start=1):
        lines.append(f"**{i}. {item['question']}**")
        lines.append("")
        for j, opt in enumerate(item["options"]):
            lines.append(f"- {chr(65 + j)}. {opt}")
        lines.append("")
        lines.append(f"*Answer:* {chr(65 + item['answer_index'])}. {item['options'][item['answer_index']]}")
        lines.append("")
        lines.append(f"*Explanation:* {item['explanation']}")
        lines.append("")
    return "\n".join(lines)


def roadmap_to_markdown(roadmap: Roadmap, days: list[Day], quizzes: list[Quiz]) -> str:
    parts = [
        f"# {roadmap.topic} - Learning Handbook",
        f"**Level:** {roadmap.level}  \n**Duration:** {roadmap.duration} days  \n"
        f"**Daily time:** {roadmap.hours_per_day:g} hours",
        "## Roadmap",
        "| Day | Title |\n|---|---|\n" + "\n".join(f"| {d.day_number} | {d.title} |" for d in days),
    ]
    parts += [day_to_markdown(d.day_number, d.title, d.content) for d in days if d.content]
    done_quizzes = [q for q in quizzes if q.questions]
    if done_quizzes:
        parts.append("# Module Quizzes")
        parts += [quiz_to_markdown(q) for q in done_quizzes]
    return "\n\n".join(parts)
