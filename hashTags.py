import os
import time
import requests
import schedule
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Load environment variables
load_dotenv()
USERNAME = os.getenv("TWITTER_USERNAME")
PASSWORD = os.getenv("TWITTER_PASSWORD")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

class TwitterHashtagScraper:
    def __init__(self, hashtags):
        self.hashtags = hashtags if isinstance(hashtags, list) else [hashtags]

        # Chrome configuration
        self.options = webdriver.ChromeOptions()  
        self.options.add_argument("--headless")
        self.options.add_argument("--disable-blink-features=AutomationControlled")
        self.options.add_experimental_option("excludeSwitches", ["enable-automation"])
        self.options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        self.options.add_argument("--no-sandbox")
        self.options.add_argument("--disable-dev-shm-usage")
        self.options.add_argument('--ignore-ssl-errors=yes')
        self.options.add_argument('--ignore-certificate-errors')


        # Initialize the WebDriver using self.options
        self.driver = webdriver.Remote(
        command_executor='http://172.17.0.2:4444/wd/hub',
        options=self.options
        )
        self.wait = WebDriverWait(self.driver, 20)
        self.login()  # Login once

    def login(self):
        """Logs into Twitter (X) once."""
        try:
            self.driver.get("https://x.com/i/flow/login")

            # Enter username
            username_field = self.wait.until(EC.presence_of_element_located((By.NAME, "text")))
            username_field.send_keys(USERNAME)
            self.wait.until(EC.element_to_be_clickable((By.XPATH, "//span[contains(text(),'Next')]"))).click()

            # Enter password
            password_field = self.wait.until(EC.presence_of_element_located((By.NAME, "password")))
            password_field.send_keys(PASSWORD)
            self.wait.until(EC.element_to_be_clickable((By.XPATH, "//span[contains(text(),'Log in')]"))).click()

            # Confirm login
            self.wait.until(EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/home')]")))
            # time.sleep(2)
            print("✅ Logged in successfully!")

        except Exception as e:
            print(f"❌ Login failed: {e}")
            self.driver.quit()
            raise

    def get_latest_tweets(self, hashtag, num_tweets=5):
        """Scrapes latest tweets for a given hashtag."""
        try:
            url = f"https://x.com/search?q=%23{hashtag}&src=typed_query&f=live"
            self.driver.get(url)
            self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'article[data-testid="tweet"]')))

            tweets_data = []
            seen_tweets = set()

            while len(tweets_data) < num_tweets:
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1.5)

                articles = self.driver.find_elements(By.CSS_SELECTOR, 'article[data-testid="tweet"]')
                for article in articles[-5:]:  # Check latest 5 tweets each scroll
                    tweet = self.extract_tweet_data(article)
                    if tweet['id'] not in seen_tweets:
                        tweets_data.append(tweet)
                        seen_tweets.add(tweet['id'])
                        if len(tweets_data) >= num_tweets:
                            break

            return tweets_data[:num_tweets]

        except Exception as e:
            print(f"❌ Error fetching tweets: {e}")
            return None

    def extract_tweet_data(self, article):
        """Extracts tweet details from the HTML."""
        tweet = {'id': article.get_attribute('aria-labelledby') or ''}

        try:
            user_element = article.find_element(By.CSS_SELECTOR, '[data-testid="User-Name"]')
            tweet['username'] = user_element.find_element(By.TAG_NAME, 'a').get_attribute('href').split('/')[-1]
            tweet['display_name'] = user_element.find_element(By.TAG_NAME, 'div').text
        except:
            tweet['username'] = tweet['display_name'] = 'N/A'

        tweet['text'] = self.get_element_text(article, '[data-testid="tweetText"]')

        try:
            time_element = article.find_element(By.TAG_NAME, 'time')
            tweet['timestamp'] = time_element.get_attribute('datetime')
            tweet['link'] = time_element.find_element(By.XPATH, './..').get_attribute('href')
        except:
            tweet['timestamp'] = tweet['link'] = 'N/A'

        metrics = ['replies', 'reposts', 'likes', 'views']
        elements = article.find_elements(By.CSS_SELECTOR, '[data-testid="reply"] span, [data-testid="retweet"] span, [data-testid="like"] span, [data-testid="app-text-transition-container"] span')
        tweet.update({metrics[i]: (e.text if e.text else '0') for i, e in enumerate(elements[:4])})

        tweet['media'] = [img.get_attribute('src') for img in article.find_elements(By.CSS_SELECTOR, 'img[alt="Image"]')]

        return tweet

    def get_element_text(self, parent, selector):
        """Returns the text of an element if it exists."""
        try:
            return parent.find_element(By.CSS_SELECTOR, selector).text
        except:
            return 'N/A'

    def close(self):
        """Closes the WebDriver."""
        self.driver.quit()

def send_to_discord(tweet):
    """Sends a tweet as an embed to Discord."""
    if not DISCORD_WEBHOOK_URL:
        print("❌ No Discord Webhook URL provided!")
        return

    embed = {
        "title": f"Tweet by {tweet['display_name']} (@{tweet['username']})",
        "description": tweet["text"][:200] + "...",
        "url": tweet["link"],
        "color": 0x1DA1F2,  # Twitter Blue
        "fields": [
            {"name": "Replies", "value": tweet["replies"], "inline": True},
            {"name": "Retweets", "value": tweet["reposts"], "inline": True},
            {"name": "Likes", "value": tweet["likes"], "inline": True}
        ],
        "image": {"url": tweet["media"][0]} if tweet["media"] else None
    }

    payload = {"embeds": [embed]}
    response = requests.post(DISCORD_WEBHOOK_URL, json=payload)

    if response.status_code == 204:
        print("✅ Successfully sent to Discord!")
    else:
        print(f"❌ Failed to send: {response.status_code} - {response.text}")

def scrape_and_send(scraper, hashtags):
    """Scrapes tweets and sends them to Discord."""
    for hashtag in hashtags:
        print(f"\n📢 Scraping #{hashtag}...")
        tweets = scraper.get_latest_tweets(hashtag, 3)

        if tweets:
            for tweet in tweets:
                send_to_discord(tweet)

def main():
    HASHTAGS = ["crypto", "bitcoin", "dogecoin"]
    scraper = TwitterHashtagScraper(HASHTAGS)

    # Schedule the job every 5 minutes
    schedule.every(1).minutes.do(scrape_and_send, scraper=scraper, hashtags=HASHTAGS)

    print("⏳ Scraper running every 5 minutes...")
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopping scraper...")
        scraper.close()

if __name__ == "__main__":
    main()
