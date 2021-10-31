function checkInfo() {
    searchParams = new URLSearchParams(window.location.search)
    window["searchParams"] = searchParams
    user_id = searchParams.get("user_id")
    token = searchParams.get("token")
    if(!user_id || !token) {
        $("#toc").html("Invalid link... has it expired?")
        return
    }

    fetch(`/api/account/recovery?user_id=${user_id}&token=${token}`, {
        method: "HEAD"
    })
    .then(r => {
        if(r.status == 200) {
            $("#toc").fadeOut()
            $("#reset-pwd-form").fadeIn()
            return
        }
        else {
            $("#toc").html("This link has been expired. Try recovering your account again to get a new link?")
        }
    }).catch(error => {
        $("#toc").html("This link has been expired. Try recovering your account again to get a new link?")
    })
}

function recoverAccount() {
    modalShow("Recovering your account...", "Please wait...")
}