var update_wb_url = push_state;

var LIVE_COOKIE_REGEX = /pywb.timestamp=([\d]{1,14})/;


function make_outer_url(url, ts)
{
    if (ts) {
        return wbinfo.prefix + ts + "/" + url;
    } else {
        return wbinfo.prefix + url;
    }
}

function make_inner_url(url, ts)
{
    if (ts) {
        return wbinfo.prefix + ts + "mp_/" + url;
    } else {
        return wbinfo.prefix + "mp_/" + url;
    }
}

function push_state(url, timestamp, capture_str, is_live) {
    var state = {}
    state.timestamp = timestamp;
    state.outer_url = make_outer_url(url, state.timestamp);
    state.inner_url = make_inner_url(url, state.timestamp);
    state.url = url;
    state.capture_str = capture_str;
    state.is_live = is_live;
    
    window.history.replaceState(state, "", state.outer_url);

    update_status(state.capture_str, is_live);
}

function pop_state(state) {
    update_status(state.capture_str, state.is_live);
    
    window.frames[0].src = state.outer_url;
}

function extract_ts(url)
{
    var inx = url.indexOf("mp_");
    if (inx < 0) {
        return "";
    }
    url = url.substring(0, inx);
    inx = url.lastIndexOf("/");
    if (inx <= 0) {
        return "";
    }
    return url.substring(inx + 1);
}

function extract_replay_url(url) {
    var inx = url.indexOf("/http:");
    if (inx < 0) {
        inx = url.indexOf("/https:");
        if (inx < 0) {
            return "";
        }
    }
    return url.substring(inx + 1);
}

function update_status(str, is_live) {
    var capture_info = document.getElementById("_wb_capture_info");
    if (capture_info) {
        capture_info.innerHTML = str;
    }

    var label = document.getElementById("_wb_label");
    if (label) {
        if (is_live) {
            label.innerHTML = _wb_js.labels.LIVE_MSG;
        } else {
            label.innerHTML = _wb_js.labels.REPLAY_MSG;
        }
    }
}

window.onpopstate = function(event) {
    var curr_state = event.state;
    
    if (curr_state) {
        pop_state(curr_state);
    }
}

function extract_ts_cookie(value) {
    var result = value.match(LIVE_COOKIE_REGEX);
    if (result) {
        return result[1];
    } else {
        return "";
    }
}

function iframe_loaded(event) {
    var iframe = window.frames[0];
    var url;
    var ts;
    var capture_str;
    var is_live = false;

    if (iframe.WB_wombat_location) {
        url = window.WB_wombat_location.href;
    } else {
        url = extract_replay_url(iframe.location.href);
    }

    if (iframe.wbinfo) {
        ts = iframe.wbinfo.timestamp;
        is_live = iframe.wbinfo.is_live;
    } else {
        ts = extract_ts_cookie(iframe.document.cookie);
        if (ts) {
            is_live = true;
        } else {
            ts = extract_ts(iframe.location.href);
        }
    }
    capture_str = _wb_js.ts_to_date(ts, true);

    update_wb_url(url, ts, capture_str, is_live);
}
