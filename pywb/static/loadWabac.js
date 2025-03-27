class WabacReplay
{
  constructor(prefix, url, ts, staticPrefix, coll, swScopePrefix) {
    this.prefix = prefix;
    this.url = url;
    this.ts = ts;
    this.staticPrefix = staticPrefix;
    this.collName = coll;
    this.isRoot = coll === "$root";
    this.archivePrefix = this.isRoot ? "/" : `/${this.collName}/`;
    this.swScope = swScopePrefix;
    this.adblockUrl = undefined;

    this.queryParams = {"replayPrefix": ""};
    if (this.isRoot) {
      this.queryParams["root"] = "$root";
    }
  }

  async init() {
    const scope = this.swScope + "/";

    await navigator.serviceWorker.register(
      `${this.staticPrefix}/sw.js?` + new URLSearchParams(this.queryParams).toString(),
      { scope },
    );

    let initedResolve = null;

    const inited = new Promise((resolve) => initedResolve = resolve);

    navigator.serviceWorker.addEventListener("message", (event) => {
      if (event.data.msg_type === "collAdded") {
        // the replay is ready to be loaded when this message is received
        initedResolve();
      }
    });

    const proxyPrefix = "";

    const msg = {
      msg_type: "addColl",
      name: this.collName,
      type: "live",
      root: this.isRoot,
      file: {"sourceUrl": `proxy:${proxyPrefix}`},
      skipExisting: true,
      extraConfig: {
        prefix: proxyPrefix,
        isLive: false,
        baseUrl: this.prefix,
        baseUrlAppendReplay: true,
        noPostToGet: false,
        archivePrefix: this.archivePrefix,
        archiveMod: "ir_",
        adblockUrl: this.adblockUrl
      },
    };

    if (!navigator.serviceWorker.controller) {
      navigator.serviceWorker.addEventListener("controllerchange", () => {
        navigator.serviceWorker.controller.postMessage(msg);
      });
    } else {
      navigator.serviceWorker.controller.postMessage(msg);
    }

    window.addEventListener("message", event => {
      let data = event.data;
      if (data.wb_type !== "load") return;
      history.replaceState({}, data.title, this.prefix + data.ts + '/' + data.url);
      window.WBBanner.onMessage(event);
    });

    window.cframe = this;

    if (inited) {
      await inited;
    }

    this.load_url(this.url, this.ts);
  }

  // called by the Vue banner when the timeline is clicked
  load_url(url, ts) {
    const iframe = document.querySelector('#replay_iframe');
    iframe.src = `${this.swScope}${this.archivePrefix}${ts}mp_/${url}`;
  }
}
