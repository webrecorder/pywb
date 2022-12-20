import appData from "./App.vue";

import { PywbData } from "./model.js";
import { PywbI18N } from "./i18n.js";

import Vue from "vue/dist/vue.esm.browser";


// ===========================================================================
export function main(staticPrefix, url, prefix, timestamp, logoUrl, logoHomeUrl, navbarBackground, navbarColor, navbarLightButtons, locale, allLocales, i18nStrings) {
  PywbI18N.init(locale, i18nStrings);
  new CDXLoader(staticPrefix, url, prefix, timestamp, logoUrl, logoHomeUrl, navbarBackground, navbarColor, navbarLightButtons, allLocales);
}

// ===========================================================================
class CDXLoader {
  constructor(staticPrefix, url, prefix, timestamp, logoUrl, logoHomeUrl, navbarBackground, navbarColor, navbarLightButtons, allLocales) {
    this.loadingSpinner = null;
    this.loaded = false;
    this.opts = {};
    this.prefix = prefix;
    this.staticPrefix = staticPrefix;
    this.logoUrl = logoUrl;
    this.logoHomeUrl = logoHomeUrl;
    this.navbarBackground = navbarBackground;
    this.navbarColor = navbarColor;
    this.navbarLightButtons = navbarLightButtons;
    this.timestamp = timestamp;

    this.isReplay = (timestamp !== undefined);

    setTimeout(() => {
      if (!this.loaded) {
        this.loadingSpinner = new LoadingSpinner({text: PywbI18N.instance?.getText('Loading...'), isSmall: !!timestamp}); // bootstrap loading-spinner EARLY ON
        this.loadingSpinner.setOn();
      }
    }, 500);

    if (this.isReplay) {
      window.WBBanner = new VueBannerWrapper(this, url, timestamp);
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

    this.app = this.initApp({logoImg, logoHomeUrl, navbarBackground, navbarColor, navbarLightButtons, url, allLocales, timestamp});

    this.loadCDX(queryURL).then((cdxList) => {
      this.setAppData(cdxList, url, this.timestamp);
    });
  }

  initApp(config = {}) {
    const app = new Vue(appData);

    app.$set(app, "config", {...app.config, ...config, prefix: this.prefix});

    app.$mount("#app");

    app.$on("show-snapshot", (snapshot) => this.loadSnapshot(snapshot));
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

    this.setAppData(cdxList, url, timestamp);
  }

  async updateTimestamp(url, timestamp) {
    this.timestamp = timestamp;

    if (this.cdxLoading) {
      return;
    }

    this.app.setSnapshot({url, timestamp});
  }

  setAppData(cdxList, url, timestamp) {
    this.app.setData(new PywbData(cdxList));

    this.app.initBannerState(this.isReplay);

    // if set on initial load, may not have timestamp yet
    // will be updated later
    if (timestamp) {
      this.updateTimestamp(url, timestamp);
    }
  }

  async loadCDX(queryURL) {
    //  this.loadingSpinner.setOn(); // start loading-spinner when CDX loading begins
    this.cdxLoading = true;
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
          this.cdxLoading = false;
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
      const ts = snapshot.id + "";
      if (ts !== this.timestamp) {
        window.cframe.load_url(snapshot.url, ts, reloadIFrame);
      }
    }
  }
}


// ===========================================================================
class VueBannerWrapper
{
  constructor(loader, url, ts) {
    this.loading = true;
    this.lastSurt = this.getSurt(url);
    this.lastTs = ts;
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

      if (event.data.title) {
        this.loader.app.updateTitle(event.data.title);
      }

      if (surt !== this.lastSurt) {
        this.loader.updateSnapshot(event.data.url, event.data.ts);
        this.lastSurt = surt;
      } else if (event.data.ts !== this.lastTs) {
        this.loader.updateTimestamp(event.data.url, event.data.ts);
        this.lastTs = event.data.ts;
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
