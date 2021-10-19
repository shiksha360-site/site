from sdk.fetcher.yt import Youtube
from ._parse import get_subject

def ln_scrape(yt: Youtube, channel_info: dict, chapter_info: dict, subtopic: str):
    """LearnNext Scraper"""
    channel_id = channel_info["channel-id"]
    subject, alt_subject = get_subject(chapter_info)
    playlists = yt.get_all_playlists(channel_id)
    kwmap, titles = playlists.get_title_with_kw(
        keywords={
            "class": 4,
            chapter_info["grade"]: 3,
            alt_subject or subject: 3
        }
    )
    print(titles)