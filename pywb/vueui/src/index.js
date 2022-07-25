import appData from "./App.vue";

import { PywbData } from "./model.js";
import { PywbI18N } from "./i18n.js";

import Vue from "vue/dist/vue.esm.browser";


// ===========================================================================
export function main(staticPrefix, url, prefix, timestamp, logoUrl, locale, allLocales, i18nStrings) {
  PywbI18N.init(locale, i18nStrings);
  new CDXLoader(staticPrefix, url, prefix, timestamp, logoUrl, allLocales);
}

// ===========================================================================
class CDXLoader {
  constructor(staticPrefix, url, prefix, timestamp, logoUrl, allLocales) {
    this.loadingSpinner = null;
    this.loaded = false;
    this.opts = {};
    this.prefix = prefix;
    this.staticPrefix = staticPrefix;
    this.logoUrl = logoUrl;

    this.isReplay = (timestamp !== undefined);

    setTimeout(() => {
      if (!this.loaded) {
        this.loadingSpinner = new LoadingSpinner({text: PywbI18N.instance?.getText('Loading...'), isSmall: !!timestamp}); // bootstrap loading-spinner EARLY ON
        this.loadingSpinner.setOn();
      }
    }, 500);

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

    const logoImg = this.staticPrefix + "/" + (this.logoUrl ? this.logoUrl : "pywb-logo-sm.png");

    this.app = this.initApp({logoImg, url, allLocales});
    this.loadCDX(queryURL).then((cdxList) => {
      this.setAppData(cdxList, timestamp ? {url, timestamp}:null);
    });
  }

  initApp(config = {}) {
    const app = new Vue(appData);

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

    app.$on("show-snapshot", this.loadSnapshot.bind(this));
    app.$on("data-set-and-render-completed", () => {
      if (this.loadingSpinner) {
        this.loadingSpinner.setOff(); // only turn off loading-spinner AFTER app has told us it is DONE DONE
      }
      this.loaded = true;
    });

    return app;
  }

  async updateSnapshot(url, timestamp) {
    const params = new URLSearchParams();
    params.set("url", url);
    params.set("output", "json");
    const queryURL = this.prefix + "cdx?" + params.toString();

    const cdxList = await this.loadCDX(queryURL);

    this.setAppData(cdxList, {url, timestamp});
  }

  setAppData(cdxList, snapshot=null) {
    this.app.setData(new PywbData(cdxList));

    if (snapshot) {
      this.app.setSnapshot(snapshot);
    }
  }

  async loadCDX(queryURL) {
    //  this.loadingSpinner.setOn(); // start loading-spinner when CDX loading begins
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

  loadSnapshot(snapshot, reloadIFrame=true) {
    if (!this.isReplay) {
      window.location.href = this.prefix + snapshot.id + "/" + snapshot.url;
    } else if (window.cframe) {
      window.cframe.load_url(snapshot.url, snapshot.id + "", reloadIFrame);
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
