

// ===========================================================================
class CDXLoader {
  constructor(staticPrefix, url, prefix, timestamp) {
    this.opts = {};
    this.prefix = prefix;

    this.isReplay = (timestamp !== undefined);

    if (this.isReplay) {
      window.WBBanner = new VueBannerWrapper(this);
    }

    this.queryWorker = new Worker(staticPrefix + '/queryWorker.js');

    // query form *?=url...
    if (window.location.href.indexOf("*?") > 0) {
      this.queryURL = window.location.href.replace("*?", "cdx?") + "&output=json";
      url = new URL(this.queryURL).searchParams.get("url");

    // otherwise, traditional calendar form /*/<url>
    } else if (url) {
      const params = new URLSearchParams();
      params.set("url", url);
      params.set("output", "json");
      this.queryURL = prefix + "cdx?" + params.toString();

    // otherwise, an error since no URL
    } else {
      throw new Error("No query URL specified");
    }

    this.opts.initialView = {url, timestamp};

    // TODO: make configurable
    this.opts.logoImg = staticPrefix + "/pywb-logo-sm.png";

    const cdxList = [];

    this.queryWorker.addEventListener("message", (event) => {
      const data = event.data;
      switch (data.type) {
        case "cdxRecord":
          cdxList.push(data.record);
          break;

        case "finished":
          PywbVue.init(cdxList, this.opts, (snapshot) => this.loadSnapshot(snapshot));
          break;
      }
    });
  }

  init() {
    this.queryWorker.postMessage({
      type: 'query',
      queryURL: this.queryURL
    });
  }

  loadSnapshot(snapshot) {
    if (!isReplay) {
      window.location.href = this.prefix + snapshot.id + "/" + snapshot.url;
    }
  }
}


// ===========================================================================
class VueBannerWrapper
{
  constructor() {
    this.loading = true;
    this.lastUrl = null;
  }

  init() {}

  stillIndicatesLoading() {
    return this.loading;
  }

  updateCaptureInfo(url, ts, is_live) {
    this.loading = false;
  }

  onMessage(event) {
    console.log(event);
  }
}
