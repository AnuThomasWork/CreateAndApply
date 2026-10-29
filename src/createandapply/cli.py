"""Command line entry point:  python -m createandapply --job-url <url> --resume data/resume.yaml"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from . import job_fetcher
from .analyzer import analyze
from .cover_letter import build_cover_letter, polish_with_llm
from .renderers import letter_docx, letter_pdf, resume_docx, resume_pdf
from .resume_model import load_resume, resume_text
from .tailor import tailor


def _slug(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_") or "job"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="createandapply", description=__doc__)
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--job-url", help="Link to the job posting")
    src.add_argument("--job-file", help="Text file containing the job description")
    src.add_argument("--job-text", help="Job description pasted as text (or '-' to read stdin)")
    p.add_argument("--resume", default="data/resume.yaml", help="Base resume YAML (default: data/resume.yaml)")
    p.add_argument("--out", default="output", help="Output folder (default: output)")
    p.add_argument("--title", help="Override detected job title")
    p.add_argument("--company", help="Override detected company name")
    p.add_argument("--headline", help="Headline under your name, e.g. 'Senior SDET'")
    p.add_argument("--llm", action="store_true", help="Polish the cover letter with the Anthropic API (needs ANTHROPIC_API_KEY)")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        if args.job_url:
            posting = job_fetcher.from_url(args.job_url)
        elif args.job_file:
            posting = job_fetcher.from_file(args.job_file)
        else:
            posting = job_fetcher.from_text(sys.stdin.read() if args.job_text == "-" else args.job_text)
        resume = load_resume(args.resume)
    except Exception as exc:  # user-facing errors
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    job = analyze(posting.text, posting.title, posting.company)
    if args.title:
        job.title = args.title
    if args.company:
        job.company = args.company

    result = tailor(resume, job, headline=args.headline)
    letter = build_cover_letter(result, job)
    if args.llm:
        letter = polish_with_llm(letter, resume_text(resume), posting.text)

    out = Path(args.out) / _slug(f"{job.company}_{job.title}" if job.company or job.title else "job")
    out.mkdir(parents=True, exist_ok=True)
    name = _slug(resume["name"])
    resume_docx(result.resume, out / f"{name}_Resume.docx")
    resume_pdf(result.resume, out / f"{name}_Resume.pdf")
    letter_docx(letter, resume["name"], out / f"{name}_Cover_Letter.docx")
    letter_pdf(letter, resume["name"], out / f"{name}_Cover_Letter.pdf")
    (out / f"{name}_Cover_Letter.txt").write_text(letter, encoding="utf-8")

    report = [
        f"# ATS match report: {job.title or "job"}{" @ " + job.company if job.company else ""}",
        f"Required-keyword coverage in your base resume: **{result.score}%**",
        "",
        f"Matched ({len(result.matched)}): {', '.join(result.matched) or '-'}",
        f"Not found in your resume ({len(result.missing)}): {', '.join(result.missing) or '-'}",
        "",
        "Add a missing keyword to data/resume.yaml only if you genuinely have that experience.",
    ]
    (out / "ats_report.md").write_text("\n".join(report), encoding="utf-8")

    print(f"Job: {job.title or '?'} @ {job.company or '?'}   |   match {result.score}%")
    print(f"Missing keywords: {', '.join(result.missing) or 'none'}")
    print(f"Files written to {out}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
