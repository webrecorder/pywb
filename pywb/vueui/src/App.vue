<template>
  <div class="app" :class="{expanded: showTimelineView || showFullView }" data-app="webrecorder-replay-app">
    <!-- Top navbar -->
    <nav
      class="navbar navbar-light navbar-expand-lg fixed-top top-navbar justify-content-center"
      :style="navbarStyle">
      <a class="navbar-brand flex-grow-1 my-1" :href="config.logoHomeUrl" v-if="config.logoHomeUrl">
        <img :src="config.logoImg" id="logo-img" :alt="_('Logo')">
      </a>
      <div class="navbar-brand flex-grow-1 my-1" v-else>
        <img :src="config.logoImg" id="logo-img" :alt="_('Logo')">
      </div>
      <div class="flex-grow-1 d-flex" id="searchdiv">
        <form
          class="form-inline my-2 my-md-0 mx-lg-auto"
          role="search"
          @submit="gotoUrl">
          <input
            id="theurl"
            type="text"
            :value="config.url"
            height="31"
            :aria-label="_('Search for archival capture of URL')"
            :title="_('Search for archival capture of URL')"></input>
        </form>
      </div>
      <button
        class="navbar-toggler btn btn-sm"
        id="collapse-button"
        type="button"
        data-toggle="collapse"
        data-target="#navbarCollapse"
        aria-controls="navbarCollapse"
        aria-expanded="false"
        :aria-label="_('Toggle navigation')">
        <span class="navbar-toggler-icon"></span>
      </button>
      <div class="collapse navbar-collapse ml-auto" id="navbarCollapse">
        <ul class="navbar-nav ml-3" id="toggles">
          <li class="nav-item">
            <button
              class="btn btn-sm"
              :class="{active: showFullView, 'btn-outline-light': lightButtons, 'btn-outline-dark': !lightButtons}"
              :title="_('Previous capture')"
              v-if="previousSnapshot"
              @click="gotoPreviousSnapshot">
              <i class="fas fa-arrow-left" :title="_('Previous capture')"></i>
            </button>
          </li>
          <li class="nav-item">
            <button
              class="btn btn-sm"
              :class="{active: showFullView, 'btn-outline-light': lightButtons, 'btn-outline-dark': !lightButtons}"
              :title="_('Next capture')"
              v-if="nextSnapshot"
              @click="gotoNextSnapshot">
              <i class="fas fa-arrow-right" :title="_('Next capture')"></i>
            </button>
          </li>
          <li class="nav-item active">
            <button
              class="btn btn-sm"
              :class="{active: showFullView, 'btn-outline-light': lightButtons, 'btn-outline-dark': !lightButtons}"
              :aria-pressed="(showFullView ? true : false)"
              @click="showFullView = !showFullView"
              :title="(showFullView ? _('Hide calendar') : _('Show calendar'))">
              <i class="far fa-calendar-alt"></i>
            </button>
          </li>
          <li class="nav-item">
            <button
              class="btn btn-sm"
              :class="{active: showTimelineView, 'btn-outline-light': lightButtons, 'btn-outline-dark': !lightButtons}"
              :aria-pressed="showTimelineView"
              @click="toggleTimelineView"
              :title="(showTimelineView ? _('Hide timeline') : _('Show timeline'))">
              <i class="far fa-chart-bar"></i>
            </button>
          </li>
          <li class="nav-item">
            <button
              class="btn btn-sm"
              :class="{'btn-outline-light': lightButtons, 'btn-outline-dark': !lightButtons}"
              :aria-pressed="printReplayFrame"
              @click="printReplayFrame"
              v-if="printingEnabled && hasReplayFrame()"
              :title="_('Print')">
              <i class="fas fa-print"></i>
            </button>
          </li>
          <li class="nav-item dropdown" v-if="localesAreSet">
            <button
              class="btn btn-sm dropdown-toggle"
              :class="{'btn-outline-light': lightButtons, 'btn-outline-dark': !lightButtons}"
              type="button"
              id="locale-dropdown"
              data-toggle="dropdown"
              aria-haspopup="true"
              aria-expanded="false"
              :title="_('Select language')">
              <i class="fas fa-globe-africa" :title="_('Language:')"></i>
            </button>
            <div class="dropdown-menu dropdown-menu-right" aria-labelledby="locale-dropdown">
              <a
                class="dropdown-item"
                v-for="(locPath, key) in config.allLocales"
                :key="key"
                :href="locPath + (currentSnapshot ? currentSnapshot.id : '*') + '/' + config.url">
                {{ key }}
              </a>
            </div>
          </li>
        </ul>
      </div>
    </nav>

    <!-- Capture title and date -->
    <nav
      class="navbar navbar-light justify-content-center title-nav fixed-top"
      id="second-navbar"
      :style="navbarStyle">
      <span class="hidden" v-if="!currentSnapshot">&nbsp;</span>
      <span v-if="currentSnapshot">
        <span class="strong mr-1">
          {{_('Current Capture')}}: 
          <span class="ml-1" v-if="config.title">
            {{ config.title }}
          </span>
        </span>
        <span class="mr-1" v-if="config.title">|</span>
        {{currentSnapshot.getTimeDateFormatted()}}
      </span>
    </nav>

    <!-- Timeline -->
    <div class="card border-top-0 border-left-0 border-right-0 timeline-wrap">
      <div class="card-body" v-if="currentPeriod && showTimelineView">
        <div class="row">
          <div class="col col-12">
            <TimelineBreadcrumbs
              :period="currentPeriod"
              @goto-period="gotoPeriod"
            ></TimelineBreadcrumbs>
          </div>
          <div class="col col-12 mt-2">
            <Timeline
              :period="currentPeriod"
              :highlight="timelineHighlight"
              :current-snapshot="currentSnapshot"
              :max-zoom-level="maxTimelineZoomLevel"
              @goto-period="gotoPeriod"
            ></Timeline>
          </div>
        </div>
      </div>    
    </div>

    <!-- Calendar -->
    <div class="card" id="calendar-card" v-if="currentPeriod && showFullView && currentPeriod.children.length">
      <div class="card-body" id="calendar-card-body">
        <CalendarYear
          :period="currentPeriod"
          :current-snapshot="currentSnapshot"
           @goto-period="gotoPeriod">
        </CalendarYear>
      </div>
    </div>
    
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
      currentSnapshotIndex: null,
      msgs: [],
      showFullView: false,
      showTimelineView: false,
      maxTimelineZoomLevel: PywbPeriod.Type.day,
      config: {
        title: "",
        initialView: {},
        allLocales: {}
      },
      timelineHighlight: false,
      locales: [],
    };
  },
  components: {Timeline, TimelineBreadcrumbs, CalendarYear},
  mounted: function() {
    // add empty unload event listener to make this page bfcache ineligible.
    // bfcache otherwises prevent the query template from reloading as expected
    // when the user navigates there via browser back/forward buttons
    addEventListener('unload', (event) => { });
  },
  updated: function() {
    // set top frame title equal to value pulled from replay frame
    document.title = this._("Archived Page: ") + this.config.title;
  },
  computed: {
    sessionStorageUrlKey() {
      // remove http(s), www and trailing slash
      return 'zoom__' + this.config.url.replace(/^https?:\/\/(www\.)?/, '').replace(/\/$/, '');
    },
    localesAreSet() {
      return Object.entries(this.config.allLocales).length > 0;
    },
    navbarStyle() {
      return {
        '--navbar-background': `#${this.config.navbarBackground}`,
        '--navbar-color': `#${this.config.navbarColor}`
      }
    },
    lightButtons() {
      return !!this.config.navbarLightButtons;
    },
    printingEnabled() {
      return !this.config.disablePrinting;
    },
    previousSnapshot() {
      if (!this.currentSnapshotIndex) {
        return null;
      }
      if (this.currentSnapshotIndex > 0) {
        return this.snapshots[this.currentSnapshotIndex - 1];
      }
      return null;
    },
    nextSnapshot() {
      if (this.currentSnapshotIndex == null) {
        return null;
      }
      if (
        (this.currentSnapshotIndex >= 0)
        && (this.currentSnapshotIndex !== this.snapshots.length - 1)) {
        return this.snapshots[this.currentSnapshotIndex + 1];
      }
      return null;
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
        this.gotoSnapshot(newPeriod.snapshot, newPeriod, true /* reloadIFrame */);
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
    gotoSnapshot(snapshot, fromPeriod, reloadIFrame=false) {
      this.currentSnapshot = snapshot;

      const isCurrentSnapshot = (snapshotInArray) => snapshotInArray.id == snapshot.id && snapshotInArray.url == snapshot.url;
      this.currentSnapshotIndex = this.snapshots.findIndex(isCurrentSnapshot);

      // if the current period doesn't match the current snapshot, update it
      if (!this.currentPeriod || (fromPeriod && !this.currentPeriod.contains(fromPeriod))) {
        const fromPeriodAtMaxZoomLevel = fromPeriod.get(this.maxTimelineZoomLevel);
        if (!this.currentPeriod || fromPeriodAtMaxZoomLevel !== this.currentPeriod) {
          this.currentPeriod = fromPeriodAtMaxZoomLevel;
        }
      }

      // update iframe only if the snapshot was selected from the calendar/timeline.
      // if the change originated from a user clicking a link in the iframe, emitting
      // snow-shapshot will only cause a flash of content
      if (reloadIFrame !== false) {
        this.$emit("show-snapshot", snapshot);
      }
      this.initBannerState(true);
    },
    gotoPreviousSnapshot() {
      let periodToChangeTo = this.currentPeriod.findByFullId(this.previousSnapshot.getFullId());
      this.gotoPeriod(periodToChangeTo, false /* onlyZoomToPeriod */);
    },
    gotoNextSnapshot() {
      let periodToChangeTo = this.currentPeriod.findByFullId(this.nextSnapshot.getFullId());
      this.gotoPeriod(periodToChangeTo, false /* onlyZoomToPeriod */);
    },
    gotoUrl(event) {
      event.preventDefault();
      const newUrl = document.querySelector("#theurl").value;
      if (newUrl !== this.config.url) {
        const ts = this.config.timestamp === undefined ? "*" : this.config.timestamp;
        window.location.href = this.config.prefix + ts + (ts ? "/" : "") + newUrl;
      }
    },
    toggleTimelineView() {
      this.showTimelineView = !this.showTimelineView;
      window.localStorage.setItem("showTimelineView", this.showTimelineView ? "1" : "0");
    },
    hasReplayFrame() {
      return !! window.frames.replay_iframe;
    },
    printReplayFrame() {
      window.frames.replay_iframe.contentWindow.focus();
      window.frames.replay_iframe.contentWindow.print();
      return false;
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
      if (!this.currentPeriod) {
        return false;
      }

      // turn off calendar (aka full) view
      this.showFullView = false;

      // convert to snapshot object to support proper rendering of time/date
      const snapshot = new PywbSnapshot(view, 0);

      this.config.url = view.url;

      let periodToChangeTo = this.currentPeriod.findByFullId(snapshot.getFullId());
      if (periodToChangeTo) {
        this.gotoPeriod(periodToChangeTo, false /* onlyZoomToPeriod */);
        return true;
      }
      return false;
    },
    initBannerState(isReplay) {
      // if not replay, always show both
      if (!isReplay) {
        this.showFullView = true;
        this.showTimelineView = true;
      } else {
        this.showFullView = false;
        this.showTimelineView = window.localStorage.getItem("showTimelineView") === "1";
      }
    },
    updateTitle(title) {
      this.config.title = title;
    }
  }
};
</script>

<style>
  body {
    padding-top: 89px !important;
  }
  .app {
    font-family: Calibri, Arial, sans-serif;
    /*border-bottom: 1px solid lightcoral;*/
    width: 100%;
  }
  .app.expanded {
    /*height: 130px;*/
    max-height: calc(100vh - 90px);
    display: flex;
    flex-direction: column;
  }
  .full-view {
    /*position: fixed;*/
    /*top: 150px;*/
    left: 0;
  }
  .navbar {
    background-color: var(--navbar-background);
    color:  var(--navbar-color);
  }
  .top-navbar {
    z-index: 90;
    padding: 2px 16px 0 16px;
  }
  .top-navbar span.navbar-toggler-icon {
    margin: .25rem !important;
  }
  #logo-img {
    max-height: 40px;
  }
  .title-nav {
    margin-top: 50px;
    z-index: 80;
  }
  #secondNavbar {
    height: 24px !important;
  }
  #navbarCollapse {
    justify-content: right;
  }
  #navbarCollapse ul#toggles {
    display: flex;
    align-content: center;
  }
  #navbarCollapse:not(.show) ul#toggles li:not(:first-child) {
    margin-left: .25rem;
  }
  #navbarCollapse.show {
    padding-bottom: 1em;
  }
  #navbarCollapse.show ul#toggles li {
    margin-top: 5px;
  }
  #navbarCollapse.show ul#toggles li {
    margin-left: 0px;
  }
  .iframe iframe {
    width: 100%;
    height: 80vh;
  }
  #searchdiv {
    height: 31px;
  }
  #theurl {
    width: 250px;
  }
  @media (min-width: 576px) {
    #theurl {
      width: 350px;
    }
  }
  @media (min-width: 768px) {
    #theurl {
      width: 500px;
    }
  }
  @media (min-width: 992px) {
    #theurl {
      width: 600px;
    }
  }
  @media (min-width: 1200px) {
    #theurl {
      width: 900px;
    }
  }
  #toggles {
    align-items: center;
  }
  .breadcrumb-row {
    display: flex;
    align-items: center;
    justify-content: center;
  }
  div.timeline-wrap div.card {
    margin-top: 55px;
  }
  #calendar-card {
    overflow-y: auto;
    max-height: 100%;
  }
  div.timeline-wrap div.card-body {
    display: flex;
    align-items: center;
    justify-content: center;
  }
  div.timeline-wrap div.card-body div.row {
    width: 100%;
    align-items: center;
    justify-content: center;
  }

  #calendar-card-body {
    padding: 0;
  }
  .strong {
    font-weight: bold;
  }
  .hidden {
    color: var(--navbar-background);
  }
</style>
