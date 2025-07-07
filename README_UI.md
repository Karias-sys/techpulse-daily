# TechPulse Daily - Web UI Setup Guide

This guide explains how to set up and run the TechPulse Daily web interface.

## Prerequisites

1. **Python 3.9+** installed
2. **TechPulse Daily scraper** already set up (from main README.md)
3. **Web browser** for accessing the UI

## Quick Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Set Up Database
Run the migration script to convert scraper data to the UI database:
```bash
python migrate_to_db.py
```

This will:
- Create the SQLite database for the UI
- Migrate existing articles from the scraper
- Create sample data if no scraper data exists

### 3. Start the Web Server
```bash
python app.py
```

The web interface will be available at: **http://localhost:5000**

## Features

### 🏠 Home Page (`/`)
- **Today's Articles**: Latest tech news from all sources
- **Statistics Dashboard**: Article counts and reading stats
- **Real-time Search**: Search across titles and summaries (300ms debounce)
- **Category Filters**: AI & ML, Cybersecurity, Emerging Tech, Stock Market, General
- **Favorites**: Star articles for later reading
- **Read Tracking**: Mark articles as read when clicked

### ⭐ Favorites Page (`/favorites`)
- **Starred Articles**: View all favorited articles
- **Search Favorites**: Find specific saved articles
- **Remove Favorites**: Unstar articles individually or clear all
- **Persistent Storage**: Favorites saved in database

### 📚 Archive Page (`/archive`)
- **Historical Articles**: Browse past articles with date filters
- **Time Filters**: Last 7 days, 30 days, 3 months, or all time
- **Category Filtering**: Same category system as home page
- **Pagination**: Navigate through large article sets
- **Search History**: Search across all archived content

## UI Design

### Dark Theme
- **Optimized for Reading**: Dark navy background (#0f172a)
- **High Contrast**: Light text on dark cards
- **Blue Accent**: Primary blue (#2563eb) for links and buttons
- **Amber Highlights**: Golden yellow (#f59e0b) for favorites

### Responsive Design
- **Mobile-First**: Works on phones, tablets, and desktops
- **Bootstrap 5**: Modern responsive grid system
- **Touch-Friendly**: Large tap targets for mobile users
- **Sticky Navigation**: Always accessible top menu

### Category Color Coding
- **AI & ML**: Purple (#7c3aed)
- **Cybersecurity**: Red (#dc2626)
- **Emerging Tech**: Green (#059669)
- **Stock Market**: Orange (#ea580c)
- **General Tech**: Blue (#2563eb)

## API Endpoints

The Flask app provides REST API endpoints:

### Articles
- `GET /api/articles` - Get articles with optional filters
- `GET /api/today` - Get today's articles
- `GET /api/search?q=query` - Search articles

### Favorites
- `GET /api/favorites` - Get favorited articles
- `POST /api/favorite/<id>` - Toggle favorite status

### Utility
- `GET /api/stats` - Dashboard statistics
- `GET /api/categories` - Available categories
- `POST /api/read/<id>` - Mark article as read

## File Structure

```
tech-news-scraper/
├── app.py              # Flask web application
├── database.py         # SQLAlchemy models and database operations
├── migrate_to_db.py    # Data migration script
├── tech_scraper.py     # Original scraper (preserved)
├── config.yaml         # Scraper configuration (preserved)
├── requirements.txt    # Python dependencies (updated)
├── templates/          # HTML templates
│   ├── index.html      # Home page
│   ├── favorites.html  # Favorites page
│   └── archive.html    # Archive page
├── static/             # Static assets (created but empty)
└── data/
    └── news.db         # SQLite database for UI
```

## Integration with Scraper

The UI works alongside the existing scraper:

1. **Scraper Continues Running**: The original `tech_scraper.py` keeps working
2. **Shared Data**: Migration script converts scraper database to UI format
3. **Real-time Updates**: Run migration script after scraper runs to sync new articles
4. **Backward Compatible**: Original scraper functionality unchanged

## Daily Workflow

1. **Morning**: Scraper runs automatically (if scheduled)
2. **Sync Data**: Run `python migrate_to_db.py` to update UI database
3. **Browse News**: Use web interface throughout the day
4. **Evening**: Review favorites and mark articles as read

## Troubleshooting

### Database Issues
```bash
# Reset database
rm data/news.db
python migrate_to_db.py
```

### Missing Articles
```bash
# Re-run migration
python migrate_to_db.py
```

### Port Already in Use
```bash
# Change port in app.py or kill existing process
lsof -ti:5000 | xargs kill -9
```

### Search Not Working
- Check that articles have content in summary or description fields
- Verify database contains articles with non-empty text

## Customization

### Change Colors
Edit CSS custom properties in template files:
```css
:root {
    --primary-color: #2563eb;    /* Main blue */
    --accent-color: #f59e0b;     /* Favorite yellow */
    --bg-color: #0f172a;         /* Background */
    --card-bg: #1e293b;          /* Card background */
}
```

### Add Sources
1. Update `config.yaml` with new RSS feeds
2. Run scraper: `python tech_scraper.py --run-once`
3. Sync data: `python migrate_to_db.py`

### Modify Categories
Edit the `categorizer` in `tech_scraper.py` and update category mappings in templates.

## Performance

- **SQLite Database**: Efficient for local use, handles thousands of articles
- **Responsive Design**: Fast loading on all devices
- **Debounced Search**: Reduces server load with 300ms delay
- **Pagination**: Archive page loads articles in chunks

The UI is designed for personal use and can handle typical tech news volumes efficiently.