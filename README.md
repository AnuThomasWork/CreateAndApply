# CreateAndApply

Generate an **ATS-friendly tailored resume and cover letter** from a job description
(pasted text, a text file, or a job-posting link), based on your own base resume.

Outputs per job (in `output/<Company>_<Title>/`): resume + cover letter as **.docx and .pdf**,
a plain-text cover letter, and `ats_report.md` showing matched / missing keywords.

## How it stays ATS-safe and honest
- Single column, standard headings (Professional Summary, Skills, Professional Experience, Education), real text,
  no tables, images, columns or text boxes.
- The tool **only reorders and selects what is already in your `resume.yaml`**: it never invents skills or
  experience. Keywords the job wants but you don't list are shown in `ats_report.md`; add them only if true.

## Setup (VS Code)
```bash
git clone https://github.com/AnuThomasWork/CreateAndApply.git
cd CreateAndApply
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
cp data/resume.example.yaml data/resume.yaml    # then edit with your real resume
```
Open the folder in VS Code, pick the `.venv` interpreter (Ctrl/Cmd+Shift+P → "Python: Select Interpreter").
Use **Run and Debug** → "CreateAndApply: job URL (prompt)" or run from the terminal.

## Usage
```bash
python -m createandapply --job-url "https://boards.greenhouse.io/acme/jobs/123"
python -m createandapply --job-file data/sample_job.txt
python -m createandapply --job-text "paste the whole description here"
pbpaste | python -m createandapply --job-text -          # read from stdin
```
Options: `--resume`, `--out`, `--title`, `--company`, `--headline "Senior SDET"`, `--llm`.

If a URL needs login or JavaScript (LinkedIn, some Workday pages), paste the text into a file and use `--job-file`.

### Optional: nicer cover letter with Claude
```bash
pip install anthropic
export ANTHROPIC_API_KEY=...
python -m createandapply --job-url ... --llm
```
The prompt restricts Claude to facts in your resume. Always read the letter before sending.

## Tests
```bash
pytest
```

## Project layout
```
src/createandapply/
  job_fetcher.py   text / file / URL (JSON-LD JobPosting first, then page text)
  analyzer.py      required vs preferred keywords, title, company
  tailor.py        reorder skills, rank bullets, keyword coverage score
  cover_letter.py  template letter, optional LLM polish
  renderers.py     DOCX + PDF output
  cli.py           command line
data/resume.example.yaml   template for your resume (copy to resume.yaml, git-ignored)
```
