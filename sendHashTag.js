import fetch from "node-fetch";

const WEBHOOK_URL_2 =
  "https://discord.com/api/webhooks/1337713733941727232/XQKhYWfWYUcIEfXiSapGKSpAlWqx2Dvfmm169c6u3nwYpHPEAimnooai8bzKTKE0_kre";

const sendWebhook = async (url, embed) => {
  try {
    if (url === "YOUR_WEBHOOK_URL_2") {
      console.log("Skipping webhook - URL not configured");
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

export const sendHashtagEmbeds = async (hashtagData) => {
  if (
    !hashtagData ||
    typeof hashtagData !== "object" ||
    Object.keys(hashtagData).length === 0
  ) {
    console.error("Error: Invalid or empty hashtag data");
    return;
  }

  for (const hashtag in hashtagData) {
    const data = hashtagData[hashtag];

    // Skip if tweets array is not present or empty
    if (
      !data.tweets ||
      !Array.isArray(data.tweets) ||
      data.tweets.length === 0
    ) {
      console.log(`Skipping ${hashtag} - no tweets available`);
      continue;
    }

    // Get the first tweet from the array
    const tweet = data.tweets[0];

    // Create an embed for this hashtag using the first tweet
    const embed = {
      title: `Latest Tweet for ${hashtag}`,
      description: tweet.text,
      color: 3447003, // Discord blue color
      fields: [
        { name: "Author", value: tweet.author, inline: true },
        { name: "Username", value: tweet.username, inline: true },
        { name: "Likes", value: tweet.likes, inline: true },
        { name: "Retweets", value: tweet.retweets, inline: true },
        { name: "Replies", value: tweet.replies, inline: true },
      ],
      timestamp: new Date(tweet.timestamp).toISOString(),
      footer: {
        text: `Scraped at: ${new Date(data.scrapedAt).toLocaleString()}`,
      },
    };

    // Send the embed
    await sendWebhook(WEBHOOK_URL_2, embed);

    // Add delay between webhook calls to avoid rate limiting
    await new Promise((resolve) => setTimeout(resolve, 1000)); // 1 second delay
  }
};
