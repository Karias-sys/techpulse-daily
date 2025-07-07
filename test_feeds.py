#!/usr/bin/env python3
"""
RSS Feed Testing Script for TechPulse Daily
Tests all RSS feeds from config.yaml and reports health metrics
"""

import yaml
import requests
import feedparser
import time
from datetime import datetime
from urllib.parse import urlencode
import sys
from pathlib import Path

class FeedTester:
    def __init__(self, config_path='config.yaml'):
        """Initialize the feed tester with configuration"""
        self.config = self._load_config(config_path)
        self.results = []
        
    def _load_config(self, config_path):
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"Error loading config: {e}")
            sys.exit(1)
    
    def generate_google_news_feed(self, query):
        """Generate Google News RSS feed URL from query"""
        base_url = "https://news.google.com/rss/search"
        params = {
            'q': query,
            'hl': 'en-US',
            'gl': 'US',
            'ceid': 'US:en'
        }
        return f"{base_url}?{urlencode(params)}"
    
    def test_feed(self, name, url, categories=None):
        """Test individual RSS feed and return detailed status"""
        start_time = time.time()
        
        try:
            # Make HTTP request
            response = requests.get(url, timeout=15, headers={
                'User-Agent': 'TechPulse Daily Feed Tester/1.0'
            })
            response_time = time.time() - start_time
            
            # Check HTTP status
            if response.status_code != 200:
                return {
                    'name': name,
                    'url': url,
                    'status': 'HTTP_ERROR',
                    'error': f"HTTP {response.status_code}: {response.reason}",
                    'response_time': response_time,
                    'categories': categories or []
                }
            
            # Parse RSS feed
            feed = feedparser.parse(response.content)
            
            # Check for feed errors
            if hasattr(feed, 'bozo') and feed.bozo:
                status = 'MALFORMED'
                error = f"Feed parsing warning: {getattr(feed, 'bozo_exception', 'Unknown')}"
            else:
                status = 'OK' if feed.entries else 'EMPTY'
                error = None if feed.entries else 'No entries found'
            
            # Extract feed information
            last_updated = 'Unknown'
            if hasattr(feed.feed, 'updated'):
                last_updated = feed.feed.updated
            elif hasattr(feed.feed, 'published'):
                last_updated = feed.feed.published
            elif feed.entries and hasattr(feed.entries[0], 'published'):
                last_updated = feed.entries[0].published
            
            # Analyze entry quality
            valid_entries = 0
            for entry in feed.entries:
                if (hasattr(entry, 'title') and entry.title and 
                    hasattr(entry, 'link') and entry.link):
                    valid_entries += 1
            
            return {
                'name': name,
                'url': url,
                'status': status,
                'entry_count': len(feed.entries),
                'valid_entries': valid_entries,
                'last_updated': last_updated,
                'response_time': response_time,
                'error': error,
                'categories': categories or [],
                'feed_title': getattr(feed.feed, 'title', 'Unknown'),
                'feed_description': getattr(feed.feed, 'description', 'Unknown')
            }
            
        except requests.exceptions.Timeout:
            return {
                'name': name,
                'url': url,
                'status': 'TIMEOUT',
                'error': 'Request timed out after 15 seconds',
                'response_time': time.time() - start_time,
                'categories': categories or []
            }
        except requests.exceptions.ConnectionError:
            return {
                'name': name,
                'url': url,
                'status': 'CONNECTION_ERROR',
                'error': 'Failed to connect to server',
                'response_time': time.time() - start_time,
                'categories': categories or []
            }
        except Exception as e:
            return {
                'name': name,
                'url': url,
                'status': 'ERROR',
                'error': str(e),
                'response_time': time.time() - start_time,
                'categories': categories or []
            }
    
    def test_all_feeds(self):
        """Test all feeds from configuration"""
        print("RSS Feed Test Report")
        print("=" * 50)
        
        # Test regular RSS sources
        sources = self.config.get('sources', [])
        print(f"Testing {len(sources)} RSS feeds...")
        print()
        
        for i, source in enumerate(sources, 1):
            print(f"[{i:2d}/{len(sources)}] Testing {source['name']}...", end=' ')
            
            result = self.test_feed(
                source['name'], 
                source['url'], 
                source.get('categories', [])
            )
            self.results.append(result)
            
            # Print immediate status
            if result['status'] == 'OK':
                print(f"✅ ({result['response_time']:.2f}s) - {result['entry_count']} entries")
            elif result['status'] == 'EMPTY':
                print(f"⚠️  ({result['response_time']:.2f}s) - No entries")
            elif result['status'] == 'MALFORMED':
                print(f"⚠️  ({result['response_time']:.2f}s) - {result['entry_count']} entries (malformed)")
            else:
                print(f"❌ ({result['response_time']:.2f}s) - {result['error']}")
        
        # Test Google News feeds if configured
        google_feeds = self.config.get('google_news_feeds', [])
        if google_feeds:
            print(f"\nTesting {len(google_feeds)} Google News feeds...")
            print()
            
            for i, feed_config in enumerate(google_feeds, 1):
                print(f"[G{i:2d}] Testing {feed_config['name']}...", end=' ')
                
                url = self.generate_google_news_feed(feed_config['query'])
                result = self.test_feed(
                    f"Google: {feed_config['name']}", 
                    url, 
                    feed_config.get('categories', [])
                )
                self.results.append(result)
                
                # Print immediate status
                if result['status'] == 'OK':
                    print(f"✅ ({result['response_time']:.2f}s) - {result['entry_count']} entries")
                elif result['status'] == 'EMPTY':
                    print(f"⚠️  ({result['response_time']:.2f}s) - No entries")
                else:
                    print(f"❌ ({result['response_time']:.2f}s) - {result['error']}")
    
    def generate_summary_report(self):
        """Generate and display summary report"""
        if not self.results:
            print("\nNo feeds tested.")
            return
        
        successful = [r for r in self.results if r['status'] == 'OK']
        malformed = [r for r in self.results if r['status'] == 'MALFORMED']
        empty = [r for r in self.results if r['status'] == 'EMPTY']
        failed = [r for r in self.results if r['status'] not in ['OK', 'MALFORMED', 'EMPTY']]
        
        total_feeds = len(self.results)
        avg_response_time = sum(r.get('response_time', 0) for r in self.results) / total_feeds
        total_articles = sum(r.get('entry_count', 0) for r in successful + malformed)
        
        print("\n" + "=" * 50)
        print("SUMMARY REPORT")
        print("=" * 50)
        print(f"Total feeds tested: {total_feeds}")
        print(f"Successful: {len(successful)}/{total_feeds} ({len(successful)/total_feeds*100:.1f}%)")
        print(f"Malformed: {len(malformed)}/{total_feeds}")
        print(f"Empty: {len(empty)}/{total_feeds}")
        print(f"Failed: {len(failed)}/{total_feeds}")
        print(f"Average response time: {avg_response_time:.2f}s")
        print(f"Total articles found: {total_articles}")
        
        # Category breakdown
        category_stats = {}
        for result in successful + malformed:
            for category in result.get('categories', []):
                if category not in category_stats:
                    category_stats[category] = {'feeds': 0, 'articles': 0}
                category_stats[category]['feeds'] += 1
                category_stats[category]['articles'] += result.get('entry_count', 0)
        
        if category_stats:
            print(f"\nCategory breakdown:")
            for category, stats in sorted(category_stats.items()):
                print(f"  {category}: {stats['feeds']} feeds, {stats['articles']} articles")
        
        # Failed feeds requiring attention
        if failed:
            print(f"\n❌ Failed feeds requiring attention:")
            for i, result in enumerate(failed, 1):
                print(f"{i:2d}. {result['name']}")
                print(f"    URL: {result['url']}")
                print(f"    Error: {result['error']}")
        
        # Empty feeds
        if empty:
            print(f"\n⚠️  Empty feeds (may be temporary):")
            for i, result in enumerate(empty, 1):
                print(f"{i:2d}. {result['name']}")
        
        # Performance issues
        slow_feeds = [r for r in self.results if r.get('response_time', 0) > 5.0]
        if slow_feeds:
            print(f"\n🐌 Slow feeds (>5 seconds):")
            for result in slow_feeds:
                print(f"   {result['name']}: {result['response_time']:.2f}s")
    
    def save_detailed_report(self, filename=None):
        """Save detailed report to file"""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"feed_test_report_{timestamp}.txt"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"RSS Feed Test Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")
            
            for result in self.results:
                f.write(f"Feed: {result['name']}\n")
                f.write(f"URL: {result['url']}\n")
                f.write(f"Status: {result['status']}\n")
                f.write(f"Response Time: {result.get('response_time', 0):.2f}s\n")
                f.write(f"Categories: {', '.join(result.get('categories', []))}\n")
                
                if result.get('entry_count') is not None:
                    f.write(f"Entries: {result['entry_count']}\n")
                    f.write(f"Valid Entries: {result.get('valid_entries', 0)}\n")
                
                if result.get('last_updated'):
                    f.write(f"Last Updated: {result['last_updated']}\n")
                
                if result.get('error'):
                    f.write(f"Error: {result['error']}\n")
                
                f.write("-" * 40 + "\n\n")
        
        print(f"\nDetailed report saved to: {filename}")

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test RSS feeds for TechPulse Daily')
    parser.add_argument('--config', default='config.yaml', help='Config file path')
    parser.add_argument('--save-report', action='store_true', help='Save detailed report to file')
    parser.add_argument('--quick', action='store_true', help='Quick test (skip detailed analysis)')
    
    args = parser.parse_args()
    
    if not Path(args.config).exists():
        print(f"Error: Config file '{args.config}' not found.")
        sys.exit(1)
    
    tester = FeedTester(args.config)
    
    print(f"Testing RSS feeds from: {args.config}")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Run tests
    start_time = time.time()
    tester.test_all_feeds()
    total_time = time.time() - start_time
    
    # Generate reports
    tester.generate_summary_report()
    
    if args.save_report:
        tester.save_detailed_report()
    
    print(f"\nTesting completed in {total_time:.1f} seconds")
    
    # Exit with error code if any feeds failed
    failed_count = len([r for r in tester.results if r['status'] not in ['OK', 'MALFORMED', 'EMPTY']])
    if failed_count > 0:
        print(f"\n⚠️  {failed_count} feeds failed - check configuration")
        sys.exit(1)
    else:
        print("\n✅ All feeds are accessible")

if __name__ == "__main__":
    main()