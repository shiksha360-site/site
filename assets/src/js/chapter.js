resourceTypeData = {}

function topicEventListener(grade, board, subject, chapter, body, topic) {
    body.html("Loading topics")
    setTimeout(() => {
        fetch(`/data/grades/${grade}/${board}/${subject}/${chapter}/resources-${topic}.lynx`)
        .then(r => parseLynx(r))
        .then(r => {
            if(searchParams.get("debug") == "1" || !isProd) { // Change this during prod
                data = JSON.stringify(r)
                body.html(baseAccordian(`${topic}-inner-accordian`))
                $(`#${topic}-inner-body`).html("Loading...")
                addCard(`${topic}-inner-accordian`, `${topic}-inner`, "Debug")
                $(`#${topic}-inner-collapse-card`).on('show.bs.collapse', function (e) {
                    e.stopPropagation() // Ensure only childs event handler runs and not parent
                    $(`#${topic}-inner-body`).html(data)
                })
            }
        })
        .catch(() => body.html("Something went wrong... Check your internet connection?"))
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
                        topicEventListener(grade, board, subject, chapter, body, key)
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