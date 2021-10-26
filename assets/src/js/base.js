if(window.location.protocol == "file:") {
    var serverHost = "http://localhost:80"
}
else {
    var serverHost = window.location.protocol + "//" + window.location.host
}

// Subject Cache
var subjectCache = {}

// For now, we will offer language switching as well
var lang = localStorage.getItem("lang")
if(!lang) {
    lang = "en"
}

console.log(serverHost)

function parseLynx(r) {
    // Parses lynx using messagepack (or whatever new format lynx now uses) and returns a promise

    // MessagePack
    if(r.headers.get("Content-Type") == "lynx/msgpack") {
        return MessagePack.decodeAsync(r.body)
    }
}


function getToc() {
    fetch("/data/keystone/html-grades_list.lynx?d=1")
    .then(r => parseLynx(r))
    .then(r => $("#toc").html(r[lang]))

    fetch("/data/keystone/index.lynx")
    .then(r => parseLynx(r))
    .then(r => {
        $("#our-vision-text").html(r.ourvision)
    })
}