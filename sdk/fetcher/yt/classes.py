from copy import deepcopy
from typing import Dict, List
import os

# For VSCode
if os.environ.get("IMPORT_YT_DONE"):
    from sdk.fetcher.yt import Youtube

class YoutubeData():
    def __init__(self, yt: "Youtube", data):
        self.data = deepcopy(data)
        self.internal_data = self.data[-1]
        del self.data[-1]
        self.yt = yt
        self.exit_loop = None
    
    def loop(self):
        for page in self.data:
            for item in page["items"]:
                yield item
    
    def get_item_title(self, item):
        """Should work in many cases. Gets the title of an item"""
        return item["snippet"]["title"]
    
    def item_min(self, item) -> dict:
        """Minifies a item"""
        return item

    def get_title_with_kw(self, keywords: Dict[str, int], max_results: int = 5):
        """Helper method to get all titles matching a set of keywords where keywords is a map of the keyword to its weightage"""
        keyword_map = {} # Store how many keyword maps
        titles = []
        for item in self.loop():
            title = self.get_item_title(item)

            item_min = self.item_min(item)
            item_min["weight"] = 0

            keyword_map[title] = item_min
            
            title_list = [s.lower() for s in title.split(" ")]
            for kw, weight in keywords.items():
                if kw.lower() in title_list:
                    keyword_map[title]["weight"] += weight
                elif kw.lower() in title.lower():
                    # Anywhere in title means 0.5 weightage
                    keyword_map[title]["weight"] += 0.5*weight
                
            if keyword_map[title]["weight"] == 0:
                del keyword_map[title]
            else:
                titles.append(title)

            print(title)
        
        if keyword_map:
            keyword_map = sorted(keyword_map.items(), key=lambda x: x[1]["weight"], reverse=True)
        else:
            keyword_map = []
        return keyword_map[:max_results], titles[:max_results]


class YoutubePlaylist(YoutubeData):
    def item_min(self, item) -> dict:
        return {
            "embed": item["player"]["embedHtml"],
            "id": item["id"],
            "description": item["snippet"]["description"],
            "weight": 0
        }

    def get_items(self, title_list: List[str] = None):
        """Get all playlist items in a generator"""
        for item in self.loop():
            if title_list and self.get_item_title(item) not in title_list:
                continue
            if self.exit_loop != "get_items":
                yield self.yt.get_playlist_item(item["id"])


class YoutubePlaylistItem(YoutubeData):
    ...