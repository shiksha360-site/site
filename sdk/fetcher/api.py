from typing import Callable, Dict, List, Optional
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
from sdk import common
from pathlib import Path
import time
import orjson

class Youtube():
    scopes = ["https://www.googleapis.com/auth/youtube.readonly"]
    api_service_name = "youtube"
    api_version = "v3"
    client_secrets_file = "secrets/ytsecret.json"

    # From google api explorer
    def __init__(self):
        # Get credentials and create an API client
        flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
            self.client_secrets_file, self.scopes)
        credentials = flow.run_console()
        self.yt = googleapiclient.discovery.build(
            self.api_service_name, self.api_version, credentials=credentials)
        
        # A cache for our use
        self.etag_cache: Dict[str, dict] = {} # Caches our operation id to an etag
        self.cache: Dict[str, dict] = {} # Cache an etag to a cache data

    def _fcache_req(self, t: str, id: str) -> Optional[dict]:
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

        if time.time() - float(cache_data["time"]) > 60*60*3:
            return None
        
        self._cache_etag(f, cache_data["etag"], cache_data)

        return cache_data
    
    def _wcache_req(self, t: str, id: str, data: dict):
        data["time"] = str(time.time())
        Path(f"tmpstor").mkdir(exist_ok=True)
        f = f"tmpstor/cache-{t}-{id}"
        fpath = Path(f"{f}.min.json")  
        with fpath.open("w") as fp:
            common.write_min_json(data, fp)
        self._cache_etag(f, data["etag"], data)

    def _cache_etag(self, id: str, etag: str, data: dict):
        self.cache[etag] = data
        self.etag_cache[id] = etag
    
    def _paginate(self, request: Callable, curr_data: dict, data: dict = None, i: int = 1):
        if not data:
            data = curr_data
        if curr_data.get("nextPageToken"):
            page_token = curr_data["nextPageToken"]
            next_req = googleapiclient.http.HttpRequest(
                request.http, request.postproc, f"{request.uri}&pageToken={page_token}", body=request.body, headers=request.headers, methodId=request.methodId
            )
            next_data = next_req.execute()
            data[str(i)] = next_data
            return self._paginate(next_req, next_data, data, i+1)
        else:
            return data

    def request(self, request: Callable, cache_type: str, cache_id: str):
        data = self._fcache_req(cache_type, cache_id)
        if not data:
            api_data = self._paginate(request, request.execute())
            self._wcache_req(cache_type, cache_id, api_data)
            return api_data

        print("Using already cached response")
        return data

    def get_channel(self, channel_id: str):
        request = self.yt.channels().list(
            part="snippet,contentDetails,statistics,localizations,contentOwnerDetails,statistics",
            maxResults=50,
            id=channel_id
        )

        return self.request(request, "getchannel", channel_id)

    def list_playlists(self, channel_id: str):
        request = self.yt.playlists().list(
            part="snippet,contentDetails,localizations,id",
            maxResults=50,
            channelId=channel_id
        )

        return self.request(request, "getchannelplaylists", channel_id)

    def get_channel_id_list():
        return common.load_yaml("data/core/yt_channels.yaml")

