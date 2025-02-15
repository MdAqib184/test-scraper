import fetch from "node-fetch";

const WEBHOOK_URL_1 =
  "https://discord.com/api/webhooks/1337468470962426037/i9hSk6hdEH6TGVb0LtLSBZcKByNGy96ppyUyEFyWbLHopC-Kv0mOiLzuwOwJAbwiWXn2";
const WEBHOOK_URL_2 = "YOUR_WEBHOOK_URL_2";

const sendWebhook = async (url, embed) => {
  try {
    if (url === "YOUR_WEBHOOK_URL_2") {
      console.log("Skipping webhook 2 - URL not configured");
      return;
    }

    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ embeds: [embed] }),
    });

    // Check if the response is ok before trying to parse JSON
    if (!response.ok) {
      throw new Error(
        `HTTP error! Status: ${response.status}, Text: ${await response.text()}`
      );
    }

    // Only try to parse JSON if we have content
    const text = await response.text();
    const result = text ? JSON.parse(text) : {};
    console.log("Webhook sent successfully:", result);
  } catch (error) {
    console.error("Error sending webhook:", error);
  }
};

export const sendTwitterEmbeds = async (profileData) => {
  for (const account in profileData) {
    const data = profileData[account];

    // Skip if tweets object is not present
    if (!data.tweets) {
      console.log(`Skipping ${account} - no tweets data available`);
      continue;
    }

    const tweet = data.tweets;

    // Create a single, comprehensive embed for this account
    const embed = {
      title: `New Tweet from ${data.profileName} (${data.username})`,
      url: tweet.postLink,
      description: `"${tweet.description}"`,
      color: 3447003,
      thumbnail: { url: tweet.imageUrl !== "No image" ? tweet.imageUrl : null },
      fields: [
        { name: "Followers", value: data.followers, inline: true },
        { name: "Following", value: data.following, inline: true },
        { name: "Likes", value: tweet.likes, inline: true },
        { name: "Retweets", value: tweet.retweets, inline: true },
        { name: "Replies", value: tweet.replies, inline: true },
      ],
      timestamp: new Date(tweet.submitted).toISOString(),
      footer: {
        text: `Scraped at: ${new Date(data.scrapedAt).toLocaleString()}`,
      },
    };

    // Send just one embed per account
    await sendWebhook(WEBHOOK_URL_1, embed);

    // Add delay between webhook calls to avoid rate limiting
    await new Promise((resolve) => setTimeout(resolve, 1000)); // 1 second delay
  }
};
