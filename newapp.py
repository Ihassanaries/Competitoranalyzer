import streamlit as st
import requests
import pandas as pd

# =========================================================
# EMBEDDED API KEY - RISKY IF CODE IS PUBLIC
# =========================================================
API_KEY = "AIzaSyBrWecWtZjfdzTQCStr5Hw8iDUu_HrS13c"

# Your provided keywords:
KEYWORDS_LIST = [
    "HFY", "Humanity F Yeah", "HFY Humanity F*** Yeah", "hfy sci fi stories", "hfy stories",
    "hfy battle", "hfy scifi", "sci fi hfy", "hfy reddit stories", "hfy war stories",
    "sci fi hfy stories", "best hfy stories", "hfy revelation", "scifi hfy stories",
    "hfy battel", "hfy galactic stories", "hfy human", "hfy deathworlder", "hfy human pet",
    "best hfy story", "hfy war", "hfy human pets"
]

# =========================================================
# UTILITY FUNCTIONS
# =========================================================

def search_channels_by_keywords(keyword, max_results=15):
    """
    Search for YouTube channels related to a single keyword.
    Return a list of channel IDs and channel titles.
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
    Get stats (subscriberCount, viewCount, etc.) for a channel ID.
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
    Fetch stats (views, likes, comments) for each video in the list.
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
    return pd.DataFrame(results)

def find_common_patterns(df):
    """
    Look for average metrics and the most common words in video titles.
    """
    patterns = {}
    if not df.empty:
        avg_views = df["View Count"].mean()
        avg_likes = df["Like Count"].mean()
        avg_comments = df["Comment Count"].mean()

        # Simple frequency analysis of words in the video titles
        titles = df["Title"].str.lower().str.cat(sep=' ')
        words = titles.split()
        freq = {}
        for w in words:
            freq[w] = freq.get(w, 0) + 1
        sorted_words = sorted(freq.items(), key=lambda x: x[1], reverse=True)

        patterns = {
            "avg_views": round(avg_views, 2),
            "avg_likes": round(avg_likes, 2),
            "avg_comments": round(avg_comments, 2),
            "common_title_words": sorted_words[:10]
        }
    return patterns

# =========================================================
# STREAMLIT APP
# =========================================================
def main():
    st.title("HFY Niche YouTube Analyzer")
    st.write("""
    This app will:
    1. Take a predefined list of **HFY**-related keywords.
    2. Search YouTube for channels matching each keyword.
    3. Collect all channels and pick the **Top 5** by subscriber count.
    4. Analyze each top channel's recent videos.
    """)

    st.write("**List of HFY Keywords**:")
    st.write(", ".join(KEYWORDS_LIST))

    max_channels_per_keyword = st.slider("Channels to fetch per keyword:", 5, 50, 15)
    max_videos_per_channel = st.slider("Videos to analyze per channel:", 5, 20, 5)
    
    if st.button("Find & Analyze Top Channels"):
        st.write("## Step 1: Search for channels across all keywords")
        all_channels = {}  # We'll use a dict to avoid duplicates: {channel_id: {title, subscriberCount, etc.}}

        # 1. Search channels for each keyword
        for kw in KEYWORDS_LIST:
            st.write(f"Searching channels for keyword: **{kw}**")
            found = search_channels_by_keywords(kw, max_results=max_channels_per_keyword)
            for ch in found:
                ch_id = ch["channel_id"]
                ch_title = ch["channel_title"]
                if ch_id not in all_channels:
                    # Initialize with minimal info
                    all_channels[ch_id] = {
                        "channel_title": ch_title,
                        "subscriberCount": 0,   # We'll fill this later
                        "viewCount": 0,
                        "videoCount": 0
                    }

        if not all_channels:
            st.error("No channels found for these keywords!")
            return

        st.write(f"Found **{len(all_channels)}** unique channels in total.")
        
        # 2. Fetch stats for each unique channel
        st.write("## Step 2: Fetch stats for each channel")
        for ch_id, ch_data in all_channels.items():
            stats = get_channel_stats(ch_id)
            ch_data["subscriberCount"] = int(stats.get("subscriberCount", 0))
            ch_data["viewCount"] = int(stats.get("viewCount", 0))
            ch_data["videoCount"] = int(stats.get("videoCount", 0))

        # 3. Rank channels by subscriberCount
        st.write("## Step 3: Select Top 5 Channels by Subscriber Count")
        sorted_channels = sorted(
            all_channels.items(),
            key=lambda x: x[1]["subscriberCount"],
            reverse=True
        )
        top_5 = sorted_channels[:5]

        st.subheader("Top 5 Channels")
        for idx, (ch_id, ch_info) in enumerate(top_5, start=1):
            st.write(f"**#{idx}:** [{ch_info['channel_title']}](https://www.youtube.com/channel/{ch_id})")
            st.write(f"- Subscribers: {ch_info['subscriberCount']:,}")
            st.write(f"- Total Views: {ch_info['viewCount']:,}")
            st.write(f"- Total Videos: {ch_info['videoCount']:,}")
            st.write("---")

        # 4. Analyze each of the Top 5
        st.write("## Step 4: Analyze Recent Videos of Top 5 Channels")
        for idx, (ch_id, ch_info) in enumerate(top_5, start=1):
            st.markdown(f"### Channel #{idx}: {ch_info['channel_title']}")
            # Fetch videos
            videos = get_channel_videos(ch_id, max_results=max_videos_per_channel)
            if not videos:
                st.write("No recent videos found or unable to fetch.")
                continue

            # Build stats DataFrame
            df_videos = analyze_videos(videos)
            if df_videos.empty:
                st.write("No stats available for these videos.")
                continue

            st.dataframe(df_videos)

            # Find patterns
            patterns = find_common_patterns(df_videos)
            st.write("**Patterns & Insights**")
            st.write(f"- **Average Views**: {patterns.get('avg_views', 0)}")
            st.write(f"- **Average Likes**: {patterns.get('avg_likes', 0)}")
            st.write(f"- **Average Comments**: {patterns.get('avg_comments', 0)}")
            st.write(f"- **Common Title Words**: {patterns.get('common_title_words', [])}")
            st.write("---")

        st.success("Analysis complete! Review the data above to uncover HFY channel strategies.")
        
if __name__ == "__main__":
    main()
