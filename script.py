import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

class TwitterScraper:
    def __init__(self, usernames):
        self.usernames = usernames if isinstance(usernames, list) else [usernames]
        self.latest_timestamps = {username: None for username in usernames}
        self.driver = None
        self.setup_driver()

    def setup_driver(self):
        """Initialize Chrome driver with Docker-compatible options"""
        self.options = webdriver.ChromeOptions()
        self.options.add_argument('--headless')
        self.options.add_argument('--no-sandbox')
        self.options.add_argument('--disable-dev-shm-usage')
        self.options.add_argument('--disable-gpu')
        self.options.add_argument("--window-size=1920,1080")
        self.options.add_argument("--disable-blink-features=AutomationControlled")
        self.options.add_argument('--ignore-ssl-errors=yes')
        self.options.add_argument('--ignore-certificate-errors')
        self.options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        # Create unique temporary user data directory
        user_data_dir = f"/tmp/chrome-data-{time.time()}"
        self.options.add_argument(f"--user-data-dir={user_data_dir}")
        
        # Initialize the WebDriver using self.options
        self.driver = webdriver.Remote(
        command_executor='http://localhost:5555/wd/hub',
        options=self.options
        )
        self.wait = WebDriverWait(self.driver, 20)

    def get_profile_info(self, username):
        """Get Twitter profile information"""
        try:
            url = f"https://x.com/{username}"
            self.driver.get(url)
            time.sleep(5)

            profile_data = {}
            
            # Get profile name and handle
            name_element = self.wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, '[data-testid="UserName"]')))
            profile_data['name'] = name_element.text.split('\n')[0]
            profile_data['handle'] = name_element.text.split('\n')[1]

            # Get bio
            try:
                bio_element = self.wait.until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, '[data-testid="UserDescription"]')))
                profile_data['bio'] = bio_element.text
            except TimeoutException:
                profile_data['bio'] = "No bio available"

            # Get following/followers counts
            for metric in ['following', 'followers']:
                try:
                    element = self.driver.find_element(
                        By.CSS_SELECTOR, 
                        f"a[href='/{username}/{metric}'] span.css-1jxf684"
                    )
                    profile_data[metric] = element.text.split()[0]
                except:
                    profile_data[metric] = "Not available"
            
            return profile_data

        except Exception as e:
            print(f"Error fetching profile info for {username}: {e}")
            return None

    def get_tweets(self, username, num_tweets=5):
        """Get recent tweets from a user"""
        try:
            url = f"https://x.com/{username}"
            self.driver.get(url)
            time.sleep(2)
            
            tweets_data = []
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            
            while len(tweets_data) < num_tweets:
                tweet_articles = self.wait.until(EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, 'article[data-testid="tweet"]')))
                
                for article in tweet_articles:
                    if len(tweets_data) >= num_tweets:
                        break
                        
                    tweet = self.extract_tweet_data(article)
                    if tweet and tweet not in tweets_data:
                        tweets_data.append(tweet)
                
                # Scroll down
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                
                if new_height == last_height:
                    break
                    
                last_height = new_height
            
            return tweets_data[:num_tweets]

        except Exception as e:
            print(f"Error fetching tweets for {username}: {e}")
            return None

    def extract_tweet_data(self, article):
        """Extract data from a tweet article element"""
        tweet = {}
        
        try:
            # Get tweet text
            text_element = article.find_element(By.CSS_SELECTOR, '[data-testid="tweetText"]')
            tweet['text'] = text_element.text
        except:
            tweet['text'] = "No text available"
        
        try:
            # Get tweet time and link
            time_element = article.find_element(By.CSS_SELECTOR, 'time')
            tweet['timestamp'] = time_element.get_attribute('datetime')
            tweet['link'] = time_element.find_element(By.XPATH, './..').get_attribute('href')
        except:
            tweet['timestamp'] = "No timestamp available"
            tweet['link'] = "No link available"
        
        # Get tweet metrics
        metrics = ['replies', 'reposts', 'likes', 'views']
        for metric in metrics:
            try:
                element = article.find_element(By.CSS_SELECTOR, f'[data-testid="{metric}"]')
                tweet[metric] = element.text or "0"
            except:
                tweet[metric] = "0"
        
        # Get media
        try:
            media_elements = article.find_elements(By.CSS_SELECTOR, 'img[alt="Image"]')
            tweet['media'] = [img.get_attribute('src') for img in media_elements]
        except:
            tweet['media'] = []
        
        return tweet

    def send_to_discord(self, webhook_url, username, profile_info, tweets):
        """Send scraped data to Discord"""
        embeds = []
        
        # Profile embed
        if profile_info:
            profile_embed = {
                "title": f"🐦 {profile_info.get('name', 'N/A')} (@{username})",
                "color": 0x1DA1F2,
                "fields": [
                    {"name": "Followers", "value": profile_info.get('followers', 'N/A'), "inline": True},
                    {"name": "Following", "value": profile_info.get('following', 'N/A'), "inline": True},
                    {"name": "Bio", "value": profile_info.get('bio', 'No bio available')[:1024]},
                ],
                "thumbnail": {"url": "https://abs.twimg.com/favicons/twitter.3.ico"}
            }
            embeds.append(profile_embed)

        # Tweet embeds
        if tweets:
            for i, tweet in enumerate(tweets[:3], 1):
                tweet_embed = {
                    "title": f"📝 Tweet #{i}",
                    "description": tweet.get('text', 'No text')[:1500],
                    "color": 0x00ACEE,
                    "fields": [
                        {"name": "Likes", "value": tweet.get('likes', '0'), "inline": True},
                        {"name": "Retweets", "value": tweet.get('reposts', '0'), "inline": True},
                        {"name": "Replies", "value": tweet.get('replies', '0'), "inline": True},
                    ],
                    "url": tweet.get('link', ''),
                    "timestamp": tweet.get('timestamp', '')
                }
                if tweet.get('media'):
                    tweet_embed["image"] = {"url": tweet['media'][0]}
                embeds.append(tweet_embed)

        payload = {
            "username": "Twitter Scraper Bot",
            "avatar_url": "https://abs.twimg.com/favicons/twitter.3.ico",
            "embeds": embeds
        }

        try:
            response = requests.post(webhook_url, json=payload)
            response.raise_for_status()
            print(f"✅ Successfully sent data for @{username} to Discord")
        except Exception as e:
            print(f"❌ Failed to send data for @{username}: {str(e)}")

    def close(self):
        """Clean up resources"""
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                print(f"Error closing driver: {e}")

def main():
    DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
    if not DISCORD_WEBHOOK_URL:
        print("❌ No Discord webhook URL provided!")
        return

    usernames = ["elonmusk", "orangie"]
    scraper = TwitterScraper(usernames)
    
    try:
        while True:
            for username in usernames:
                print(f"\n🟦 Checking @{username}")
                tweets = scraper.get_tweets(username, num_tweets=1)
                
                if tweets:
                    latest_tweet = tweets[0]
                    latest_timestamp = latest_tweet.get('timestamp')
                    
                    if latest_timestamp != scraper.latest_timestamps[username]:
                        print(f"🆕 New tweet from @{username}")
                        scraper.latest_timestamps[username] = latest_timestamp
                        scraper.send_to_discord(DISCORD_WEBHOOK_URL, username, None, [latest_tweet])
                    else:
                        print(f"⏩ No new tweets from @{username}")
                else:
                    print(f"⚠️ No tweets found for @{username}")
            
            print("\n⏳ Waiting 2 minutes...")
            time.sleep(300)

    except KeyboardInterrupt:
        print("\n🛑 Script stopped by user.")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    finally:
        scraper.close()

if __name__ == "__main__":
    main()