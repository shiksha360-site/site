from sdk.fetcher.yt import Youtube
from ._parse import get_subject, print_kwmap, create_kwlist

def ln_scrape(yt: Youtube, channel_info: dict, chapter_info: dict, subtopic: str, global_cache: object):
    """LearnNext Scraper"""
    channel_id = channel_info["channel-id"]
    subject, alt_subject, gr6b = get_subject(chapter_info)
    if not gr6b:
        # LearnNext does not categorize grade 6 and below
        args = {alt_subject or subject: 3}
        max_results = 5
    else:
        args = {}
        max_results = 1
    playlists = yt.get_all_playlists(channel_id)
    kwmap, titles = playlists.get_title_with_kw(
        keywords={
            "class": 4,
            str(chapter_info["grade"]): 3,
            **args
        },
        max_results=max_results,
        silent=True
    )

    print_kwmap(kwmap)

    keywords, reject = create_kwlist(chapter_info, subtopic)


    for playlist_item in playlists.get_items(title_list=titles):
        kwmap, titles = playlist_item.get_title_with_kw(
            keywords=keywords,
            reject_keywords=reject,
            cache=global_cache,
            silent=True
        )

        print_kwmap(kwmap)

        for video in playlist_item.get_videos(title_list=titles):
            for video_item in video.loop():
                view_count = int(video_item["statistics"]["viewCount"])
                print(video.item_min(video_item))