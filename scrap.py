import os
import requests
import json
import logging
from bs4 import BeautifulSoup

# 🔐 Secure Telegram Bot Credentials (From GitHub Secrets)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    print("❌ Missing Telegram credentials! Check GitHub Secrets.")
    exit(1)

# 📌 Headers to mimic a real browser request
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept-Language": "ne-NP,ne;q=0.9,en-US;q=0.8,en;q=0.7",
}

# 🔧 Configure logging (Save logs in the runner environment)
LOG_FILE = "scraper_error.log"
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def extract_summary(article):
    """Extracts a brief summary from the article content"""
    paragraph = article.find("p")
    return paragraph.get_text(strip=True) if paragraph else "No summary available."


def scrape_kathmandupost():
    """Scrapes up to 10 latest news from Kathmandu Post with summaries"""
    url = "https://kathmandupost.com/"
    base_url = "https://kathmandupost.com"

    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code != 200:
            logging.error(f"Failed to fetch Kathmandu Post: {response.status_code}")
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        news_items = set()

        for article in soup.find_all("article", class_="article-image")[:10]:
            headline_tag = article.find("h3")
            link_tag = headline_tag.find("a") if headline_tag else None
            summary = extract_summary(article)

            if link_tag and "href" in link_tag.attrs:
                title = link_tag.get_text(strip=True)
                link = base_url + link_tag["href"] if link_tag["href"].startswith("/") else link_tag["href"]
                news_items.add((title, link, summary))

        return [{"Source": "Kathmandu Post", "Headline": title, "Link": link, "Summary": summary} for title, link, summary in news_items]

    except requests.RequestException as e:
        logging.error(f"Error fetching Kathmandu Post: {str(e)}")
        return []


def scrape_onlinekhabar():
    """Scrapes up to 10 latest news from OnlineKhabar with summaries"""
    url = "https://english.onlinekhabar.com/"

    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code != 200:
            logging.error(f"Failed to fetch OnlineKhabar: {response.status_code}")
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        news_items = set()

        for article in soup.find_all("div", class_="ok-post-contents")[:10]:
            headline_tag = article.find("h2")
            link_tag = headline_tag.find("a") if headline_tag else None
            summary = extract_summary(article)

            if link_tag:
                title = link_tag.get_text(strip=True)
                link = link_tag["href"]
                news_items.add((title, link, summary))

        return [{"Source": "OnlineKhabar", "Headline": title, "Link": link, "Summary": summary} for title, link, summary in news_items]

    except requests.RequestException as e:
        logging.error(f"Error fetching OnlineKhabar: {str(e)}")
        return []


def scrape_myrepublica():
    """Scrapes up to 10 latest economy news from MyRepublica with summaries"""
    url = "https://myrepublica.nagariknetwork.com/category/economy"
    base_url = "https://myrepublica.nagariknetwork.com"

    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code != 200:
            logging.error(f"Failed to fetch MyRepublica: {response.status_code}")
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        news_items = set()

        articles = soup.find_all("div", class_="cat_list")[:10]

        if not articles:
            logging.warning("No news articles found on MyRepublica.")
            return []

        for article in articles:
            headline_tag = article.find("h3")
            link_tag = headline_tag.find("a") if headline_tag else None
            summary = extract_summary(article)

            if link_tag and "href" in link_tag.attrs:
                title = link_tag.get_text(strip=True)
                link = base_url + link_tag["href"] if link_tag["href"].startswith("/") else link_tag["href"]
                news_items.add((title, link, summary))

        return [{"Source": "MyRepublica", "Headline": title, "Link": link, "Summary": summary} for title, link, summary in news_items]

    except requests.RequestException as e:
        logging.error(f"Error fetching MyRepublica: {str(e)}")
        return []


def send_telegram_message(news_list):
    """Sends new news articles with summaries to Telegram"""
    if not news_list:
        return

    message = "📰 **Nepali News Update**\n\n"
    for news in news_list:
        message += f"🔹 *{news['Source']}*\n{news['Headline']}\n{news['Summary']}\n🔗 {news['Link']}\n\n"

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}

    requests.post(url, json=payload)


def load_past_news():
    """Loads past news to avoid duplicates"""
    try:
        with open("past_news.json", "r", encoding="utf-8") as file:
            past_news_list = json.load(file)
            return {tuple(item) for item in past_news_list}
    except (FileNotFoundError, json.JSONDecodeError):
        return set()


def save_past_news(news_set):
    """Saves new news articles to avoid duplicates"""
    with open("past_news.json", "w", encoding="utf-8") as file:
        json.dump([list(item) for item in news_set], file, indent=4, ensure_ascii=False)


# 🔥 Scrape news from all sources
news_sources = {
    "Kathmandu Post": scrape_kathmandupost(),
    "OnlineKhabar": scrape_onlinekhabar(),
    "MyRepublica": scrape_myrepublica(),
}

# Load past news
past_news = load_past_news()
unique_news = set()
new_news_list = []

# 📌 Ensure maximum of 30 articles total
for source, articles in news_sources.items():
    for article in articles:
        news_tuple = (article["Headline"], article["Link"], article["Summary"])
        if news_tuple not in past_news and len(new_news_list) < 30:
            unique_news.add(news_tuple)
            new_news_list.append(article)

# Save updated past news
save_past_news(unique_news | past_news)

# Send new news to Telegram
send_telegram_message(new_news_list)
print(f"✅ Sent {len(new_news_list)} new articles to Telegram.")
