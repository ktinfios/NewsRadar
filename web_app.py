from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_cors import CORS
import pandas as pd
import json
import os
import logging
from datetime import datetime
from NewsRadar import search_news_rss, get_old_articles, write_to_text_file, write_to_email_body, COMPANIES, KEY_TERMS
from Email import send_email
import threading
from time import sleep
from tqdm import tqdm

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Use the actual lists from NewsRadar.py as defaults
DEFAULT_COMPANIES = COMPANIES
DEFAULT_KEY_TERMS = KEY_TERMS

# Load user preferences
def load_user_preferences():
    """Load user preferences from JSON file"""
    try:
        if os.path.exists("user_preferences.json"):
            with open("user_preferences.json", "r") as f:
                preferences = json.load(f)
                # Ensure we have the updated default lists
                if not preferences.get("selected_companies"):
                    preferences["selected_companies"] = DEFAULT_COMPANIES.copy()
                if not preferences.get("selected_key_terms"):
                    preferences["selected_key_terms"] = DEFAULT_KEY_TERMS.copy()
                return preferences
    except Exception as e:
        logger.error(f"Error loading preferences: {e}")
    
    # Return defaults if file doesn't exist or error occurs
    return {
        "selected_companies": DEFAULT_COMPANIES.copy(),
        "selected_key_terms": DEFAULT_KEY_TERMS.copy(),
        "custom_companies": [],
        "custom_key_terms": [],
        "receiver_email": os.getenv("SENDER_EMAIL", "")
    }

def save_user_preferences(preferences):
    """Save user preferences to JSON file"""
    try:
        with open("user_preferences.json", "w") as f:
            json.dump(preferences, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving preferences: {e}")
        return False

# Global variable to track search status
search_status = {"running": False, "progress": 0, "message": "Ready"}

def run_custom_search(selected_companies, selected_key_terms):
    """Run NewsRadar search with custom company and key term selection"""
    global search_status
    
    try:
        search_status = {"running": True, "progress": 10, "message": "Initializing search..."}
        
        # Get old articles to avoid duplicates
        old_articles = get_old_articles()
        news_articles = []
        
        total_combinations = len(selected_companies) * len(selected_key_terms)
        current_combination = 0
        
        search_status = {"running": True, "progress": 20, "message": "Searching for news articles..."}
        
        for company in selected_companies:
            for term in selected_key_terms:
                current_combination += 1
                progress = 20 + int((current_combination / total_combinations) * 60)
                search_status = {"running": True, "progress": progress, 
                               "message": f"Searching {company} for {term}..."}
                
                news_article = search_news_rss(company, term)
                for article in news_article:
                    news_articles.append(article)
                sleep(0.25)
        
        search_status = {"running": True, "progress": 85, "message": "Processing results..."}
        
        news_articles = pd.DataFrame(news_articles)
        
        if not old_articles.empty and 'url' in old_articles.columns:
            new_news_articles = news_articles[~news_articles['url'].isin(old_articles['url'])]
        else:
            new_news_articles = news_articles
            logger.info("No previous articles found or invalid format, treating all articles as new.")

        # Save articles
        if not news_articles.empty:
            news_articles[["company", "key_term","title", "publish_date", "url"]].to_csv(
                "news_articles.csv", index=False, encoding='utf-8-sig', mode='a')

        # Prepare email
        subject = f"NewsRadar - {datetime.now().strftime('%Y-%m-%d')}"
        body = ""

        if not new_news_articles.empty:
            logger.info(f"Found {len(new_news_articles)} new articles.")
            write_to_text_file(new_news_articles, "news_articles.txt")
            subject += f"- Found {len(new_news_articles)} new articles"
            body = write_to_email_body(new_news_articles)
        else:
            logger.info("No new articles found.")
            subject += " - No New Articles"
            body = "No news articles found this week."
        
        # Try to send email if configured
        preferences = load_user_preferences()
        if preferences.get("receiver_email"):
            try:
                send_email(preferences["receiver_email"], subject, body)
                logger.info(f"Email sent successfully to {preferences['receiver_email']}")
            except Exception as e:
                logger.error(f"Failed to send email: {e}")
        
        search_status = {"running": False, "progress": 100, 
                        "message": f"Search completed! Found {len(new_news_articles)} new articles."}
        
    except Exception as e:
        logger.error(f"Error running custom search: {e}")
        search_status = {"running": False, "progress": 0, "message": f"Search failed: {str(e)}"}

def get_recent_articles(limit=20):
    """Get recent articles from the CSV file"""
    try:
        if os.path.exists("news_articles.csv"):
            df = pd.read_csv("news_articles.csv")
            # Sort by most recent if publish_date exists
            if not df.empty and 'publish_date' in df.columns:
                df['publish_date'] = pd.to_datetime(df['publish_date'], errors='coerce')
                df = df.sort_values('publish_date', ascending=False)
                # Convert datetime back to string for JSON serialization
                df['publish_date'] = df['publish_date'].dt.strftime('%Y-%m-%d %H:%M:%S')
                # Replace NaT with empty string
                df['publish_date'] = df['publish_date'].fillna('')
            
            # Convert to dict and ensure all values are JSON serializable
            articles = df.head(limit).to_dict('records')
            
            # Clean up any remaining pandas objects or NaN values
            for article in articles:
                for key, value in article.items():
                    if pd.isna(value):
                        article[key] = ''
                    elif isinstance(value, pd.Timestamp):
                        article[key] = str(value) if not pd.isna(value) else ''
            
            return articles
        return []
    except Exception as e:
        logger.error(f"Error reading articles: {e}")
        return []

@app.route('/')
def dashboard():
    """Main dashboard page"""
    articles = get_recent_articles()
    preferences = load_user_preferences()
    
    all_companies = DEFAULT_COMPANIES + preferences.get("custom_companies", [])
    all_key_terms = DEFAULT_KEY_TERMS + preferences.get("custom_key_terms", [])
    
    return render_template('dashboard.html', 
                         articles=articles, 
                         total_articles=len(articles),
                         companies=all_companies,
                         key_terms=all_key_terms,
                         default_companies=DEFAULT_COMPANIES,
                         default_key_terms=DEFAULT_KEY_TERMS,
                         selected_companies=preferences.get("selected_companies", []),
                         selected_key_terms=preferences.get("selected_key_terms", []))

@app.route('/api/articles')
def api_articles():
    """API endpoint to get articles"""
    try:
        limit = request.args.get('limit', 20, type=int)
        articles = get_recent_articles(limit)
        return jsonify(articles)
    except Exception as e:
        logger.error(f"Error in api_articles: {e}")
        return jsonify({"error": "Failed to retrieve articles"}), 500

@app.route('/api/search', methods=['POST'])
def api_search():
    """API endpoint to trigger manual search"""
    global search_status
    
    if search_status["running"]:
        return jsonify({"error": "Search already in progress"}), 400
    
    # Get search parameters from request or use preferences
    data = request.get_json() or {}
    preferences = load_user_preferences()
    
    selected_companies = data.get('companies', preferences.get("selected_companies", DEFAULT_COMPANIES))
    selected_key_terms = data.get('key_terms', preferences.get("selected_key_terms", DEFAULT_KEY_TERMS))
    
    if not selected_companies or not selected_key_terms:
        return jsonify({"error": "No companies or key terms selected"}), 400
    
    # Start search in background thread
    thread = threading.Thread(target=run_custom_search, args=(selected_companies, selected_key_terms))
    thread.daemon = True
    thread.start()
    
    return jsonify({"message": "Search started", "status": search_status})

@app.route('/api/search/status')
def api_search_status():
    """API endpoint to get search status"""
    return jsonify(search_status)

@app.route('/api/stats')
def api_stats():
    """API endpoint to get statistics"""
    try:
        preferences = load_user_preferences()
        
        if os.path.exists("news_articles.csv"):
            df = pd.read_csv("news_articles.csv")
            
            stats = {
                "total_articles": len(df),
                "companies_tracked": len(preferences.get("selected_companies", [])),
                "key_terms": len(preferences.get("selected_key_terms", [])),
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            if not df.empty:
                # Articles by company
                if 'company' in df.columns:
                    company_stats = df['company'].value_counts().head(10).to_dict()
                    stats["top_companies"] = company_stats
                
                # Articles by key term
                if 'key_term' in df.columns:
                    term_stats = df['key_term'].value_counts().to_dict()
                    stats["key_term_distribution"] = term_stats
            
            return jsonify(stats)
        else:
            return jsonify({
                "total_articles": 0,
                "companies_tracked": len(preferences.get("selected_companies", [])),
                "key_terms": len(preferences.get("selected_key_terms", [])),
                "last_updated": "Never",
                "top_companies": {},
                "key_term_distribution": {}
            })
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/settings')
def settings():
    """Settings page"""
    preferences = load_user_preferences()
    all_companies = DEFAULT_COMPANIES + preferences.get("custom_companies", [])
    all_key_terms = DEFAULT_KEY_TERMS + preferences.get("custom_key_terms", [])
    
    return render_template('settings.html', 
                         companies=all_companies, 
                         key_terms=all_key_terms,
                         default_companies=DEFAULT_COMPANIES,
                         default_key_terms=DEFAULT_KEY_TERMS,
                         preferences=preferences)

@app.route('/api/preferences', methods=['GET', 'POST'])
def api_preferences():
    """API endpoint to get or update user preferences"""
    if request.method == 'GET':
        return jsonify(load_user_preferences())
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            current_preferences = load_user_preferences()
            
            # Update preferences with new data
            if 'selected_companies' in data:
                current_preferences['selected_companies'] = data['selected_companies']
            if 'selected_key_terms' in data:
                current_preferences['selected_key_terms'] = data['selected_key_terms']
            if 'custom_companies' in data:
                current_preferences['custom_companies'] = data['custom_companies']
            if 'custom_key_terms' in data:
                current_preferences['custom_key_terms'] = data['custom_key_terms']
            if 'receiver_email' in data:
                current_preferences['receiver_email'] = data['receiver_email']
            
            if save_user_preferences(current_preferences):
                return jsonify({"message": "Preferences saved successfully"})
            else:
                return jsonify({"error": "Failed to save preferences"}), 500
                
        except Exception as e:
            logger.error(f"Error updating preferences: {e}")
            return jsonify({"error": str(e)}), 500

@app.route('/api/add_custom', methods=['POST'])
def api_add_custom():
    """API endpoint to add custom company or key term"""
    try:
        data = request.get_json()
        item_type = data.get('type')  # 'company' or 'key_term'
        item_value = data.get('value', '').strip()
        
        if not item_value:
            return jsonify({"error": "Value cannot be empty"}), 400
        
        preferences = load_user_preferences()
        
        if item_type == 'company':
            if item_value not in preferences.get('custom_companies', []):
                preferences.setdefault('custom_companies', []).append(item_value)
                # Also add to selected companies by default
                if item_value not in preferences.get('selected_companies', []):
                    preferences.setdefault('selected_companies', []).append(item_value)
            else:
                return jsonify({"error": "Company already exists"}), 400
                
        elif item_type == 'key_term':
            if item_value not in preferences.get('custom_key_terms', []):
                preferences.setdefault('custom_key_terms', []).append(item_value)
                # Also add to selected key terms by default
                if item_value not in preferences.get('selected_key_terms', []):
                    preferences.setdefault('selected_key_terms', []).append(item_value)
            else:
                return jsonify({"error": "Key term already exists"}), 400
        else:
            return jsonify({"error": "Invalid type"}), 400
        
        if save_user_preferences(preferences):
            return jsonify({"message": f"Custom {item_type} added successfully"})
        else:
            return jsonify({"error": "Failed to save preferences"}), 500
            
    except Exception as e:
        logger.error(f"Error adding custom item: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Ensure templates and static directories exist
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
