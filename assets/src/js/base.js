if(window.location.protocol == "file:") {
    var serverHost = "http://localhost:80"
}
else {
    var serverHost = window.location.protocol + "//" + window.location.host
}

const isProd = false // Whether the site is in production mode or not

// Subject Cache
var subjectCache = {}

// For now, we will offer language switching as well
var lang = localStorage.getItem("lang")
if(!lang) {
    lang = "en"
}

window.lang = lang

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

function waitForElm(selector) {
    return new Promise(resolve => {
        if (document.querySelector(selector)) {
            return resolve(document.querySelector(selector));
        }

        const observer = new MutationObserver(mutations => {
            if (document.querySelector(selector)) {
                resolve(document.querySelector(selector));
                observer.disconnect();
            }
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    });
}


// Accordian stuff

baseAccordian = (id) => `
    <div class="accordion" id="${id}">
    </div>
`

function addCard(id, prefix, title) {
    baseHTML = `
    <div class="card" id="${prefix}-card">
        <div class="card-header" data-toggle="collapse" aria-controls="${prefix}-collapse-card" data-target="#${prefix}-collapse-card" id="${prefix}-card-div">
            <h4 id="${prefix}-header" class="mb-0">
                ${title}
            </h4>
        </div>
        <div id="${prefix}-collapse-card" class="collapse" aria-labelledby="${prefix}-card-div" data-parent="#${id}">
            <div class="card-body">
                <p class="text-center" style="font-size: 18px; display: none;" id="${prefix}-body-para"></p>
                <div id="${prefix}-body">
                </div>
            </div>
        </div>
    </div>
    `
    $(`#${id}`).append(baseHTML)
}