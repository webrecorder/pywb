<template>
  <div class="app" :class="{expanded: showTimelineView}" data-app="webrecorder-replay-app">
    <div class="banner">
      <div class="line">
        <div class="logo"><a href="/"><img :src="config.logoImg" style="max-width: 80px" /></a></div>
        <div class="timeline-wrap">
          <div class="line">
            <div class="breadcrumbs-wrap">
              <TimelineBreadcrumbs
                  v-if="currentPeriod && showTimelineView"
                  :period="currentPeriod"
                  @goto-period="gotoPeriod"
              ></TimelineBreadcrumbs>
              <span v-if="!showTimelineView" v-html="'&nbsp;'"></span><!-- for spacing -->
            </div>

            <div class="toggles">
              <span class="toggle" :class="{expanded: showFullView}" @click="showFullView = !showFullView" :title="(showTimelineView ? _('show calendar'):_('hide calendar'))">
                <img src="/static/calendar-icon.png" />
              </span>
              <span class="toggle" :class="{expanded: showTimelineView}" @click="showTimelineView = !showTimelineView" :title="(showTimelineView ? _('show timeline'):_('hide timeline'))">
                <img src="/static/timeline-icon.png" />
              </span>
            </div>
          </div>
          <Timeline
                  v-if="currentPeriod && showTimelineView"
                  :period="currentPeriod"
                  :highlight="timelineHighlight"
                  :current-snapshot="currentSnapshot"
                  :max-zoom-level="maxTimelineZoomLevel"
                  @goto-period="gotoPeriod"
          ></Timeline>
        </div>
      </div>
    </div>
    <div class="snapshot-title">
      <form @submit="gotoUrl">
        <input id="theurl" type="text" :value="config.url"></input>
      </form>
      <div v-if="currentSnapshot && !showFullView">
        <span v-if="config.title">{{ config.title }}</span>
        {{_('Current Capture')}}: {{currentSnapshot.getTimeDateFormatted()}}
      </div>
    </div>
    <CalendarYear v-if="showFullView && currentPeriod && currentPeriod.children.length"
                  :period="currentPeriod"
                  :current-snapshot="currentSnapshot"
                   @goto-period="gotoPeriod">
    </CalendarYear>
  </div>
</template>

<script>
import Timeline from "./components/Timeline.vue";
import TimelineBreadcrumbs from "./components/TimelineBreadcrumbs.vue";
import CalendarYear from "./components/CalendarYear.vue";

import { PywbSnapshot, PywbPeriod } from "./model.js";
import {PywbI18N} from "./i18n";

export default {
  name: "PywbReplayApp",
  //el: '[data-app="webrecorder-replay-app"]',
  data: function() {
    return {
      snapshots: [],
      currentPeriod: null,
      currentSnapshot: null,
      msgs: [],
      showFullView: true,
      showTimelineView: true,
      maxTimelineZoomLevel: PywbPeriod.Type.day,
      config: {
        title: "",
        initialView: {}
      },
      timelineHighlight: false,
    };
  },
  components: {Timeline, TimelineBreadcrumbs, CalendarYear},
  mounted: function() {
  },
  computed: {
    sessionStorageUrlKey() {
      // remove http(s), www and trailing slash
      return 'zoom__' + this.config.url.replace(/^https?:\/\/(www\.)?/, '').replace(/\/$/, '');
    }
  },
  methods: {
    _(id, embeddedVariableStrings=null) {
      return PywbI18N.instance.getText(id, embeddedVariableStrings);
    },
    gotoPeriod: function(newPeriod, onlyZoomToPeriod) {
      if (this.timelineHighlight) {
        setTimeout((() => {
          this.timelineHighlight=false;
        }).bind(this), 3000);
      }
      // only go to snapshot if caller did not request to zoom only
      if (newPeriod.snapshot && !onlyZoomToPeriod) {
        this.gotoSnapshot(newPeriod.snapshot, newPeriod);
      } else {
        // save current period (aka zoom)
        // use sessionStorage (not localStorage), as we want this to be a very temporary memory for current page tab/window and no longer; NOTE: it serves when navigating from an "*" query to a specific capture and subsequent reloads
        if (window.sessionStorage) {
          window.sessionStorage.setItem(this.sessionStorageUrlKey, newPeriod.fullId);
        }
        // If new period goes beyond allowed max level
        if (newPeriod.type > this.maxTimelineZoomLevel) {
          this.currentPeriod = newPeriod.get(this.maxTimelineZoomLevel);
        } else {
          this.currentPeriod = newPeriod;
        }
      }
    },
    gotoSnapshot(snapshot, fromPeriod) {
      this.currentSnapshot = snapshot;

      // if the current period is not matching the current snapshot, updated it!
      if (fromPeriod && !this.currentPeriod.contains(fromPeriod)) {
        const fromPeriodAtMaxZoomLevel = fromPeriod.get(this.maxTimelineZoomLevel);
        if (fromPeriodAtMaxZoomLevel !== this.currentPeriod) {
          this.currentPeriod = fromPeriodAtMaxZoomLevel;
        }
      }

      // COMMUNICATE TO ContentFrame
      this.$emit("show-snapshot", snapshot);
      this.showFullView = false;
    },
    gotoUrl(event) {
      event.preventDefault();
      const newUrl = document.querySelector("#theurl").value;
      if (newUrl !== this.url) {
        window.location.href = this.config.prefix + "*/" + newUrl;
      }
    },
    setData(/** @type {PywbData} data */ data) {

      // data-set will usually happen at App INIT (from parent caller)
      this.$set(this, "snapshots", data.snapshots);
      this.$set(this, "currentPeriod", data.timeline);

      // get last-saved current period from previous page/app refresh (if there was such)
      if (window.sessionStorage) {
        const currentPeriodId = window.sessionStorage.getItem(this.sessionStorageUrlKey);
        if (currentPeriodId) {
          const newCurrentPeriodFromStorage = this.currentPeriod.findByFullId(currentPeriodId);
          if (newCurrentPeriodFromStorage) {
            this.currentPeriod = newCurrentPeriodFromStorage;
          }
        }
      }

      // signal app is DONE setting and rendering data; ON NEXT TICK
      this.$nextTick(function isDone() {
        this.$emit('data-set-and-render-completed');
      }.bind(this));
    },
    setSnapshot(view) {
      // turn off calendar (aka full) view
      this.showFullView = false;

      // convert to snapshot object to support proper rendering of time/date
      const snapshot = new PywbSnapshot(view, 0);

      // set config current URL and title
      this.config.url = view.url;
      this.config.title = view.title;

      this.gotoSnapshot(snapshot);
    }
  }
};
</script>

<style>
  .app {
    font-family: Calibri, Arial, sans-serif;
    border-bottom: 1px solid lightcoral;
    width: 100%;
  }
  .app.expanded {
    height: 150px;
  }
  .full-view {
    /*position: fixed;*/
    /*top: 150px;*/
    left: 0;
  }
  .iframe iframe {
    width: 100%;
    height: 80vh;
  }
  .logo {
    margin-right: 30px;
    width: 180px;
  }
  .banner {
    width: 100%;
    max-width: 1200px; /* limit width */
    position: relative;
  }
  .banner .line {
    display: flex;
    justify-content: flex-start;
  }

  .banner .logo {
    flex-shrink: initial;
    /* for any content/image inside the logo container */
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .banner .logo img {
    flex-shrink: 1;
  }

  .banner .timeline-wrap {
    flex-grow: 2;
    overflow-x: hidden;
    text-align: left;
    margin: 0 25px;
    position: relative;
  }

  .timeline-wrap .line .breadcrumbs-wrap {
    display: inline-block;
    flex-grow: 1;
  }
  .timeline-wrap .line .toggles {
    display: inline-block;
    flex-shrink: 1;
  }

  .toggles > .toggle {
    display: inline-block;
    border-radius: 5px;
    padding: 0 4px;
    height: 100%;
    cursor: zoom-in;
  }
  .toggles > .toggle > img {
    height: 18px;
    display: inline-block;
    margin-top: 2px;
  }
  .toggles .toggle:hover {
    background-color: #eeeeee;
  }
  .toggles .toggle.expanded {
    background-color: #eeeeee;
    cursor: zoom-out;
  }
  .snapshot-title {
    text-align: center;
    font-weight: bold;
    font-size: 16px;
  }
  #theurl {
    width: 400px;
  }
</style>
