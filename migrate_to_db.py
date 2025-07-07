#!/usr/bin/env python3
"""
Migration script to convert existing scraper data to SQLite database
"""

import sqlite3
import json
from datetime import datetime
from dateutil import parser as date_parser
from pathlib import Path
import sys

from database import DatabaseManager, Article

def migrate_from_existing_db():
    """Migrate from existing SQLite database created by scraper"""
    
    # Check if the scraper's database exists
    scraper_db_path = './news_data.db'
    if not Path(scraper_db_path).exists():
        print(f"Scraper database {scraper_db_path} not found. Run the scraper first.")
        return False
    
    # Initialize new database
    db = DatabaseManager()
    
    # Connect to existing scraper database
    conn = sqlite3.connect(scraper_db_path)
    cursor = conn.cursor()
    
    try:
        # Get all articles from scraper database
        cursor.execute('SELECT * FROM articles')
        articles = cursor.fetchall()
        
        # Get column names
        cursor.execute('PRAGMA table_info(articles)')
        columns = [column[1] for column in cursor.fetchall()]
        
        migrated_count = 0
        
        for article_row in articles:
            # Convert row to dictionary
            article_dict = dict(zip(columns, article_row))
            
            # Parse dates
            published_date = None
            if article_dict.get('published_date'):
                try:
                    published_date = date_parser.parse(article_dict['published_date'])
                except:
                    published_date = None
            
            scraped_date = None
            if article_dict.get('scraped_date'):
                try:
                    scraped_date = date_parser.parse(article_dict['scraped_date'])
                except:
                    scraped_date = datetime.utcnow()
            
            # Create article data for new database
            article_data = {
                'title': article_dict.get('title', ''),
                'url': article_dict.get('url', ''),
                'description': article_dict.get('description', ''),
                'content': article_dict.get('content', ''),
                'author': article_dict.get('author', ''),
                'published_date': published_date,
                'scraped_date': scraped_date,
                'source': article_dict.get('source', ''),
                'categories': article_dict.get('categories', '[]'),
                'summary': article_dict.get('summary', ''),
                'hash': article_dict.get('hash', ''),
                'is_duplicate': bool(article_dict.get('is_duplicate', False)),
                'is_read': False  # New field
            }
            
            # Add to new database
            try:
                new_article = db.add_article(article_data)
                if new_article:
                    migrated_count += 1
                    print(f"Migrated: {article_data['title'][:50]}...")
                else:
                    print(f"Failed to migrate: {article_data['title'][:50]}...")
            except Exception as e:
                print(f"Error migrating article: {e}")
        
        print(f"\nMigration completed! Migrated {migrated_count} articles.")
        
    except Exception as e:
        print(f"Error during migration: {e}")
        return False
    
    finally:
        conn.close()
        db.close()
    
    return True

def create_sample_data():
    """Create sample data for testing if no existing data"""
    
    db = DatabaseManager()
    
    sample_articles = [
        {
            'title': 'Revolutionary AI Breakthrough in Natural Language Processing',
            'url': 'https://example.com/ai-breakthrough',
            'description': 'Scientists achieve new milestone in AI language understanding',
            'content': 'Full article content about AI breakthrough...',
            'author': 'Tech Reporter',
            'published_date': datetime.utcnow(),
            'scraped_date': datetime.utcnow(),
            'source': 'TechCrunch',
            'categories': '["ai", "general"]',
            'summary': 'Scientists have achieved a major breakthrough in AI language processing.',
            'hash': 'sample_hash_1',
            'is_duplicate': False,
            'is_read': False
        },
        {
            'title': 'Major Cybersecurity Threat Discovered in Popular Software',
            'url': 'https://example.com/cyber-threat',
            'description': 'Security researchers find critical vulnerability',
            'content': 'Full article content about cybersecurity threat...',
            'author': 'Security Expert',
            'published_date': datetime.utcnow(),
            'scraped_date': datetime.utcnow(),
            'source': 'The Hacker News',
            'categories': '["cybersecurity"]',
            'summary': 'A critical security vulnerability has been discovered in widely-used software.',
            'hash': 'sample_hash_2',
            'is_duplicate': False,
            'is_read': False
        },
        {
            'title': 'Tech Stocks Rally on Earnings Reports',
            'url': 'https://example.com/tech-stocks',
            'description': 'Major tech companies exceed expectations',
            'content': 'Full article content about tech stocks...',
            'author': 'Financial Analyst',
            'published_date': datetime.utcnow(),
            'scraped_date': datetime.utcnow(),
            'source': 'MarketWatch',
            'categories': '["stock", "general"]',
            'summary': 'Tech stocks are surging following better-than-expected earnings reports.',
            'hash': 'sample_hash_3',
            'is_duplicate': False,
            'is_read': False
        }
    ]
    
    for article_data in sample_articles:
        db.add_article(article_data)
        print(f"Created sample article: {article_data['title'][:50]}...")
    
    print(f"\nCreated {len(sample_articles)} sample articles.")
    db.close()

def main():
    """Main migration function"""
    
    # Create data directory
    Path('data').mkdir(exist_ok=True)
    
    print("TechPulse Daily - Database Migration")
    print("="*40)
    
    # Try to migrate from existing scraper database
    if migrate_from_existing_db():
        print("\nMigration successful! You can now run the Flask app.")
    else:
        print("\nNo existing data found. Creating sample data for testing...")
        create_sample_data()
        print("\nSample data created! You can now run the Flask app.")
        print("To get real data, run the scraper first: python tech_scraper.py --run-once")

if __name__ == "__main__":
    main()