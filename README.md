# reNews: AI-Powered Technical News Aggregator

reNews is a news aggregator that automates the process of fetching RSS feeds, extracting core content, and performing AI analysis using Google Gemini. It provides concise summaries, categorical classification, and scoring for every article.

## 🚀 Key Features

- **Automated Fetching:** Periodically polls RSS/Atom feeds for new content a set intervals.
- **URL parsing** Parses each extracted URL from RSS feed using httpx.AsyncClient and trafilatura
- **AI-Driven Insights:**
  - **Summarization:** 1-2 sentence summaries(200 charactrers max).
  - **Categorization:** Automatic sorting into predefined categories.
  - **Quality Scoring:** 1-10 score based on insightfulness and value.
  - **Language** Autodetect language in which article is written.
- **Admin Control:** Secure dashboard to manage feed sources.
- **Modern Stack:** Fully asynchronous Python (FastAPI, SQLAlchemy) with a responsive frontend.

## 🛠 Tech Stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2.0 (Async), APScheduler.
- **Database:** PostgreSQL.
- **AI:** Google Gemini API.
- **Frontend:** Jinja2, Vanilla JavaScript, Tailwind CSS.
- **DevOps:** Docker, Docker Compose.
