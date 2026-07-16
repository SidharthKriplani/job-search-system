"""
Skill extraction at ingestion — the skills FLYWHEEL.

Runs inside make_job() while the connector still holds the FULL job
description (the stored snippet is trimmed to 280 chars, so this is the only
moment skills can be extracted). Output: a sorted list of canonical skill
names stored on jobs_pool.skills (jsonb) — the corpus for per-role skill
density, gap detection, and trend stats.

Lexicon-based (word-boundary regex, multi-word first) — no ML needed at this
layer; counting + TF-IDF happen downstream on accrued data. EXTEND the lexicon
freely; alias → canonical.
"""
import re
from functools import lru_cache
from typing import List, Optional

# canonical skill -> aliases (matched case-insensitively on word boundaries)
LEXICON = {
    # Languages
    "Python": ["python"], "Java": ["java"], "JavaScript": ["javascript", "js"],
    "TypeScript": ["typescript"], "C++": [r"c\+\+"], "C#": ["c#", "c sharp"],
    "Go": ["golang"], "Rust": ["rust"], "Kotlin": ["kotlin"], "Swift": ["swift"],
    "Ruby": ["ruby on rails", "ruby"], "PHP": ["php"], "Scala": ["scala"], "R": [r"\br\b(?=[ ,/]|$)"],
    "SQL": ["sql"], "NoSQL": ["nosql"], "Bash": ["bash", "shell scripting"],
    # Data / AI
    "Machine Learning": ["machine learning", "ml engineer", r"\bml\b"],
    "Deep Learning": ["deep learning"], "NLP": ["nlp", "natural language processing"],
    "Computer Vision": ["computer vision"], "LLM": ["llm", "large language model", "genai", "generative ai"],
    "PyTorch": ["pytorch"], "TensorFlow": ["tensorflow"], "scikit-learn": ["scikit-learn", "sklearn"],
    "Pandas": ["pandas"], "NumPy": ["numpy"], "Spark": ["pyspark", "apache spark", "spark"],
    "Hadoop": ["hadoop"], "Kafka": ["kafka"], "Airflow": ["airflow"], "dbt": [r"\bdbt\b"],
    "ETL": ["etl", "elt"], "Data Modeling": ["data modeling", "data modelling"],
    "Data Warehousing": ["data warehouse", "data warehousing"],
    "Snowflake": ["snowflake"], "Databricks": ["databricks"], "BigQuery": ["bigquery"],
    "Redshift": ["redshift"], "Tableau": ["tableau"], "Power BI": ["power bi", "powerbi"],
    "Looker": ["looker"], "Excel": ["excel", "ms excel", "microsoft excel"],
    "Statistics": ["statistics", "statistical analysis", "statistical modeling"],
    "A/B Testing": ["a/b testing", "ab testing", "experimentation"],
    "MLOps": ["mlops"], "Feature Engineering": ["feature engineering"],
    # Backend / infra
    "Node.js": ["node.js", "nodejs", "node js"], "Django": ["django"], "Flask": ["flask"],
    "FastAPI": ["fastapi"], "Spring Boot": ["spring boot", "springboot"], "Spring": ["spring framework"],
    ".NET": [r"\.net", "dotnet"], "GraphQL": ["graphql"], "REST API": ["rest api", "restful", "rest apis"],
    "Microservices": ["microservices", "micro-services"], "gRPC": ["grpc"],
    "PostgreSQL": ["postgresql", "postgres"], "MySQL": ["mysql"], "MongoDB": ["mongodb", "mongo"],
    "Redis": ["redis"], "Elasticsearch": ["elasticsearch", "elastic search"], "Cassandra": ["cassandra"],
    "RabbitMQ": ["rabbitmq"], "DynamoDB": ["dynamodb"], "Oracle DB": ["pl/sql", "plsql"],
    # Cloud / DevOps
    "AWS": ["aws", "amazon web services"], "Azure": ["azure"], "GCP": ["gcp", "google cloud"],
    "Docker": ["docker"], "Kubernetes": ["kubernetes", "k8s"], "Terraform": ["terraform"],
    "Ansible": ["ansible"], "Jenkins": ["jenkins"], "CI/CD": ["ci/cd", "cicd", "continuous integration"],
    "Linux": ["linux", "unix"], "Git": [r"\bgit\b", "github", "gitlab"],
    "Prometheus": ["prometheus"], "Grafana": ["grafana"], "Datadog": ["datadog"],
    "Serverless": ["serverless", "lambda functions", "aws lambda"],
    "Networking": ["tcp/ip", "networking protocols"], "Security": ["cybersecurity", "application security", "infosec"],
    "DevOps": ["devops"], "SRE": ["site reliability", r"\bsre\b"],
    # Frontend / mobile
    "React": ["react.js", "reactjs", "react"], "Angular": ["angular"], "Vue": ["vue.js", "vuejs", "vue"],
    "Next.js": ["next.js", "nextjs"], "HTML/CSS": ["html", "css"], "Tailwind": ["tailwind"],
    "Redux": ["redux"], "React Native": ["react native"], "Flutter": ["flutter"],
    "Android": ["android development", "android sdk", "android"], "iOS": ["ios development", r"\bios\b"],
    # Product / design / management
    "Product Management": ["product management", "product roadmap", "product strategy"],
    "Agile": ["agile", "scrum", "kanban"], "JIRA": ["jira"],
    "Stakeholder Management": ["stakeholder management", "stakeholder engagement"],
    "Project Management": ["project management", r"\bpmp\b"],
    "UX Design": ["ux design", "user experience", "ux research"], "UI Design": ["ui design", "user interface design"],
    "Figma": ["figma"], "Wireframing": ["wireframing", "wireframes", "prototyping"],
    "Market Research": ["market research"], "Growth": ["growth hacking", "growth marketing"],
    "SEO": [r"\bseo\b"], "Digital Marketing": ["digital marketing", "performance marketing"],
    "Content Marketing": ["content marketing", "content strategy"],
    "CRM": [r"\bcrm\b", "hubspot"], "Sales": ["b2b sales", "inside sales", "sales pipeline"],
    "Account Management": ["account management", "key account"],
    "Customer Success": ["customer success"], "Operations": ["operations management", "process improvement"],
    "Supply Chain": ["supply chain", "logistics"], "Procurement": ["procurement", "sourcing"],
    # Finance / analytics
    "Financial Modeling": ["financial modeling", "financial modelling", "dcf"],
    "Valuation": ["valuation", "comparable company analysis"],
    "Equity Research": ["equity research"], "Investment Banking": ["investment banking", r"\bib\b"],
    "FP&A": ["fp&a", "financial planning"], "Accounting": ["accounting", "general ledger", "ifrs", "gaap", r"\bca\b"],
    "Audit": ["internal audit", "statutory audit", "audit"], "Taxation": ["taxation", "direct tax", "indirect tax", "gst"],
    "Risk Management": ["risk management", "credit risk", "market risk", "operational risk"],
    "Compliance": ["compliance", "aml", "kyc", "regulatory reporting"],
    "Treasury": ["treasury"], "Derivatives": ["derivatives", "fixed income", "equities trading"],
    "Quantitative Analysis": ["quantitative analysis", "quant"],
    "Bloomberg": ["bloomberg"], "SAP FICO": ["sap fico"], "Tally": ["tally"],
    "Underwriting": ["underwriting"], "Actuarial": ["actuarial"],
    "Business Analysis": ["business analysis", "business analyst", "requirements gathering"],
    "Data Analysis": ["data analysis", "data analytics"],
    # Enterprise platforms
    "Salesforce": ["salesforce", "apex", "visualforce", "lightning web components"],
    "SAP": ["sap abap", "sap hana", "s/4hana", r"\bsap\b"],
    "ServiceNow": ["servicenow"], "Workday HCM": ["workday hcm"], "Oracle ERP": ["oracle erp", "oracle ebs"],
    "Sharepoint": ["sharepoint"], "Power Automate": ["power automate", "power apps"],
    # QA
    "Selenium": ["selenium"], "Cypress": ["cypress"], "Playwright": ["playwright"],
    "API Testing": ["api testing", "postman"], "Automation Testing": ["test automation", "automation testing"],
    "Manual Testing": ["manual testing"], "Performance Testing": ["performance testing", "jmeter", "load testing"],
    # Soft-ish but signal-bearing
    "Communication": ["communication skills"], "Leadership": ["team leadership", "people management"],
}

_MAX_SKILLS = 30


@lru_cache(maxsize=1)
def _compiled():
    pats = []
    for canonical, aliases in LEXICON.items():
        for a in aliases:
            # raw regex if it contains regex metachars we put there; else escape
            pat = a if a.startswith("\\b") or "\\" in a or "+" in a and "\\+" in a else re.escape(a)
            # (?<!\w) not (?<![\w/]) — "Docker/Kubernetes" lists are common in JDs
            pats.append((re.compile(rf"(?<!\w){pat}(?![\w+])", re.IGNORECASE), canonical))
    return pats


def extract_skills(text: Optional[str]) -> List[str]:
    """Full-text → sorted unique canonical skills (capped). Never raises."""
    if not text:
        return []
    try:
        t = str(text)[:20000]
        found = set()
        for rx, canonical in _compiled():
            if rx.search(t):
                found.add(canonical)
                if len(found) >= _MAX_SKILLS:
                    break
        return sorted(found)
    except Exception:
        return []
