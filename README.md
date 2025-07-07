# TechPulse Daily - Tech News Aggregator & Summarizer

An automated web scraping tool that collects, aggregates, and summarizes technology news from multiple sources daily.

## Features

- **RSS Feed Parsing**: Collect articles from 8+ tech news sources
- **AI-Powered Summarization**: Generate concise summaries using OpenAI API
- **Smart Categorization**: Auto-categorize articles by topic (AI, Cybersecurity, etc.)
- **Duplicate Detection**: Prevent duplicate articles
- **Multiple Output Formats**: HTML and Markdown reports
- **Automated Scheduling**: Run daily at configured time
- **Database Storage**: SQLite for article storage and history

## Quick Start

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Settings**:
   - Edit `config.yaml`
   - Add your OpenAI API key for summarization (optional)

3. **Run Once**:
   ```bash
   python tech_scraper.py --run-once
   ```

4. **Start Scheduler**:
   ```bash
   python tech_scraper.py --schedule
   ```

## Configuration

Edit `config.yaml` to customize:

- **Sources**: Add/remove RSS feeds
- **Scheduling**: Set daily run time
- **Output**: Choose formats (HTML, Markdown)
- **Summarization**: Configure AI model settings
- **Storage**: Database and file paths

## Output

Daily reports are generated in the `./daily_news/` directory:
- `techpulse_YYYY-MM-DD.html` - Web-friendly report
- `techpulse_YYYY-MM-DD.md` - Markdown format

## News Sources

Default sources include:
- TechCrunch
- The Verge
- Ars Technica
- Wired
- The Hacker News
- Krebs on Security
- MIT Technology Review
- VentureBeat AI

## Requirements

- Python 3.9+
- OpenAI API key (for summarization)
- Internet connection
- Disk space for database and reports

## Usage Examples

```bash
# Run immediately with default config
python tech_scraper.py --run-once

# Use custom config file
python tech_scraper.py --config my_config.yaml --run-once

# Start background scheduler
python tech_scraper.py --schedule
```

## Troubleshooting

- Check `logs/scraper.log` for error messages
- Verify RSS feed URLs are still active
- Ensure OpenAI API key is valid for summarization
- Review database file permissions

## Architecture

The scraper consists of modular components:
- `DatabaseManager`: SQLite storage
- `RSSParser`: RSS feed processing
- `WebScraper`: Content extraction
- `Summarizer`: AI-powered summaries
- `Categorizer`: Topic classification
- `OutputGenerator`: Report generation

Built according to the Tech News Aggregator PRD specifications.