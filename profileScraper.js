import puppeteer from "puppeteer";

const sentTweetsSet = new Set(); // Store already scraped tweets

const normalizeTwitterUrl = (input) => {
  if (input.startsWith("http")) {
    return input;
  }
  const username = input.startsWith("@") ? input.slice(1) : input;
  return `https://x.com/${username}`;
};

const getProfileInfo = async (page) => {
  await page.waitForSelector('[data-testid="UserName"]', { timeout: 10000 });

  return await page.evaluate(() => {
    const $ = (selector) => document.querySelector(selector);
    const getTextOrDefault = (selector, defaultValue = "N/A") => {
      const element = $(selector);
      return element ? element.innerText : defaultValue;
    };

    try {
      return {
        profileName: getTextOrDefault('[data-testid="UserName"] div span'),
        username: getTextOrDefault(
          '[data-testid="UserName"] div:nth-of-type(2) span'
        ),
        followers: getTextOrDefault('a[href$="/verified_followers"] span span'),
        following: getTextOrDefault('a[href$="/following"] span span'),
      };
    } catch (error) {
      console.error("Error extracting profile info:", error);
      return {
        profileName: "N/A",
        username: "N/A",
        followers: "N/A",
        following: "N/A",
      };
    }
  });
};

const getRecentTweets = async (page) => {
  await page.waitForSelector("article", { timeout: 40000 });

  await page.evaluate(async () => {
    await new Promise((resolve) => {
      window.scrollBy(0, window.innerHeight * 2);
      setTimeout(resolve, 2000);
    });
  });

  const tweets = await page.evaluate(() => {
    try {
      const tweetElements = [...document.querySelectorAll("article")];

      return tweetElements.map((el) => {
        const getTextOrDefault = (selector, defaultValue = "0") => {
          const element = el.querySelector(selector);
          return element ? element.innerText : defaultValue;
        };

        const timestamp = el.querySelector("time")?.dateTime || "N/A";

        return {
          submitted: timestamp,
          submittedFormatted: new Date(timestamp).toLocaleString(),
          postLink: el.querySelector("time")?.parentElement?.href
            ? `https://x.com${el
                .querySelector("time")
                .parentElement.getAttribute("href")}`
            : "N/A",
          description: getTextOrDefault("div[lang]"),
          replies: getTextOrDefault('[data-testid="reply"]'),
          retweets: getTextOrDefault('[data-testid="retweet"]'),
          likes: getTextOrDefault('[data-testid="like"]'),
          imageUrl: el.querySelector('img[alt="Image"]')?.src || "No image",
        };
      });
    } catch (error) {
      console.error("Error extracting tweet metrics:", error);
      return [];
    }
  });

  // Filter out duplicate tweets
  const newTweets = tweets.filter(
    (tweet) => !sentTweetsSet.has(tweet.submitted)
  );

  // Add new tweets to the set
  newTweets.forEach((tweet) => sentTweetsSet.add(tweet.submitted));

  return newTweets;
};

export const getTwitterData = async (accounts) => {
  let browser;
  const results = {};

  try {
    browser = await puppeteer.launch({
      headless: "new",
      args: [
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
        "--disable-accelerated-2d-canvas",
        "--disable-gpu",
      ],
    });

    const page = await browser.newPage();

    await page.setRequestInterception(true);
    page.on("request", (req) => {
      if (["stylesheet", "font", "image"].includes(req.resourceType())) {
        req.abort();
      } else {
        req.continue();
      }
    });

    await page.setUserAgent(
      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    );
    await page.setViewport({ width: 1280, height: 800 });

    for (const account of accounts) {
      const url = normalizeTwitterUrl(account);
      console.log(`Scraping account: ${url}`);

      try {
        await page.goto(url, {
          waitUntil: "domcontentloaded",
          timeout: 40000,
        });

        const profileData = await getProfileInfo(page);
        const recentTweets = await getRecentTweets(page);

        results[account] = {
          ...profileData,
          tweetCount: recentTweets.length,
          tweets: recentTweets[0],
          scrapedAt: new Date().toISOString(),
        };
      } catch (error) {
        console.error(`Error scraping ${account}:`, error);
        results[account] = {
          error: "Failed to fetch Twitter data",
          details: error.message,
          timestamp: new Date().toISOString(),
        };
      }
    }

    return results;
  } catch (error) {
    console.error("Error during scraping:", error);
    return {
      error: "Failed to initialize scraper",
      details: error.message,
      timestamp: new Date().toISOString(),
    };
  } finally {
    if (browser) {
      await browser.close();
    }
  }
};
