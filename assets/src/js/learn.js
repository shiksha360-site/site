function fetchSubjectHTML(grade, board) {
    fetch(`/data/grades/${grade}/html-subject_base_accordian.lynx?d=1`)
    .then(r => parseLynx(r))
    .then(r => $("#toc").html(r[lang]))
    .then(() => {
        waitForElm(".subject-collapse")
        .then(() => {
            $('.subject-collapse').on('show.bs.collapse', function () {
                console.log("Shown")
                subject = this.id.replace("collapse-subject", "")
                body = $(`#subject-body-${subject}`)
                
                if(!body.attr("loaded-topics")) {
                    body.html("Loading topics")
                    setTimeout(() => {
                        fetch(`/data/grades/${grade}/${board}/${subject}/chapter_list.lynx`)
                        .then(r => parseLynx(r))
                        .then(r => {
                            if(r == undefined) {
                                body.html("Huh? No topics found?")
                                body.attr("loaded-topics", true)
                                return
                            }
                            topicList = ""
                            Object.entries(r).forEach(([key, value]) => {
                                console.log(key)
                                console.log(value)
                                topicList += `
                                <a href="/chapter.html?grade=${grade}&board=${board}&subject=${subject}&chapter=${key}" class="chapter-button card-link btn-lg">${value.name}</a>
                                `
                            })
                            body.html(topicList)
                            body.attr("loaded-topics", true)
                        })
                    }, 1)
                }
            })
        })
        .then(() => {
            $(".top-subject").collapse("show")
        })
    })
    .catch(() => $("#toc").html("Something went wrong... Check your URL?"))
}

function learnPane() {
    searchParams = new URLSearchParams(window.location.search)
    grade = searchParams.get("grade")
    board = searchParams.get("board")
    if(!grade) {
        console.log("Invalid grade")
        $("#toc").html("Hmmm... we couldn't find that grade?")
    }
    if(!board) {
        console.log("Invalid board")
        $("#toc").html("Hmmm... we couldn't find that board?")
    }

    document.title = `Grade ${grade} - ${board.toUpperCase()}`
    fetchSubjectHTML(grade, board.toLowerCase())
}