<template>
  <div class="full-view border-top-0 border-left-0 border-right-0 border-bottom border-dark shadow">
    <h2>
      <i
        class="fas fa-arrow-left year-arrow"
        @click="gotoPreviousYear"
        @keyup.enter="gotoPreviousYear"
        v-if="previousYear"
        tabindex="0"></i>
      <span class="mx-1">
      {{year.id}} ({{ $root._(year.snapshotCount !== 1 ? '{count} captures':'{count} capture', {count: year.snapshotCount}) }})
      </span>
      <i
        class="fas fa-arrow-right year-arrow"
        @click="gotoNextYear"
        @keyup.enter="gotoNextYear"
        v-if="nextYear"
        tabindex="0"></i>
    </h2>
    <div class="months">
      <CalendarMonth
        v-for="month in year.children"
        :key="month.id"
        :month="month"
        :year="year"
        :current-snapshot="containsCurrentSnapshot ? currentSnapshot : null"
        :is-current="month === currentMonth"
        @goto-period="$emit('goto-period', $event)"
        @show-day-timeline="setCurrentTimeline"
      ></CalendarMonth>
    </div>
    <Tooltip
      :position="currentTimelinePos"
      v-if="currentTimelinePeriod"
      ref="timelineLinearTooltip">
      <TimelineLinear
        :period="currentTimelinePeriod"
        :current-snapshot="containsCurrentSnapshot ? currentSnapshot : null"
        @goto-period="gotoPeriod"
      ></TimelineLinear>
    </Tooltip>
  </div>
</template>

<script>
import CalendarMonth from "./CalendarMonth.vue";
import TimelineLinear from "./TimelineLinear.vue";
import Tooltip from "./Tooltip.vue";
import { PywbPeriod } from "../model.js";

export default {
  components: {CalendarMonth, TimelineLinear, Tooltip},
  props: ["period", "currentSnapshot"],
  data: function() {
    return {
      firstZoomLevel: PywbPeriod.Type.day,
      currentTimelinePeriod: null,
      currentTimelinePos: '0,0'
    };
  },
  mounted() {
    document.querySelector('body').addEventListener('click', this.resetCurrentTimeline);
  },
  computed: {
    year() { // the year that the timeline period is in
      let year = null;
      // if timeline is showing all year
      if (this.period.type === PywbPeriod.Type.all) {
        // if no current snapshot => pick the LAST YEAR
        if (!this.currentSnapshot) {
          year = this.period.children[this.period.children.length-1];
        } else {
          year = this.period.findByFullId(String(this.currentSnapshot.year));
        }
      } else if (this.period.type === PywbPeriod.Type.year) {
        year = this.period;
      } else {
        year = this.period.getParents().filter(p => p.type === PywbPeriod.Type.year)[0];
      }
      if (year) {
        year.fillEmptyChildPeriods(true);
      }
      return year;
    },
    currentYearIndex() {
      if (this.year.parent) {
        return this.year.parent.children.findIndex(year => year.fullId === this.year.fullId);
      }
    },
    previousYear() {
      return this.year.getPrevious();
    },
    nextYear() {
      return this.year.getNext();
    },
    currentMonth() { // the month that the timeline period is in
      let month = null;
      if (this.period.type === PywbPeriod.Type.month) {
        month = this.period;
      } else {
        month = this.period.getParents().filter(p => p.type === PywbPeriod.Type.month)[0];
      }
      return month;
    },
    containsCurrentSnapshot() {
      return this.currentSnapshot &&
        this.year.contains(this.currentSnapshot);
    }
  },
  methods: {
    gotoPreviousYear() {
      this.gotoPeriod(this.previousYear, true /* changeYearOnly */);
    },
    gotoNextYear() {
      this.gotoPeriod(this.nextYear, true /* changeYearOnly */);
    },
    resetCurrentTimeline(event) {
      if (event && this.$refs.timelineLinearTooltip) {
        let el = event.target;
        let clickWithinTooltip = false;
        while(el.parentElement) {
          if (el === this.$refs.timelineLinearTooltip.$el) {
            clickWithinTooltip = true;
            break;
          }
          el = el.parentElement;
        }
        if (!clickWithinTooltip) {
          this.currentTimelinePeriod = null;
        }
      }
    },
    setCurrentTimeline(day, event) {
      this.currentTimelinePeriod = day;
      if (!day) {
        return;
      }
      if (event.code === "Enter") {
        let middleXPos = (window.innerWidth / 2) - 60;
        this.currentTimelinePos = `${middleXPos},200`;
      } else {
        this.currentTimelinePos = `${event.x},${event.y}`;
      }
      
      event.stopPropagation();
      event.preventDefault();
    },
    gotoPeriod(period, changeYearOnly=false) {
      if (period.snapshot || period.snapshotPeriod || changeYearOnly) {
        this.$emit('goto-period', period);
      } else {
        this.currentTimelinePeriod = period;
      }
    },

  }
};
</script>

<style scoped>
  .full-view {
    display: flex;
    flex: 1;
    flex-wrap: wrap;
    z-index: 10;
    overflow-y: scroll;
    width: 100%;
    background-color: white;
    padding-bottom: 1em;
    justify-content: center;
  }
  .full-view .months {
    display: flex;
    justify-content: center;
    flex-wrap: wrap;
    align-items: flex-start;
  }
  .full-view h2 {
    margin: 10px 0;
    font-size: 20px;
    text-align: center;
  }
  .year-arrow:hover {
    cursor: pointer;
  }
</style>
