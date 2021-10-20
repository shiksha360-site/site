import os
from ._parse import get_subject, print_kwmap, create_kwlist

# For VSCode
if True is False:
    from sdk.fetcher import ScrapeData

def ln_scrape(data: "ScrapeData"):
    """LearnNext Scraper"""
    channel_id = data.channel_info["channel-id"]
    subject, alt_subject, gr6b = get_subject(data.chapter_info)
    if not gr6b:
        # LearnNext does not categorize grade 6 and below
        args = {alt_subject or subject: 3}
        max_results = 5
    else:
        args = {}
        max_results = 1
    playlists = data.yt.get_all_playlists(channel_id)
    kwmap, titles = playlists.get_title_with_kw(
        keywords={
            "class": 4,
            str(data.chapter_info["grade"]): 3,
            **args
        },
        max_results=max_results,
        silent=True
    )

    print_kwmap(kwmap)

    keywords, reject = create_kwlist(data.chapter_info, data.subtopic)

    for playlist_item in playlists.get_items(title_list=titles):
        kwmap, titles = playlist_item.get_title_with_kw(
            keywords=keywords,
            reject_keywords=reject,
            cache=data.scrape_cache,
            silent=True
        )

        print(f"Subtopic: {data.subtopic}")
        print_kwmap(kwmap)

        for video in playlist_item.get_videos(title_list=titles):
            for video_item in video.loop():
                view_count = int(video_item["statistics"]["viewCount"])
                #print(video.item_min(video_item))