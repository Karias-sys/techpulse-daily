#!/usr/bin/env python3
"""
TechPulse Daily - Tech News Aggregator & Summarizer
"""

import os
import sys
import sqlite3
import yaml
import logging
import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urljoin, urlparse
from typing import List, Dict, Optional, Tuple
import time

import feedparser
import requests
from bs4 import BeautifulSoup
import openai
from dateutil import parser as date_parser
import schedule


class DatabaseManager:
    """Handle all database operations"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                url TEXT UNIQUE NOT NULL,
                description TEXT,
                content TEXT,
                author TEXT,
                published_date TEXT,
                scraped_date TEXT,
                source TEXT,
                categories TEXT,
                summary TEXT,
                hash TEXT UNIQUE,
                is_duplicate BOOLEAN DEFAULT 0
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                url TEXT NOT NULL,
                type TEXT NOT NULL,
                last_scraped TEXT,
                status TEXT,
                error_count INTEGER DEFAULT 0
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_article(self, article: Dict) -> bool:
        """Save article to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO articles 
                (title, url, description, content, author, published_date, 
                 scraped_date, source, categories, summary, hash, is_duplicate)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                article['title'],
                article['url'],
                article.get('description', ''),
                article.get('content', ''),
                article.get('author', ''),
                article.get('published_date', ''),
                article.get('scraped_date', ''),
                article.get('source', ''),
                json.dumps(article.get('categories', [])),
                article.get('summary', ''),
                article.get('hash', ''),
                article.get('is_duplicate', False)
            ))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()
    
    def get_articles(self, days: int = 1, category: Optional[str] = None) -> List[Dict]:
        """Get articles from the last N days"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        since_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        if category:
            query = '''
                SELECT * FROM articles 
                WHERE scraped_date > ? AND categories LIKE ?
                ORDER BY published_date DESC
            '''
            cursor.execute(query, (since_date, f'%{category}%'))
        else:
            query = '''
                SELECT * FROM articles 
                WHERE scraped_date > ?
                ORDER BY published_date DESC
            '''
            cursor.execute(query, (since_date,))
        
        articles = []
        for row in cursor.fetchall():
            article = {
                'id': row[0],
                'title': row[1],
                'url': row[2],
                'description': row[3],
                'content': row[4],
                'author': row[5],
                'published_date': row[6],
                'scraped_date': row[7],
                'source': row[8],
                'categories': json.loads(row[9]) if row[9] else [],
                'summary': row[10],
                'hash': row[11],
                'is_duplicate': row[12]
            }
            articles.append(article)
        
        conn.close()
        return articles
    
    def cleanup_old_articles(self, keep_days: int):
        """Remove articles older than keep_days"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff_date = (datetime.now() - timedelta(days=keep_days)).isoformat()
        cursor.execute('DELETE FROM articles WHERE scraped_date < ?', (cutoff_date,))
        
        conn.commit()
        conn.close()


class RSSParser:
    """Parse RSS feeds from news sources"""
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'TechPulse Daily/1.0 (News Aggregator)'
        })
    
    def parse_feed(self, url: str, source_name: str) -> List[Dict]:
        """Parse RSS feed and return articles"""
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            feed = feedparser.parse(response.content)
            articles = []
            
            for entry in feed.entries:
                article = {
                    'title': entry.get('title', ''),
                    'url': entry.get('link', ''),
                    'description': entry.get('description', '') or entry.get('summary', ''),
                    'author': entry.get('author', ''),
                    'published_date': self._parse_date(entry.get('published', '')),
                    'scraped_date': datetime.now().isoformat(),
                    'source': source_name,
                    'content': '',
                    'categories': [],
                    'summary': '',
                    'hash': self._generate_hash(entry.get('title', '') + entry.get('link', ''))
                }
                
                if article['title'] and article['url']:
                    articles.append(article)
            
            return articles
            
        except Exception as e:
            logging.error(f"Error parsing RSS feed {url}: {str(e)}")
            return []
    
    def _parse_date(self, date_str: str) -> str:
        """Parse date string to ISO format"""
        if not date_str:
            return datetime.now().isoformat()
        
        try:
            return date_parser.parse(date_str).isoformat()
        except:
            return datetime.now().isoformat()
    
    def _generate_hash(self, content: str) -> str:
        """Generate hash for duplicate detection"""
        return hashlib.md5(content.encode()).hexdigest()


class WebScraper:
    """Fallback web scraper for non-RSS sources"""
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'TechPulse Daily/1.0 (News Aggregator)'
        })
    
    def scrape_article_content(self, url: str) -> str:
        """Scrape full article content from URL"""
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove unwanted elements
            for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                tag.decompose()
            
            # Try to find main content
            content_selectors = [
                'article', '.article-content', '.post-content', 
                '.entry-content', '.content', 'main'
            ]
            
            content = ""
            for selector in content_selectors:
                element = soup.select_one(selector)
                if element:
                    content = element.get_text(strip=True)
                    break
            
            # Fallback to body if no content found
            if not content:
                content = soup.get_text(strip=True)
            
            return content[:5000]  # Limit content length
            
        except Exception as e:
            logging.error(f"Error scraping content from {url}: {str(e)}")
            return ""


class Summarizer:
    """AI-powered article summarization"""
    
    def __init__(self, config: Dict):
        self.config = config
        if config.get('api') == 'openai' and config.get('api_key'):
            openai.api_key = config['api_key']
    
    def summarize_article(self, title: str, content: str) -> str:
        """Generate summary for article"""
        if not self.config.get('api_key'):
            return content[:200] + "..." if len(content) > 200 else content
        
        try:
            prompt = f"""
            Summarize this tech news article in 2-3 sentences. Focus on key facts and implications:
            
            Title: {title}
            Content: {content[:1000]}
            
            Summary:
            """
            
            response = openai.ChatCompletion.create(
                model=self.config.get('model', 'gpt-3.5-turbo'),
                messages=[{"role": "user", "content": prompt}],
                max_tokens=self.config.get('max_length', 100),
                temperature=0.3
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logging.error(f"Error generating summary: {str(e)}")
            return content[:200] + "..." if len(content) > 200 else content


class Categorizer:
    """Categorize articles by topic"""
    
    def __init__(self):
        self.categories = {
            'ai': ['artificial intelligence', 'machine learning', 'AI', 'ML', 'neural', 'deep learning'],
            'cybersecurity': ['security', 'hack', 'breach', 'vulnerability', 'cyber', 'malware'],
            'emerging': ['blockchain', 'quantum', 'VR', 'AR', 'IoT', 'edge computing'],
            'stock': ['stock', 'market', 'IPO', 'earnings', 'valuation', 'investment'],
            'general': []
        }
    
    def categorize_article(self, title: str, description: str, source_categories: List[str]) -> List[str]:
        """Categorize article based on content and source"""
        categories = set(source_categories)
        
        text = (title + " " + description).lower()
        
        for category, keywords in self.categories.items():
            if any(keyword.lower() in text for keyword in keywords):
                categories.add(category)
        
        if not categories:
            categories.add('general')
        
        return list(categories)


class OutputGenerator:
    """Generate output in various formats"""
    
    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
    
    def generate_html_report(self, articles: List[Dict], date: str) -> str:
        """Generate HTML report"""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>TechPulse Daily - {date}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .article {{ border: 1px solid #ddd; padding: 15px; margin: 10px 0; }}
                .title {{ font-size: 18px; font-weight: bold; margin-bottom: 10px; }}
                .meta {{ color: #666; font-size: 12px; margin-bottom: 10px; }}
                .summary {{ margin-bottom: 10px; }}
                .categories {{ background: #f0f0f0; padding: 5px; border-radius: 3px; }}
                .category {{ background: #007cba; color: white; padding: 2px 8px; border-radius: 10px; margin-right: 5px; font-size: 11px; }}
            </style>
        </head>
        <body>
            <h1>TechPulse Daily - {date}</h1>
            <p>Total Articles: {len(articles)}</p>
        """
        
        # Group by category
        categorized = {}
        for article in articles:
            for category in article.get('categories', ['general']):
                if category not in categorized:
                    categorized[category] = []
                categorized[category].append(article)
        
        for category, cat_articles in categorized.items():
            html_content += f"<h2>{category.title()} ({len(cat_articles)} articles)</h2>"
            
            for article in cat_articles:
                html_content += f"""
                <div class="article">
                    <div class="title"><a href="{article['url']}" target="_blank">{article['title']}</a></div>
                    <div class="meta">Source: {article['source']} | Published: {article['published_date'][:10]}</div>
                    <div class="summary">{article.get('summary', article.get('description', ''))}</div>
                    <div class="categories">
                        Categories: {', '.join(article.get('categories', []))}
                    </div>
                </div>
                """
        
        html_content += "</body></html>"
        
        output_file = self.output_dir / f"techpulse_{date}.html"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return str(output_file)
    
    def generate_markdown_report(self, articles: List[Dict], date: str) -> str:
        """Generate Markdown report"""
        md_content = f"# TechPulse Daily - {date}\n\n"
        md_content += f"Total Articles: {len(articles)}\n\n"
        
        # Group by category
        categorized = {}
        for article in articles:
            for category in article.get('categories', ['general']):
                if category not in categorized:
                    categorized[category] = []
                categorized[category].append(article)
        
        for category, cat_articles in categorized.items():
            md_content += f"## {category.title()} ({len(cat_articles)} articles)\n\n"
            
            for article in cat_articles:
                md_content += f"### [{article['title']}]({article['url']})\n\n"
                md_content += f"**Source:** {article['source']} | **Published:** {article['published_date'][:10]}\n\n"
                md_content += f"{article.get('summary', article.get('description', ''))}\n\n"
                md_content += f"**Categories:** {', '.join(article.get('categories', []))}\n\n"
                md_content += "---\n\n"
        
        output_file = self.output_dir / f"techpulse_{date}.md"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        return str(output_file)


class TechScraper:
    """Main scraper class"""
    
    def __init__(self, config_path: str = 'config.yaml'):
        self.config = self._load_config(config_path)
        self.db = DatabaseManager(self.config['database']['path'])
        self.rss_parser = RSSParser()
        self.web_scraper = WebScraper()
        self.summarizer = Summarizer(self.config['summarization'])
        self.categorizer = Categorizer()
        self.output_generator = OutputGenerator(self.config['general']['output_dir'])
        
        # Setup logging
        self._setup_logging()
    
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logging.error(f"Error loading config: {str(e)}")
            sys.exit(1)
    
    def _setup_logging(self):
        """Setup logging configuration"""
        log_dir = Path(self.config['logging']['file']).parent
        log_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=getattr(logging, self.config['logging']['level']),
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.config['logging']['file']),
                logging.StreamHandler()
            ]
        )
    
    def scrape_all_sources(self) -> List[Dict]:
        """Scrape all configured sources including Google News feeds"""
        all_articles = []
        
        # Scrape regular RSS sources
        for source in self.config['sources']:
            logging.info(f"Scraping {source['name']}...")
            
            try:
                if source['type'] == 'rss':
                    articles = self.rss_parser.parse_feed(source['url'], source['name'])
                else:
                    continue  # Skip non-RSS for now
                
                # Limit articles per source
                max_articles = self.config['general'].get('max_articles_per_source', 20)
                articles = articles[:max_articles]
                
                for article in articles:
                    # Add source categories
                    article['categories'] = source.get('categories', [])
                    
                    # Categorize article
                    article['categories'] = self.categorizer.categorize_article(
                        article['title'], 
                        article['description'], 
                        article['categories']
                    )
                    
                    # Scrape full content if needed
                    if not article['content']:
                        article['content'] = self.web_scraper.scrape_article_content(article['url'])
                    
                    # Generate summary
                    content_for_summary = article['content'] or article['description']
                    if content_for_summary:
                        article['summary'] = self.summarizer.summarize_article(
                            article['title'], 
                            content_for_summary
                        )
                    
                    # Save to database
                    if self.db.save_article(article):
                        all_articles.append(article)
                        logging.info(f"Saved: {article['title']}")
                    else:
                        logging.info(f"Duplicate: {article['title']}")
                
                logging.info(f"Scraped {len(articles)} articles from {source['name']}")
                
            except Exception as e:
                logging.error(f"Error scraping {source['name']}: {str(e)}")
        
        # Scrape Google News feeds if configured
        google_feeds = self.config.get('google_news_feeds', [])
        for feed_config in google_feeds:
            logging.info(f"Scraping Google News: {feed_config['name']}...")
            
            try:
                google_url = self._generate_google_news_url(feed_config['query'])
                articles = self.rss_parser.parse_feed(google_url, f"Google: {feed_config['name']}")
                
                # Limit articles per Google News feed
                max_articles = self.config['general'].get('max_articles_per_source', 10)
                articles = articles[:max_articles]
                
                for article in articles:
                    # Add Google News feed categories
                    article['categories'] = feed_config.get('categories', [])
                    
                    # Categorize article
                    article['categories'] = self.categorizer.categorize_article(
                        article['title'], 
                        article['description'], 
                        article['categories']
                    )
                    
                    # Generate summary for Google News articles
                    content_for_summary = article['description']
                    if content_for_summary:
                        article['summary'] = self.summarizer.summarize_article(
                            article['title'], 
                            content_for_summary
                        )
                    
                    # Save to database
                    if self.db.save_article(article):
                        all_articles.append(article)
                        logging.info(f"Saved Google News: {article['title']}")
                    else:
                        logging.info(f"Duplicate Google News: {article['title']}")
                
                logging.info(f"Scraped {len(articles)} articles from Google News: {feed_config['name']}")
                
            except Exception as e:
                logging.error(f"Error scraping Google News {feed_config['name']}: {str(e)}")
        
        return all_articles
    
    def _generate_google_news_url(self, query: str) -> str:
        """Generate Google News RSS URL from search query"""
        from urllib.parse import urlencode
        
        base_url = "https://news.google.com/rss/search"
        params = {
            'q': query,
            'hl': 'en-US',
            'gl': 'US',
            'ceid': 'US:en'
        }
        return f"{base_url}?{urlencode(params)}"
    
    def run_daily_scrape(self):
        """Run daily scraping process"""
        logging.info("Starting daily scrape...")
        
        # Scrape all sources
        articles = self.scrape_all_sources()
        
        # Get today's articles from database
        today_articles = self.db.get_articles(days=1)
        
        # Generate outputs
        date_str = datetime.now().strftime('%Y-%m-%d')
        
        if 'html' in self.config['output']['formats']:
            html_file = self.output_generator.generate_html_report(today_articles, date_str)
            logging.info(f"Generated HTML report: {html_file}")
        
        if 'markdown' in self.config['output']['formats']:
            md_file = self.output_generator.generate_markdown_report(today_articles, date_str)
            logging.info(f"Generated Markdown report: {md_file}")
        
        # Cleanup old articles
        self.db.cleanup_old_articles(self.config['general']['keep_days'])
        
        logging.info(f"Daily scrape completed. Processed {len(today_articles)} articles.")
    
    def run_scheduler(self):
        """Run the scheduler"""
        run_time = self.config['general']['run_time']
        schedule.every().day.at(run_time).do(self.run_daily_scrape)
        
        logging.info(f"Scheduler started. Will run daily at {run_time}")
        
        while True:
            schedule.run_pending()
            time.sleep(60)


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='TechPulse Daily News Scraper')
    parser.add_argument('--config', default='config.yaml', help='Config file path')
    parser.add_argument('--run-once', action='store_true', help='Run once and exit')
    parser.add_argument('--schedule', action='store_true', help='Run scheduler')
    
    args = parser.parse_args()
    
    scraper = TechScraper(args.config)
    
    if args.run_once:
        scraper.run_daily_scrape()
    elif args.schedule:
        scraper.run_scheduler()
    else:
        print("Use --run-once to run immediately or --schedule to start scheduler")


if __name__ == "__main__":
    main()