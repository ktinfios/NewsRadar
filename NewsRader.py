import csv 
import feedparser 
import pandas as pd 
import nltk 
from datetime import datetime, timedelta
from newspaper import Article
from playwright.sync_api import sync_playwright
from time import sleep 
from tqdm import tqdm 
from transformers import PegasusTokenizer, PegasusForConditionalGeneration
from urllib.parse import quote_plus

GOOGLE_NEWS_URL = "https://news.google.com"
GOOGLE_NEWS_SEARCH_URL = "https://news.google.com/search?q={}&hl=en-US&gl=US&ceid=US%3Aen"

COMPANIES = ["Bulten", "Volvo", "Viking Life", "Rockwool A/S", "Carlsberg", 
             "Hornbach Baumarkt AG", "Bültel Bekleidungswerke GmbH",
             "OBI Group Holding SE & Co.KGaA", "LKW Walter", "F. H. Bertling"]
KEY_TERMS = ["Digital Transformation", "Bottleneck", "Warehouse", "CEO", "Optimization", "Fulfillment",
             "Investment Funding", "Merger Acquisition"]

ARTICLE_AGE_DAYS = 1000

# NLTK Resources
nltk.download('popular')

# Pegasus Model for Summarization
model = "google/pegasus-xsum"
tokenizer = PegasusTokenizer.from_pretrained(model)
model = PegasusForConditionalGeneration.from_pretrained(model)

def get_old_articles():
    try:
        with open("news_articles.csv", "r") as f:
            reader = csv.DictReader(f)
            return pd.DataFrame(reader)
    except FileNotFoundError:
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
            print(f"Error during redirect resolution: {e}")
            browser.close()
            return url  # Return original URL if redirect fails

def skip_article_based_on_age(news_item, age_days: int) -> bool:
    # Skip article if it contains certain keywords
    article_date = datetime(*news_item.published_parsed[:6])
    time_frame = datetime.now() - timedelta(days=age_days)

    return article_date < time_frame

def summarize_article(text: str) -> str:
    
    tokens = tokenizer(text, truncation=True, padding="longest", return_tensors="pt")
    summary_ids = model.generate(**tokens)
    summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)

    return summary

def parse_article(article: Article, url: str = None) -> dict:
    try:

        article.download()
        article.parse()
        # article.nlp()

        summary = summarize_article(article.text) if article.text else ""

        return {
            "title": article.title,
            "authors": article.authors,
            "publish_date": article.publish_date,
            # "summary": article.summary,
            "summary": summary,
            "text": article.text,
            "url": url
        }
    except Exception as e:
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
                print(f"Skipping article with failed redirect: {entry.title[:50]}...")
                continue

            news_item = {
                'title': entry.title,
                'url': entry.link,
                'published': entry.published,
                'summary': entry.summary if 'summary' in entry else '',
                'text': "",
                'company': company,
                'key_term': key_term
            }

            if skip_article_based_on_age(entry, ARTICLE_AGE_DAYS):
                # print(f"Skipping old article from {news_item['published'].strftime('%Y-%m-%d')}: {entry.title[:50]}...")
                continue

            try:
                article_obj = Article(article_url)
                parsed_article = parse_article(article_obj, article_url)
                news_item["publish_date"] = parsed_article["publish_date"]
                if parsed_article["summary"]:
                    news_item["summary"] = parsed_article["summary"]
                news_item["text"] = parsed_article["text"]

            except Exception as e:
                # print(f"Error parsing article {article_url}: {e}")
                pass
            
            news_data.append(news_item)

        return news_data
    except Exception as e:
        # print(f"Error fetching RSS feed for {company} - {key_term}: {e}")
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

    # Can replace with a DB to keep track of what old articles have been seen
    # Can remove old articles if they are past the date range 
    old_articles = get_old_articles() 

    news_articles = []

    for company in tqdm(COMPANIES, desc="Processing Companies"):
        for term in KEY_TERMS:
            news_article = search_news_rss(company, term)

            for article in news_article:
                news_articles.append(article)
            sleep(0.5)

    news_articles = pd.DataFrame(news_articles)

    if not old_articles.empty and 'url' in old_articles.columns:
        new_news_articles = news_articles[~news_articles['url'].isin(old_articles['url'])]
    else:
        new_news_articles = news_articles
        print("No previous articles found or invalid format, treating all articles as new.")

    news_articles[["company", "key_term","title", "publish_date", "url"]].to_csv("news_articles.csv", index=False, encoding='utf-8-sig', mode='a')

    if not new_news_articles.empty:
        print(f"Found {len(new_news_articles)} new articles.")
        write_to_text_file(new_news_articles, "news_articles.txt")
    else:
        print("No new articles found.")

if __name__ == "__main__":
    main()