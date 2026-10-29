"""Tailor the base resume to a job. Only reorders/selects what is already in the resume:
nothing is invented, so every claim stays truthful."""
from __future__ import annotations

import copy
import re
from dataclasses import dataclass, field

from .analyzer import JobAnalysis, count_term
from .resume_model import resume_text

MAX_BULLETS = [8, 6, 4]  # most recent job first; older jobs get fewer


@dataclass
class TailorResult:
    resume: dict
    matched: list[str]
    missing: list[str]
    score: int  # % of required keywords present in the base resume
    weights: dict[str, int] = field(default_factory=dict)


def _weights(job: JobAnalysis) -> dict[str, int]:
    w: dict[str, int] = {}
    for k in job.extra_terms:
        w[k] = 1
    for k in job.preferred:
        w[k] = 2
    for k in job.required:
        w[k] = 3
    return w


def _score_text(text: str, weights: dict[str, int]) -> int:
    return sum(w for k, w in weights.items() if count_term(text, k))


def tailor(resume: dict, job: JobAnalysis, headline: str | None = None) -> TailorResult:
    base_text = resume_text(resume)
    weights = _weights(job)
    matched = [k for k in job.all_keywords if count_term(base_text, k)]
    missing = [k for k in job.all_keywords if k not in matched]
    req = job.required or job.all_keywords
    score = round(100 * sum(1 for k in req if k in matched) / len(req)) if req else 0

    out = copy.deepcopy(resume)

    # headline: explicit override or the one in the resume. Never auto-claim a title.
    if headline:
        out["headline"] = headline

    # summary: keep the user's words, add a truthful keyword sentence
    top = [k for k in matched if k in job.required][:6]
    summary = out.get("summary", "").strip()
    if top:
        summary = (summary + f" Core strengths: {', '.join(top)}.").strip()
    out["summary"] = summary

    # skills: categories with most job matches first; matches first within each category
    def skill_hits(item: str) -> int:
        return _score_text(item, weights)

    cats = {}
    for cat, items in out.get("skills", {}).items():
        cats[cat] = sorted(items, key=lambda s: -skill_hits(s))  # stable
    out["skills"] = dict(
        sorted(cats.items(), key=lambda kv: -sum(1 for s in kv[1] if skill_hits(s)))
    )

    # experience: keep chronological order; rank bullets inside each role
    for i, job_entry in enumerate(out["experience"]):
        limit = MAX_BULLETS[i] if i < len(MAX_BULLETS) else MAX_BULLETS[-1]
        bullets = job_entry.get("bullets", [])
        ranked = sorted(
            enumerate(bullets),
            key=lambda ib: (-_score_text(ib[1], weights), -int(bool(re.search(r"\d", ib[1]))), ib[0]),
        )
        keep = sorted(ranked[:limit], key=lambda ib: ib[0])  # restore original order of kept bullets
        # put the strongest match first, as recruiters skim the first bullet
        best = ranked[0][1] if ranked else None
        ordered = [b for _, b in keep]
        if best in ordered:
            ordered.remove(best)
            ordered.insert(0, best)
        job_entry["bullets"] = ordered

    return TailorResult(out, matched, missing, score, weights)


def top_achievements(resume: dict, weights: dict[str, int], n: int = 3) -> list[str]:
    pool = [b for j in resume["experience"] for b in j.get("bullets", [])]
    pool.sort(key=lambda b: (-_score_text(b, weights), -int(bool(re.search(r"\d", b)))))
    return pool[:n]
