if(window.location.protocol == "file:") {
    var serverHost = "http://localhost:80"
}
else {
    var serverHost = window.location.protocol + "//" + window.location.host
}

// Subject Cache
var subjectCache = {}

// For now, we will offer language switching as well
var lang = "en"

htmlURL = "/data/keystone/html.min.json?d=1"

console.log(serverHost)

function getToc() {
    fetch(htmlURL)
    .then(r => r.json())
    .then(r => $("#toc").html(r.grades_list[lang]))
}

// Fetch the toc for the user before doing anything else
getToc()
// More functions below

function getBoard(grade, board) {
    boardDiv = `grade${grade}-${board}`

    a = $("#"+boardDiv+"-pane")
    if(a.length) {
        if(!a.attr("view")) {
            a.attr("view", "1")
            a.fadeOut('fast')
        }
        else {
            a.fadeIn('fast')
            a.removeAttr("view")
        }
        return
    }

    html = ""

    subjectListURL = `/data/grades/${grade}/${board}/subject_list.min.json`
    fetch(subjectListURL)
    .then(r => r.json())
    .then(r => {
        r.forEach(subject => {
            subject_dat = subjectCache[subject]
            if(!subject_dat) {
                console.log("Still waiting for subject cache")
                return
            }
            html += `<li><a href='#' onclick='loadSubject(${grade},"${board}","${subject}")'>${subject_dat.name}</a><br/>${subject_dat.desc}<br/></li>`
        })    
        a = $("<ul>", {
            "class": "subject",
            "html": html,
            "css": {
                display: "none"
            }
        })
        a.fadeIn('fast').appendTo("#"+boardDiv)
        a.attr("id", boardDiv+"-pane")
    })
}

function loadSubject(grade, board, subject) {

}

$(document).ready(() => {
    fetch(`/data/keystone/subjects.min.json`)
    .then(r => r.json())
    .then(r => subjectCache = r)
})