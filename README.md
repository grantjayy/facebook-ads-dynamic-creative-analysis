# Facebook Ads Dynamic Creative Analysis Tool

This repository contains a Python script for analyzing Facebook ad campaign data. It extracts
data using the Facebook Marketing API, processes it, and generates visualizations and CSV reports.

## What this is for

You can use this script to gain meaningful insights about the performance of various elements of your creatives.

Want to know which headline performs the best in a campaign? Done.

Want to know which primary text has the highest conversion rate? Easy.

No more flying blind when launching new creatives. Make data-driven decisions to make an impact on your marketing.

## Features

- Fetch ads data from a specified Facebook Ads account.
- Calculate metrics such as click-through rate, cost per lead, lead conversion rate, and more.
- Create bar plots for total metrics by different ad breakdowns.
- Create scatter plots to visualize the relationship between click-through rate, lead conversion rate, and cost per lead.
- Export processed data to CSV for further analysis.

## Setup

To use this tool, you will need to set up a Meta app and get your app ID, app secret, and access token. 
Here are the steps to get started:

1. Go to [Meta for Developers](https://developers.facebook.com/) and create a new app.
2. Add the 'Marketing API' product to your app.
3. In the app's settings, find your App ID and App Secret.
4. Generate an access token with the necessary permissions (e.g., `ads_read`).
5. Save these credentials in a `.env` file at the root of this project with the following keys:
   - `MY_APP_ID`
   - `MY_APP_SECRET`
   - `MY_ACCESS_TOKEN`
   - `AD_ACCOUNT_ID` with your ad account ID.

## Usage

Run the script using Python 3. Make sure all dependencies are installed by running `pip install -r requirements.txt`.

```bash
python creatives.py
```

## Output

The script will generate visualizations and save them in an `output` directory, organized by timestamps and breakdown types. CSV reports will also be saved in this directory.

Note: The date range for the data can be customized using the `since` and `until` variables in the script.
