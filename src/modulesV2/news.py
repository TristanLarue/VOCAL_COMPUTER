# news.py - V2
# Enhanced news fetching with multiple sources
# Simplified interface with consistent keywords

import requests
import os
import json
from datetime import datetime
from utils import log

def run(action="headlines", return_data=False, **kwargs):
    """
    Unified news interface
    Actions: headlines, search, tech, business, sports, world
    Returns: Direct data or file-based response
    """
    try:
        action = action.lower()
        
        # Route to appropriate function
        if action in ['headlines', 'top', 'latest', 'breaking']:
            return handle_headlines(return_data, **kwargs)
        elif action in ['search', 'find', 'query']:
            return handle_search_news(return_data, **kwargs)
        elif action in ['tech', 'technology', 'science']:
            return handle_category_news('technology', return_data, **kwargs)
        elif action in ['business', 'finance', 'economy']:
            return handle_category_news('business', return_data, **kwargs)
        elif action in ['sports', 'sport']:
            return handle_category_news('sports', return_data, **kwargs)
        elif action in ['world', 'international', 'global']:
            return handle_category_news('general', return_data, **kwargs)
        else:
            # Default to headlines
            return handle_headlines(return_data, **kwargs)
            
    except Exception as e:
        error_msg = f"Error in news module: {str(e)}"
        log(error_msg, "ERROR")
        return create_response(False, error_msg, return_data)

def handle_headlines(return_data, **kwargs):
    """Handle top headlines"""
    try:
        country = kwargs.get('country', 'us')
        count = int(kwargs.get('count', 10))
        
        # Try NewsAPI first, fallback to free sources
        news_data = fetch_from_newsapi('top-headlines', country=country, pageSize=count)
        
        if not news_data:
            news_data = fetch_from_free_sources()
        
        if not news_data:
            return create_response(False, "No news sources available", return_data)
        
        success_msg = f"Retrieved {len(news_data)} top headlines"
        return create_response(True, success_msg, return_data, {
            'articles': news_data,
            'count': len(news_data),
            'category': 'headlines',
            'country': country
        })
        
    except Exception as e:
        error_msg = f"Error fetching headlines: {str(e)}"
        log(error_msg, "ERROR")
        return create_response(False, error_msg, return_data)

def handle_search_news(return_data, **kwargs):
    """Handle news search"""
    try:
        query = kwargs.get('query') or kwargs.get('search') or kwargs.get('term')
        
        if not query:
            return create_response(False, "Search query is required", return_data)
        
        count = int(kwargs.get('count', 10))
        
        # Try NewsAPI search
        news_data = fetch_from_newsapi('everything', q=query, pageSize=count, sortBy='relevancy')
        
        if not news_data:
            return create_response(False, "No news found for query", return_data)
        
        success_msg = f"Found {len(news_data)} articles for '{query}'"
        return create_response(True, success_msg, return_data, {
            'articles': news_data,
            'count': len(news_data),
            'query': query,
            'category': 'search'
        })
        
    except Exception as e:
        error_msg = f"Error searching news: {str(e)}"
        log(error_msg, "ERROR")
        return create_response(False, error_msg, return_data)

def handle_category_news(category, return_data, **kwargs):
    """Handle category-specific news"""
    try:
        country = kwargs.get('country', 'us')
        count = int(kwargs.get('count', 10))
        
        # Fetch category news
        news_data = fetch_from_newsapi('top-headlines', category=category, country=country, pageSize=count)
        
        if not news_data:
            return create_response(False, f"No {category} news available", return_data)
        
        success_msg = f"Retrieved {len(news_data)} {category} articles"
        return create_response(True, success_msg, return_data, {
            'articles': news_data,
            'count': len(news_data),
            'category': category,
            'country': country
        })
        
    except Exception as e:
        error_msg = f"Error fetching {category} news: {str(e)}"
        log(error_msg, "ERROR")
        return create_response(False, error_msg, return_data)

def fetch_from_newsapi(endpoint, **params):
    """Fetch news from NewsAPI"""
    try:
        api_key = os.getenv('NEWS_API_KEY')
        if not api_key:
            log("NEWS_API_KEY not found, skipping NewsAPI", "WARNING")
            return None
        
        base_url = f"https://newsapi.org/v2/{endpoint}"
        
        # Add API key to params
        params['apiKey'] = api_key
        
        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get('status') != 'ok':
            log(f"NewsAPI error: {data.get('message', 'Unknown error')}", "ERROR")
            return None
        
        articles = data.get('articles', [])
        
        # Format articles
        formatted_articles = []
        for article in articles:
            formatted_articles.append({
                'title': article.get('title', 'No Title'),
                'description': article.get('description', ''),
                'url': article.get('url', ''),
                'source': article.get('source', {}).get('name', 'Unknown'),
                'published': article.get('publishedAt', ''),
                'author': article.get('author', 'Unknown')
            })
        
        return formatted_articles
        
    except Exception as e:
        log(f"Error fetching from NewsAPI: {str(e)}", "ERROR")
        return None

def fetch_from_free_sources():
    """Fetch news from free sources as fallback"""
    try:
        # Use HackerNews API as a free fallback
        response = requests.get('https://hacker-news.firebaseio.com/v0/topstories.json', timeout=10)
        response.raise_for_status()
        
        story_ids = response.json()[:10]  # Get top 10 stories
        
        articles = []
        for story_id in story_ids:
            try:
                story_response = requests.get(f'https://hacker-news.firebaseio.com/v0/item/{story_id}.json', timeout=5)
                story_data = story_response.json()
                
                if story_data.get('title'):
                    articles.append({
                        'title': story_data.get('title', 'No Title'),
                        'description': story_data.get('text', '')[:200] + '...' if story_data.get('text') else '',
                        'url': story_data.get('url', f'https://news.ycombinator.com/item?id={story_id}'),
                        'source': 'Hacker News',
                        'published': datetime.fromtimestamp(story_data.get('time', 0)).isoformat() if story_data.get('time') else '',
                        'author': story_data.get('by', 'Unknown')
                    })
            except Exception:
                continue
        
        return articles
        
    except Exception as e:
        log(f"Error fetching from free sources: {str(e)}", "ERROR")
        return None

def create_response(success, message, return_data, data=None):
    """Create standardized response"""
    if return_data:
        return {
            'success': success,
            'message': message,
            'data': data or {},
            'module': 'news'
        }
    else:
        # File-based response for complex analysis
        filename = f"news_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        temp_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../temp'))
        os.makedirs(temp_dir, exist_ok=True)
        
        file_data = {
            'success': success,
            'message': message,
            'data': data or {},
            'module': 'news',
            'timestamp': datetime.now().isoformat()
        }
        
        with open(os.path.join(temp_dir, filename), 'w', encoding='utf-8') as f:
            json.dump(file_data, f, indent=2)
        
        log(message, "COMMAND")
        return f"News operation completed. Data saved to {filename}"
