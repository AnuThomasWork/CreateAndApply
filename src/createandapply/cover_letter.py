"""Cover letter generation: deterministic template by default, optional LLM polish."""
from __future__ import annotations

import datetime as dt
import os

from .analyzer import JobAnalysis
from .tailor import TailorResult, top_achievements


def _lower_first(s: str) -> str:
    s = s.strip().rstrip(".")
    return s[0].lower() + s[1:] if s and not s[:2].isupper() else s


def build_cover_letter(tr: TailorResult, job: JobAnalysis) -> str:
    r = tr.resume
    role = job.title or "open position"
    company = job.company or "your team"
    cl = r.get("cover_letter") or {}
    skills = [k for k in tr.matched if k in job.required][:5] or tr.matched[:5]
    wins = top_achievements(r, tr.weights, 3)
    current = r["experience"][0]

    paras = [
        f"Dear Hiring Team at {company}," if job.company else "Dear Hiring Team,",
        cl.get("opening")
        or (
            f"I am excited to apply for the {role} role{f" at {company}" if job.company else ""}. "
            f"As {current.get('title', 'an engineer')} at {current.get('company', 'my current company')}, "
            f"I bring hands-on experience in {', '.join(skills[:-1])}"
            f"{' and ' if len(skills) > 1 else ''}{skills[-1] if skills else 'quality engineering'}, "
            "which aligns closely with what you are looking for."
        ),
    ]
    if wins:
        paras.append(
            "Highlights of my recent work include:\n"
            + "\n".join(f"- {w.rstrip('.')}." for w in wins)
        )
    paras.append(
        cl.get("middle")
        or "I enjoy partnering with developers, product owners, and fellow engineers to build "
        "reliable automation and ship quality software with confidence."
    )
    paras.append(
        cl.get("closing")
        or f"I would welcome the opportunity to discuss how I can contribute to {company}. "
        "Thank you for your time and consideration."
    )
    paras.append(f"Sincerely,\n{r['name']}")

    c = r["contact"]
    header = "\n".join(
        x for x in [r["name"], " | ".join(filter(None, [c.get("phone"), c.get("email"), c.get("location")])),
                    dt.date.today().strftime("%B %d, %Y")] if x
    )
    return header + "\n\n" + "\n\n".join(paras)


def polish_with_llm(draft: str, resume_facts: str, job_text: str, model: str = "claude-sonnet-5-5") -> str:
    """Optional: rewrite the draft more naturally using the Anthropic API (needs ANTHROPIC_API_KEY)."""
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise RuntimeError("Set ANTHROPIC_API_KEY to use --llm.")
    import anthropic  # optional dependency: pip install anthropic

    client = anthropic.Anthropic()
    msg = client.messages.create(
        model=model,
        max_tokens=1200,
        messages=[{
            "role": "user",
            "content": (
                "Rewrite this cover letter draft so it reads naturally and speaks to the job description. "
                "Use ONLY facts present in the resume facts. Do not invent employers, tools, numbers or "
                "degrees. Plain text, no markdown, 250-350 words, keep the header block unchanged.\n\n"
                f"<job>\n{job_text[:6000]}\n</job>\n<resume_facts>\n{resume_facts}\n</resume_facts>\n"
                f"<draft>\n{draft}\n</draft>"
            ),
        }],
    )
    return msg.content[0].text.strip()
