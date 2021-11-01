var loginHTML = `
<form id="login-form" onsubmit="event.preventDefault();loginUser()">
    <p id="login-err" style="color: red;"></p>
    <div class="form-group">
    <label for="username">Username (or email)</label>
    <input type="text" class="form-control" id="username">
    </div>
    <div class="form-group">
    <label for="password">Password</label>
    <input type="password" class="form-control" id="password">
    <button type="submit" style="visibility: hidden;" onclick="event.preventDefault();loginUser()"></button>
    </div>
</form>
`

function showLoginPrompt() {
    modal = modalShow("Login", loginHTML, true)
    if($("#login-user-button").length == 0) {
        $("#base-modal-footer").append('<button id="login-user-button" class="btn btn-primary" onclick="loginUser()" aria-label="Login">Login</button>')
    }
    if(window["loginAttempt"]) {
        loginAttempt = window["loginAttempt"]
        console.log("Found prior login attempt", loginAttempt)
        $("#username").val(loginAttempt.username)
        $("#password").val("")
        $("#login-err").html(loginAttempt.error)
    }
    modal.modal()
}

async function loginUser() {
    username = $("#username").val()
    password = $("#password").val()
    
    if(!username || !password) {
        window["loginAttempt"] = {
            username: username,
            error: "You must provide both a username and password!"
        }
        showLoginPrompt()
        return
    }
    if(username.includes("@") && username.includes(".")) {
        data = {email: username, password: password}
    }
    else {
        data = {username: username, password: password}
    }

    modalShow("Login", "Logging you in...")
    r = await fetch("/api/login", {
        method: "POST",
        body: JSON.stringify(data)
    })

    switch(r.status) {
        case 422:
            data = await r.json()
            modalShow("Something's went wrong...", "Please report the below error <a href='https://github.com/shiksha360-site/site/issues/new/choose'>here</a>:<br/><pre>" + JSON.stringify(data) + "</pre>")
            modalShow()
            break
        case 404:
            modalShow("Something's went wrong...", "We're working on it... don't worry!")
            break
        case 400:
            data = await r.json()
            window["loginAttempt"] = {
                username: username,
                error: data.reason
            }
            showLoginPrompt()
            break
        case 206:
            data = await r.json()
            data["username"] = username
            console.log("Successful login")
            localStorage.setItem("login-data", JSON.stringify(data))
            prefs = data.ctx.preferences
            window.location.href = `/learn.html?grade=${prefs.grade}&board=${prefs.board}`
    }
}

function logoutUser() {
    localStorage.clear()
    window.location.reload()
}

function loginCheck() {
    loginData = localStorage.getItem("login-data")
    if(loginData) {
        loginData = JSON.parse(loginData)
        $("#navbar-login-check").html("Logout")
        $("#navbar-login-check").on("click", logoutUser)
        $("#main-navbar").prepend(`
        <li class="nav-item active" id="navbar-profile-check-item">
          <a class="nav-link" id="navbar-profile-check" href="/profile.html?user_id=${loginData.ctx.user_id}">Profile</a>
        </li>
        `)
    }
    else {
        $("#navbar-login-check").html("Login")
        $("#navbar-login-check").on("click", showLoginPrompt)
    }
}