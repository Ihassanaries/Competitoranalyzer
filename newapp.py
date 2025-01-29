import streamlit as st
import requests
import pandas as pd
import numpy as np
import nltk
import altair as alt
from nltk import ngrams
nltk.download('punkt')  # To ensure tokenization works if not already downloaded

# =========================================================
# EMBEDDED API KEY - In practice, use Streamlit secrets if public!
# =========================================================
API_KEY = "YOUR_API_KEY_HERE"

# =========================================================
# SAMPLE KEYWORDS (you can replace or extend as you wish)
# =========================================================
KEYWORDS_LIST = [
    "HFY", "Humanity F Yeah", "HFY Humanity F*** Yeah", "hfy sci fi stories", "hfy stories",
    "hfy battle", "hfy scifi", "sci fi hfy", "hfy reddit stories", "hfy war stories",
    "sci fi hfy stories", "best hfy stories", "hfy revelation", "scifi hfy stories",
    "hfy battel", "hfy galactic stories", "hfy human", "hfy deathworlder", "hfy human pet",
    "best hfy story", "hfy war", "hfy human pets"
]

# =========================================================
# FUNCTIONS TO FETCH CHANNEL & VIDEO DATA
# =========================================================

def search_channels_by_keywords(keyword, max_results=15):
    """
    Search YouTube for channels matching a single keyword.
    Return a list of {channel_id, channel_title}.
    """
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "q": keyword,
        "type": "channel",
        "maxResults": max_results,
        "key": API_KEY
    }
    response = requests.get(url, params=params)
    data = response.json()
    
    channels_found = []
    if "items" in data:
        for item in data["items"]:
            snippet = item.get("snippet", {})
            ch_id = snippet.get("channelId")
            ch_title = snippet.get("title", "No Title")
            if ch_id:
                channels_found.append({
                    "channel_id": ch_id,
                    "channel_title": ch_title
                })
    return channels_found

def get_channel_stats(channel_id):
    """
    Get stats (subscriberCount, viewCount, videoCount) for a channel ID.
    """
    url = f"https://www.googleapis.com/youtube/v3/channels?part=statistics&id={channel_id}&key={API_KEY}"
    response = requests.get(url)
    data = response.json()
    if "items" in data and len(data["items"]) > 0:
        stats = data["items"][0]["statistics"]
        return stats
    return {}

def get_channel_videos(channel_id, max_results=5):
    """
    Get recent videos for a channel.
    """
    url = f"https://www.googleapis.com/youtube/v3/search?part=snippet,id&channelId={channel_id}&order=date&maxResults={max_results}&key={API_KEY}"
    response = requests.get(url)
    data = response.json()
    
    video_data = []
    if "items" in data:
        for item in data["items"]:
            if item["id"]["kind"] == "youtube#video":
                vid_id = item["id"]["videoId"]
                snippet = item["snippet"]
                video_data.append({
                    "video_id": vid_id,
                    "title": snippet.get("title", ""),
                    "published_at": snippet.get("publishedAt", ""),
                    "description": snippet.get("description", "")
                })
    return video_data

def analyze_videos(video_list):
    """
    Fetch stats (views, likes, comments) for each video.
    Return a DataFrame with columns: Video ID, Title, Published At, View Count, Like Count, Comment Count, Description
    """
    results = []
    for vid in video_list:
        vid_id = vid["video_id"]
        stats_url = f"https://www.googleapis.com/youtube/v3/videos?part=statistics&id={vid_id}&key={API_KEY}"
        resp = requests.get(stats_url)
        data = resp.json()
        if "items" in data and len(data["items"]) > 0:
            details = data["items"][0]["statistics"]
            results.append({
                "Video ID": vid_id,
                "Title": vid["title"],
                "Published At": vid["published_at"],
                "View Count": int(details.get("viewCount", 0)),
                "Like Count": int(details.get("likeCount", 0)),
                "Comment Count": int(details.get("commentCount", 0)),
                "Description": vid["description"]
            })
    df = pd.DataFrame(results)
    return df

# =========================================================
# DEEPER ANALYSIS FUNCTIONS
# =========================================================

def get_top_bigrams(titles, top_n=5):
    """
    Given a list (or series) of video titles, extract the most common bigrams.
    Returns a list of (bigram, frequency) sorted by frequency descending.
    """
    # Combine all titles into one string (lowercase)
    text = " ".join(titles).lower()
    # Tokenize (simple split or nltk word_tokenize)
    tokens = nltk.word_tokenize(text)
    
    # Generate bigrams
    bigrams_list = list(ngrams(tokens, 2))
    
    # Count frequency
    freq_dict = {}
    for bg in bigrams_list:
        freq_dict[bg] = freq_dict.get(bg, 0) + 1
    
    # Sort by frequency
    sorted_bigrams = sorted(freq_dict.items(), key=lambda x: x[1], reverse=True)
    
    return sorted_bigrams[:top_n]

def find_deeper_patterns(df):
    """
    1. Identify "viral" videos (views > 1.5 x average)
    2. Calculate ratio metrics (like/view, comment/view)
    3. Get top bigrams in titles
    """
    if df.empty:
        return {}, pd.DataFrame()

    avg_views = df["View Count"].mean()
    
    # 1. Mark "viral" videos
    df["Is Viral?"] = df["View Count"] > (1.5 * avg_views)
    
    # 2. Ratio metrics
    df["Like/View Ratio"] = df.apply(lambda row: row["Like Count"] / row["View Count"] if row["View Count"] != 0 else 0, axis=1)
    df["Comment/View Ratio"] = df.apply(lambda row: row["Comment Count"] / row["View Count"] if row["View Count"] != 0 else 0, axis=1)
    
    # 3. Top Bigrams in titles
    sorted_bigrams = get_top_bigrams(df["Title"], top_n=5)
    
    # Summaries
    patterns = {
        "average_views": round(avg_views, 2),
        "average_likes": round(df["Like Count"].mean(), 2),
        "average_comments": round(df["Comment Count"].mean(), 2),
        "viral_threshold": round(1.5 * avg_views, 2),
        "top_5_bigrams": [(f"{a} {b}", freq) for (a, b), freq in sorted_bigrams],
    }
    
    return patterns, df

def make_bar_chart(df, x_col, y_col, title="Bar Chart"):
    """
    Create a simple Altair bar chart for the DataFrame.
    """
    chart = (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X(x_col, sort='-y'),
            y=y_col,
            tooltip=[x_col, y_col]
        )
        .properties(title=title)
    )
    return chart


# =========================================================
# STREAMLIT APP
# =========================================================
def main():
    st.title("Deep Dive HFY Niche YouTube Analyzer")
    st.write("""
    This app will:
    1. Use a list of **HFY**-related keywords.
    2. Search YouTube for channels that match those keywords.
    3. Gather all channels, pick the **Top 5** (by subscriber count).
    4. Fetch **recent videos** of each top channel.
    5. Perform **deeper analysis**:
       - Identify potential **"viral"** videos (views > 1.5× average).
       - Show **like/view** and **comment/view** ratios.
       - Find the **top bigrams** in video titles.
       - Display **charts** of engagement.
    """)

    st.write("**Keywords being searched:**")
    st.write(", ".join(KEYWORDS_LIST))

    max_channels_per_keyword = st.slider("Channels to fetch per keyword:", 5, 50, 15)
    max_videos_per_channel = st.slider("Videos to analyze per channel:", 5, 20, 5)

    if st.button("Find & Analyze Top Channels"):
        st.write("### Step 1: Search for channels across all keywords")
        all_channels = {}  # { channel_id: {channel_title, subCount, ... } }

        # 1. Search channels for each keyword
        for kw in KEYWORDS_LIST:
            st.write(f"- Searching for keyword: **{kw}**")
            found = search_channels_by_keywords(kw, max_results=max_channels_per_keyword)
            for ch in found:
                ch_id = ch["channel_id"]
                ch_title = ch["channel_title"]
                if ch_id not in all_channels:
                    all_channels[ch_id] = {
                        "channel_title": ch_title,
                        "subscriberCount": 0,
                        "viewCount": 0,
                        "videoCount": 0
                    }

        if not all_channels:
            st.error("No channels found for these keywords. Try adjusting or adding more keywords.")
            return

        st.write(f"**Total unique channels found:** {len(all_channels)}")

        # 2. Fetch stats for each channel
        st.write("### Step 2: Fetching channel stats (subscribers, total views, etc.)")
        for ch_id, ch_data in all_channels.items():
            stats = get_channel_stats(ch_id)
            ch_data["subscriberCount"] = int(stats.get("subscriberCount", 0))
            ch_data["viewCount"] = int(stats.get("viewCount", 0))
            ch_data["videoCount"] = int(stats.get("videoCount", 0))

        # 3. Pick top 5 channels by subscriberCount
        st.write("### Step 3: Selecting Top 5 Channels by Subscriber Count")
        sorted_channels = sorted(
            all_channels.items(),
            key=lambda x: x[1]["subscriberCount"],
            reverse=True
        )
        top_5 = sorted_channels[:5]

        # Display top 5
        for idx, (ch_id, info) in enumerate(top_5, start=1):
            st.write(f"**#{idx}:** [{info['channel_title']}](https://www.youtube.com/channel/{ch_id})")
            st.write(f"- Subscribers: {info['subscriberCount']:,}")
            st.write(f"- Total Views: {info['viewCount']:,}")
            st.write(f"- Total Videos: {info['videoCount']:,}")
            st.write("---")

        # 4. Analyze each of the Top 5
        st.write("### Step 4: Deep Analysis of Each Top Channel’s Recent Videos")

        for idx, (ch_id, ch_info) in enumerate(top_5, start=1):
            ch_title = ch_info["channel_title"]
            st.subheader(f"Channel #{idx}: {ch_title}")

            # Fetch recent videos
            videos = get_channel_videos(ch_id, max_results=max_videos_per_channel)
            if not videos:
                st.write("No recent videos found or unable to fetch data.")
                continue

            # Build DataFrame
            df_videos = analyze_videos(videos)
            if df_videos.empty:
                st.write("Could not fetch video statistics.")
                continue

            # 4A. Show raw data
            st.write("**Raw Video Data**:")
            st.dataframe(df_videos)

            # 4B. Deeper Patterns
            patterns, df_videos = find_deeper_patterns(df_videos)

            # Show summary stats
            st.write("**Pattern Highlights**:")
            st.write(f"- Average Views: {patterns.get('average_views', 0)}")
            st.write(f"- Average Likes: {patterns.get('average_likes', 0)}")
            st.write(f"- Average Comments: {patterns.get('average_comments', 0)}")
            st.write(f"- Viral Threshold (1.5× avg views): {patterns.get('viral_threshold', 0)}")

            # List viral videos if any
            viral_vids = df_videos[df_videos["Is Viral?"] == True]
            if not viral_vids.empty:
                st.write("**Viral Videos** (exceeding 1.5× average views):")
                st.table(viral_vids[["Title", "View Count", "Like Count", "Comment Count"]])
            else:
                st.write("No videos found above the viral threshold in the latest uploads.")

            # Show top 5 bigrams
            st.write("**Top 5 Bigrams in Video Titles**:")
            for bigram, freq in patterns.get("top_5_bigrams", []):
                st.write(f"- `{bigram}` appeared **{freq}** times")

            # 4C. Show ratio metrics & visuals
            st.write("**Detailed Video Statistics with Ratios**:")
            st.dataframe(df_videos[[
                "Title", "View Count", "Like Count", "Comment Count",
                "Like/View Ratio", "Comment/View Ratio", "Is Viral?"
            ]])

            # Create a bar chart of views per video
            st.write("**View Count Bar Chart**")
            if not df_videos.empty:
                chart_data = df_videos.copy()
                # Keep only columns we need for plotting
                chart_data = chart_data[["Title", "View Count"]]
                # Use Altair for a sorted bar chart
                bar_chart = make_bar_chart(
                    df=chart_data, 
                    x_col="Title", 
                    y_col="View Count", 
                    title="Recent Videos: View Counts"
                )
                st.altair_chart(bar_chart, use_container_width=True)

            st.write("---")

        st.success("Deep analysis completed! Review the data, patterns, and charts above to discover what works best.")

if __name__ == "__main__":
    main()
