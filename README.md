# Insight-Core

Insight-Core is the core backend of a micro-SaaS that detects, clusters, and analyzes real user problems from online communities (e.g. Reddit) to generate actionable insights for founders, marketers, and product teams.

This repository contains:
- API (FastAPI)
- Data ingestion & scraping
- ML / embeddings pipeline
- Scoring & relevance logic

---

## Project status
🚧 Early development – local setup only

---

## Local setup (WIP)

### Requirements
- Python 3.10+
- PostgreSQL (local or cloud)
- Git

### Setup steps
```bash
git clone https://github.com/Jaimeplumber/insight-core.git
cd insight-core
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

