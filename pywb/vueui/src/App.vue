<template>
  <div class="app" data-app="webrecorder-replay-app">
    <div class="short-nav">
      <div class="first-line">
        <div class="logo"><img :src="config.logoImg" /></div>
        <div class="url-and-timeline">
          <div class="url">
            <strong>{{config.title}}</strong> ({{snapshots.length}} captures: {{snapshots[0].getDateFormatted()}} - {{snapshots[snapshots.length-1].getDateFormatted()}})<br/>
            <TimelineSummary
                    v-if="currentPeriod"
                    :period="currentPeriod"
                    @goto-period="gotoPeriod"
            ></TimelineSummary>
            <span class="full-view-toggle" :class="{expanded: showFullView}" @click="showFullView = !showFullView">
              <template v-if="!showFullView"><span class="detail">show year calendar</span></template><template v-else><span class="detail">hide year calendar</span></template>
              <img src="/static/calendar-icon.png" />
            </span>
          </div>
          <Timeline
                  v-if="currentPeriod"
                  :period="currentPeriod"
                  :highlight="timelineHighlight"
                  @goto-period="gotoPeriod"
          ></Timeline>
        </div>
      </div>
      <div class="second-line" v-if="currentSnapshot && !showFullView">
        <h2>Showing Capture from {{currentSnapshot.getTimeDateFormatted()}}</h2>
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
import TimelineSummary from "./components/Summary.vue";
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
  components: {Timeline, TimelineSummary, CalendarYear},
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
      if (!this.config.title) {
        this.config.title = this.config.initialView.url;
      }
      if (this.config.initialView.timestamp === undefined) {
        this.showFullView = true;
      } else {
        this.showFullView = false;
        this.setSnapshot(this.config.initialView);
      }
    },
    setSnapshot(view) {
      // convert to snapshot objec to support proper rendering of time/date
      const snapshot = new PywbSnapshot(view, 0);
      this.config.title = view.url;
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
  .iframe iframe {
    width: 100%;
    height: 80vh;
  }
  .logo {
    margin-right: 30px;
    width: 180px;
  }
  .short-nav {
    width: 100%;
    position: relative;
  }
  .short-nav .first-line {
    display: flex;
    justify-content: flex-start;
  }
  .short-nav .second-line {
    display: flex;
    justify-content: flex-start;
  }

  .short-nav .logo {
    flex-shrink: initial;
  }

  .short-nav .url-and-timeline {
    flex-grow: 2;
    overflow-x: hidden;
  }

  .short-nav .url {
    text-align: left;
    margin: 0 25px;
    position: relative;
  }

  .full-view-toggle {
    position: absolute;
    top: 0;
    right: 0;
    border-radius: 5px;
    padding: 4px;
    cursor: zoom-in;
  }
  .full-view-toggle img {
    width: 17px;
    display: inline-block;
    margin-top: 2px;
  }
  .full-view-toggle:hover {
    background-color: #eeeeee;
  }
  .full-view-toggle .detail {
    display: none;
  }
  .full-view-toggle:hover .detail {
    display: inline;
  }
  .full-view-toggle.expanded {
    background-color: #eeeeee;
    cursor: zoom-out;
  }
</style>
