from typing import Callable, Dict, List, Optional
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
from sdk import common
from pathlib import Path
import time
import orjson
import pickle
import copy

class YoutubeData():
    def __init__(self, data, data_type):
        self.data = copy.deepcopy(data)
        self.internal_data = self.data[-1]
        self.data_type = data_type
        del self.data[-1]
    
    def loop(self):
        for page in self.data:
            for item in page["items"]:
                yield item
    
    def get_playlists_with_title(self, keywords: Dict[str, int], max_results: int = 5):
        """Helper method to get all playlists matching a set of keywords where keywords is a map of the keyword to its weightage"""
        if self.data_type != "channelplaylists":
            raise NotImplementedError("Not a playlist items response")
        keyword_map = {} # Store how many keyword maps
        for item in self.loop():
            title = item["snippet"]["title"]

            print(item)

            item_min = {
                "embed": item["player"]["embedHtml"],
                "id": item["id"],
                "description": item["snippet"]["description"],
                "weight": 0
            }

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

            print(title)
        
        if keyword_map:
            keyword_map = sorted(keyword_map.items(), key=lambda x: x[1]["weight"], reverse=True)
        else:
            keyword_map = []
        return keyword_map[:max_results]

class Youtube():
    scopes = ["https://www.googleapis.com/auth/youtube.readonly"]
    api_service_name = "youtube"
    api_version = "v3"
    client_secrets_file = "secrets/ytsecret.json"

    # From google api explorer
    def __init__(self):
        # Get credentials and create an API client
        credentials = self.get_credentials()
        self.yt = googleapiclient.discovery.build(
            self.api_service_name, self.api_version, credentials=credentials)
        
        # A cache for our use
        self.etag_cache: Dict[str, dict] = {} # Caches our operation id to an etag
        self.cache: Dict[str, dict] = {} # Cache an etag to a cache data

    def get_credentials(self):
        """Either get Credentials object using pickle or do oauth manually and store credentials"""
        creds = Path("tmpstor/creds_oauth.pickle")
        if creds.exists():
            with creds.open('rb') as f:
                return pickle.load(f)
        else:
            flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
                self.client_secrets_file, self.scopes)
            credentials = flow.run_console()
            with creds.open('wb') as f:
                pickle.dump(credentials, f)
            return credentials

    def _fcache_req(self, t: str, id: str) -> Optional[List[dict]]:
        """Attempt to fetch request from cache"""
        Path(f"tmpstor").mkdir(exist_ok=True)
        f = f"tmpstor/cache-{t}-{id}"
        fpath = Path(f"{f}.min.json")        
        if self.etag_cache.get(f):
            cache_data = self.cache[self.etag_cache[f]]
        
        elif fpath.exists():
            with fpath.open() as fp:
                cache_data = orjson.loads(fp.read())
        
        else:
            return None

        if time.time() - float(cache_data[-1]["time"]) > 60*60*3:
            return None
        
        self._cache_etag(f, cache_data[0]["etag"], cache_data)

        return cache_data
    
    def _wcache_req(self, t: str, id: str, data: List[dict]):
        data.append({"time": str(time.time()), "internal": True})
        Path(f"tmpstor").mkdir(exist_ok=True)
        f = f"tmpstor/cache-{t}-{id}"
        fpath = Path(f"{f}.min.json")  
        with fpath.open("w") as fp:
            common.write_min_json(data, fp)
        self._cache_etag(f, data[0]["etag"], data)

    def _cache_etag(self, id: str, etag: str, data: dict):
        self.cache[etag] = data
        self.etag_cache[id] = etag
    
    def _paginate(self, request: Callable, curr_data: dict, data: List[dict] = None):
        if not data:
            data = [curr_data]
        if curr_data.get("nextPageToken"):
            page_token = curr_data["nextPageToken"]
            next_req = googleapiclient.http.HttpRequest(
                request.http, request.postproc, f"{request.uri}&pageToken={page_token}", body=request.body, headers=request.headers, methodId=request.methodId
            )
            next_data = next_req.execute()
            data.append(next_data)
            return self._paginate(next_req, next_data, data)
        else:
            return data

    def request(self, request: Callable, cache_type: str, cache_id: str) -> List[Dict]:
        data = self._fcache_req(cache_type, cache_id)
        if not data:
            api_data = self._paginate(request, request.execute())
            self._wcache_req(cache_type, cache_id, api_data)
            return YoutubeData(api_data, cache_type)

        print("Using already cached response")
        return YoutubeData(data, cache_type)

    def get_channel(self, channel_id: str):
        """https://developers.google.com/youtube/v3/docs/channels#resource"""
        request = self.yt.channels().list(
            part="snippet,contentDetails,statistics,localizations,contentOwnerDetails,statistics",
            maxResults=50,
            id=channel_id
        )

        return self.request(request, "channel", channel_id)

    def list_playlist(self, channel_id: str):
        """https://developers.google.com/youtube/v3/docs/playlists/list"""
        request = self.yt.playlists().list(
            part="snippet,contentDetails,localizations,id,player",
            maxResults=50,
            channelId=channel_id
        )

        return self.request(request, "channelplaylists", channel_id)

    def get_channel_id_list():
        return common.load_yaml("data/core/yt_channels.yaml")
    
    def item_loop(self, data: List[dict]):
        for page in data:
            if "internal" in page:
                page["items"] = []

            for item in page["items"]:
                yield item