import requests
import streamlit as st

API_KEY = "AIzaSyBrWecWtZjfdzTQCStr5Hw8iDUu_HrS13c"

def test_youtube_search(keyword):
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "q": keyword,
        "type": "video",
        "maxResults": 50,
        "safeSearch": "none",  # or you can omit
        "key": API_KEY
    }
    resp = requests.get(url, params=params)
    data = resp.json()
    return data

def main():
    keyword = st.text_input("Enter test keyword", "HFY")
    if st.button("Search YouTube"):
        data = test_youtube_search(keyword)
        st.write(data)  # See exactly what's returned

if __name__ == "__main__":
    main()
