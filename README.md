# reNews: AI-Powered Technical News Aggregator

reNews is a sophisticated technical news aggregator that automates the process of fetching RSS feeds, extracting core content, and performing deep AI analysis using Google Gemini. It goes beyond simple headlines by providing concise summaries, categorical classification, and quality scoring for every article.

## 🚀 Key Features

- **Automated Fetching:** Periodically polls RSS/Atom feeds for new content.
- **Clean Extraction:** Uses `trafilatura` to strip ads, navbars, and noise, focusing only on the article text.
- **AI-Driven Insights:** 
    - **Summarization:** 1-2 sentence high-impact summaries.
    - **Categorization:** Automatic sorting into tech, science, business, and more.
    - **Quality Scoring:** 1-10 score based on insightfulness and value.
- **Admin Control:** Secure dashboard to manage feed sources.
- **Modern Stack:** Fully asynchronous Python (FastAPI, SQLAlchemy) with a responsive Tailwind CSS frontend.

## 🛠 Tech Stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2.0 (Async), APScheduler.
- **Database:** PostgreSQL.
- **AI:** Google Gemini API (`gemini-1.5-flash`).
- **Frontend:** Jinja2, Vanilla JavaScript, Tailwind CSS.
- **DevOps:** Docker, Docker Compose.

## 🚦 Getting Started

### Prerequisites
- Docker & Docker Compose
- Google Gemini API Key

### Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd reNews
   ```

2. **Configure Environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your GEMINI_API_KEY and other settings
   ```

3. **Launch with Docker:**
   ```bash
   docker-compose up --build
   ```

4. **Access the App:**
   - Dashboard: `http://localhost:8000`
   - Admin Panel: `http://localhost:8000/admin` (Default: admin/admin)

## 📖 API Documentation
Once running, interactive API docs are available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 🤝 Contributing
1. Fork the project.
2. Create your feature branch (`git checkout -b feature/AmazingFeature`).
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`).
4. Push to the branch (`git push origin feature/AmazingFeature`).
5. Open a Pull Request.
