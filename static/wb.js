

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
        banner.style.cssText = "display: block; width: 100%; border: 1px solid; background-color: lightYellow; text-align: center";

        //banner.innerHTML = "<img src='http://wbgrp-svc112.us.archive.org:8080/images/logo_WM.png#wb_pass'/>";
        banner.innerHTML = "PyWb Banner!"
        document.body.insertBefore(banner, document.body.firstChild);
    }
}

var readyStateCheckInterval = setInterval(function() {
    if (document.readyState === "interactive" || document.readyState === "complete") {
        initBanner();
        clearInterval(readyStateCheckInterval);
    }
}, 10);




