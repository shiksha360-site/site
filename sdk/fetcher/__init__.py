from sdk.fetcher.yt import Youtube
from sdk import common
from .scrapers import ln_scrape

scrapers = {
    "lnscrape": ln_scrape
}

def get_channel_list():
    return common.load_yaml("data/core/yt_channels.yaml")

def scrape(chapter_info: dict):
    yt = Youtube()
    channel_list = get_channel_list()
    scraped_data = {}
    for name, channel_info in channel_list.items():
        scraped_data[name] = scrapers[channel_info["scraper"]](yt, channel_info, chapter_info)
    return scraped_data