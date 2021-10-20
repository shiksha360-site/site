from typing import Optional
from sdk.fetcher.yt import Youtube

class ScrapeCache():
    def __init__(self):
        self.cache = {}
        self.current = None
    
    def keys(self):
        return self.cache.keys()
    
    def set_current(self, current: str):
        if current not in self.keys():
            self.cache[current] = []
        self.current = current
    
    def get_cached(self) -> list:
        return self.cache[self.current]
    
    def add(self, title: str):
        self.cache[self.current].append(title)
    
    def clear(self):
        self.cache = {}
        self.current = None

# TODO
class ScrapeOutput():
    ...

class ScrapeData():
    def __init__(
        self, 
        yt: Youtube,
        chapter_info: dict,
        subtopic: str,
        scrape_cache: ScrapeCache,
        channel_info: Optional[dict] = None
    ):
        self.yt = yt
        self.channel_info = channel_info
        self.chapter_info = chapter_info
        self.subtopic = subtopic
        self.scrape_cache = scrape_cache

    # TODO
    def output(self):
        return ScrapeOutput()
