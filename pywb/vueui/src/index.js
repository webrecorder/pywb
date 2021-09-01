import appData from "./App.vue";

import { PywbData } from "./model.js";

import Vue from "vue/dist/vue.esm.browser";

var app = null;

export function init(data, config = {}, loadCallback = null) {
  app = new Vue(appData);

  const pywbData = new PywbData(data);

  app.$set(app, "snapshots", pywbData.snapshots);
  app.$set(app, "currentPeriod", pywbData.timeline);

  app.$set(app, "config", {...app.config, ...config});

  app.$mount("#app");

  if (loadCallback) {
    app.$on("show-snapshot", loadCallback);
  }
}

export function update(data, snapshotData) {
  const pywbData = new PywbData(data);

  app.$set(app, "snapshots", pywbData.snapshots);
  app.$set(app, "currentPeriod", pywbData.timeline);

  app.setSnapshot(snapshotData);
}
