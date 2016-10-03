/*
Copyright(c) 2013-2014 Ilya Kreymer. Released under the GNU General Public License.

This file is part of pywb, https://github.com/ikreymer/pywb

    pywb is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    pywb is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with pywb.  If not, see <http://www.gnu.org/licenses/>.
*/

// VidRw 1.0 -- video rewriting
//
//

var _pywbvid = "default";

var _pywb_yt_err = undefined;

if (window.location.hash) {
    var m = window.location.hash.match(/_pywbvid=([\w]+)/);
    if (m) {
        _pywbvid = m[1];
    }

    if (_pywbvid == "html" || _pywbvid == "flash") {
        var YT_W_E_RX = /^(https?:\/\/.*youtube.com)\/(watch|embed).*$/;

        if (wbinfo.url.match(YT_W_E_RX)) {
            // special case: prevent yt player from being inited
            Object.defineProperty(window, 'yt', {writeable: false});
            Object.defineProperty(window, 'ytplayer', {writeable: false});
        }
    }
}


__wbvidrw = (function() {

    var checked_embeds = false;

    var FLASH_PLAYER = wbinfo.static_prefix + "/flowplayer/flowplayer-3.2.18.swf";

    var replay_prefix = wbinfo.prefix;
    if (wbinfo.mod) {
        replay_prefix += wbinfo.mod + "/";
    }

    function check_videos() {
        if (checked_embeds) {
            return;
        }

        function handle_all_embeds() {
            var embeds = document.getElementsByTagName("embed");

            for (var i = 0; i < embeds.length; i++) {
                handle_embed_tag(embeds[i]);
            }
        }

        function handle_all_objects() {
            var objects = document.getElementsByTagName("object");

            for (var i = 0; i < objects.length; i++) {
                handle_object_tag(objects[i]);
            }
        }

        handle_all_embeds();
        handle_all_objects();

        checked_embeds = true;

        handle_yt_videos(_pywbvid);

        //window.setInterval(handle_all_embeds, 2000);
        //_wb_wombat.add_tag_handler("embed", handle_all_embeds);
        //_wb_wombat.add_tag_handler("object", handle_all_objects);
    }

    function check_broken_vimeo()
    {
        if (document.querySelector("video")) {
            return;
        }

        if (document.querySelector("object") || document.querySelector("embed")) {
            return;
        }

        var player = document.getElementById("player");

        if (!player) {
            return;
        }

        player.classList.remove("loading");

        // Add placeholder embed
        var embed = document.createElement("embed");
        embed.src = wbinfo.url;
        player.appendChild(embed);

        if (!window.MutationObserver) {
            handle_embed_tag(embed);
        }
    }

    function handle_embed_tag(elem)
    {
        var src = elem.getAttribute("src");
        if (!src) {
            return false;
        }
        
        if (elem._vidrw) {
            return false;
        }

        // already rewritten
        if (elem.outerHTML.indexOf(FLASH_PLAYER) >= 0) {
            return false;
        }

        elem._vidrw = true;
        
        if (src.indexOf("ustream.tv/flash") >= 0) {
            var flashvars = elem.getAttribute("flashvars");
            var res = flashvars.match(/[vc]id=([\d]+)/);
            if (res) {
                src = "http://www.ustream.tv/recorded/" + res[1];
            }
        }

        check_replacement(elem, src);
        return true;
    }

    function handle_object_tag(elem)
    {
        var obj_url = undefined;

        // already rewritten
        if (elem.outerHTML.indexOf(FLASH_PLAYER) >= 0) {
            return false;
        }

        for (var j = 0; j < elem.children.length; j++) {
            var child = elem.children[j];

            if (child.tagName == "EMBED") {
                return false;
            }

            if (child.tagName == "PARAM" && !obj_url) {
                var name = child.getAttribute("name");
                name = name.toLowerCase();

                if (name == "movie" || name == "src") {
                    var value = child.getAttribute("value");
                    obj_url = value;
                }

                //flashvars extraction: work in progress: for now, only ustream
                if (name == "flashvars") {
                    if (wbinfo.url.indexOf("ustream") >= 0) {
                        var value = child.getAttribute("value");

                        var pairs = value.split('&');

                        var result = {};
                        pairs.forEach(function(pair) {
                            if (obj_url) {
                                return;
                            }
                            pair = pair.split('=');
                            var qval = decodeURIComponent(pair[1] || '');
                            //TODO: allow for picking from multiple urls
                            if (qval.indexOf("http") == 0) {
                                obj_url = qval;
                                return;
                            }
                        });
                    }

                    //if (wbinfo.url.indexOf("livestream") >= 0) {
                    obj_url = wbinfo.url;
                    //}
                }
            }
        }

        if (obj_url) {
            if (elem._vidrw) {
                return false;
            }

            elem._vidrw = true;

            check_replacement(elem, obj_url);
            return true;
        }

        return false;
    }

    var YT_W_E_RX = /^(https?:\/\/.*youtube.com)\/(watch|embed).*$/;
    var YT_V_RX = /^(https?:\/\/.*youtube.com)\/v\/([^&?]+)(.*)$/;
    var VIMEO_RX = /^https?:\/\/.*vimeo.*clip_id=([^&]+)/;

    function remove_yt()
    {
        // yt special case
        if (window.yt && window.yt.player && window.yt.player.getPlayerByElement) {
            //yt.player.Application.create("player-api", ytplayer.config).dispose();

            var elem = window.yt.player.getPlayerByElement("player-api");

            if (!elem) {
                elem = window.yt.player.getPlayerByElement("player");
            }

            if (elem) {
                elem.destroy();
            }

            delete window.yt;
            if (window.ytplayer) {
                delete window.ytplayer;
            }
        }
        // end yt special case
    }

    function handle_yt_videos(_pywbvid)
    {
        function do_yt_video_replace(elem)
        {
            remove_yt();

            while (elem.hasChildNodes()) {
                elem.removeChild(elem.lastChild);
            }

            //add placeholder child to remove
            var placeholder = document.createElement("div", true);
            elem.appendChild(placeholder);
            check_replacement(placeholder, wbinfo.url);
        }

        // special case: yt
        if (wbinfo.url.match(YT_W_E_RX)) {
            //var ytvideo = document.getElementsByTagName("video");
            var player_div = document.getElementById("player-api");
            if (!player_div) {
                player_div = document.getElementById("player");
            }

            //if (ytvideo.length == 1 && ytvideo[0].getAttribute("data-youtube-id") != "") {
            if (player_div) {
                if (_pywbvid == "html" || _pywbvid == "flash") {
                    do_yt_video_replace(player_div);
                } else if (!wbinfo.is_live) {
                    var player = undefined;

                    if (window.yt && window.yt.player && window.yt.player.getPlayerByElement) {
                        player = window.yt.player.getPlayerByElement(player_div);
                    }

                    if (player) {
                        _pywb_yt_err = function() {
                            do_yt_video_replace(player_div);
                        }

                        player.addEventListener("onError", "_pywb_yt_err");
                    }

                    setTimeout(function() {
                        if (!window.yt || !window.yt.player) {
                            do_yt_video_replace(player_div);
                            return;
                        }

                        var state = -1;

                        if (player && player.getPlayerState) {
                            state = player.getPlayerState();
                        }

                        // if no player or player is still buffering (is this ok), then replace
                        if (state < 0) {
                            do_yt_video_replace(player_div);
                            return;
                        }
                    }, 4000);
                }
            }
        }
    }

    function check_replacement(elem, src, no_retry) {
        if (!src || src.indexOf("javascript:") == 0) {
            return;
        }

        if (src.indexOf("blob:") == 0) {
            src = wbinfo.url;
            no_retry = true;
        }

        src = _wb_wombat.extract_orig(src);

        // special cases
        if (src.indexOf("dailymotion.com/swf/") > 0) {
            src = src.replace("/swf/", "/video/");
        }

        src = src.replace(VIMEO_RX, "http://player.vimeo.com/video/$1");

        if (_pywbvid == "orig") {
            var repl_src = src.replace(YT_V_RX, "$1/embed/$2?$3&controls=0");
            if (repl_src != src) {
                do_replace_iframe(elem, repl_src);
                return;
            }
        }
        // end special cases

        var xhr = new XMLHttpRequest();
        xhr._no_rewrite = true;

        var info_url;

        // if in proxy mode, access video info via special proxy magic path
        // eg: http://pywb.proxy/<coll>/vi_/<url>
        if (wbinfo.proxy_magic) {
            info_url = window.location.protocol + "//" + wbinfo.proxy_magic + "/" + wbinfo.coll + "/";
        } else {
            info_url = wbinfo.prefix;
        }

        info_url += "vi_/" + src;

        xhr.open('GET', info_url, true);
        xhr.onload = function() {
            if (xhr.status == 200) {
                var videoinfo = JSON.parse(xhr.responseText);

                // special cases
                // Soundcloud
                if (videoinfo._type == "playlist" && videoinfo.extractor == "soundcloud:playlist") {
                    var player_url = "https://w.soundcloud.com/player/?visual=true&show_artwork=true&url=" + encodeURIComponent(videoinfo.webpage_url);
                    do_replace_iframe(elem, player_url);
                    return;
                }

                if (videoinfo._type == "playlist") {
                    if (videoinfo.entries && videoinfo.entries.length > 0) {
                        do_replace_video(elem, videoinfo.entries[0]);
                        return;
                    }
                }

                if (!videoinfo.formats && videoinfo.url && videoinfo.ext && videoinfo.format_id &&
                    !(videoinfo.ext == "swf" && videoinfo.format_id == "0")) {
                    videoinfo.formats = [{ext: videoinfo.ext,
                                          url: videoinfo.url,
                                          format_id: videoinfo.format_id
                                         }];
                }

                if (videoinfo.formats) {
                    do_replace_video(elem, videoinfo);
                    return;
                }
            }

            // Retry with current page as last resort
            if (!no_retry) {
                check_replacement(elem, wbinfo.url, true);
            }
        };
        xhr.send();
    }

    function do_replace_iframe(elem, url) {
        var iframe = document.createElement("iframe");
        var dim = get_dim(elem);
        iframe.width = dim[0];
        iframe.height = dim[1];
        iframe.src = url;
        iframe.setAttribute("frameborder", 0);
        do_replace_elem(elem, iframe);
    }

    function get_dim(elem) {
        var width = elem.width;
        if (!width) {
            width = "100%";
        }

        var height = elem.height;
        if (!height) {
            height = "100%";
        }

        return [width, height];
    }

    function do_replace_elem(elem, replacement) {
        var tag_name = elem.tagName.toLowerCase();

        if (!elem.parentNode) {
            console.warn("vidrw: Missing Parent Node for Video Replace!");
            return;
        }

        if (tag_name == "iframe" || tag_name == "object") {
            elem.parentNode.replaceChild(replacement, elem);
        } else if (tag_name == "embed") {
            if (elem.parentElement && elem.parentElement.tagName.toLowerCase() == "object") {
                elem = elem.parentElement;
            }

            elem.parentNode.replaceChild(replacement, elem);

        } else {
            elem.parentNode.replaceChild(replacement, elem);
        }
    }


    function do_replace_video(elem, info) {
        var thumb_url = null;

        if (info.thumbnail) {
            thumb_url = replay_prefix + info.thumbnail;
        }

        var tag_name = elem.tagName.toLowerCase();

        var dim = get_dim(elem);
        var width = dim[0], height = dim[1];

        // sort in reverse preference
        info.formats.sort(function(f1, f2) {
            var pref1 = f1.preference ? f1.preference : 0;
            var pref2 = f2.preference ? f2.preference : 0;
            return pref2 - pref1;
        });

        // Try HTML5 Video
        var htmlelem = document.createElement("video", true);

        var replacement = null;

        if (htmlelem.canPlayType) {
            var type = can_play_video_or_audio(htmlelem, info);

            if (type) {
                if (type == "audio") {
                    htmlelem = document.createElement("audio", true);
                }
                if (_pywbvid != "flash") {
                    replacement = init_html_player(htmlelem, type, width, height, info, thumb_url);
                }
            }
        }

        var vidId = undefined;

        if (!replacement) {

            // check format, if this is just an swf file, and not a video, nothing to replace!
            if (get_format_ext(info) == "swf") {
                return;
            }

            replacement = document.createElement("div", true);

            vidId = "_wb_vid" + Date.now() + Math.random();
            replacement.setAttribute("id", vidId);
        }

        do_replace_elem(elem, replacement);

        if (vidId) {
            init_flash_player(vidId, replacement, width, height, info, thumb_url);
        }
    }

    function get_format_ext(info_format) {
        if (info_format.ext == "unknown_video") {
            return info_format.format_id;
        } else {
            return info_format.ext;
        }
    }

    function can_play_video_or_audio(elem, info) {
        var types = ["video", "audio"];
        var type = undefined;

        // include main url
        info._wb_avail = 1;

        for (var i = 0; i < info.formats.length; i++) {
            // Skip DASH formats
            if (info.formats[i].format_note && info.formats[i].format_note.indexOf("DASH") >= 0) {
                continue;
            }

            for (var j = 0; j < types.length; j++) {
                var ext = get_format_ext(info.formats[i]);

                if (can_play(elem, ext, types[j])) {
                    info.formats[i]._wb_canPlay = true;
                    info._wb_avail++;
                    type = types[j];
                    break;
                }
            }
        }

        return type;
    }

    function can_play(elem, ext, type) {
        var canplay = elem.canPlayType(type + "/" + ext);
        if (canplay === "probably" || canplay === "maybe") {
            return true;
        } else {
            return false;
        }
    }

    function init_html_player(htmlelem, type, width, height, info, thumb_url)
    {
        htmlelem.setAttribute("width", width);
        htmlelem.setAttribute("height", height);
        htmlelem.setAttribute("controls", "1");
        htmlelem.style.backgroundColor = "#000";
        htmlelem.style.visibility = "visible";

        if (thumb_url) {
            htmlelem.setAttribute("poster", thumb_url);
        }

        var num_failed = 0;

        var fallback = function() {
            num_failed++;
            // only handle if all have failed
            if (num_failed < info._wb_avail) {
                return;
            }

            var replacement = document.createElement("div", true);

            var vidId = "_wb_vid" + Date.now();
            replacement.setAttribute("id", vidId);

            htmlelem.parentNode.replaceChild(replacement, htmlelem);

            init_flash_player(vidId, replacement, width, height, info, thumb_url);
        };

        for (var i = -1; i < info.formats.length; i++) {
            var source = document.createElement("source", true);

            var url, format;

            if (i < 0) {
                url = info.url;
                format = get_format_ext(info);
            } else {
                if (!info.formats[i]._wb_canPlay) {
                    continue;
                }
                url = info.formats[i].url;
                format = get_format_ext(info.formats[i]);
            }

            url = replay_prefix + url;
            format = type + "/" + format;

            source.setAttribute("src", url);
            source.setAttribute("type", format);
            source.addEventListener("error", fallback);

            htmlelem.appendChild(source);
        }

        htmlelem.addEventListener("error", fallback);
        return htmlelem;
    }

    function init_flash_player(div_id, elem, width, height, info, thumb_url)
    {
        if (width[width.length - 1] != '%') {
            width += "px";
        }
        if (height[height.length - 1] != '%') {
            height += "px";
        }

        var style = 'width: ' + width + '; height: ' + height + '; display: block; visibility: visible !important';

        elem.style.cssText += ';' + style;

        var url;

        if (wbinfo.is_live) {
            url = info.url;
        } else {
            url = info.url;
        }

        url = replay_prefix + url;

        var config = {
            clip: {
                url: url,
            },

            plugins: {
                rangeRequests: true
            }
        };

        var opts = {
            src: FLASH_PLAYER,
            onFail: function() { console.log("FAILED");  }
        };

        var do_embed = function() {
            var flash = window.flashembed(div_id, opts, {"config": config});
        };

        if (!window.flashembed) {
            var script = document.createElement("script", true);
            script._no_rewrite = true;
            script.onload = do_embed;
            script.setAttribute("src", wbinfo.static_prefix + "/flowplayer/toolbox.flashembed.js");
            document.body.appendChild(script);
        } else {
            do_embed();
        }
    }

    //============================================
    function init_node_insert_obs(window)
    {
        function do_handle(te, func)
        {
            setTimeout(function() { func(te); }, 100);
        }

        var m = new MutationObserver(function(records, observer)
                                     {
            for (var i = 0; i < records.length; i++) {
                var r = records[i];
                if (r.type == "childList") {
                    for (var j = 0; j < r.addedNodes.length; j++) {

                        var elem = undefined;
                        var tag_name = undefined;

                        try {
                            elem = r.addedNodes[j];
                            tag_name = elem.tagName;
                        } catch (e) {
                            continue;
                        }

                        if (tag_name) {
                            if (tag_name == "OBJECT") {
                                do_handle(elem, handle_object_tag);
                            } else if (tag_name == "EMBED") {
                                do_handle(elem, handle_embed_tag);
                            }
                        }                           
                    }
                }
            }
        });

        m.observe(window.document.documentElement, {
            childList: true,
            subtree: true,
        });
    }


    if (!window.MutationObserver) {
        document.addEventListener("DOMContentLoaded", function() {
            window.setTimeout(check_videos, 200);
        });
    } else {
        init_node_insert_obs(window);
    }


    // VIMEO FIX
    if (wbinfo && wbinfo.url.indexOf("player.vimeo.com/") >= 0) {
        document.addEventListener("DOMContentLoaded", function() {
            window.setTimeout(check_broken_vimeo, 500);
        });
    }

})();
