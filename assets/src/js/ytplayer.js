// From https://developers.google.com/youtube/iframe_api_reference

var player;

videoInfo = {
    divId: null,
    startCallback: null,
    stateCallback: null,
    isInNewVideo: true,
    apiReady: false,
    player: null,
    target: null,
    doneTracking: false,
    tracker: 0
}

function playYt(divId, startCallback, stateCallback) {
    // sCallback is what to call on starting the video
    if(!startCallback) {
        startCallback = (event) => console.log(event)
    }
    // stateCallback is what to call if the player state changes
    if(!stateCallback) {
        stateCallback = (event) => console.log(event)
    }

    videoInfo.divId = divId
    videoInfo.startCallback = startCallback
    videoInfo.stateCallback = stateCallback
    videoInfo.isInNewVideo = true

    // This code loads the IFrame Player API code asynchronously.
    if(videoInfo.apiReady) {
        videoInfo.player.stopVideo()
        playVideo()
    }
    else {
        var tag = document.createElement('script');

        tag.src = "https://www.youtube.com/iframe_api";
        var firstScriptTag = document.getElementsByTagName('script')[0];
        firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);
    }
}

function onYouTubeIframeAPIReady() {
    videoInfo.apiReady = true
    playVideo()
}

function playVideo() {
    setTimeout(_playVideo, 100)
}

function _playVideo() {
    player = new YT.Player(videoInfo.divId, {
        playerVars: {
            'playsinline': 1
        },
        events: {
            'onReady': function(event) {
                event.target.playVideo();
                videoInfo.isInNewVideo = false
                videoInfo.player = player
                videoInfo.target = event.target
                videoInfo.startCallback(event)
            },
            'onStateChange': videoInfo.stateCallback
        }
    })
}
