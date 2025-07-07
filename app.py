#!/usr/bin/env python3
"""
Flask web application for TechPulse Daily UI
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for
from database import DatabaseManager
import json
from datetime import datetime, date
import atexit
import signal
import sys

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'

# Initialize database
db = DatabaseManager()

# Cleanup function
def cleanup():
    """Cleanup resources on shutdown"""
    try:
        if 'db' in globals():
            db.close()
    except:
        pass

# Register cleanup handlers
atexit.register(cleanup)
signal.signal(signal.SIGTERM, lambda s, f: cleanup())
signal.signal(signal.SIGINT, lambda s, f: cleanup())

@app.route('/')
def index():
    """Homepage with today's articles"""
    return render_template('index.html')

@app.route('/favorites')
def favorites():
    """Favorites page"""
    return render_template('favorites.html')

@app.route('/archive')
def archive():
    """Archive page with historical articles"""
    return render_template('archive.html')

@app.route('/category/<category_name>')
def category_view(category_name):
    """Category filtered view"""
    return render_template('index.html', category=category_name)

# API Endpoints

@app.route('/api/articles')
def api_articles():
    """Fetch articles with optional filters"""
    try:
        # Get query parameters
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        category = request.args.get('category', None)
        search = request.args.get('search', None)
        days = request.args.get('days', None, type=int)
        
        # Get articles from database
        articles = db.get_articles(
            limit=limit,
            offset=offset,
            category=category,
            search=search,
            days=days
        )
        
        # Convert to dictionaries
        articles_data = [article.to_dict() for article in articles]
        
        # Parse categories JSON for each article
        for article in articles_data:
            try:
                if article['categories']:
                    article['categories'] = json.loads(article['categories'])
                else:
                    article['categories'] = []
            except:
                article['categories'] = [article['categories']] if article['categories'] else []
        
        return jsonify({
            'success': True,
            'articles': articles_data,
            'total': len(articles_data)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/favorite/<int:article_id>', methods=['POST'])
def api_toggle_favorite(article_id):
    """Toggle favorite status of an article"""
    try:
        is_favorited = db.toggle_favorite(article_id)
        
        return jsonify({
            'success': True,
            'is_favorited': is_favorited,
            'article_id': article_id
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/read/<int:article_id>', methods=['POST'])
def api_mark_read(article_id):
    """Mark article as read"""
    try:
        success = db.mark_as_read(article_id)
        
        return jsonify({
            'success': success,
            'article_id': article_id
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/stats')
def api_stats():
    """Get dashboard statistics"""
    try:
        stats = db.get_statistics()
        
        return jsonify({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/search')
def api_search():
    """Search articles"""
    try:
        query = request.args.get('q', '')
        limit = request.args.get('limit', 20, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        if not query:
            return jsonify({
                'success': True,
                'articles': [],
                'total': 0
            })
        
        articles = db.get_articles(
            limit=limit,
            offset=offset,
            search=query
        )
        
        # Convert to dictionaries
        articles_data = [article.to_dict() for article in articles]
        
        # Parse categories JSON for each article
        for article in articles_data:
            try:
                if article['categories']:
                    article['categories'] = json.loads(article['categories'])
                else:
                    article['categories'] = []
            except:
                article['categories'] = [article['categories']] if article['categories'] else []
        
        return jsonify({
            'success': True,
            'articles': articles_data,
            'total': len(articles_data),
            'query': query
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/favorites')
def api_favorites():
    """Get favorited articles"""
    try:
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        favorites = db.get_favorites(limit=limit, offset=offset)
        
        # Convert to dictionaries
        articles_data = [article.to_dict() for article in favorites]
        
        # Parse categories JSON for each article
        for article in articles_data:
            try:
                if article['categories']:
                    article['categories'] = json.loads(article['categories'])
                else:
                    article['categories'] = []
            except:
                article['categories'] = [article['categories']] if article['categories'] else []
        
        return jsonify({
            'success': True,
            'articles': articles_data,
            'total': len(articles_data)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/categories')
def api_categories():
    """Get all available categories"""
    try:
        categories = db.get_categories()
        
        # Add standard categories if not present
        standard_categories = ['all', 'ai', 'cybersecurity', 'emerging', 'stock', 'general']
        all_categories = list(set(standard_categories + categories))
        
        return jsonify({
            'success': True,
            'categories': all_categories
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/today')
def api_today():
    """Get today's articles"""
    try:
        articles = db.get_articles(days=1)
        
        # Convert to dictionaries
        articles_data = [article.to_dict() for article in articles]
        
        # Parse categories JSON for each article
        for article in articles_data:
            try:
                if article['categories']:
                    article['categories'] = json.loads(article['categories'])
                else:
                    article['categories'] = []
            except:
                article['categories'] = [article['categories']] if article['categories'] else []
        
        return jsonify({
            'success': True,
            'articles': articles_data,
            'total': len(articles_data),
            'date': date.today().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return render_template('index.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500

# Template filters
@app.template_filter('format_date')
def format_date(date_str):
    """Format date for display"""
    if not date_str:
        return ''
    
    try:
        if isinstance(date_str, str):
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        else:
            dt = date_str
        
        return dt.strftime('%B %d, %Y')
    except:
        return date_str

@app.template_filter('format_time')
def format_time(date_str):
    """Format time for display"""
    if not date_str:
        return ''
    
    try:
        if isinstance(date_str, str):
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        else:
            dt = date_str
        
        return dt.strftime('%I:%M %p')
    except:
        return date_str

@app.template_filter('truncate_text')
def truncate_text(text, length=150):
    """Truncate text to specified length"""
    if not text:
        return ''
    
    if len(text) <= length:
        return text
    
    return text[:length] + '...'

if __name__ == '__main__':
    import socket
    
    # Find an available port
    def find_free_port():
        ports_to_try = [5000, 5001, 5002, 8000, 8080, 3000]
        for port in ports_to_try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(('localhost', port))
                    return port
                except OSError:
                    continue
        # If all common ports are taken, let the system choose
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('localhost', 0))
            return s.getsockname()[1]
    
    port = find_free_port()
    
    print("Starting TechPulse Daily UI...")
    print(f"Visit http://localhost:{port} to view the application")
    print("Press Ctrl+C to stop the server")
    
    if port != 5000:
        print(f"Note: Using port {port} because 5000 is in use (likely AirPlay Receiver)")
    
    try:
        app.run(debug=True, host='0.0.0.0', port=port, threaded=True)
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
        cleanup()
        sys.exit(0)
    except Exception as e:
        print(f"Error starting server: {e}")
        cleanup()
        sys.exit(1)