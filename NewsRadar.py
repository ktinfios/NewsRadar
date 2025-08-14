import csv 
import feedparser 
import logging
import pandas as pd 
import nltk 
import os 
from dotenv import load_dotenv
from datetime import datetime, timedelta
from Email import send_email
from newspaper import Article
from playwright.sync_api import sync_playwright
from time import sleep 
from tqdm import tqdm 
from transformers import PegasusTokenizer, PegasusForConditionalGeneration
from urllib.parse import quote_plus

# region 
load_dotenv()

# endregion 

# region Constants
GOOGLE_NEWS_URL = "https://news.google.com"
GOOGLE_NEWS_SEARCH_URL = "https://news.google.com/search?q={}&hl=en-US&gl=US&ceid=US%3Aen"

COMPANIES = ["Bulten", "Volvo", "Viking Life", "Rockwool A/S", "Carlsberg", 
             "Hornbach Baumarkt AG", "Bültel Bekleidungswerke GmbH",
             "OBI Group Holding SE & Co.KGaA", "LKW Walter", "F. H. Bertling",
             "Boulanger", "Lyreco", "Etam", "Rossignol", "Schneider", "Log's"]
KEY_TERMS = ["Digital Transformation", "Bottleneck", "Warehouse", "CEO", "Optimization", "Fulfillment",
             "Investment Funding", "Merger Acquisition", "Sustainability", "Lead Time", "Bill of Lading",
             "Incoterms", "Freight Forwarder", "Third-Party Logistics (3PL)", "Fourth-Party Logistics (4PL)",
             "Last-Mile Delivery", "Cross-Docking", "Reverse Logistics", "Safety Stock",
             "Stock Keeping Unit (SKU)", "Economic Order Quantity (EOQ)", "Just-in-Time (JIT)", 
             "Consignment Inventory", "Backorder", "Pick and Pack", "Order Fulfillment",
             "Freight Consolidation", "Cold Chain Logistics", "Customs Clearance", "LTL (Less Than Truckload)",
             "FTL (Full Truckload)", "Demurrage", "Detention", "Intermodal Transport",
             "Port of Discharge (POD)", "Port of Loading (POL)", "Demand Forecasting",
             "Vendor-Managed Inventory (VMI)", "Supply Chain Visibility (SCV)", "Reshoring",
             "Nearshoring", "Offshoring", "Global Sourcing", "Supply Chain Resilience",
             "Risk Mitigation", "Sustainability", "Green Supply Chain", "Circular Supply Chain",
             "Carbon Footprint", "Decarbonization", "Digital Supply Chain", "Supply Chain 4.0",
             "Blockchain in Logistics", "Artificial Intelligence (AI)", "Machine Learning (ML)",
             "Predictive Analytics", "Internet of Things (IoT)", "Big Data Analytics",
             "End-to-End Visibility", "Control Tower", "Omnichannel Fulfillment", "E-commerce Logistics",
             "Supply Chain Diversification", "Geopolitical Risk", "Trade Compliance", "Port Congestion",
             "Inventory Optimization", "Supplier Collaboration", "Total Cost of Ownership (TCO)",
             "Agility", "Resilience Index", "Network Optimization", "Multi-Echelon Inventory",
             "Strategic Sourcing", "Dual Sourcing", "Supplier Risk Management",
             "Critical Supply", "Decentralized Warehousing", "Micro-Fulfillment Center",
             "Urban Logistics", "Smart Warehousing", "Autonomous Vehicles", "Drones in Logistics",
             "Robotics Process Automation (RPA)", "Additive Manufacturing (3D Printing)", "Digital Twin",
             "Dynamic Routing", "Capacity Crunch", "Freight Rate Volatility", "Global Trade Tensions",
             "Tariff Impact", "Energy Transition in Transport", "Sustainable Packaging",
             "Extended Producer Responsibility (EPR)", "Reverse Supply Chain", "Collaborative Logistics",
             "Shared Transport Networks", "Strategic Partnerships", "Outsourcing Strategy",
             "Lines Orders", "Radio Parc", "Freight", "Highjump"
]

# KEY_TERMS = ["Warehouse", "CEO", "Investment Funding", "Merger Acquisition"]

ARTICLE_AGE_DAYS = 90

RECIEVER_EMAIL = os.getenv("SENDER_EMAIL")
# endregion

# region Logging 
logging.basicConfig(filename='app.log', level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# endregion

# region NLTK Resources
nltk.download('popular')
# endregion

def get_old_articles() -> pd.DataFrame:
    try:
        with open("news_articles.csv", "r") as f:
            reader = csv.DictReader(f)
            return pd.DataFrame(reader)
    except FileNotFoundError:
        logging.debug('No existing news articles found.')
        return pd.DataFrame()

def get_redirect_link(url) -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            # Set user agent to avoid detection
            page.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            })
            
            # Navigate with longer timeout and wait for load
            page.goto(url, wait_until="load", timeout=10000)
            
            # Try to wait for network to be idle with shorter timeout
            try:
                page.wait_for_load_state("networkidle", timeout=5000)
            except:
                pass  # Continue if network idle times out
            
            # Get the final URL before closing
            final_url = page.url
            browser.close()
            return final_url
            
        except Exception as e:
            logging.error(f"Error during redirect resolution: {e}")
            browser.close()
            return url  # Return original URL if redirect fails

def skip_article_based_on_age(news_item, age_days: int) -> bool:
    # Skip article if it contains certain keywords
    article_date = datetime(*news_item.published_parsed[:6])
    time_frame = datetime.now() - timedelta(days=age_days)

    return article_date < time_frame

def parse_article(article: Article, url: str = "") -> dict:
    try:

        article.download()
        article.parse()
        article.nlp()

        # summary = summarize_article(article.text) if article.text else ""

        return {
            "title": article.title,
            "authors": article.authors,
            "publish_date": article.publish_date,
            "summary": article.summary,
            # "summary": summary,
            "text": article.text,
            "url": url
        }
    except Exception as e:
        logging.debug(f"Error parsing and summarizing article {url}: {e}")
        return {
            "title": "",
            "publish_date": None,
            "url": "",
            "summary": ""
        }

def search_news_rss(company: str, key_term: str) -> list:
    search_query = f"{company} company {key_term}"
    encoded_query = quote_plus(search_query)

    rss_url = f"https://news.google.com/rss/search?q={encoded_query}"

    try:
        feed = feedparser.parse(rss_url)

        news_data = []

        for entry in feed.entries[:1]:
            article_url = get_redirect_link(entry.link)
            # print(f"Redirected URL for {company} - {key_term}: {article_url}")

            if "google.com" in article_url:
                logging.debug(f"Skipping article with failed redirect: {entry.title} {entry.link}")
                continue

            news_item = {
                'title': entry.title,
                'url': article_url,
                'publish_date': entry.published,
                'summary': entry.summary if 'summary' in entry else '',
                'text': "",
                'company': company,
                'key_term': key_term
            }

            if skip_article_based_on_age(entry, ARTICLE_AGE_DAYS):
                logging.debug(f"Skipping old article from {news_item['published']}: {entry.title[:50]}...")
                continue

            try:
                article_obj = Article(article_url)
                parsed_article = parse_article(article_obj, article_url)

                if parsed_article["publish_date"]:
                    news_item["publish_date"] = parsed_article["publish_date"]

                if parsed_article["summary"]:
                    news_item["summary"] = parsed_article["summary"]
                else:
                    logging.debug(f"No summary generated for article {article_url}, default entry summary.")
                news_item["text"] = parsed_article["text"]
            except Exception as e:
                logging.error(f"Error parsing article {article_url}: {e}")
            
            news_data.append(news_item)

        return news_data
    except Exception as e:
        logging.error(f"Error fetching RSS feed for {company} - {key_term}: {e}")
        return []

def write_to_text_file(news_articles: pd.DataFrame, filename: str = "news_articles.txt"):
    with open(filename, "w", encoding="utf-8") as f:
        for index, row in news_articles.iterrows():
            if row['title'] == "":
                continue
            f.write(f"Title: {row['title']}\n")
            f.write(f"Publish Date: {row['publish_date']}\n")
            f.write(f"URL: {row['url']}\n")
            f.write(f"Summary: {row['summary']}\n")
            f.write("\n")

def write_to_email_body(news_articles: pd.DataFrame) -> str:
    body = "Found the following news articles:\n\n"
    for index, row in news_articles.iterrows():
        if row["title"] == "":
            continue
        body += f"{row['company']} - Focus: {row['key_term']}\n"
        body += f"Title: {row['title']}\n"
        body += f"Publish Date: {row['publish_date']}\n"
        body += f"URL: {row['url']}\n"
        body += f"Summary: {row['summary']}\n"
        body += "\n"
    return body

def main(companies : list[str] = COMPANIES, key_terms: list[str] = KEY_TERMS):

    # Can replace with a DB to keep track of what old articles have been seen
    # Can remove old articles if they are past the date range 
    old_articles = get_old_articles() 

    news_articles = []

    for company in tqdm(companies, desc="Processing Companies"):
        for term in key_terms:
            news_article = search_news_rss(company, term)

            for article in news_article:
                news_articles.append(article)
            sleep(0.25)

    news_articles = pd.DataFrame(news_articles)

    if not old_articles.empty and 'url' in old_articles.columns:
        new_news_articles = news_articles[~news_articles['url'].isin(old_articles['url'])]
    else:
        new_news_articles = news_articles
        logging.info("No previous articles found or invalid format, treating all articles as new.")

    news_articles[["company", "key_term","title", "publish_date", "url"]].to_csv("news_articles.csv", index=False, encoding='utf-8-sig', mode='a')

    subject = f"NewsRadar - {datetime.now().strftime('%Y-%m-%d')}"
    body = ""

    if not new_news_articles.empty:
        print(f"Found {len(new_news_articles)} new articles.")
        write_to_text_file(new_news_articles, "news_articles.txt")
        subject += f"- Found {len(new_news_articles)} new articles"
        body = write_to_email_body(new_news_articles)
    else:
        print("No new articles found.")
        subject += " - No New Articles"
        body = "No news articles found this week."
        
    try:
        send_email(RECIEVER_EMAIL, subject, body)
        logging.info(f"Email sent successfully to {RECIEVER_EMAIL}")
    except Exception as e:
        logging.error(f"Failed to send email to {RECIEVER_EMAIL}: {e}")
    
    # Return results for web app usage
    return {
        'all_articles': news_articles,
        'new_articles': new_news_articles,
        'subject': subject,
        'body': body
    }

def main_web_friendly(companies: list[str], key_terms: list[str], progress_callback=None, receiver_email=None):
    """Web-app friendly version of main function with progress tracking and custom email"""
    try:
        if progress_callback:
            progress_callback(10, "Initializing search...")
        
        old_articles = get_old_articles()
        news_articles = []
        
        total_combinations = len(companies) * len(key_terms)
        current_combination = 0
        
        if progress_callback:
            progress_callback(20, "Searching for news articles...")
        
        for company in companies:
            for term in key_terms:
                current_combination += 1
                if progress_callback:
                    progress = 20 + int((current_combination / total_combinations) * 60)
                    progress_callback(progress, f"Searching {company} for {term}...")
                
                news_article = search_news_rss(company, term)
                for article in news_article:
                    news_articles.append(article)
                sleep(0.25)
        
        if progress_callback:
            progress_callback(85, "Processing results...")
        
        news_articles = pd.DataFrame(news_articles)
        
        if not old_articles.empty and 'url' in old_articles.columns:
            new_news_articles = news_articles[~news_articles['url'].isin(old_articles['url'])]
        else:
            new_news_articles = news_articles
            logging.info("No previous articles found or invalid format, treating all articles as new.")
        
        # Save articles
        if not news_articles.empty:
            news_articles[["company", "key_term","title", "publish_date", "url"]].to_csv(
                "news_articles.csv", index=False, encoding='utf-8-sig', mode='a')
        
        # Prepare email
        subject = f"NewsRadar - {datetime.now().strftime('%Y-%m-%d')}"
        body = ""
        
        if not new_news_articles.empty:
            logging.info(f"Found {len(new_news_articles)} new articles.")
            write_to_text_file(new_news_articles, "news_articles.txt")
            subject += f"- Found {len(new_news_articles)} new articles"
            body = write_to_email_body(new_news_articles)
        else:
            logging.info("No new articles found.")
            subject += " - No New Articles"
            body = "No news articles found this week."
        
        # Send email if receiver_email is provided
        if receiver_email:
            try:
                send_email(receiver_email, subject, body)
                logging.info(f"Email sent successfully to {receiver_email}")
            except Exception as e:
                logging.error(f"Failed to send email to {receiver_email}: {e}")
        
        if progress_callback:
            progress_callback(100, f"Search completed! Found {len(new_news_articles)} new articles.")
        
        return {
            'success': True,
            'all_articles': news_articles,
            'new_articles': new_news_articles,
            'subject': subject,
            'body': body,
            'message': f"Found {len(new_news_articles)} new articles."
        }
        
    except Exception as e:
        logging.error(f"Error in main_web_friendly: {e}")
        if progress_callback:
            progress_callback(0, f"Search failed: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'all_articles': pd.DataFrame(),
            'new_articles': pd.DataFrame(),
            'message': f"Search failed: {str(e)}"
        }

if __name__ == "__main__":
    main()