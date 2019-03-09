(function() {
  var loaded = false;

  document.addEventListener("readystatechange", function() {
    if (document.readyState === "complete") {
      if (!loaded) {
        loadTransclusions();
        loaded = true;
      }
    }
  });

  function loadTransclusions() {
    var viUrl = window.location.href.replace("mp_", "vi_");

    window.fetch(viUrl)
      .then(function(response) {
        return response.json();
      })
      .then(function(json) {
        addTransclusions(json);
      })
      .catch(function(err) {
      });
  }

  function addTransclusions(json) {
    var selector = json.selector || "object, embed";
    var result = document.querySelector(selector);
    if (!result) {
      console.warn("No target to add video/audio transclusions");
      return;
    }

    var parentElem = result.parentElement;

    if (!json.formats) {
      console.warn("No formats to add!");
      return;
    }

    var isAudio = false;

    try {
      isAudio = json.formats.reduce(function(accum, curr) {
        return accum && (curr.skip_as_source || (curr && curr.mime && curr.mime.startsWith("audio/")));
      }, true);
    } catch (e) {
      isAudio = false;
    }

    var media = document.createElement(!isAudio ? "video" : "audio");
    media.setAttribute("controls", "true");
    media.setAttribute("style", "width: 100%; height: 100%");
    //media.setAttribute("autoplay", "true");
    //media.setAttribute("muted", true);

    media.oncanplaythrough = function() {
        if (!media.hasStarted) {
          //media.muted = true;
          media.hasStarted = true;
        }
        //media.play();
    }

    json.formats.forEach(function(data) {
      if (data.skip_as_source) {
        return;
      }

      if (data.name === "png_poster") {
        media.setAttribute("poster", data.url);
        return;
      }

      var source = document.createElement("source");
      source.src = data.url;
      if (data.mime) {
        source.type = data.mime;
      }
      media.appendChild(source);
    });

    parentElem.replaceChild(media, result);
  }

})();

