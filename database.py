"""
Database models and operations for TechPulse Daily UI
"""

from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, joinedload
from sqlalchemy.sql import func
import os
import atexit

Base = declarative_base()

class Article(Base):
    __tablename__ = 'articles'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(500), nullable=False)
    url = Column(String(1000), unique=True, nullable=False)
    description = Column(Text)
    content = Column(Text)
    author = Column(String(200))
    published_date = Column(DateTime)
    scraped_date = Column(DateTime, default=datetime.utcnow)
    source = Column(String(100))
    categories = Column(String(200))  # JSON string of categories
    summary = Column(Text)
    hash = Column(String(32), unique=True)
    is_duplicate = Column(Boolean, default=False)
    
    # Relationship to favorites
    favorites = relationship("Favorite", back_populates="article", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<Article {self.title[:50]}>'
    
    def to_dict(self):
        """Convert article to dictionary for API responses"""
        # Handle detached objects - check if favorites can be accessed
        is_favorited = False
        try:
            is_favorited = len(self.favorites) > 0
        except:
            # If we can't access favorites, assume not favorited
            pass
        
        return {
            'id': self.id,
            'title': self.title,
            'url': self.url,
            'description': self.description,
            'content': self.content,
            'author': self.author,
            'published_date': self.published_date.isoformat() if self.published_date else None,
            'scraped_date': self.scraped_date.isoformat() if self.scraped_date else None,
            'source': self.source,
            'categories': self.categories,
            'summary': self.summary,
            'hash': self.hash,
            'is_duplicate': self.is_duplicate,
            'is_favorited': is_favorited
        }

class Favorite(Base):
    __tablename__ = 'favorites'
    
    id = Column(Integer, primary_key=True)
    article_id = Column(Integer, ForeignKey('articles.id'), nullable=False)
    date_favorited = Column(DateTime, default=datetime.utcnow)
    
    # Relationship to article
    article = relationship("Article", back_populates="favorites")
    
    def __repr__(self):
        return f'<Favorite {self.article_id}>'

class Alert(Base):
    __tablename__ = 'alerts'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, default=1)  # Single user for now
    alert_type = Column(String(20), nullable=False)  # 'ticker' or 'keyword'
    alert_value = Column(String(200), nullable=False)  # ticker symbol or keyword phrase
    conditions = Column(Text)  # JSON string of alert conditions
    frequency = Column(String(20), default='immediate')  # 'immediate', 'hourly', 'daily'
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship to alert history
    history = relationship("AlertHistory", back_populates="alert", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<Alert {self.alert_type}: {self.alert_value}>'
    
    def to_dict(self):
        """Convert alert to dictionary for API responses"""
        import json
        
        conditions = {}
        try:
            if self.conditions:
                conditions = json.loads(self.conditions)
        except:
            pass
        
        return {
            'id': self.id,
            'alert_type': self.alert_type,
            'alert_value': self.alert_value,
            'conditions': conditions,
            'frequency': self.frequency,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'trigger_count': len(self.history)
        }

class AlertHistory(Base):
    __tablename__ = 'alert_history'
    
    id = Column(Integer, primary_key=True)
    alert_id = Column(Integer, ForeignKey('alerts.id'), nullable=False)
    article_id = Column(Integer, ForeignKey('articles.id'), nullable=False)
    triggered_at = Column(DateTime, default=datetime.utcnow)
    delivered = Column(Boolean, default=False)
    
    # Relationships
    alert = relationship("Alert", back_populates="history")
    article = relationship("Article")
    
    def __repr__(self):
        return f'<AlertHistory {self.alert_id}->{self.article_id}>'
    
    def to_dict(self):
        """Convert alert history to dictionary for API responses"""
        return {
            'id': self.id,
            'alert_id': self.alert_id,
            'article_id': self.article_id,
            'triggered_at': self.triggered_at.isoformat() if self.triggered_at else None,
            'delivered': self.delivered,
            'article': self.article.to_dict() if self.article else None
        }

class DatabaseManager:
    def __init__(self, db_path='./news_data.db'):
        self.db_path = db_path
        
        # Create data directory if it doesn't exist
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        
        # Create engine with proper connection pooling for SQLite
        self.engine = create_engine(
            f'sqlite:///{db_path}',
            pool_pre_ping=True,
            pool_recycle=300,
            pool_timeout=20,
            max_overflow=0,
            pool_size=1,
            connect_args={
                'check_same_thread': False,
                'timeout': 20,
                'isolation_level': None
            }
        )
        Base.metadata.create_all(self.engine)
        
        # Create session factory instead of single session
        self.Session = sessionmaker(bind=self.engine, expire_on_commit=False)
        
        # Register cleanup function
        atexit.register(self._cleanup)
    
    def get_session(self):
        """Get a new database session"""
        return self.Session()
    
    def execute_with_session(self, operation):
        """Execute operation with a new session and proper cleanup"""
        session = self.get_session()
        try:
            result = operation(session)
            session.commit()
            return result
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def add_article(self, article_data):
        """Add a new article to the database"""
        def _add_article(session):
            # Convert string date to datetime if needed
            if isinstance(article_data.get('published_date'), str):
                from dateutil import parser as date_parser
                article_data['published_date'] = date_parser.parse(article_data['published_date'])
            
            if isinstance(article_data.get('scraped_date'), str):
                from dateutil import parser as date_parser
                article_data['scraped_date'] = date_parser.parse(article_data['scraped_date'])
            
            article = Article(**article_data)
            session.add(article)
            return article
        
        try:
            return self.execute_with_session(_add_article)
        except Exception as e:
            print(f"Error adding article: {e}")
            return None
    
    def get_articles(self, limit=None, offset=0, category=None, search=None, days=None):
        """Get articles with optional filtering"""
        def _get_articles(session):
            query = session.query(Article).options(joinedload(Article.favorites)).filter(Article.is_duplicate == False)
            
            if category and category != 'all':
                query = query.filter(Article.categories.like(f'%{category}%'))
            
            if search:
                search_term = f'%{search}%'
                query = query.filter(
                    (Article.title.like(search_term)) |
                    (Article.summary.like(search_term)) |
                    (Article.description.like(search_term))
                )
            
            if days:
                from datetime import timedelta
                cutoff_date = datetime.utcnow() - timedelta(days=days)
                query = query.filter(Article.scraped_date >= cutoff_date)
            
            query = query.order_by(Article.published_date.desc())
            
            if limit:
                query = query.limit(limit).offset(offset)
            
            return query.all()
        
        session = self.get_session()
        try:
            return _get_articles(session)
        finally:
            session.close()
    
    def get_article_by_id(self, article_id):
        """Get a specific article by ID"""
        session = self.get_session()
        try:
            return session.query(Article).options(joinedload(Article.favorites)).filter(Article.id == article_id).first()
        finally:
            session.close()
    
    def mark_as_read(self, article_id):
        """Mark an article as read"""
        def _mark_as_read(session):
            article = session.query(Article).filter(Article.id == article_id).first()
            if article:
                # Article marked as accessed
                return True
            return False
        
        try:
            return self.execute_with_session(_mark_as_read)
        except Exception as e:
            print(f"Error marking article as read: {e}")
            return False
    
    def toggle_favorite(self, article_id):
        """Toggle favorite status of an article"""
        def _toggle_favorite(session):
            article = session.query(Article).filter(Article.id == article_id).first()
            if not article:
                return False
            
            # Check if already favorited
            existing_favorite = session.query(Favorite).filter(
                Favorite.article_id == article_id
            ).first()
            
            if existing_favorite:
                # Remove from favorites
                session.delete(existing_favorite)
                return False
            else:
                # Add to favorites
                favorite = Favorite(article_id=article_id)
                session.add(favorite)
                return True
        
        try:
            return self.execute_with_session(_toggle_favorite)
        except Exception as e:
            print(f"Error toggling favorite: {e}")
            return False
    
    def get_favorites(self, limit=None, offset=0):
        """Get favorited articles"""
        def _get_favorites(session):
            query = session.query(Article).options(joinedload(Article.favorites)).join(Favorite).order_by(Favorite.date_favorited.desc())
            
            if limit:
                query = query.limit(limit).offset(offset)
            
            return query.all()
        
        session = self.get_session()
        try:
            return _get_favorites(session)
        finally:
            session.close()
    
    def get_statistics(self):
        """Get dashboard statistics"""
        def _get_statistics(session):
            from datetime import date
            
            today = date.today()
            
            # Today's articles
            today_articles = session.query(Article).filter(
                func.date(Article.scraped_date) == today
            ).count()
            
            # Total favorites
            total_favorites = session.query(Favorite).count()
            
            # Active sources (sources that have articles)
            active_sources = session.query(Article.source).distinct().count()
            
            # Articles read today
            articles_read_today = session.query(Article).filter(
                func.date(Article.scraped_date) == today,
                Article.id.isnot(None)  # All articles
            ).count()
            
            return {
                'today_articles': today_articles,
                'total_favorites': total_favorites,
                'active_sources': active_sources,
                'articles_read_today': articles_read_today
            }
        
        session = self.get_session()
        try:
            return _get_statistics(session)
        finally:
            session.close()
    
    def get_categories(self):
        """Get all unique categories"""
        def _get_categories(session):
            import json
            
            articles = session.query(Article.categories).all()
            categories = set()
            
            for article in articles:
                if article.categories:
                    try:
                        cats = json.loads(article.categories)
                        categories.update(cats)
                    except:
                        # Handle simple string categories
                        categories.add(article.categories)
            
            return sorted(list(categories))
        
        session = self.get_session()
        try:
            return _get_categories(session)
        finally:
            session.close()
    
    def cleanup_old_articles(self, days=30):
        """Remove articles older than specified days"""
        def _cleanup_old_articles(session):
            from datetime import timedelta
            
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Delete old articles (cascades to favorites)
            deleted = session.query(Article).filter(
                Article.scraped_date < cutoff_date
            ).delete()
            
            return deleted
        
        try:
            return self.execute_with_session(_cleanup_old_articles)
        except Exception as e:
            print(f"Error cleaning up old articles: {e}")
            return 0
    
    def close(self):
        """Close database connections"""
        try:
            if hasattr(self, 'engine') and self.engine:
                self.engine.dispose()
        except:
            pass
    
    def _cleanup(self):
        """Cleanup function called on exit"""
        try:
            if hasattr(self, 'engine') and self.engine:
                self.engine.dispose()
        except:
            pass
    
    # Alert management methods
    def create_alert(self, alert_data):
        """Create a new alert"""
        def _create_alert(session):
            import json
            
            alert = Alert(
                alert_type=alert_data['alert_type'],
                alert_value=alert_data['alert_value'],
                conditions=json.dumps(alert_data.get('conditions', {})),
                frequency=alert_data.get('frequency', 'immediate'),
                is_active=alert_data.get('is_active', True)
            )
            session.add(alert)
            return alert
        
        try:
            return self.execute_with_session(_create_alert)
        except Exception as e:
            print(f"Error creating alert: {e}")
            return None
    
    def get_alerts(self, active_only=True):
        """Get all alerts"""
        def _get_alerts(session):
            query = session.query(Alert)
            if active_only:
                query = query.filter(Alert.is_active == True)
            return query.order_by(Alert.created_at.desc()).all()
        
        session = self.get_session()
        try:
            return _get_alerts(session)
        finally:
            session.close()
    
    def get_alert_by_id(self, alert_id):
        """Get a specific alert by ID"""
        session = self.get_session()
        try:
            return session.query(Alert).filter(Alert.id == alert_id).first()
        finally:
            session.close()
    
    def update_alert(self, alert_id, alert_data):
        """Update an existing alert"""
        def _update_alert(session):
            import json
            
            alert = session.query(Alert).filter(Alert.id == alert_id).first()
            if not alert:
                return False
            
            if 'alert_value' in alert_data:
                alert.alert_value = alert_data['alert_value']
            if 'conditions' in alert_data:
                alert.conditions = json.dumps(alert_data['conditions'])
            if 'frequency' in alert_data:
                alert.frequency = alert_data['frequency']
            if 'is_active' in alert_data:
                alert.is_active = alert_data['is_active']
            
            return True
        
        try:
            return self.execute_with_session(_update_alert)
        except Exception as e:
            print(f"Error updating alert: {e}")
            return False
    
    def delete_alert(self, alert_id):
        """Delete an alert"""
        def _delete_alert(session):
            alert = session.query(Alert).filter(Alert.id == alert_id).first()
            if alert:
                session.delete(alert)
                return True
            return False
        
        try:
            return self.execute_with_session(_delete_alert)
        except Exception as e:
            print(f"Error deleting alert: {e}")
            return False
    
    def check_alerts_for_article(self, article):
        """Check if an article triggers any alerts"""
        import json
        import re
        
        alerts = self.get_alerts(active_only=True)
        triggered_alerts = []
        
        for alert in alerts:
            triggered = False
            
            if alert.alert_type == 'ticker':
                # Check if ticker symbol appears in title or content
                ticker = alert.alert_value.upper()
                search_text = f"{article.get('title', '')} {article.get('description', '')} {article.get('content', '')}".upper()
                
                # Look for ticker as word boundary
                if re.search(rf'\b{re.escape(ticker)}\b', search_text):
                    triggered = True
            
            elif alert.alert_type == 'keyword':
                # Check keyword matching
                keyword = alert.alert_value.lower()
                search_text = f"{article.get('title', '')} {article.get('description', '')} {article.get('content', '')}".lower()
                
                # Parse conditions
                conditions = {}
                try:
                    if alert.conditions:
                        conditions = json.loads(alert.conditions)
                except:
                    pass
                
                # Simple keyword matching
                if keyword in search_text:
                    triggered = True
                
                # Check category filters
                if triggered and conditions.get('categories'):
                    article_categories = article.get('categories', [])
                    if isinstance(article_categories, str):
                        try:
                            article_categories = json.loads(article_categories)
                        except:
                            article_categories = [article_categories]
                    
                    # Check if any article category matches alert categories
                    if not any(cat in conditions['categories'] for cat in article_categories):
                        triggered = False
            
            if triggered:
                triggered_alerts.append(alert)
        
        return triggered_alerts
    
    def create_alert_history(self, alert_id, article_id):
        """Create alert history entry"""
        def _create_alert_history(session):
            history = AlertHistory(
                alert_id=alert_id,
                article_id=article_id
            )
            session.add(history)
            return history
        
        try:
            return self.execute_with_session(_create_alert_history)
        except Exception as e:
            print(f"Error creating alert history: {e}")
            return None
    
    def get_alert_history(self, alert_id=None, limit=50):
        """Get alert history"""
        def _get_alert_history(session):
            query = session.query(AlertHistory)
            
            if alert_id:
                query = query.filter(AlertHistory.alert_id == alert_id)
            
            return query.order_by(AlertHistory.triggered_at.desc()).limit(limit).all()
        
        session = self.get_session()
        try:
            return _get_alert_history(session)
        finally:
            session.close()
    
    def get_undelivered_alerts(self):
        """Get undelivered alert notifications"""
        def _get_undelivered_alerts(session):
            return session.query(AlertHistory).filter(
                AlertHistory.delivered == False
            ).order_by(AlertHistory.triggered_at.desc()).all()
        
        session = self.get_session()
        try:
            return _get_undelivered_alerts(session)
        finally:
            session.close()
    
    def mark_alert_delivered(self, history_id):
        """Mark alert as delivered"""
        def _mark_alert_delivered(session):
            history = session.query(AlertHistory).filter(
                AlertHistory.id == history_id
            ).first()
            
            if history:
                history.delivered = True
                return True
            return False
        
        try:
            return self.execute_with_session(_mark_alert_delivered)
        except Exception as e:
            print(f"Error marking alert as delivered: {e}")
            return False

# Global database instance - use same path as scraper config
db = DatabaseManager('./news_data.db')