"""Extract the keywords an ATS is likely to screen for from a job description."""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

# canonical term -> aliases that should count as the same thing
SKILL_VOCAB: dict[str, list[str]] = {
    # QA / SDET
    "Selenium": ["selenium", "webdriver"],
    "Playwright": ["playwright"],
    "Cypress": ["cypress"],
    "Appium": ["appium"],
    "Rest Assured": ["rest assured", "restassured"],
    "Postman": ["postman"],
    "TestNG": ["testng"],
    "JUnit": ["junit"],
    "pytest": ["pytest"],
    "Cucumber": ["cucumber"],
    "BDD": ["bdd", "behavior driven", "behaviour driven"],
    "TDD": ["tdd", "test driven"],
    "API testing": ["api testing", "api test", "rest api", "restful"],
    "Test automation": ["test automation", "automated testing", "automation framework", "automated tests"],
    "Performance testing": ["performance testing", "load testing", "jmeter", "gatling", "k6"],
    "JMeter": ["jmeter"],
    "Regression testing": ["regression"],
    "Mobile testing": ["mobile testing", "ios", "android"],
    "Test strategy": ["test strategy", "test plan", "test planning"],
    "Quality engineering": ["quality engineering", "quality assurance", "qa"],
    "Shift-left": ["shift-left", "shift left"],
    "Page Object Model": ["page object"],
    "Flaky tests": ["flaky"],
    # languages
    "Python": ["python"],
    "Java": ["java"],
    "JavaScript": ["javascript"],
    "TypeScript": ["typescript"],
    "C#": ["c#", ".net", "dotnet"],
    "SQL": ["sql", "postgresql", "mysql", "oracle", "sql server"],
    "Bash": ["bash", "shell script"],
    "Groovy": ["groovy"],
    "Kotlin": ["kotlin"],
    "Go": ["golang"],
    # platform / devops
    "CI/CD": ["ci/cd", "ci cd", "continuous integration", "continuous delivery", "continuous deployment"],
    "Jenkins": ["jenkins"],
    "GitHub Actions": ["github actions"],
    "GitLab CI": ["gitlab ci", "gitlab"],
    "Azure DevOps": ["azure devops", "ado"],
    "Docker": ["docker", "containers"],
    "Kubernetes": ["kubernetes", "k8s"],
    "AWS": ["aws", "amazon web services"],
    "Azure": ["azure"],
    "GCP": ["gcp", "google cloud"],
    "Terraform": ["terraform"],
    "Git": ["git", "github", "bitbucket"],
    "Linux": ["linux"],
    # process / tools
    "Agile": ["agile", "scrum", "kanban", "sprint"],
    "Jira": ["jira"],
    "TestRail": ["testrail"],
    "Confluence": ["confluence"],
    "Microservices": ["microservices", "microservice"],
    "GraphQL": ["graphql"],
    "Kafka": ["kafka"],
    "React": ["react"],
    "Node.js": ["node.js", "nodejs"],
    "Data validation": ["data validation", "etl", "data quality"],
    "Security testing": ["security testing", "owasp"],
    "Accessibility": ["accessibility", "wcag", "a11y"],
    "Salesforce": ["salesforce"],
    "Mentoring": ["mentor", "mentors", "mentored", "mentoring", "coach", "coached"],
    "Leadership": ["lead", "leadership", "stakeholder"],
    "Cross-functional collaboration": ["cross-functional", "cross functional"],
}

PREFERRED_MARKERS = re.compile(
    r"(nice to have|preferred|bonus|plus\b|a plus|desired|good to have|ideal)", re.I
)
TITLE_HINT = re.compile(
    r"(sdet|software development engineer in test|qa|quality|test|automation|software|engineer|developer|analyst|lead|manager)",
    re.I,
)


@dataclass
class JobAnalysis:
    title: str
    company: str
    required: list[str] = field(default_factory=list)
    preferred: list[str] = field(default_factory=list)
    extra_terms: list[str] = field(default_factory=list)

    @property
    def all_keywords(self) -> list[str]:
        seen: list[str] = []
        for k in self.required + self.preferred + self.extra_terms:
            if k not in seen:
                seen.append(k)
        return seen


def _contains(text_lc: str, alias: str) -> int:
    pattern = r"(?<![a-z0-9+#])" + re.escape(alias) + r"(?![a-z0-9+#])"
    return len(re.findall(pattern, text_lc))


def count_term(text: str, term: str) -> int:
    """Occurrences of a canonical skill (any alias) or a free term in text."""
    text_lc = text.lower()
    aliases = SKILL_VOCAB.get(term, [term.lower()])
    return sum(_contains(text_lc, a) for a in set(aliases) | {term.lower()})


SEP = re.compile(r"\s[-|–@]\s")


def _title_line(text: str, fallback: str) -> str:
    if fallback and TITLE_HINT.search(fallback):
        return fallback.strip()
    for line in text.splitlines()[:8]:
        line = line.strip()
        if 3 < len(line) < 90 and TITLE_HINT.search(line):
            return re.sub(r"^(job title|title|position|role)\s*[:\-]\s*", "", line, flags=re.I)
    return ""


def _guess_title(text: str, fallback: str) -> str:
    return SEP.split(_title_line(text, fallback))[0].strip()


def _guess_company(text: str, given: str, title_line: str = "") -> str:
    if given:
        return given
    parts = SEP.split(title_line)
    if len(parts) > 1 and len(parts[1]) < 40:  # "Senior SDET - Acme Cloud"
        return parts[1].strip()
    m = re.search(r"(?i:about|join|at)\s+([A-Z][\w&.\-]*(?: [A-Z][\w&.\-]*){0,3})(?=[,.\n]| is | are | we )", text)
    return m.group(1).strip() if m else ""


def analyze(text: str, title: str = "", company: str = "", extra_limit: int = 8) -> JobAnalysis:
    # split into "preferred" section vs rest, so required skills rank first
    split = PREFERRED_MARKERS.search(text)
    head, tail = (text, "") if not split else (text[: split.start()], text[split.start():])

    scored: list[tuple[str, int, bool]] = []
    for term in SKILL_VOCAB:
        n_head, n_tail = count_term(head, term), count_term(tail, term)
        if n_head + n_tail:
            scored.append((term, n_head + n_tail, n_head == 0))
    required = [t for t, _, pref_only in sorted(scored, key=lambda x: -x[1]) if not pref_only]
    preferred = [t for t, _, pref_only in sorted(scored, key=lambda x: -x[1]) if pref_only]

    # frequent capitalised / hyphenated phrases not in the vocab (domain terms, product names)
    known = {a for v in SKILL_VOCAB.values() for a in v} | {k.lower() for k in SKILL_VOCAB}
    words = re.findall(r"\b[A-Z][A-Za-z0-9+#.]{2,}(?:\s[A-Z][A-Za-z0-9+#.]{2,})?\b", text)
    stop = {"The", "You", "Our", "We", "This", "Your", "And", "For", "With", "Experience", "Ability",
            "Strong", "Knowledge", "Understanding", "Responsibilities", "Requirements", "Qualifications"}
    counts = Counter(w for w in words if w not in stop and w.lower() not in known)
    extra = [w for w, c in counts.most_common(extra_limit * 2) if c >= 2][:extra_limit]

    return JobAnalysis(
        title=_guess_title(text, title),
        company=_guess_company(text, company, _title_line(text, title)),
        required=required,
        preferred=preferred,
        extra_terms=extra,
    )
