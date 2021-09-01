<template>
    <div class="timeline">
        <div class="arrow previous" :class="{disabled: isScrollZero && !previousPeriod}" @click="scrollPrev" @dblclick.stop.prevent>&#x25C0;</div>
        <div class="scroll" ref="periodScroll" :class="{highlight: highlight}">
            <div class="periods" ref="periods">
                <div v-for="subPeriod in period.children"
                     :key="subPeriod.id"
                     class="period"
                     :class="{empty: !subPeriod.snapshotCount, highlight: highlightPeriod === subPeriod, 'last-level': isLastZoomLevel}"
                     v-on:click="changePeriod(subPeriod)">
                    <div class="histo">
                        <div class="count" v-if="!subPeriod.snapshot && !isLastZoomLevel"><span class="count-inner">{{subPeriod.snapshotCount}}</span></div>
                        <div class="line"
                             v-for="histoPeriod in subPeriod.children"
                             :key="histoPeriod.id"
                             :style="{height: getHistoLineHeight(histoPeriod.snapshotCount)}"
                             v-on:click="changePeriodFromHistogram(histoPeriod)"
                        >
                            <div class="snap-info" v-if="isLastZoomLevel">{{histoPeriod.snapshot.getTimeDateFormatted()}}</div>
                        </div>
                    </div>
                    <div class="inner">
                        <div class="label">{{subPeriod.getReadableId()}}</div>
                    </div>
                </div>
            </div>
        </div>
        <div class="arrow next" :class="{disabled: isScrollMax && !nextPeriod}" @click="scrollNext" @dblclick.stop.prevent>&#x25B6;</div>
    </div>
</template>

<script>
import { PywbPeriod } from "../model.js";

export default{
  props: ["period", "highlight"],
  data: function() {
    return {
      // TODO: remove widths (now using flex css for width calculation)
      subPeriodBoxWidths: {// in pixels
        [PywbPeriod.Type.year]: 80, // year box
        [PywbPeriod.Type.month]: 80, // month box in year
        [PywbPeriod.Type.day]: 20, // days box in month
        [PywbPeriod.Type.hour]: 60, // hour box in day
        [PywbPeriod.Type.snapshot]: 10 // snapshot box in hour/day
      },
      // TODO: remove widths (now using flex css for width calculation)
      emptySubPeriodBoxWidths: {// in pixels
        [PywbPeriod.Type.year]: 40, // year box
        [PywbPeriod.Type.month]: 40, // month box in year
        [PywbPeriod.Type.day]: 20, // days box in month
        [PywbPeriod.Type.hour]: 40, // hour box in day
        [PywbPeriod.Type.snapshot]: 20 // snapshot box in hour/day
      },
      highlightPeriod: null,
      previousPeriod: null,
      nextPeriod: null,
      isScrollZero: true,
      isScrollMax: true,
    };
  },
  created: function() {
    this.addEmptySubPeriods();
  },
  mounted: function() {
    this.$refs.periods._computedStyle = window.getComputedStyle(this.$refs.periods);
    this.$refs.periodScroll._computedStyle = window.getComputedStyle(this.$refs.periodScroll);
    this.$watch("period", this.onPeriodChanged);
    // TODO: remove widths (now using flex css for width calculation), so we don't need manual calc
    //this.adjustScrollElWidth();

    this.$refs.periodScroll.addEventListener("scroll", this.updateScrollArrows);
    window.addEventListener("resize", this.updateScrollArrows);
    this.updateScrollArrows();
  },
  computed: {
    subPeriodBoxWidth: function() {
      return this.subPeriodBoxWidths[this.period.type+1]; // the type of the period children
    },
    // TODO: remove widths (now using flex css for width calculation)
    emptySubPeriodBoxWidth: function() {
      return this.emptySubPeriodBoxWidths[this.period.type+1]; // the type of the period children
    },
    // this determins which the last zoom level is before we go straight to showing snapshot
    isLastZoomLevel() {
      return this.period.type === PywbPeriod.Type.day;
    }
  },
  updated() {
    // do something on update
  },
  methods: {
    addEmptySubPeriods() {
      this.period.fillEmptyChildPeriods(true);
    },
    updateScrollArrows() {
      this.period.scroll = this.$refs.periodScroll.scrollLeft;
      const maxScroll = parseInt(this.$refs.periods._computedStyle.width) - parseInt(this.$refs.periodScroll._computedStyle.width);
      this.isScrollZero = !this.period.scroll; // if 0, then true (we are at scroll zero)
      this.isScrollMax = Math.abs(maxScroll - this.period.scroll) < 5;
    },
    restoreScroll() {
      this.$refs.periodScroll.scrollLeft = this.period.scroll;
    },
    scrollNext: function () {
      if (this.isScrollMax) {
        if (this.nextPeriod) {
          this.$emit("goto-period", this.nextPeriod);
        }
      } else {
        this.$refs.periodScroll.scrollLeft += 30;
      }
    },
    scrollPrev: function () {
      if (this.isScrollZero) {
        if (this.previousPeriod) {
          this.$emit("goto-period", this.previousPeriod);
        }
      } else {
        this.$refs.periodScroll.scrollLeft -= 30;
      }
    },
    getTimeFormatted: function(date) {
      return (date.hour < 13 ? date.hour : (date.hour % 12)) + ":" + ((date.minute < 10 ? "0":"")+date.minute) + " " + (date.hour < 12 ? "am":"pm");
    },
    getHistoLineHeight: function(value) {
      const percent = Math.ceil((value/this.period.maxGrandchildSnapshotCount) * 100);
      return (percent ? (5 + Math.ceil(percent*.95)) : 0) + "%";
      // return percent + '%';
    },
    changePeriod(period) {
      if (period.snapshotCount) {
        if (this.isLastZoomLevel) {
          if (period.type === PywbPeriod.Type.snapshot) {
            this.$emit("goto-period", period);
          }
        } else {
          this.$emit("goto-period", period);
        }
      }
    },
    // special "change period" from histogram lines
    changePeriodFromHistogram(period) {
      if (this.isLastZoomLevel && period.type === PywbPeriod.Type.snapshot) {
        this.$emit("goto-period", period);
      }
    },
    onPeriodChanged(newPeriod, oldPeriod) {
      this.addEmptySubPeriods();
      this.previousPeriod = this.period.getPrevious();
      this.nextPeriod = this.period.getNext();

      // detect if going up level of period (new period type should be in old period parents)
      if (oldPeriod.type - newPeriod.type > 0) {
        let highlightPeriod = oldPeriod;
        for (let i=oldPeriod.type - newPeriod.type; i > 1; i--) {
          highlightPeriod = highlightPeriod.parent;
        }
        this.highlightPeriod = highlightPeriod;
        setTimeout((function() {
          this.highlightPeriod = null;
        }).bind(this), 2000);
      }
      setTimeout((function() {
        // TODO: remove widths (now using flex css for width calculation), so we don't need manual calc
        //this.adjustScrollElWidth();
        this.restoreScroll();
        this.updateScrollArrows();
      }).bind(this), 1);
    },
    // TODO: remove widths (now using flex css for width calculation), so we don't need manual calc
    adjustScrollElWidth() {
      //this.$refs.periodScroll.style.maxWidth = this.$refs.periods._computedStyle.width;
    }
  }
};
</script>


<style>
    .timeline {
        position: relative;
        display: flex;
        width: auto;
        height: 80px;
        margin: 5px;
        justify-content: left;
    }

    .timeline .id {
        display: inline-block;
        font-size: 30px;
    }
    .timeline .arrow {
        display: inline-block;
        width: 20px;
        font-size: 20px; /* font-size = width of arrow, as it UTF char */
        line-height: 80px;
        vertical-align: top;
        cursor: pointer;
    }
    .timeline .arrow.previous {
    }
    .timeline .arrow.next {
    }
    .timeline .arrow.disabled, .timeline .arrow.disabled:hover {
        color: lightgray;
        background-color: transparent;
        cursor: not-allowed;
    }
    .timeline .arrow:hover {
        background-color: antiquewhite;
        color: firebrick;
    }

    .timeline .scroll {
        position: relative;
        display: inline-block;
        width: 100%; /* */
        height: 100%;

        /* maker scrollable horizontally */
        overflow-x: scroll;
        overflow-y: hidden;
        white-space: nowrap;
        scroll-behavior: smooth;

        text-align: center;

        transition: background-color 500ms ease-in;
    }
    /* hide scroll bar */
    .timeline .scroll::-webkit-scrollbar {
        display: none;
    }
    /* highlight the scroll period: usually triggered from root app */
    .timeline .scroll.highlight {
        background-color: #fff7ce;
    }
    .timeline .scroll .periods {
        display: flex;
        justify-content: space-between;
        height: 100%;
        width: 100%;
        min-width: 600px;
    }


    .timeline .period {
        flex-grow: 1;
        position: relative;
        display: inline-block;
        height: 100%;
        /* line-height: 80px; /* use to center middle vertically */
        white-space: normal;
        vertical-align: top;
        text-align: center;
        /*background-color: #eee;*/
        /*border-right: 1px solid white; !* all other periods have right border, except first period*!*/
        cursor: pointer;

        transition: background-color 500ms ease-in-out;
    }
    /* 1st period period child el */
    .timeline .period:nth-child(1) {
        /*border-left: 1px solid white; !* has left border; all other periods have right border *!*/
    }

    .timeline .period:hover {
        background-color: #eeeeee;
    }

    /* empty period */
    .timeline .period.empty {
        color: #aaa;
        /*background-color: transparent;*/
    }
    /* highlighted period */
    .timeline .period.highlight {
        background-color: cyan;
    }

    .timeline .period .label {
        font-weight: bold;
        font-size: 14px;
        font-family: Baskerville, sans-serif;
    }
    .timeline .period .count {
        position: absolute;
        top: 0;
        left: 0;
        display: none;
        width: 100%;
        height: 100%;
        padding: 10px 0 0 0;
        text-align: center;
        font-size: 25px;
    }
    .timeline .period .count .count-inner {
        display: inline;
        width: auto;
        background-color: rgba(255,255,255,.85);
        padding: 1px;
        border-radius: 5px;
    }
    .timeline .period:hover .count {
        display: block;
    }
    .timeline .period .inner {
        display: block;
        position: absolute;
        bottom: 0;
        left: 0;
        width: 100%;
        height: 16px;
        background-color: white;
        border-top: 1px solid gray;
    }
    .timeline .period.last-level .inner {
        text-align: left;
    }

    .timeline .period .histo {
        display: flex;
        position: absolute;
        top: 1px;
        left: 0;
        width: 100%;
        height: 60px;
        align-items: flex-end;
        justify-content: space-between;
        text-align: left;
    }

    .timeline .period .histo .line {
        flex-grow: 1;
        display: inline-block;
        background-color: #a6cdf5;
        margin: 0;
        padding: 0;
    }

    /* Last level period histogram spaces things evenly */
    .timeline .period.last-level .histo {
        justify-content: space-around;
    }

    /* Last level period histogram lines do not grow, but are fixed width/margin */
    .timeline .period.last-level .histo .line {
        flex-grow: unset;
        width: 5px;
        margin-left: 2px;

        position: relative;
    }

        /* update line color on hover*/
        .timeline .period.last-level .histo .line:hover {
            background-color: #f5a6eb;
        }

        /*Last level period histogram line has extra info*/
        .timeline .period.last-level  .histo .line .snap-info {
            position: absolute;
            z-index: 10;
            top: 30%;
            left: 120%;
            display: none;
            background-color: white;
            border: 1px solid gray;
            padding: 2px;
            white-space: nowrap; /*no wrapping allowed*/
        }
            /*show on hover*/
            .timeline .period.last-level .histo .line:hover .snap-info {
                display: block;
            }

</style>
