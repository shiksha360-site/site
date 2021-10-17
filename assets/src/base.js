if(window.location.protocol == "file:") {
    var serverHost = "http://localhost:80"
}
else {
    var serverHost = window.location.protocol + "//" + window.location.host
}

// For now, we will offer language switching as well
var lang = "en"

htmlURL = "/data/keystone/html.min.json?v=259"

console.log(serverHost)

function getToc() {
    fetch(htmlURL)
    .then(r => r.json())
    .then(r => $("#toc").html(r.grades_list[lang]))
}

getToc()
