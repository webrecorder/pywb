

// ===========================================================================
class CDXLoader {
  constructor(staticPrefix, url, prefix, timestamp) {
    this.opts = {};
    this.prefix = prefix;
    this.staticPrefix = staticPrefix;

    this.isReplay = (timestamp !== undefined);

    if (this.isReplay) {
      window.WBBanner = new VueBannerWrapper(this);
    }

    let queryURL;

    // query form *?=url...
    if (window.location.href.indexOf("*?") > 0) {
      queryURL = window.location.href.replace("*?", "cdx?") + "&output=json";
      url = new URL(queryURL).searchParams.get("url");

    // otherwise, traditional calendar form /*/<url>
    } else if (url) {
      const params = new URLSearchParams();
      params.set("url", url);
      params.set("output", "json");
      queryURL = prefix + "cdx?" + params.toString();

    // otherwise, an error since no URL
    } else {
      throw new Error("No query URL specified");
    }

    this.opts.initialView = {url, timestamp};

    // TODO: make configurable
    this.opts.logoImg = staticPrefix + "/pywb-logo-sm.png";

    this.loadCDX(queryURL).then((cdxList) => {
      PywbVue.init(cdxList, this.opts, (snapshot) => this.loadSnapshot(snapshot));
    });
  }

  async updateSnapshot(url, timestamp) {
    const params = new URLSearchParams();
    params.set("url", url);
    params.set("output", "json");
    const queryURL = this.prefix + "cdx?" + params.toString();

    const cdxList = await this.loadCDX(queryURL);

    PywbVue.update(cdxList, {url, timestamp});
  }

  async loadCDX(queryURL) {
    const queryWorker = new Worker(this.staticPrefix + '/queryWorker.js');

    const p = new Promise((resolve) => {
      const cdxList = [];

      queryWorker.addEventListener("message", (event) => {
        const data = event.data;
        switch (data.type) {
          case "cdxRecord":
            cdxList.push(data.record);
            break;

          case "finished":
            resolve(cdxList);
            break;
        }
      });
    });

    queryWorker.postMessage({
      type: 'query',
      queryURL
    });

    const results = await p;

    queryWorker.terminate();
    //delete queryWorker;

    return results;
  }

  loadSnapshot(snapshot) {
    if (!this.isReplay) {
      window.location.href = this.prefix + snapshot.id + "/" + snapshot.url;
    } else if (cframe) {
      cframe.load_url(snapshot.url, snapshot.id + "");
    }
  }
}


// ===========================================================================
class VueBannerWrapper
{
  constructor(loader) {
    this.loading = true;
    this.lastUrl = null;
    this.loader = loader;
  }

  init() {}

  stillIndicatesLoading() {
    return this.loading;
  }

  updateCaptureInfo(url, ts, is_live) {
    this.loading = false;
  }

  onMessage(event) {
    const type = event.data.wb_type;

    if (type === 'load' || type === 'replace-url') {
      if (event.data.url !== this.lastUrl) {
        this.loader.updateSnapshot(event.data.url, event.data.ts);
        this.lastUrl = event.data.url;
      }
    }
  }
}
