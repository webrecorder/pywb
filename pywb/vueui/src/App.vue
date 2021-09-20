<template>
  <div class="app" data-app="webrecorder-replay-app">
    <div class="banner">
      <div class="line">
        <div class="logo"><img :src="config.logoImg" /></div>
        <div class="timeline-wrap">
          <div class="line">
            <TimelineBreadcrumbs
                    v-if="currentPeriod"
                    :period="currentPeriod"
                    @goto-period="gotoPeriod"
                    class="breadcrumbs"
            ></TimelineBreadcrumbs>

            <div class="toggles">
              <span class="toggle" :class="{expanded: showFullView}" @click="showFullView = !showFullView">
                <template v-if="!showFullView"><span class="detail">show year calendar</span></template><template v-else><span class="detail">hide year calendar</span></template>
                <img src="/static/calendar-icon.png" />
              </span>
            </div>
          </div>
          <Timeline
                  v-if="currentPeriod"
                  :period="currentPeriod"
                  :highlight="timelineHighlight"
                  @goto-period="gotoPeriod"
          ></Timeline>
        </div>
      </div>
    </div>
    <div class="snapshot-title">
      <div>{{ config.url }}</div>
      <div v-if="currentSnapshot && !showFullView">
        <span v-if="config.title">{{ config.title }}</span>
        {{currentSnapshot.getTimeDateFormatted()}}
      </div>
    </div>
    <CalendarYear v-if="showFullView"
                   :period="currentPeriod"
                   @goto-period="gotoPeriod">
    </CalendarYear>
  </div>
</template>

<script>
import Timeline from "./components/Timeline.vue";
import TimelineBreadcrumbs from "./components/TimelineBreadcrumbs.vue";
import CalendarYear from "./components/CalendarYear.vue";

import { PywbSnapshot } from "./model.js";

export default {
  name: "PywbReplayApp",
  //el: '[data-app="webrecorder-replay-app"]',
  data: function() {
    return {
      snapshots: [],
      currentPeriod: null,
      currentSnapshot: null,
      msgs: [],
      showFullView: false,
      config: {
        title: "",
        initialView: {}
      },
      timelineHighlight: false
    };
  },
  components: {Timeline, TimelineBreadcrumbs, CalendarYear},
  mounted: function() {
    this.init();
  },
  methods: {
    gotoPeriod: function(newPeriod/*, initiator*/) {
      if (this.timelineHighlight) {
        setTimeout((() => {
          this.timelineHighlight=false;
        }).bind(this), 3000);
      }
      if (newPeriod.snapshot) {
        this.gotoSnapshot(newPeriod.snapshot);
      } else {
        // save current period (aka zoom)
        // use sessionStorage (not localStorage), as we want this to be a very temporary memory for current page tab/window and no longer; NOTE: it serves when navigating from an "*" query to a specific capture and subsequent reloads
        if (window.sessionStorage) {
          window.sessionStorage.setItem('zoom__'+this.config.url, newPeriod.getFullId());
        }
        this.currentPeriod = newPeriod;
      }
    },
    gotoSnapshot(snapshot) {
      this.currentSnapshot = snapshot;
      // COMMUNICATE TO ContentFrame
      this.$emit("show-snapshot", snapshot);
      this.showFullView = false;
    },
    init() {
      this.config.url = this.config.initialView.url;
      if (this.config.initialView.title) {
        this.config.title = this.config.initialView.title;
      }
      if (this.config.initialView.timestamp === undefined) {
        this.showFullView = true;
      } else {
        this.showFullView = false;
        this.setSnapshot(this.config.initialView);
      }
      if (window.sessionStorage) {
        const currentPeriodId = window.sessionStorage.getItem('zoom__'+this.config.url);
        if (currentPeriodId) {
          const newCurrentPeriodFromStorage = this.currentPeriod.findByFullId(currentPeriodId);
          if (newCurrentPeriodFromStorage) {
            this.currentPeriod = newCurrentPeriodFromStorage;
          }
        }
      }
    },
    setSnapshot(view) {
      // convert to snapshot objec to support proper rendering of time/date
      const snapshot = new PywbSnapshot(view, 0);
      this.config.url = view.url;
      this.config.title = view.title;
      this.gotoSnapshot(snapshot);
    }
  }
};
</script>

<style>
  .app {
    border-bottom: 1px solid lightcoral;
    height: 150px;
    width: 100%;
  }
  .full-view {
    position: fixed;
    top: 150px;
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

  .timeline-wrap .line .breadcrumbs {
    display: inline-block;
    flex-grow: 1;
  }
  .timeline-wrap .line .toggles {
    display: inline-block;
    flex-shrink: 1;
  }

  .toggles .toggle {
    border-radius: 5px;
    padding: 4px;
    cursor: zoom-in;
  }
  .toggles .toggle img {
    width: 17px;
    display: inline-block;
    margin-top: 2px;
  }
  .toggles .toggle:hover {
    background-color: #eeeeee;
  }
  .toggles .toggle .detail {
    display: none;
  }
  .toggles .toggle:hover .detail {
    display: inline;
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
</style>
