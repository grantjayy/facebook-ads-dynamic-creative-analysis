import sys
import os
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import re
from datetime import datetime
from dotenv import load_dotenv

from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.adsinsights import AdsInsights

load_dotenv()

# Don't change these
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

    current_time = datetime.now()
    formatted_time = current_time.strftime("%Y-%m-%dT%H-%M-%S")

    time_period = ''

    if since and until:
        time_period = f"{since} to {until}"
    else:
        time_period = date_preset

    for breakdown in breakdowns:
        ads = get_ads(breakdown, since=since, until=until, date_preset=date_preset)

        df = pd.DataFrame.from_dict(ads)

        if df.empty:
            print(f"No ads found for breakdown: {breakdown}. Skipping...")
            continue

        df["click_through_rate"] = (df["clicks"] / df["impressions"]) * 100
        df["cost_per_click"] = df["spend"] / df["clicks"]
        df["cost_per_lead"] = df["spend"] / df["lead"]
        df["cost_per_purchase"] = df["spend"] / df["purchase"]
        df["lead_conversion_rate"] = (df["lead"] / df["clicks"]) * 100

        print(f"Creating plots for breakdown: {breakdown}")

        dir = f"output/{formatted_time}__{safe_folder_name(time_period)}"

        create_plot(
                df,
                "barplot",
                "breakdown",
                "click_through_rate",
                f"Total Click Through Rate by {breakdown}",
                f"{dir}/totals/{breakdown}_total_ctr.png",
        )

        create_plot(
                df,
                "barplot",
                "breakdown",
                "cost_per_lead",
                f"Total Cost per Lead by {breakdown}",
                f"{dir}/totals/{breakdown}_total_cpl.png",
        )

        create_plot(
                df,
                "barplot",
                "breakdown",
                "lead_conversion_rate",
                f"Total Lead Conversion Rate by {breakdown}",
                f"{dir}/totals/{breakdown}_total_lcvr.png",
        )


        plt.figure(figsize=(12, 5)) 

        # CTR vs. Conversion Rate plot
        plt.subplot(1, 2, 1)
        sns.regplot(x='lead_conversion_rate', y='click_through_rate', data=df, ci=None, scatter_kws={'alpha':0.5})
        plt.title('CTR vs. Lead Conversion Rate')
        plt.xlabel('Click Through Rate (%)')
        plt.ylabel('Lead Conversion Rate (%)')

        # Conversion Rate vs. Cost Per Lead plot
        plt.subplot(1, 2, 2)
        sns.regplot(x='cost_per_lead', y='lead_conversion_rate', data=df, ci=None, scatter_kws={'alpha':0.5})
        plt.title('Conversion Rate vs. Cost Per Lead')
        plt.xlabel('Lead Conversion Rate (%)')
        plt.ylabel('Cost Per Lead ($)')
        
        plt.savefig(f"{dir}/totals/{breakdown}_scatter.png", bbox_inches="tight")

        # Loop through each campaign and create a plot for each
        for c in df["campaign_name"].unique():
            campaign_df = df[df["campaign_name"] == c]

            create_plot(
                campaign_df,
                "barplot",
                "breakdown",
                "click_through_rate",
                f"Click Through Rate by {breakdown} for {c}",
                f"{dir}/campaigns/{safe_folder_name(c)}/{breakdown}_ctr.png",
            )

            create_plot(
                campaign_df,
                "barplot",
                "breakdown",
                "cost_per_lead",
                f"Cost per Lead by {breakdown} for {c}",
                f"{dir}/campaigns/{safe_folder_name(c)}/{breakdown}_cpl.png",
            )

            create_plot(
                campaign_df,
                "barplot",
                "breakdown",
                "lead_conversion_rate",
                f"Lead conversion rate by {breakdown} for {c}",
                f"{dir}/campaigns/{safe_folder_name(c)}/{breakdown}_lcvr.png",
            )

        print(f"Exporting data to CSV for breakdown: {breakdown}")
        export_to_csv(df, f"{dir}/csv/{breakdown}.csv")

def get_ads(breakdown, date_preset=None, since=None, until=None):
    print(f"Getting ads for breakdown: {breakdown}")

    my_app_id = os.getenv('MY_APP_ID')
    my_app_secret = os.getenv('MY_APP_SECRET')
    my_access_token = os.getenv('MY_ACCESS_TOKEN')
    ad_account_id = os.getenv('AD_ACCOUNT_ID')

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

    print(f"Retrieved {len(ads)} ads for breakdown: {breakdown}")

    # Mapping of breakdown types to their key and id in the asset
    breakdown_mapping = {
        "body_asset": ('text', 'id'),
        "call_to_action_asset": ('name', 'id'),
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
            "campaign_id": remove_emojis(ad.get("campaign_id")),
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
        ad["breakdown"] = remove_emojis(asset.get(key_field, "")).replace('\n', ' ')
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
    folder_name = folder_name.replace(' ', '_')  # Replace spaces with underscores
    safe_name = re.sub(r'[^\w\-_]', '', folder_name)  # Keep only alphanumerics, underscores, and hyphens
    return safe_name


def create_plot(
    df,
    plot_type,
    x,
    y,
    title,
    filename,
    figsize=(30, 30),
    label_length=120,
    axis_font_size=15,
    title_font_size=20,
    legend_font_size=15
):
    # Sort the DataFrame by the 'y' column in descending order
    df_sorted = df.sort_values(by=y, ascending=False)

    # Apply the function to truncate labels and remove emojis
    truncated_labels = df_sorted[x].apply(
        lambda label: label[:(label_length - 3)] + '...'
        if len(label) > label_length 
        else label
    )

    plt.figure(figsize=figsize)

    if plot_type == 'boxplot':
        ax = sns.boxplot(x=df_sorted[y], y=truncated_labels, data=df_sorted)
        # Extract the median values for each category
        medians = df_sorted.groupby(truncated_labels)[y].median().reindex(truncated_labels)
        # Use the values to annotate the median in the plot
        for tick, label in enumerate(ax.get_yticklabels()):
            ax.text(
                medians[label.get_text()],  # x-position (median value)
                tick,  # y-position (index of the box)
                f'{medians[label.get_text()]:.2f}',  # label text
                verticalalignment='center',  # Center alignment vertically
                horizontalalignment='right',  # Align right of the median line
                size=axis_font_size,  # Font size
                color='black',  # Text color
                weight='semibold'  # Text weight
            )
    elif plot_type == 'barplot':
        ax = sns.barplot(x=df_sorted[y], y=truncated_labels, data=df_sorted)
        for p in ax.patches:
                ax.annotate(
                    format(p.get_width(), '.2f'),  # Format the label
                    (p.get_x() + p.get_width(), p.get_y() + ((p.get_height() / 2)) + .2),  # Position at the end of the bar
                    ha='left',  # Align horizontally to left
                    va='center',  # Align vertically to center
                    xytext=(5, 0),  # Offset text by 5 points to the right
                    textcoords='offset points',  # Interpret xytext as offset in points
                    fontsize=axis_font_size,  # Font size
                )
    else:
        sys.exit(f"Invalid plot type: {plot_type}. Exiting.")

    overall_avg = df[y].mean()
    std_dev = df[y].std()

    # Add lines for the average and standard deviations
    ax.axvline(overall_avg, color="#ff6961", linestyle="--", label="Average")
    ax.axvline(overall_avg + std_dev, color="#03C6FC", linestyle="--", label="+1 Std Dev")
    ax.axvline(max(overall_avg - std_dev, 0), color="#03C6FC", linestyle="--", label="-1 Std Dev")

    # Add annotations for the average and standard deviations
    ax.annotate(
        f"Average: {overall_avg:.2f}",
        xy=(overall_avg + .17, .1),
        xytext=(overall_avg, -0.5),
        textcoords="offset points",
        ha="center",
        va="center",
        fontsize=axis_font_size,
        color="#ff6961",
    )

    ax.annotate(
        f"+1 Std Dev: {overall_avg + std_dev:.2f}",
        xy=(overall_avg + std_dev + .17, .1),
        xytext=(overall_avg + std_dev, -0.5),
        textcoords="offset points",
        ha="center",
        va="center",
        fontsize=axis_font_size,
        color="#03C6FC",
    )

    ax.annotate(
        f"-1 Std Dev: {max(overall_avg - std_dev, 0):.2f}",
        xy=(max(overall_avg - std_dev + .17, 0), .1),
        xytext=(max(overall_avg - std_dev, 0), -0.5),
        textcoords="offset points",
        ha="center",
        va="center",
        fontsize=axis_font_size,
        color="#03C6FC",
    )
   
    plt.title(title, fontsize=title_font_size)
    plt.xlabel(y, fontsize=axis_font_size)
    plt.ylabel(x, fontsize=axis_font_size)
    plt.legend(fontsize=legend_font_size)

    # Get the name of the file to save
    folder = "/".join(filename.split("/")[:-1])

    # Check if the directory exists, create it if it doesn't
    if not os.path.exists(folder):
        os.makedirs(folder)

    plt.savefig(filename, bbox_inches="tight")
    plt.close()


def export_to_csv(data, file_path):
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

    # Extract dynamic headers from DataFrame, excluding those already in preferred_order
    dynamic_headers = sorted(set(data.columns) - set(preferred_order))

    # Combine preferred_order headers with dynamically determined and sorted headers
    ordered_headers = preferred_order + dynamic_headers

    # Reorder DataFrame columns
    ordered_data = data.reindex(columns=ordered_headers)

    # Check if the directory exists, create it if it doesn't 
    folder = "/".join(file_path.split("/")[:-1])
    if not os.path.exists(folder):
        os.makedirs(folder)

    # Export the DataFrame to CSV
    ordered_data.to_csv(file_path, index=False)


main()
