# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TechPulse Daily is a tech news aggregator and summarizer that collects articles from RSS feeds, processes them with AI-powered summarization, and provides both a web interface and daily reports. The system consists of two main components:

1. **Backend Scraper** (`tech_scraper.py`) - Collects, processes, and stores articles
2. **Web Interface** (`app.py`) - Flask-based UI for browsing and managing articles

## Architecture

### Core Components

- **DatabaseManager** (`database.py`): SQLAlchemy-based models and database operations
- **RSSParser** (`tech_scraper.py`): Fetches and processes RSS feeds
- **WebScraper** (`tech_scraper.py`): Extracts full article content
- **Summarizer** (`tech_scraper.py`): OpenAI-powered article summarization
- **Categorizer** (`tech_scraper.py`): Automatic topic classification
- **OutputGenerator** (`tech_scraper.py`): HTML/Markdown report generation

### Database Schema

Articles are stored with these key fields:
- Basic metadata (title, URL, author, dates)
- Content (description, full content, summary)
- Classification (source, categories, hash for deduplication)
- User interaction (is_read, favorites relationship)

## Development Commands

### Running the Application

```bash
# Install dependencies
pip install -r requirements.txt

# Run scraper once
python tech_scraper.py --run-once

# Start scheduled scraper (runs daily at configured time)
python tech_scraper.py --schedule

# Start web interface
python app.py
```

### Testing

```bash
# Test RSS feed parsing
python test_feeds.py
```

## Configuration

The application uses `config.yaml` for configuration:

- **Sources**: RSS feed URLs with categories
- **Summarization**: OpenAI API settings
- **Output**: Report generation settings
- **Database**: SQLite database path
- **Scheduling**: Daily run time configuration

## Key Files

- `tech_scraper.py`: Main scraper with all processing logic
- `app.py`: Flask web application with API endpoints
- `database.py`: SQLAlchemy models and database operations
- `config.yaml`: Application configuration
- `requirements.txt`: Python dependencies
- `templates/`: HTML templates (index.html, favorites.html, archive.html)
- `static/`: CSS, JS, and other static assets

## Data Flow

1. RSS feeds are parsed from configured sources
2. Articles are deduplicated using content hashing
3. Full content is scraped from article URLs
4. Articles are categorized and summarized using OpenAI
5. Data is stored in SQLite database
6. Reports are generated in HTML/Markdown formats
7. Web interface provides browsing, search, and favorites functionality

## Article Categories

The system automatically categorizes articles into:
- `general`: General tech news
- `ai`: AI and machine learning
- `cybersecurity`: Security and privacy
- `emerging`: Emerging technologies
- `stock`: Financial and market news
- `startups`: Startup and venture capital news

## API Endpoints

The Flask app exposes these key endpoints:
- `/api/articles`: Get articles with filtering
- `/api/favorites`: Get/manage favorite articles
- `/api/search`: Search articles
- `/api/categories`: Get available categories
- `/api/stats`: Get dashboard statistics

## Development Notes

- The web interface automatically finds available ports (5000, 5001, etc.)
- Database connections are properly cleaned up with signal handlers
- Articles are deduplicated using MD5 hashing of content
- The system supports multiple output formats (HTML, Markdown)
- Logging is configured to `logs/scraper.log`