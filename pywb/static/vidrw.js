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

__wbvidrw = (function() {

    var found_embeds = false;

    function check_videos() {
        if (found_embeds) {
            return;
        }

        var tags = [];

        var embeds = document.getElementsByTagName("embed");

        for (var i = 0; i < embeds.length; i++) {
            found_embeds = true;
            tags.push([embeds[i], embeds[i].getAttribute("src")]);
        }

        var objects = document.getElementsByTagName("object");

        for (var i = 0; i < objects.length; i++) {
            var obj_url = undefined;
            found_embeds = true;

            for (var j = 0; j < objects[i].children.length; j++) {
                var child = objects[i].children[j];

                if (child.tagName == "EMBED") {
                    obj_url = undefined;
                    break;
                }

                if (child.tagName == "PARAM" && !obj_url) {
                    var name = child.getAttribute("name");
                    name = name.toLowerCase();
 /*                   if (name == "flashvars") {
                        var value = child.getAttribute("value");
                        value = decodeURIComponent(value);
                        var inx = value.indexOf("=http");
                        if (inx >= 0) {
                            obj_url = value.substring(inx + 1);
                        }
                    }
*/
                    if (name == "movie") {
                        var value = child.getAttribute("value");
                        obj_url = value;
                    }
                }
            }

            if (obj_url) {
                tags.push([objects[i], obj_url]);
            }
        }

        for (var i = 0; i < tags.length; i++) {
            check_replacement(tags[i][0], tags[i][1]);
        }

        // special case: yt
        /*
        if (!found_embeds && wbinfo.url.indexOf("://www.youtube.com/watch") > 0) {
            var ytvideo = document.getElementsByTagName("video");

            if (ytvideo.length == 1) {
                if (ytvideo[0].getAttribute("data-youtube-id") != "") {
                    // Wait to see if video is playing, if so, don't replace it
                    window.setTimeout(function() {
                        if (!ytvideo || !ytvideo.length || ytvideo[0].readyState == 0) {
                            delete window.yt;
                            delete window.ytplayer;
                            console.log("REPLACING YT: " + wbinfo.url);
                            check_replacement(ytvideo[0], wbinfo.url);
                        }
                    }, 4000);
                }
            }
        }
        */
    }

    var VIMEO_RX = /^https?:\/\/.*vimeo.*clip_id=([^&]+).*/;

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

        if (window.yt) {
            delete window.yt;
        }
        if (window.ytplayer) {
            delete window.ytplayer;
        }
        // end special cases

        var xhr = new XMLHttpRequest();
        xhr._no_rewrite = true;
        xhr.open('GET', wbinfo.prefix + 'vi_/' + src, true);
        xhr.onload = function() {
            if (xhr.status == 200) {
                var videoinfo = JSON.parse(xhr.responseText);

                // special case
                if (videoinfo._type == "playlist" && videoinfo.extractor == "soundcloud:playlist") {
                    var player_url = "https://w.soundcloud.com/player/?visual=true&show_artwork=true&url=" + encodeURIComponent(videoinfo.webpage_url);
                    do_replace_iframe(elem, player_url);
                    return;
                }
                // end special case

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

        if (tag_name == "iframe" || tag_name == "object") {
            elem.parentNode.replaceChild(replacement, elem);
        } else if (tag_name == "embed") {
            if (elem.parentNode && elem.parentElement.tagName.toLowerCase() == "object") {
                elem = elem.parentNode;
            }
            elem.parentNode.replaceChild(replacement, elem);
        } else if (tag_name == "video") {
            elem.parentNode.replaceChild(replacement, elem);
        }
    }


    function do_replace_video(elem, info) {
        var thumb_url = null;

        if (info.thumbnail) {
            thumb_url = wbinfo.prefix + info.thumbnail;
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
        var htmlelem = document.createElement("video");

        var replacement = null;

        if (htmlelem.canPlayType) {
            var type = can_play_video_or_audio(htmlelem, info);

            if (type) {
                if (type == "audio") {
                    htmlelem = document.createElement("audio");
                }
                replacement = init_html_player(htmlelem, type, width, height, info, thumb_url);
            }
        }

        var vidId = undefined;

        if (!replacement) {
            replacement = document.createElement("div");

            vidId = "_wb_vid" + Date.now();
            replacement.setAttribute("id", vidId);
        }

        do_replace_elem(elem, replacement);

        if (vidId) {
            init_flash_player(vidId, width, height, info, thumb_url);
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
                if (can_play(elem, info.formats[i].ext, types[j])) {
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

            //console.log("html5 " + type +" error");
            var replacement = document.createElement("div");

            var vidId = "_wb_vid" + Date.now();
            replacement.setAttribute("id", vidId);

            htmlelem.parentNode.replaceChild(replacement, htmlelem);

            init_flash_player(vidId, width, height, info, thumb_url);
        };

        for (var i = -1; i < info.formats.length; i++) {
            var source = document.createElement("source");

            var url, format;

            if (i < 0) {
                url = info.url;
                format = info.ext;
            } else {
                url = info.formats[i].url;
                format = info.formats[i].ext;
                if (!info.formats[i]._wb_canPlay) {
                    continue;
                }
            }

            url = wbinfo.prefix + url;
            format = type + "/" + format;

            source.setAttribute("src", url);
            source.setAttribute("type", format);
            source.addEventListener("error", fallback);

            htmlelem.appendChild(source);
        }

        htmlelem.addEventListener("error", fallback);
        return htmlelem;
    }

    function init_flash_player(div_id, width, height, info, thumb_url)
    {
        var swf = wbinfo.static_prefix + "/flowplayer/flowplayer-3.2.18.swf";

        if (width[width.length - 1] != '%') {
            width += "px";
        }
        if (height[height.length - 1] != '%') {
            height += "px";
        }

        var style = 'width: ' + width + '; height: ' + height + '; display: block';
        document.getElementById(div_id).style.cssText += ';' + style;

        var url;

        if (wbinfo.is_live) {
            url = info.url;
        } else {
            url = info.url;
        }

        url = wbinfo.prefix + url;

        config = {
            clip: {
                url: url,
            },

            plugins: {
                rangeRequests: true
            }
        };

        opts = {
            src: swf,
            onFail: function() { alert("TEST"); }
        };

        var do_embed = function() {
            window.flashembed(div_id, opts, {"config": config});
        };

        if (!window.flashembed) {
            var script = document.createElement("script");
            script._no_rewrite = true;
            script.onload = do_embed;
            script.setAttribute("src", wbinfo.static_prefix + "/flowplayer/toolbox.flashembed.js");
            document.body.appendChild(script);
        } else {
            do_embed();
        }
    }

    document.addEventListener("DOMContentLoaded", function() {
        window.setTimeout(check_videos, 200);
    });

})();
