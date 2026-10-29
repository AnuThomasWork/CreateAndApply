"""Load and validate the base resume (YAML)."""
from __future__ import annotations

from pathlib import Path

import yaml

REQUIRED = ["name", "contact", "experience"]


def load_resume(path: str | Path) -> dict:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Copy data/resume.example.yaml to data/resume.yaml and fill it in."
        )
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    missing = [k for k in REQUIRED if not data.get(k)]
    if missing:
        raise ValueError(f"Resume is missing required sections: {', '.join(missing)}")
    data.setdefault("summary", "")
    data.setdefault("skills", {})
    data.setdefault("education", [])
    data.setdefault("certifications", [])
    return data


def resume_text(resume: dict) -> str:
    """Flatten a resume to plain text (used for keyword coverage checks)."""
    parts = [resume.get("summary", "")]
    for cat, items in resume.get("skills", {}).items():
        parts.append(cat + " " + " ".join(items))
    for job in resume.get("experience", []):
        parts.append(f"{job.get('title','')} {job.get('company','')}")
        parts.extend(job.get("bullets", []))
    parts.extend(str(c) for c in resume.get("certifications", []))
    return "\n".join(parts)
