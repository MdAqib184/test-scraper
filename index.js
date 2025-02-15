import cron from "node-cron";
import { getTwitterData } from "./profileScraper.js";
import { scrapeTwitterHashtags } from "./hashTags.js";

const credentials = {
  username: "jawed_uwais_21",
  password: "Iloveux100",
};

const accounts = ["elonmusk", "https://x.com/orangie"];
const hashtags = ["#crypto", "#bitcoin"];

// Function to run both scraping tasks
const runScrapers = async () => {
  console.log("Running Twitter scrapers...");

  try {
    const profileData = await getTwitterData(accounts);
    console.log("Profile Data:", JSON.stringify(profileData, null, 2));

    const hashtagData = await scrapeTwitterHashtags(credentials, hashtags);
    console.log("Hashtag Data:", JSON.stringify(hashtagData, null, 2));
  } catch (error) {
    console.error("Error running scrapers:", error);
  }
};

runScrapers();

//Schedule the cron job to run every 2 minutes
cron.schedule("*/2 * * * *", () => {
  console.log("Cron job triggered");
  runScrapers();
});

console.log("Cron job scheduled to run every 2 minutes");

