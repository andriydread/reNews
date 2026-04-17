# reNews: AI-Powered Technical News Aggregator

reNews is a news aggregator that automates the process of fetching RSS feeds, extracting core content, and performing AI analysis using Google Gemini. It provides concise summaries, categorical classification, and scoring for every article.

## 🚀 Key Features

- **Automated Fetching:** Periodically polls RSS/Atom feeds for new content.
- **Clean Extraction:** Uses `trafilatura` to strip ads, navbars, and noise.
- **AI-Driven Insights:**
  - **Summarization:** 1-2 sentence summaries.
  - **Categorization:** Automatic sorting into tech, science, business, and more.
  - **Quality Scoring:** 1-10 score based on insightfulness and value.
- **Admin Control:** Secure dashboard to manage feed sources.
- **Modern Stack:** Fully asynchronous Python (FastAPI, SQLAlchemy) with a responsive frontend.

## 🛠 Tech Stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2.0 (Async), APScheduler.
- **Database:** PostgreSQL.
- **AI:** Google Gemini API.
- **Frontend:** Jinja2, Vanilla JavaScript, Tailwind CSS.
- **DevOps:** Docker, Docker Compose.
