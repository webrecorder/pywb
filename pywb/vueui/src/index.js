import appData from "./App.vue";

import { PywbData } from "./model.js";

import Vue from "vue/dist/vue.esm.browser";


// ===========================================================================
export function main(staticPrefix, url, prefix, timestamp, logoUrl) {
  new CDXLoader(staticPrefix, url, prefix, timestamp, logoUrl);
}

// ===========================================================================
class CDXLoader {
  constructor(staticPrefix, url, prefix, timestamp, logoUrl) {
    this.opts = {};
    this.prefix = prefix;
    this.staticPrefix = staticPrefix;
    this.logoUrl = logoUrl;

    this.isReplay = (timestamp !== undefined);

    if (this.isReplay) {
      window.WBBanner = new VueBannerWrapper(this, url);
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

    this.opts.logoImg = this.staticPrefix + "/" + (this.logoUrl ? this.logoUrl : "pywb-logo-sm.png");

    this.loadCDX(queryURL).then((cdxList) => {
      this.app = this.initApp(cdxList, this.opts, (snapshot) => this.loadSnapshot(snapshot));
    });
  }

  initApp(data, config = {}, loadCallback = null) {
    const app = new Vue(appData);

    const pywbData = new PywbData(data);

    app.$set(app, "snapshots", pywbData.snapshots);
    app.$set(app, "currentPeriod", pywbData.timeline);

    app.$set(app, "config", {...app.config, ...config, prefix: this.prefix});

    app.$mount("#app");

    // TODO (Ilya): make this work with in-page snapshot/capture/replay updates!
    // app.$on("show-snapshot", snapshot => {
    //   const replayUrl = app.config.url;
    //   const url = location.href.replace('/'+replayUrl, '').replace(/\d+$/, '') + snapshot.id + '/' + replayUrl;
    //   window.history.pushState({url: replayUrl, timestamp: snapshot.id}, document.title, url);
    //   if (!window.onpopstate) {
    //     window.onpopstate = (ev) => {
    //       updateSnapshot(ev.state.url, ev.state.timestamp);
    //     };
    //   }
    // });
    if (loadCallback) {
      app.$on("show-snapshot", loadCallback);
    }

    return app;
  }

  async updateSnapshot(url, timestamp) {
    const params = new URLSearchParams();
    params.set("url", url);
    params.set("output", "json");
    const queryURL = this.prefix + "cdx?" + params.toString();

    const cdxList = await this.loadCDX(queryURL);

    const pywbData = new PywbData(cdxList);

    const app = this.app;
    app.$set(app, "snapshots", pywbData.snapshots);
    app.$set(app, "currentPeriod", pywbData.timeline);

    app.setSnapshot({url, timestamp});
  }

  async loadCDX(queryURL) {
    const queryWorker = new Worker(this.staticPrefix + "/queryWorker.js");

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
      type: "query",
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
    } else if (window.cframe) {
      window.cframe.load_url(snapshot.url, snapshot.id + "");
    }
  }
}


// ===========================================================================
class VueBannerWrapper
{
  constructor(loader, url) {
    this.loading = true;
    this.lastSurt = this.getSurt(url);
    this.loader = loader;
  }

  init() {}

  stillIndicatesLoading() {
    return this.loading;
  }

  updateCaptureInfo(/*url, ts, is_live*/) {
    this.loading = false;
  }

  onMessage(event) {
    const type = event.data.wb_type;

    if (type === "load" || type === "replace-url") {
      const surt = this.getSurt(event.data.url);

      if (surt !== this.lastSurt) {
        this.loader.updateSnapshot(event.data.url, event.data.ts);
        this.lastSurt = surt;
      }
    }
  }

  getSurt(url) {
    try {
      if (!url.startsWith("https:") && !url.startsWith("http:")) {
        return url;
      }
      url = url.replace(/^(https?:\/\/)www\d*\./, "$1");
      const urlObj = new URL(url.toLowerCase());

      const hostParts = urlObj.hostname.split(".").reverse();
      let surt = hostParts.join(",");
      if (urlObj.port) {
        surt += ":" + urlObj.port;
      }
      surt += ")";
      surt += urlObj.pathname;
      if (urlObj.search) {
        urlObj.searchParams.sort();
        surt += urlObj.search;
      }
      return surt;
    } catch (e) {
      return url;
    }
  }
}
