resourceTypeData = {}
alreadyRendered = {}


function isMobile() {
    // Returns whether a device is a mobile device or not
    return $(window).width() < 600;
}

function topicRenderer(grade, board, subject, chapter, body, topic, topicData, subtopic, res) {
    // This actually renders topics with their videos, experiments etc
    alert(JSON.stringify(res))
    console.log("Called topic renderer with: ", grade, board, subject, chapter, body, topic, topicData, subtopic, res)
    Object.entries(resourceTypeData).forEach(([key, value]) => {
        if(res[key].length) {
            console.log(`Got ${topic}:${subtopic}`)
            body.append(`<div id='${topic}-${subtopic}-${value.enum_name}'><strong>${value.doc}</strong></div>`)
        }
    })

    body.append("<br/><br/>")
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

function topicEventListener(grade, board, subject, chapter, body, topic, topicData, subtopic) {
    // Recursively handling topic clicks
    if(!subtopic) {
        subtopic = "_root"
    }
    isRendered = topicAlreadyRendered(topic, subtopic)
    setTimeout(() => {
        fetch(`/data/grades/${grade}/${board}/${subject}/${chapter}/resources-${topic}-${subtopic}.lynx`)
        .then(r => parseLynx(r))
        .then(r => {
            if(isRendered) {
                return r
            }
            if(subtopic == "_root") {
                renderElem = $("<div>").appendTo(`#${topic}-body`)
            }
            else {
                renderElem = $("<div>").appendTo(`#${topic}-${subtopic}-body`)
            }
            setTimeout(() => topicRenderer(grade, board, subject, chapter, renderElem, topic, topicData, subtopic, r), 0)
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
                            topicEventListener(grade, board, subject, chapter, sbody, topic, value, key)
                        }
                    })
                })   
                console.log(key, value)
            })
            return r
        })
        .then(r => {
            // Debug code
            if(topic != "main" && subtopic != "main") {
                return r
            }
            console.log("Started up debug code")
            if(searchParams.get("debug") == "1" || !isProd) { // Change this during prod
                data = JSON.stringify(r)
                if(!isRendered) {
                    body.append(baseAccordian(`${topic}-dbg-accordian`))
                    addCard(`${topic}-dbg-accordian`, `${topic}-dbg`, "Debug")
                }
                $(`#${topic}-dbg-body`).html("Loading...")
                $(`#${topic}-dbg-collapse-card`).on('show.bs.collapse', function (e) {
                    e.stopPropagation() // Ensure only childs event handler runs and not parent
                    $(`#${topic}-dbg-body`).html(`<pre>${data}</pre>`)
                })
            }
            return r
        })
        .catch((e) => body.html(`Something went wrong... Check your internet connection? ${e}`))
    }, 1)
}

function renderTopic(grade, board, subject, chapter) {
    $("#toc").html(baseAccordian("chapter-accordian"))
    fetch(`/data/grades/${grade}/${board}/${subject}/${chapter}/info.lynx`)
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
            waitForElm(`#${key}-collapse-card`)
            .then(() => {
                $(`#${key}-collapse-card`).on('show.bs.collapse', function (e) {
                    console.log(`Shown ${this.id}`)
                    body = $(`#${key}-body`)
                    
                    if(!body.attr("loaded-topics")) {
                        topicEventListener(grade, board, subject, chapter, body, key, r.topics[key], null)
                    }
                })
            })
        })
    })
    .catch(() => $("#toc").html("Something went wrong... Check your URL?"))
}

function chapterPane() {
    searchParams = new URLSearchParams(window.location.search)
    window["searchParams"] = searchParams
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

    document.title = `Grade ${grade} ${board.toUpperCase()} - ${subject} - Chapter ${chapter}`

    fetch("/data/keystone/resource_types.lynx")
    .then(r => parseLynx(r))
    .then(r => resourceTypeData = r)
    .then(() => renderTopic(grade, board.toLowerCase(), subject, chapter))
    .catch(() => $("#toc").html("Something went wrong... Check your internet connection?"))
}