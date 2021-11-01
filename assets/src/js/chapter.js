resourceTypeData = {}
alreadyRendered = {}

// Base Info (so we dont need huge function args)
baseInfo = {}

// Global Counter
var globCounter = 0

var currintervalYt = -1

function isMobile() {
    // Returns whether a device is a mobile device or not
    return $(window).width() < 600;
}

function trackYtProgress(event) {
    videoId = event.player.getVideoData().video_url
    if(localStorage.getItem("login-data")) {
        loginData = JSON.parse(loginData)
        fetch("/api/videos/track", {
            method: "PATCH",
            headers: {"Authorization": loginData.ctx.token},
            body: JSON.stringify({
                user_id: loginData.ctx.user_id,
                video_id: videoId, 
                duration: event.player.getCurrentTime(), 
                is_playing: event.data == YT.PlayerState.PLAYING,
            })
        })
    }
}

function videoIframeEvent(count) {
    console.log("Called iframe event")
    if(currintervalYt != -1) {
        clearInterval(currintervalYt)
        currintervalYt = -1
    }
    info = baseInfo[count]
    res_meta = info.data.resource_metadata
    html = ""
    var id = `${info.topic}-${info.subtopic}-${info.data.resource_id}`
    if(res_meta.yt_video_url) {
        html += `<iframe id='${id}' width="500px" height="400px" src="https://www.youtube.com/embed/${res_meta.yt_video_url}?enablejsapi=1" title="${info.data.resource_metadata}" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>`
    }
    modalShow(info.data.resource_title, html)
    waitForElm(`#${id}`)
    .then(() => {
        playYt(id, trackYtProgress, trackYtProgress)
        currintervalYt = setInterval(trackYtProgress, 3000)
    })
}

function videoRender(topic, subtopic, type, res, mobile_user, enumerator) {
    let id =`${topic}-${subtopic}-${type}`
    let body = $(`#${id}`)
    let html = ""
    if(!mobile_user) {
        html = `<div class="video-container">`
        res[type].forEach((v) => {
            baseInfo[globCounter] = {"data": v, "topic": topic, "subtopic": subtopic, "enum": enumerator}
            html += `<div onclick="videoIframeEvent('${globCounter}')" class="video-item"><img src="${v.resource_icon}" alt="${v.resource_description}"/><br/><small class="video-title">${v.resource_title}</small></div>`
            globCounter += 1
        })
        html += "</div>"
    }
    else {
        // TODO
    }
    body.append(html)
}

function topicRenderer(body, topic, subtopic, res) {
    // This actually renders topics with their videos, experiments etc
    calculated = {}
    mobile_user = isMobile()
    console.log("Is mobile user:", mobile_user)
    Object.entries(resourceTypeData).forEach(([key, value]) => {
        if(res[key].length && !calculated[key]) {
            body.append(`<div id='${topic}-${subtopic}-${key}'><strong>${value.doc}</strong></div>`)
            calculated[key] = true
            if(value.enum_name == "whiteboard" || value.enum_name == "animated" || value.enum_name == "lab") {
                videoRender(topic, subtopic, key, res, mobile_user, value)
            }
        }
    })
}

function topicAlreadyRendered(topic, subtopic) {
    // Helper function to check if a topic is already rendered or not
    if(subtopic) {
        arKey = topic + subtopic
    } else {
        arKey = topic
    }
    if(alreadyRendered[arKey]) {
        return true
    } else {
        alreadyRendered[arKey] = true
        return false
    }
}

function topicEventListener(body, topic, topicData, subtopic) {
    // Recursively handling topic clicks
    if(!subtopic) {
        subtopic = "main"
    }
    isRendered = topicAlreadyRendered(topic, subtopic)
    setTimeout(() => {
        fetch(`/data/grades/${baseInfo.grade}/${baseInfo.board}/${baseInfo.subject}/${baseInfo.chapter}/resources-${topic}-${subtopic}.lynx`)
        .then(r => parseLynx(r))
        .then(r => {
            if(isRendered) {
                return r
            }
            if(subtopic == "main") {
                renderElem = $("<div>").appendTo(`#${topic}-body`)
            }
            else {
                renderElem = $("<div>").appendTo(`#${topic}-${subtopic}-body`)
            }
            setTimeout(() => topicRenderer(renderElem, topic, subtopic, r), 0)
            return r
        })
        .then(r => {
            // Handle subtopics recursively if not already rendered
            if(isRendered) {
                return r
            }

            if(!topicData.subtopics) {
                topicData.subtopics = {}
            }
            Object.entries(topicData.subtopics).forEach(([key, value]) => {
                body.append(baseAccordian(`${topic}-${key}-accordian`))
                addCard(`${topic}-${key}-accordian`, `${topic}-${key}`, value.name)
                waitForElm(`#${topic}-${key}-collapse-card`)
                .then(() => {
                    $(`#${topic}-${key}-collapse-card`).on('show.bs.collapse', function (e) {
                        e.stopPropagation()
                        console.log(`Shown ${this.id}`)
                        sbody = $(`#${topic}-${key}-body`)
                        
                        if(!body.attr("loaded-topics")) {
                            topicEventListener(sbody, topic, value, key)
                        }
                    })
                })   
                console.log(key, value)
            })
            return r
        })
        .then(r => {
            // Debug code
            if(subtopic != "main") {
                return r
            }
            console.log(subtopic)
            console.log("Started up debug code")
            if(searchParams.get("debug") == "1" || !isProd) { // Change this during prod
                data = JSON.stringify(r)
                if(!isRendered) {
                    body.append(baseAccordian(`${topic}-dbg-accordian`))
                    addCard(`${topic}-dbg-accordian`, `${topic}-dbg`, "Debug")
                    $(`#${topic}-dbg-body`).html("Loading...")
                }
                $(`#${topic}-dbg-collapse-card`).on('show.bs.collapse', function (e) {
                    e.stopPropagation() // Ensure only childs event handler runs and not parent
                    $(`#${topic}-dbg-body`).html(`<pre style="font-size: 12px;">${data}</pre>`)
                })
            }
            return r
        })
        .catch((e) => body.html(`Something went wrong... Check your internet connection? ${e}`))
    }, 1)
}

function createTopicEventListener(key, r) {
    waitForElm(`#${key}-collapse-card`)
    .then(() => {
        $(`#${key}-collapse-card`).on('show.bs.collapse', function (e) {
            body = $(`#${key}-body`)
            
            if(!body.attr("loaded-topics")) {
                topicEventListener(body, key, r.topics[key], null)
            }
        })
    })
    if(alreadyRendered["_main-card"]) {
        waitForElm("#main-collapse-card")
        .then(() => $("#main-collapse-card").collapse("show"))
    }
}

function renderTopic() {
    $("#toc").append(baseAccordian("chapter-accordian"))
    fetch(`/data/grades/${baseInfo.grade}/${baseInfo.board}/${baseInfo.subject}/${baseInfo.chapter}/info.lynx`)
    .then(r => parseLynx(r))
    .then(r => {
        Object.entries(r.topics).forEach(([key, value]) => {
            if(key == "main") {
                value.name = "Introduction"
            }
            else if (key == "summary") {
                value.name = "Summary"
            }
            addCard("chapter-accordian", key, value.name)
            setTimeout(() => createTopicEventListener(key, r), 1)
            alreadyRendered[`_${key}-card`] = true
        })
    })
    .then(() => {
        $("#load-title").css("display", "none")
    })
    .catch(() => $("#toc").html("Something went wrong... Check your URL?"))
}

function chapterPane() {
    searchParams = new URLSearchParams(window.location.search)
    window["searchParams"] = searchParams
    window["inChapter"] = true
    grade = searchParams.get("grade")
    board = searchParams.get("board")
    subject = searchParams.get("subject")
    chapter = searchParams.get("chapter")
    if(!grade) {
        console.log("Invalid grade")
        $("#toc").html("Hmmm... we couldn't find that grade?")
    }
    if(!board) {
        console.log("Invalid board")
        $("#toc").html("Hmmm... we couldn't find that board?")
    }
    if(!subject) {
        console.log("Invalid subject")
        $("#toc").html("Hmmm... we couldn't find that subject?")
    }
    if(!chapter) {
        console.log("Invalid chapter")
        $("#toc").html("Hmmm... we couldn't find that chapter?")
    }

    baseInfo.grade = grade
    baseInfo.board = board
    baseInfo.subject = subject
    baseInfo.chapter = chapter

    document.title = `Grade ${grade} ${board.toUpperCase()} - ${subject} - Chapter ${chapter}`

    fetch("/data/keystone/resource_types.lynx")
    .then(r => parseLynx(r))
    .then(r => resourceTypeData = r)
    .then(() => renderTopic())
    .catch(() => $("#toc").html("Something went wrong... Check your internet connection?"))
}