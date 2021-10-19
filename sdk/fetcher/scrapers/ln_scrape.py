from sdk.fetcher.yt import Youtube
from ._parse import get_subject

def ln_scrape(yt: Youtube, channel_info: dict, chapter_info: dict, subtopic: str):
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

    print([(title, k["weight"]) for title, k in [a for a in kwmap]])