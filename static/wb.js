

// Rewritten location and domain obj setup
window.WB_wombat_location = window.location

if (window.top != window) {
    window.top.WB_wombat_location = window.top.location
}

if (window.opener) {
    window.opener.WB_wombat_location = window.opener.location
}

document.WB_wombat_domain = document.domain


function initBanner()
{
    var BANNER_ID = "_wayback_banner";

    var banner = document.getElementById(BANNER_ID);

    if (!banner) {
        banner = document.createElement("wb_div");
        banner.setAttribute("id", BANNER_ID);
        banner.innerHTML = "PyWb Test Banner!"
        document.body.insertBefore(banner, document.body.firstChild);
    }
}

var readyStateCheckInterval = setInterval(function() {
    if (document.readyState === "interactive" || document.readyState === "complete") {
        initBanner();
        clearInterval(readyStateCheckInterval);
    }
}, 10);




