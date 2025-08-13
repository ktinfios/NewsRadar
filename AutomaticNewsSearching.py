import csv
import feedparser
import pandas as pd 
import nltk 
import random
from newspaper import Article
from playwright.sync_api import sync_playwright
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from tqdm import tqdm
from time import sleep 
from datetime import datetime, timedelta
from urllib.parse import quote_plus

nltk.download('popular')

# COMPANIES = ["Bulten", "Volvo", "Viking Life", "Rockwool A/S", "Carlsberg", 
#              "Hornbach Baumarkt AG", "Bültel Bekleidungswerke GmbH",
#              "OBI Group Holding SE & Co.KGaA", "LKW Walter", "F. H. Bertling"]
# COMPANIES = ["Bulten", "Volvo", "Viking Life", "Rockwool A/S", "Carlsberg", 
#              "Hornbach Baumarkt AG", "Bültel Bekleidungswerke GmbH"]
COMPANIES = ["OBI Group Holding SE & Co.KGaA", "LKW Walter", "F. H. Bertling"]

KEY_TERMS = ["Digital Transformation", "Bottleneck", "Warehouse", "CEO", "Optimization", "Fulfillment",
             "Investment Funding", "Merger Acquisition"]

GOOGLE_NEWS_URL = "https://news.google.com"
GOOGLE_NEWS_SEARCH_URL = "https://news.google.com/search?q={}&hl=en-US&gl=US&ceid=US%3Aen"

def get_companies():
    # FUTURE WORK 
    # Read CSV and return company names
    return COMPANIES

def get_old_articles():
    try:
        with open("news_articles.csv", "r") as f:
            reader = csv.DictReader(f)
            return pd.DataFrame(reader)
    except FileNotFoundError:
        return pd.DataFrame()

def get_selenium_driver():
    options = Options()
    options.add_argument("--headless")  # Run in headless mode
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    # Suppress SSL and security warnings
    options.add_argument("--ignore-ssl-errors")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--allow-running-insecure-content")
    options.add_argument("--disable-web-security")
    options.add_argument("--ignore-certificate-errors-spki-list")
    options.add_argument("--disable-extensions")
    
    # Suppress logging and console output
    options.add_argument("--disable-logging")
    options.add_argument("--log-level=3")  # Only fatal errors
    options.add_argument("--silent")
    options.add_argument("--disable-gpu-logging")
    
    # Additional performance and error suppression
    options.add_argument("--disable-background-timer-throttling")
    options.add_argument("--disable-renderer-backgrounding")
    options.add_argument("--disable-backgrounding-occluded-windows")
    
    # Initialize the Chrome driver
    driver = webdriver.Chrome(options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    return driver

def end_selenium_driver(driver: webdriver):
    driver.quit()

def get_redirect_link(driver: webdriver, article_url: str, max_retries: int = 2) -> str:
    """
    Get the final redirect URL from a Google News link with retry logic
    """
    for attempt in range(max_retries):
        try:
            driver.get(article_url)
            # Wait a bit for redirects to complete
            sleep(0.5)
            final_url = driver.current_url
            
            # Check if redirect was successful
            if "google.com" not in final_url:
                return final_url
            else:
                print(f"Attempt {attempt + 1}: Still contains google.com, retrying...")
                if attempt < max_retries - 1:
                    sleep(0.5)  # Wait before retry
                    
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                sleep(0.5)
    
    # If all retries failed, return the original URL
    print(f"All {max_retries} attempts failed for {article_url}")
    return article_url

def parse_article(article: Article, original_url: str = None) -> dict:

    try:
        article.download()
        article.parse()
        article.nlp()

        return {
            "title": article.title,
            "publish_date": article.publish_date,
            "url": original_url if original_url else article.source_url,
            "keywords": article.keywords,
            "summary": article.summary
        }
    except Exception as e:
        print(f"Error parsing article: {e}")
        return {
            "title": "",
            "publish_date": None,
            "url": "",
            # "keywords": [],
            "summary": ""
        }

def search_news_rss(company: str, key_term: str, driver: webdriver) -> list:
    search_query = f"{company} company {key_term}"
    encoded_query = quote_plus(search_query)
    
    # Google News RSS URL
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}"

    # print(rss_url)
    feed = feedparser.parse(rss_url)

    try:
        news_data = []
        for entry in feed.entries[:1]: # get the first article only
            article_url = get_redirect_link(driver, entry.link)
            
            # Skip if redirect failed (still contains google.com)
            if "google.com" in article_url:
                print(f"Skipping article with failed redirect: {entry.title[:50]}...")
                continue
            
            article_data = {
                "title": entry.title,
                "publish_date": entry.published,
                "url": article_url,  # Use the resolved URL
                "company": company,
                "key_term": key_term
            }

            if entry.published_parsed is None:
                print(f"Skipping article with no publish date: {entry.title[:50]}...")
                continue
            
            # Check if article is from the past month
            article_date = datetime(*entry.published_parsed[:6])
            one_month_ago = datetime.now() - timedelta(days=30)

            if article_date < one_month_ago:
                print(f"Skipping old article from {article_date.strftime('%Y-%m-%d')}: {entry.title[:50]}...")
                continue

            try:
                article_obj = Article(article_url)
                parsed_article = parse_article(article_obj, article_url)
                parsed_article["publish_date"] = entry.published
                parsed_article["company"] = company
                parsed_article["key_term"] = key_term
                news_data.append(parsed_article)
            except Exception as e:
                print(f"Error parsing article {article_url}: {e}")
                # Still add basic article data even if parsing fails
                news_data.append(article_data)
        
        return news_data
    except Exception as e:
        print(f"Error fetching RSS feed for {company} - {key_term}: {e}")
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

def main():
    companies = get_companies()

    driver = get_selenium_driver()

    old_articles = get_old_articles()

    news_articles = pd.DataFrame(columns=["company", "key_term","title", "publish_date", "url", "summary"])

    for company in tqdm(companies):
        print(f"Searching news for {company}...")
        for search_term in KEY_TERMS:
            # delay = random.uniform(0.3, 0.5)
            # print(f"Waiting {delay:.1f} seconds before next request...")
            sleep(0.25)

            news_data = search_news_rss(company, search_term, driver=driver)
            if news_data:  # Only add if we got data
                news_articles = pd.concat([news_articles, pd.DataFrame(news_data)], ignore_index=True)
    
    # Check if old_articles has 'url' column and handle comparison safely
    if not old_articles.empty and 'url' in old_articles.columns:
        new_news_articles = news_articles[~news_articles['url'].isin(old_articles['url'])]
    else:
        # If no old articles or no 'url' column, treat all articles as new
        new_news_articles = news_articles
        print("No previous articles found or invalid format, treating all articles as new.")

    news_articles[["company", "key_term","title", "publish_date", "url"]].to_csv("Results/news_articles.csv", index=False, encoding='utf-8-sig', mode='a')

    if not new_news_articles.empty:
        print(f"Found {len(new_news_articles)} new articles.")
        write_to_text_file(new_news_articles, "Results/news_articles.txt")
    else:
        print("No new articles found.")

    end_selenium_driver(driver)

if __name__ == "__main__":
    # Take in Excel file name 
    main()

# Make an automatic weekly email with the news articles 
# Update with new articles one a week 
# take in email address 
# Document the processes of the code 
# Make sure a video is made before august 8th 