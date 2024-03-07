import sys
import os
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
import re
import json
from collections import defaultdict
from datetime import datetime
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.adsinsights import AdsInsights

since = None
until = None


date_preset = 'last_7d'
# since = '2022-01-01'
# until = '2022-01-31'


def main():
    breakdowns = [
            "body_asset",
            "call_to_action_asset",
            "description_asset",
            "image_asset",
            "link_url_asset",
            "title_asset",
            "video_asset",
    ]

    for breakdown in breakdowns:
        ads = get_ads(breakdown, since=since, until=until, date_preset=date_preset)

        # print(json.dumps(ads, indent=4))

        df = pd.DataFrame.from_dict(ads)

        df["click_through_rate"] = df["clicks"] / df["impressions"]
        df["cost_per_click"] = df["spend"] / df["clicks"]
        df["cost_per_lead"] = df["spend"] / df["lead"]
        df["cost_per_purchase"] = df["spend"] / df["purchase"]

        create_plot(
                df,
                "barplot",
                "breakdown",
                "click_through_rate",
                f"Click Through Rate by {breakdown}",
                f"ctr_by_{breakdown}.png",
                figsize=(30, 30),
        )


        # current_time = datetime.now()
        # formatted_time = current_time.strftime("%Y-%m-%dT%H-%M-%S")
        #
        # time_period = ''
        #
        # if since and until:
        #     time_period = f"{since} to {until}"
        # else:
        #     time_period = date_preset

        # export_to_csv(df, f"{formatted_time} {breakdown} {time_period}.csv")
        break

def get_ads(breakdown, date_preset=None, since=None, until=None):
    print(f"Getting ads for breakdown: {breakdown}")

    my_app_id = os.environ.get('FB_APP_ID')
    my_app_secret = os.environ.get('MY_APP_SECRET')
    my_access_token = os.environ.get('MY_ACCESS_TOKEN')
    ad_account_id = os.environ.get('AD_ACCOUNT_ID')

    FacebookAdsApi.init(my_app_id, my_app_secret, my_access_token)
    ad_account = AdAccount(f'act_{ad_account_id}')

    params = {
        "level": "ad",
        "breakdowns": [breakdown],
        "filtering": [
            {
                "field": "ad.effective_status",
                "operator": "IN",
                "value": ["ACTIVE", "PAUSED", "DELETED", "ARCHIVED", "IN_PROCESS", "WITH_ISSUES"],
            }
        ],
    }

    # Conditionally add date preset or time range to params
    if date_preset:
        params["date_preset"] = date_preset
    elif since and until:
        params["time_range"] = {"since": since, "until": until}

    ads = ad_account.get_insights(params=params,
                                  fields=[
                                      AdsInsights.Field.account_id,
                                      AdsInsights.Field.account_name,
                                      AdsInsights.Field.campaign_id,
                                      AdsInsights.Field.adset_id,
                                      AdsInsights.Field.ad_id,
                                      AdsInsights.Field.campaign_name,
                                      AdsInsights.Field.adset_name,
                                      AdsInsights.Field.ad_name,
                                      AdsInsights.Field.spend,
                                      AdsInsights.Field.impressions,
                                      AdsInsights.Field.clicks,
                                      AdsInsights.Field.actions,
                                  ])

    ads = [ad for ad in ads]

    print(f"Retrieved {len(ads)} ads for breakdown: {breakdown}. Formatting data...")

    # Mapping of breakdown types to their key and id in the asset
    breakdown_mapping = {
        "body_asset": ('text', 'id'),
        "call_to_action_asset": ('type', 'id'),
        "description_asset": ('text', 'id'),
        "image_asset": ('image_name', 'id'),
        "link_url_asset": ('display_url', 'id'),
        "title_asset": ('text', 'id'),
        "video_asset": ('video_name', 'id'),
    }

    if breakdown not in breakdown_mapping:
        sys.exit(f"Invalid breakdown: {breakdown}. Exiting.")

    for i, ad in enumerate(ads):
        ad = {
            "account_id": ad.get("account_id"),
            "account_name": ad.get("account_name"),
            "campaign_id": ad.get("campaign_id"),
            "adset_id": ad.get("adset_id"),
            "ad_id": ad.get("ad_id"),
            "campaign_name": ad.get("campaign_name"),
            "adset_name": ad.get("adset_name"),
            "ad_name": ad.get("ad_name"),
            "spend": float(ad.get("spend")),
            "impressions": int(ad.get("impressions")),
            "clicks": int(ad.get("clicks")),
            "actions": ad.get("actions"),
            "breakdown": ad.get(breakdown),
        }

        asset = ad.get('breakdown')
        if not asset:
            sys.exit(f"Breakdown {breakdown} not found in ad data. Exiting.")

        key_field, id_field = breakdown_mapping[breakdown]
        ad["breakdown"] = remove_emojis(asset.get(key_field)).replace('\n', ' ')
        ad["breakdown_id"] = asset.get(id_field)        

        for a in ad["actions"]:
            ad[a["action_type"]] = int(a["value"])

        del ad["actions"]

        ads[i] = ad

    return ads

def remove_emojis(text):
    # Unicode ranges for emojis
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F700-\U0001F77F"  # alchemical symbols
        "\U0001F780-\U0001F7FF"  # Geometric Shapes Extended
        "\U0001F800-\U0001F8FF"  # Supplemental Arrows-C
        "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
        "\U0001FA00-\U0001FA6F"  # Chess Symbols
        "\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
        "\U00002702-\U000027B0"  # Dingbats
        "\U000024C2-\U0001F251"
        "]+", flags=re.UNICODE
    )
    
    return emoji_pattern.sub(r'', text)


def safe_folder_name(folder_name):
    # Remove special characters from the folder name
    return folder_name.replace(" ", "_").replace(":", "").lower()


def create_plot(
    df,
    plot_type,
    x,
    y,
    title,
    filename,
    figsize=(10, 6),
    save_dir="output",
    label_length=60,
    axis_font_size=15,
    title_font_size=20,
    legend_font_size=15
):
    print(f"Creating {plot_type}: {save_dir}/{filename}")

    # Sort the DataFrame by the 'y' column in descending order
    df_sorted = df.sort_values(by=y, ascending=False)

    # Apply the function to truncate labels and remove emojis
    truncated_labels = df_sorted[x].apply(
        lambda label: label[:(label_length - 3)]
        if len(label) > label_length 
        else label
    )

    plt.figure(figsize=figsize)

    if plot_type == 'boxplot':
        ax = sns.boxplot(x=df_sorted[y], y=truncated_labels, data=df_sorted)
    elif plot_type == 'barplot':
        ax = sns.barplot(x=df_sorted[y], y=truncated_labels, data=df_sorted)
    else:
        sys.exit(f"Invalid plot type: {plot_type}. Exiting.")

    overall_avg = df[y].mean()
    std_dev = df[y].std()

    # Add lines for the average and standard deviations
    ax.axvline(overall_avg, color="#ff6961", linestyle="--", label="Average")
    ax.axvline(overall_avg + std_dev, color="#03C6FC", linestyle="--", label="+1 Std Dev")
    ax.axvline(max(overall_avg - std_dev, 0), color="#03C6FC", linestyle="--", label="-1 Std Dev")

    ax.annotate(
        f"Average: {overall_avg:.2f}",
        xy=(overall_avg, 0),
        xytext=(overall_avg, -0.5),
        arrowprops=dict(facecolor="black", shrink=0.05),
        fontsize=axis_font_size,
    )

    ax.annotate(
        f"+1 Std Dev: {overall_avg + std_dev:.2f}",
        xy=(overall_avg + std_dev, 0),
        xytext=(overall_avg + std_dev, -0.5),
        arrowprops=dict(facecolor="black", shrink=0.05),
        fontsize=axis_font_size,
    )

    ax.annotate(
        f"-1 Std Dev: {max(overall_avg - std_dev, 0):.2f}",
        xy=(max(overall_avg - std_dev, 0), 0),
        xytext=(max(overall_avg - std_dev, 0), -0.5),
        arrowprops=dict(facecolor="black", shrink=0.05),
        fontsize=axis_font_size,
    )

    plt.title(title, fontsize=title_font_size)
    plt.xlabel(y, fontsize=axis_font_size)
    plt.ylabel(x, fontsize=axis_font_size)
    plt.legend(fontsize=legend_font_size)

    # Check if the directory exists, create it if it doesn't
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    filepath = os.path.join(save_dir, filename)

    try:
        plt.savefig(filepath, bbox_inches="tight")
    except RuntimeWarning as e:
        print(f"An error occurred while saving the file: {e}")
    finally:
        plt.close()

    print(f"Saved {plot_type} to {filepath}")


def export_to_csv_with_ordered_headers(data, file_path):
    preferred_order = [
        "account_id",
        "campaign_id",
        "breakdown_id",
        "account_name",
        "campaign_name",
        "breakdown",
        "click_through_rate",
        "cost_per_click",
        "cost_per_lead",
        "cost_per_purchase",
        "spend",
        "impressions",
        "clicks",
        "lead",
        "purchase",
        "post_reaction",
        "post_engagement",
        "video_view",
    ]

    preferred_order = [
    "account_id",
    "campaign_id",
    "ad_id",
    "breakdown_id",
    "account_name",
    "campaign_name",
    "ad_name",
    "breakdown",
    "click_through_rate",
    "avg_campaign_ctr",
    'ctr_greater_than_avg',  
    "cost_per_click",
    "avg_campaign_cpc",
    'cpc_greater_than_avg', 
    "cost_per_lead",
    "avg_campaign_cpl",
    'cpl_greater_than_avg',
    "cost_per_purchase",
    "avg_campaign_cpp",
    'cpp_greater_than_avg',
    "spend",
    "impressions",
    "clicks",
    "lead",
    "purchase",
    "post_reaction",
    "post_engagement",
    "video_view",
]

    # Extract dynamic headers from DataFrame, excluding those already in preferred_order
    dynamic_headers = sorted(set(data.columns) - set(preferred_order))

    # Combine preferred_order headers with dynamically determined and sorted headers
    ordered_headers = preferred_order + dynamic_headers

    # Reorder DataFrame columns
    ordered_data = data.reindex(columns=ordered_headers)

    # Export the DataFrame to CSV
    ordered_data.to_csv(file_path, index=False)

# Example usage
# Assume 'df' is your DataFrame loaded with data
# export_to_csv_with_ordered_headers(df, 'path_to_your_file.csv')


main()
