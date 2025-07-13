import json
import os
import requests
import traceback
from datetime import datetime
from dotenv import load_dotenv
from utils import log

load_dotenv()

def send_news_api_request(service, endpoint=None, params=None, headers=None):
    """Send requests to news APIs"""
    try:
        service_urls = {
            'bbc': 'http://feeds.bbci.co.uk/news',
            'reddit': 'https://www.reddit.com',
            'newsapi': 'https://newsapi.org/v2'
        }
        
        if service not in service_urls:
            log(f"Unsupported news service: {service}", "ERROR")
            return None
        
        if endpoint:
            url = f"{service_urls[service]}/{endpoint}"
        else:
            url = service_urls[service]
        
        default_headers = {
            "User-Agent": "VocalComputer/1.0 (contact: user@example.com)"
        }
        
        if headers:
            default_headers.update(headers)
        
        response = requests.get(url, headers=default_headers, params=params, timeout=10)
        response.raise_for_status()
        
        if service == 'bbc':
            return response.text  # RSS XML content
        else:
            return response.json()  # JSON content
        
    except Exception as e:
        log(f"News API request failed for {service}: {e}\n{traceback.format_exc()}", "ERROR")
        return None

def api_get_bbc_news(category=None):
    """Get BBC news RSS feed"""
    if category:
        endpoint = f"{category}/rss.xml"
    else:
        endpoint = "rss.xml"
    return send_news_api_request('bbc', endpoint)

def api_get_reddit_news(subreddit="news"):
    """Get Reddit news from specified subreddit"""
    endpoint = f"r/{subreddit}.json"
    return send_news_api_request('reddit', endpoint)

def get_newsapi_headlines(api_key, params=None):
    """Get news headlines using NewsAPI"""
    headers = {"X-API-Key": api_key} if api_key else {}
    return send_news_api_request('newsapi', 'top-headlines', params, headers)

def run(action=None, category=None, count=None, **kwargs):
    """
    News module using free public APIs
    
    Actions:
    - headlines: Get top headlines
    - tech: Technology news
    - business: Business news  
    - science: Science news
    - world: World news
    """
    script_name = "news.py"
    
    if not action:
        action = "headlines"  # Default action
    
    if not count:
        count = 10  # Default number of articles
    
    try:
        count = int(count)
        count = min(count, 50)  # Limit to 50 articles max
    except (ValueError, TypeError):
        count = 10
    
    try:
        if action == "headlines":
            news_data = get_top_headlines(count)
            filename = kwargs.get('filename', 'top_headlines.json')
            save_news_to_temp(news_data, filename)
            return f"Top headlines retrieved and saved to {filename}."
            
        elif action in ["tech", "technology"]:
            news_data = get_category_news("technology", count)
            filename = kwargs.get('filename', 'tech_news.json')
            save_news_to_temp(news_data, filename)
            return f"Technology news retrieved and saved to {filename}."
            
        elif action == "business":
            news_data = get_category_news("business", count)
            filename = kwargs.get('filename', 'business_news.json')
            save_news_to_temp(news_data, filename)
            return f"Business news retrieved and saved to {filename}."
            
        elif action == "science":
            news_data = get_category_news("science", count)
            filename = kwargs.get('filename', 'science_news.json')
            save_news_to_temp(news_data, filename)
            return f"Science news retrieved and saved to {filename}."
            
        elif action == "world":
            news_data = get_world_news(count)
            filename = kwargs.get('filename', 'world_news.json')
            save_news_to_temp(news_data, filename)
            return f"World news retrieved and saved to {filename}."
            
        else:
            log(f"Unknown action: {action}", "ERROR", script="news.py")
            return f"Unknown news action: {action}. Use headlines, tech, business, science, or world."
            
    except Exception as e:
        log(f"[news.py] Error in news operation: {e}", level="ERROR", script=script_name)
        return f"Error retrieving news: {str(e)}"

def get_top_headlines(count=10):
    """
    Get top headlines using multiple free news sources
    """
    try:
        # Try BBC RSS first (most reliable free source)
        articles = get_bbc_news(count)
        
        if not articles:
            # Fallback to Reddit news as JSON
            articles = get_reddit_news(count)
        
        if not articles:
            # Last fallback to NewsAPI free tier (limited)
            articles = get_newsapi_headlines_func(count)
        
        return {
            "source": "Multiple Sources",
            "total_articles": len(articles),
            "articles": articles,
            "retrieved_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        log(f"[news.py] Error fetching top headlines: {e}", level="ERROR", script="news.py")
        return {"articles": [], "error": str(e)}

def get_category_news(category, count=10):
    """
    Get news by category
    """
    try:
        # Use BBC RSS feeds for categories
        if category == "technology":
            articles = get_bbc_category_news("technology", count)
        elif category == "business":
            articles = get_bbc_category_news("business", count)
        elif category == "science":
            articles = get_bbc_category_news("science", count)
        else:
            articles = get_bbc_news(count)
        
        return {
            "source": "BBC News",
            "category": category,
            "total_articles": len(articles),
            "articles": articles,
            "retrieved_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        log(f"[news.py] Error fetching {category} news: {e}", level="ERROR", script="news.py")
        return {"articles": [], "error": str(e)}

def get_world_news(count=10):
    """
    Get world news from multiple sources
    """
    try:
        articles = get_bbc_category_news("world", count)
        
        return {
            "source": "BBC World News",
            "category": "world",
            "total_articles": len(articles),
            "articles": articles,
            "retrieved_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        log(f"[news.py] Error fetching world news: {e}", level="ERROR", script="news.py")
        return {"articles": [], "error": str(e)}

def get_bbc_news(count=10):
    """
    Get news from BBC RSS (free, no API key required)
    """
    try:
        import xml.etree.ElementTree as ET
        
        content = api_get_bbc_news()
        if not content:
            return []
        
        root = ET.fromstring(content.encode('utf-8'))
        articles = []
        
        for item in root.findall(".//item")[:count]:
            title = item.find("title")
            description = item.find("description")
            link = item.find("link")
            pub_date = item.find("pubDate")
            
            article = {
                "title": title.text if title is not None else "No title",
                "description": description.text if description is not None else "No description",
                "url": link.text if link is not None else "",
                "published_at": pub_date.text if pub_date is not None else "",
                "source": "BBC News"
            }
            articles.append(article)
        
        return articles
        
    except Exception as e:
        log(f"[news.py] Error fetching BBC news: {e}", level="ERROR", script="news.py")
        return []

def get_bbc_category_news(category, count=10):
    """
    Get BBC news by category using RSS feeds
    """
    try:
        import xml.etree.ElementTree as ET
        
        # Map categories to endpoints
        category_endpoints = {
            "technology": "technology/rss.xml",
            "business": "business/rss.xml", 
            "science": "science_and_environment/rss.xml",
            "world": "world/rss.xml"
        }
        
        endpoint = category_endpoints.get(category, "rss.xml")
        content = api_get_bbc_news(endpoint)
        if not content:
            return []
        
        root = ET.fromstring(content.encode('utf-8'))
        articles = []
        
        for item in root.findall(".//item")[:count]:
            title = item.find("title")
            description = item.find("description")
            link = item.find("link")
            pub_date = item.find("pubDate")
            
            article = {
                "title": title.text if title is not None else "No title",
                "description": description.text if description is not None else "No description",
                "url": link.text if link is not None else "",
                "published_at": pub_date.text if pub_date is not None else "",
                "source": f"BBC {category.title()} News"
            }
            articles.append(article)
        
        return articles
        
    except Exception as e:
        log(f"[news.py] Error fetching BBC {category} news: {e}", level="ERROR", script="news.py")
        return []

def get_reddit_news(count=10):
    """
    Get news from Reddit's news subreddit (free JSON API)
    """
    try:
        data = api_get_reddit_news("news")
        if not data:
            return []
        
        articles = []
        posts = data.get("data", {}).get("children", [])
        
        for post in posts[:count]:
            post_data = post.get("data", {})
            
            # Skip pinned posts and non-news content
            if post_data.get("stickied") or post_data.get("over_18"):
                continue
            
            article = {
                "title": post_data.get("title", "No title"),
                "description": post_data.get("selftext", "")[:200] + "..." if post_data.get("selftext") else "No description",
                "url": post_data.get("url", ""),
                "published_at": datetime.fromtimestamp(post_data.get("created_utc", 0)).isoformat(),
                "source": "Reddit r/news",
                "score": post_data.get("score", 0),
                "comments": post_data.get("num_comments", 0)
            }
            articles.append(article)
        
        return articles
        
    except Exception as e:
        log(f"[news.py] Error fetching Reddit news: {e}", level="ERROR", script="news.py")
        return []

def get_newsapi_headlines_func(count=10):
    """
    Fallback: NewsAPI free tier (limited requests per day)
    Note: Requires API key but has free tier
    """
    try:
        # This would require an API key, but keeping as fallback option
        # You can sign up for free at newsapi.org
        api_key = os.getenv("NEWSAPI_KEY")  # Optional: set if you want to use NewsAPI
        
        if not api_key:
            return []
        
        params = {
            "country": "us",
            "pageSize": count
        }
        
        data = get_newsapi_headlines(api_key, params)
        if not data:
            return []
        
        articles = []
        for article in data.get("articles", []):
            formatted_article = {
                "title": article.get("title", "No title"),
                "description": article.get("description", "No description"),
                "url": article.get("url", ""),
                "published_at": article.get("publishedAt", ""),
                "source": article.get("source", {}).get("name", "Unknown")
            }
            articles.append(formatted_article)
        
        return articles
        
    except Exception as e:
        log(f"[news.py] Error fetching NewsAPI headlines: {e}", level="ERROR", script="news.py")
        return []

def save_news_to_temp(news_data, filename):
    """Save news data to temp folder for AI analysis"""
    try:
        temp_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../temp'))
        os.makedirs(temp_dir, exist_ok=True)
        
        file_path = os.path.join(temp_dir, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(news_data, f, indent=2, ensure_ascii=False)
            
        
    except Exception as e:
        log(f"Error saving news data: {e}", "ERROR", script="news.py")
