import streamlit as st
import requests
import pandas as pd
import nltk
import altair as alt
from nltk import ngrams

nltk.download('punkt', quiet=True)  # Ensure tokenizers are available

# =========================================================
# EMBEDDED API KEY - For demonstration only!
# =========================================================
API_KEY = "AIzaSyBrWecWtZjfdzTQCStr5Hw8iDUu_HrS13c"

# =========================================================
# SAMPLE KEYWORDS
# =========================================================
KEYWORDS_LIST = [
    "HFY", "Humanity F Yeah", "HFY Humanity F*** Yeah", "hfy sci fi stories", "hfy stories",
    "hfy battle", "hfy scifi", "sci fi hfy", "hfy reddit stories", "hfy war stories",
    "sci fi hfy stories", "best hfy stories", "hfy revelation", "scifi hfy stories",
    "hfy battel", "hfy galactic stories", "hfy human", "hfy deathworlder", "hfy human pet",
    "best hfy story", "hfy war", "hfy human pets"
]

# =========================================================
# FUNCTIONS TO FETCH VIDEO & CHANNEL DATA
# =========================================================

def search_videos_for_keyword(keyword, max_results=15):
    """
    Search YouTube for videos matching the given keyword.
    Return a list of dictionaries: {video_id, channel_id, channel_title, video_title, published_at}
    """
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "q": keyword,
        "type": "video",          # <-- We search for videos, not channels
        "maxResults": max_results,
        "key": API_KEY
    }
    response = requests.get(url, params=params)
    data = response.json()

    video_info = []
    if "items" in data:
        for item in data["items"]:
            snippet = item["snippet"]
            video_id = item["id"]["videoId"]
            channel_id = snippet["channelId"]
            channel_title = snippet["channelTitle"]
            video_title = snippet["title"]
            published_at = snippet["publishedAt"]
            video_info.append({
                "video_id": video_id,
                "channel_id": channel_id,
                "channel_title": channel_title,
                "video_title": video_title,
                "published_at": published_at
            })
    return video_info

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
    Get recent videos for a channel by channel_id.
    """
    url = f"https://www.googleapis.com/youtube/v3/search?part=snippet,id&channelId={channel_id}&order=date&maxResults={max_results}&key={API_KEY}"
    response = requests.get(url)
    data = response.json()

    video_data = []
    if "items" in data:
        for item in data["items"]:
            kind = item["id"]["kind"]
            if kind == "youtube#video":
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
    For each video in video_list, fetch its stats (views, likes, comments) using the Videos API.
    Return a DataFrame with relevant columns.
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
    text = " ".join(titles).lower()
    tokens = nltk.word_tokenize(text)
    bigrams_list = list(ngrams(tokens, 2))

    freq_dict = {}
    for bg in bigrams_list:
        freq_dict[bg] = freq_dict.get(bg, 0) + 1

    sorted_bigrams = sorted(freq_dict.items(), key=lambda x: x[1], reverse=True)
    return sorted_bigrams[:top_n]

def find_deeper_patterns(df):
    if df.empty:
        return {}, df

    avg_views = df["View Count"].mean()
    df["Is Viral?"] = df["View Count"] > (1.5 * avg_views)  # > 150% of average

    df["Like/View Ratio"] = df.apply(
        lambda row: row["Like Count"] / row["View Count"] if row["View Count"] != 0 else 0,
        axis=1
    )
    df["Comment/View Ratio"] = df.apply(
        lambda row: row["Comment Count"] / row["View Count"] if row["View Count"] != 0 else 0,
        axis=1
    )

    sorted_bigrams = get_top_bigrams(df["Title"], top_n=5)
    patterns = {
        "average_views": round(avg_views, 2),
        "average_likes": round(df["Like Count"].mean(), 2),
        "average_comments": round(df["Comment Count"].mean(), 2),
        "viral_threshold": round(1.5 * avg_views, 2),
        "top_5_bigrams": [(f"{w1} {w2}", freq) for ((w1, w2), freq) in sorted_bigrams]
    }

    return patterns, df

def make_bar_chart(df, x_col, y_col, title="Bar Chart"):
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
    st.title("Topic-Based Channel Finder & Deep Analysis")
    st.markdown("""
    **How this works**:
    1. We take a list of keywords describing the HFY niche.
    2. For each keyword, we **search for videos** (not channels!) that match that topic.
    3. We collect the channels from those videos.
    4. Rank all those channels by subscriber count.
    5. Analyze the **top 5** channels in-depth (recent uploads, viral detection, bigrams, etc.).
    """)

    # Let the user adjust these
    max_videos_search = st.slider("Max videos to fetch per keyword (for searching channels):", 5, 50, 15)
    max_videos_per_channel = st.slider("How many recent videos to analyze for each channel:", 5, 20, 5)

    st.write("**Keywords being used**:", ", ".join(KEYWORDS_LIST))
    
    if st.button("Run Analysis"):
        st.write("### Step 1: Search for videos for each keyword, gather channel IDs")
        channel_map = {}  # channel_id -> { 'channel_title': ..., 'subscriberCount': 0, ... }

        for kw in KEYWORDS_LIST:
            st.write(f"Searching videos for keyword: **{kw}**")
            video_results = search_videos_for_keyword(kw, max_results=max_videos_search)

            for vid in video_results:
                ch_id = vid["channel_id"]
                ch_title = vid["channel_title"]
                if ch_id not in channel_map:
                    channel_map[ch_id] = {
                        "channel_title": ch_title,
                        "subscriberCount": 0,
                        "viewCount": 0,
                        "videoCount": 0
                    }

        # If no channels found at all
        if not channel_map:
            st.error("No channels found from these videos/keywords. Try changing the keywords or increasing max results.")
            return

        st.write(f"**Total unique channels discovered:** {len(channel_map)}")

        st.write("### Step 2: Fetch channel stats (subscribers, total views, etc.)")
        for ch_id, data in channel_map.items():
            stats = get_channel_stats(ch_id)
            data["subscriberCount"] = int(stats.get("subscriberCount", 0))
            data["viewCount"] = int(stats.get("viewCount", 0))
            data["videoCount"] = int(stats.get("videoCount", 0))

        st.write("### Step 3: Pick Top 5 Channels by subscriberCount")
        channels_sorted = sorted(
            channel_map.items(), 
            key=lambda x: x[1]["subscriberCount"], 
            reverse=True
        )
        top_5 = channels_sorted[:5]

        for idx, (ch_id, info) in enumerate(top_5, start=1):
            st.markdown(f"**#{idx}** - [{info['channel_title']}](https://www.youtube.com/channel/{ch_id})")
            st.write(f"- **Subscribers**: {info['subscriberCount']:,}")
            st.write(f"- **Total Views**: {info['viewCount']:,}")
            st.write(f"- **Total Videos**: {info['videoCount']:,}")
            st.write("---")

        st.write("### Step 4: Deep Dive into Each of the Top 5 Channels")
        for idx, (ch_id, info) in enumerate(top_5, start=1):
            ch_title = info["channel_title"]
            st.subheader(f"Channel #{idx}: {ch_title}")

            # Get recent videos
            videos = get_channel_videos(ch_id, max_results=max_videos_per_channel)
            if not videos:
                st.write("No recent videos found or unable to fetch data.")
                continue

            # Analyze them (views, likes, comments)
            df_videos = analyze_videos(videos)
            if df_videos.empty:
                st.write("Could not fetch video stats for these uploads.")
                continue

            st.write("**Recent Videos Data**")
            st.dataframe(df_videos)

            # Deeper patterns
            patterns, df_videos = find_deeper_patterns(df_videos)

            # Summaries
            st.write("**Key Insights**:")
            st.write(f"- Average Views: {patterns.get('average_views', 0)}")
            st.write(f"- Average Likes: {patterns.get('average_likes', 0)}")
            st.write(f"- Average Comments: {patterns.get('average_comments', 0)}")
            st.write(f"- Viral Threshold (1.5× avg views): {patterns.get('viral_threshold', 0)}")

            viral_df = df_videos[df_videos["Is Viral?"]]
            if not viral_df.empty:
                st.write("**Viral Videos** (exceeding threshold):")
                st.table(viral_df[["Title", "View Count", "Like Count", "Comment Count"]])
            else:
                st.write("No videos exceeded the viral threshold in the latest uploads.")

            st.write("**Top 5 Bigrams in Titles**:")
            top_bigrams = patterns.get("top_5_bigrams", [])
            for bigram, freq in top_bigrams:
                st.write(f"- `{bigram}` appeared **{freq}** times")

            st.write("**Detailed Ratios** (Likes/Views, Comments/Views):")
            st.dataframe(df_videos[[
                "Title", "View Count", "Like Count", "Comment Count", 
                "Like/View Ratio", "Comment/View Ratio", "Is Viral?"
            ]])

            st.write("**View Count Bar Chart**")
            chart_data = df_videos[["Title", "View Count"]].copy()
            bar_chart = make_bar_chart(chart_data, "Title", "View Count", "Recent Videos: View Counts")
            st.altair_chart(bar_chart, use_container_width=True)

            st.write("---")

        st.success("Analysis complete! Check the data above to see which channels stand out and why.")

if __name__ == "__main__":
    main()
