from typing import Callable, Dict, List, Optional
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
from sdk import common
from pathlib import Path
import time
import orjson
import pickle
import os
from .classes import YoutubeData, YoutubePlaylist, YoutubePlaylistItem, YoutubeVideo

# For VSCode
os.environ["IMPORT_YT_DONE"] = "1"

class Youtube():
    scopes = ["https://www.googleapis.com/auth/youtube.readonly"]
    api_service_name = "youtube"
    api_version = "v3"
    client_secrets_file = "secrets/ytsecret.json"
    secrets_cache_file = "secrets/creds_oauth.pickle"

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
        creds = Path(self.secrets_cache_file)
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
        fpath = Path(f"{f}.lynx")        
        if self.etag_cache.get(f):
            cache_data = self.cache[self.etag_cache[f]]
        
        elif fpath.exists():
            cache_data = common.read_min(fpath)
        
        else:
            return None

        if time.time() - float(cache_data[-1]["time"]) > 60*60*24:
            return None
        
        self._cache_etag(f, cache_data[0]["etag"], cache_data)

        return cache_data
    
    def _wcache_req(self, t: str, id: str, data: List[dict]):
        data.append({"time": str(time.time()), "internal": True})
        Path(f"tmpstor").mkdir(exist_ok=True)
        f = f"tmpstor/cache-{t}-{id}"
        fpath = Path(f"{f}.lynx")  
        with fpath.open("w") as fp:
            common.write_min(data, fp, no_debug=True)
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

    def request(self, request: Callable, cache_type: str, cache_id: str, cls: YoutubeData = YoutubeData) -> List[Dict]:
        data = self._fcache_req(cache_type, cache_id)
        if not data:
            api_data = self._paginate(request, request.execute())
            self._wcache_req(cache_type, cache_id, api_data)
            return cls(self, api_data)

        print("Using already cached response")
        return cls(self, data)

    def get_channel(self, channel_id: str) -> YoutubeData:
        """https://developers.google.com/youtube/v3/docs/channels#resource"""
        request = self.yt.channels().list(
            part="snippet,contentDetails,statistics,localizations,contentOwnerDetails,statistics",
            maxResults=50,
            id=channel_id
        )

        return self.request(request, "channel", channel_id)

    def get_all_playlists(self, channel_id: str) -> YoutubePlaylist:
        """https://developers.google.com/youtube/v3/docs/playlists#resource"""
        request = self.yt.playlists().list(
            part="snippet,contentDetails,localizations,id,player",
            maxResults=50,
            channelId=channel_id
        )

        return self.request(request, "channelplaylists", channel_id, YoutubePlaylist)
    
    def get_playlist_item(self, playlist_id: str) -> YoutubePlaylistItem:
        """https://developers.google.com/youtube/v3/docs/playlistItems#resource"""
        request = self.yt.playlistItems().list(
            part="snippet,contentDetails",
            maxResults=50,
            playlistId=playlist_id
        )

        return self.request(request, "playlistitem", playlist_id, YoutubePlaylistItem)
    
    def get_video(self, video_id: str) -> YoutubeVideo:
        """https://developers.google.com/youtube/v3/docs/videos#resource"""
        request = self.yt.videos().list(
            part="snippet,contentDetails,statistics,player",
            maxResults=50,
            id=video_id
        )

        return self.request(request, "video", video_id, YoutubeVideo)
