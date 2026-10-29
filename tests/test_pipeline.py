from pathlib import Path

from createandapply.analyzer import analyze, count_term
from createandapply.cli import main
from createandapply.resume_model import load_resume
from createandapply.tailor import tailor

ROOT = Path(__file__).resolve().parents[1]
JOB = (ROOT / "data/sample_job.txt").read_text()


def test_count_term_aliases_and_boundaries():
    assert count_term("We use Java and JavaScript", "Java") == 1
    assert count_term("k8s and CI/CD", "Kubernetes") == 1
    assert count_term("golang", "Java") == 0


def test_analyze_splits_required_and_preferred():
    job = analyze(JOB)
    assert "Selenium" in job.required and "Rest Assured" in job.required
    assert {"Cypress", "Kafka", "Terraform"} <= set(job.preferred)
    assert job.title.startswith("Senior SDET")


def test_tailor_never_invents_skills():
    resume = load_resume(ROOT / "data/resume.example.yaml")
    res = tailor(resume, analyze(JOB))
    before = {s for v in resume["skills"].values() for s in v}
    after = {s for v in res.resume["skills"].values() for s in v}
    assert before == after
    assert "Kubernetes" in res.missing
    assert res.resume["experience"][0]["bullets"]


def test_cli_creates_files(tmp_path):
    rc = main(["--job-file", str(ROOT / "data/sample_job.txt"),
               "--resume", str(ROOT / "data/resume.example.yaml"), "--out", str(tmp_path)])
    assert rc == 0
    names = {p.suffix for p in tmp_path.rglob("*") if p.is_file()}
    assert {".docx", ".pdf", ".txt", ".md"} <= names
