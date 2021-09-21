<template>
    <div class="timeline">
        <div class="period-tooltip" v-show="tooltipPeriod" :style="{left: tooltipPeriodPos.x+'px', top: tooltipPeriodPos.y+'px'}">
            <template v-if="tooltipPeriod">
              <div v-if="tooltipPeriod.snapshot">View capture on
                {{ tooltipPeriod.snapshot.getTimeDateFormatted() }}
              </div>
              <div v-else-if="tooltipPeriod.snapshotPeriod">View capture on
                {{ tooltipPeriod.snapshotPeriod.snapshot.getTimeDateFormatted() }}
              </div>
              <div v-else-if="tooltipPeriod.snapshotCount">
                {{ tooltipPeriod.snapshotCount }} captures
                <span v-if="isTooltipPeriodDayOrHour">on</span><span v-else>in</span>
                {{ tooltipPeriod.getFullReadableId() }}
              </div>
            </template>
        </div>
        <div v-html="'&#x25C0;'" class="arrow previous" :class="{disabled: isScrollZero && !previousPeriod}" @click="scrollPrev" @dblclick.stop.prevent></div>
        <div class="scroll" ref="periodScroll" :class="{highlight: highlight}">
            <div class="periods" ref="periods">
                <div v-for="subPeriod in period.children"
                     :key="subPeriod.id"
                     class="period"
                     :class="{empty: !subPeriod.snapshotCount, highlight: highlightPeriod === subPeriod, 'last-level': isLastZoomLevel}"
                     @click="changePeriod(subPeriod, $event)"
                     @mouseover="setTooltipPeriod(subPeriod, $event)"
                     @mouseout="setTooltipPeriod(null, $event)"
                >
                    <div class="histo">
                        <div class="line"
                             v-for="histoPeriod in subPeriod.children"
                             :key="histoPeriod.id"
                             :style="{height: getHistoLineHeight(histoPeriod.snapshotCount)}"
                             :class="{'has-single-snap': !!histoPeriod.snapshotPeriod}"
                             @click="changePeriod(histoPeriod, $event)"
                             @mouseover="setTooltipPeriod(histoPeriod, $event)"
                             @mouseout="setTooltipPeriod(null, $event)"
                        >
                        </div>
                    </div>
                    <div class="inner">
                        <div class="label">
                          {{subPeriod.getReadableId()}}
                        </div>
                    </div>
                </div>
            </div>
        </div>
        <div v-html="'&#x25B6;'" class="arrow next" :class="{disabled: isScrollMax && !nextPeriod}" @click="scrollNext" @dblclick.stop.prevent></div>
    </div>
</template>

<script>
import { PywbPeriod } from "../model.js";

export default{
  props: ["period", "currentSnapshot", "highlight"],
  data: function() {
    return {
      highlightPeriod: null,
      previousPeriod: null,
      nextPeriod: null,
      isScrollZero: true,
      isScrollMax: true,
      tooltipPeriod: null,
      tooltipPeriodPos: {x:0,y:0}
    };
  },
  created: function() {
    this.addEmptySubPeriods();
  },
  mounted: function() {
    this.$refs.periods._computedStyle = window.getComputedStyle(this.$refs.periods);
    this.$refs.periodScroll._computedStyle = window.getComputedStyle(this.$refs.periodScroll);
    this.$watch("period", this.onPeriodChanged);

    this.$refs.periodScroll.addEventListener("scroll", this.updateScrollArrows);
    window.addEventListener("resize", this.updateScrollArrows);
    this.updateScrollArrows();
  },
  computed: {
    // this determins which the last zoom level is before we go straight to showing snapshot
    isLastZoomLevel() {
      return this.period.type === PywbPeriod.Type.day;
    },
    isTooltipPeriodDayOrHour() {
      return this.tooltipPeriod.type >= PywbPeriod.Type.day;
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
    changePeriod(period, $event) {
      // if not empty
      if (period.snapshotCount) {
        let periodToChangeTo = null;
        // if contains a single snapshot only, navigate to snapshot (load snapshot in FRAME, do not ZOOM IN)
        if (period.snapshot) {
          // if period is at level "snapshot" (no more children), send period, else send the child period, a reference to which is stored (by data/model layer) in the current period; App event needs a period to be passed (cannot pass in snapshot object itself)
          if (period.type === PywbPeriod.Type.snapshot) {
            periodToChangeTo = period;
          } else if (period.snapshotPeriod) {
            periodToChangeTo = period.snapshotPeriod;
          }
        } else {
        // if contains mulitple snapshots, just ZOOM to period clicked itself
          if (period.type <= PywbPeriod.Type.day) {
            periodToChangeTo = period;
          }
        }

        // if we selected a period to go to, emit event
        if (periodToChangeTo) {
          this.$emit("goto-period", periodToChangeTo);
        }
      }
      $event.stopPropagation();
      return false;
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
        this.restoreScroll();
        this.updateScrollArrows();
      }).bind(this), 1);
    },
    setTooltipPeriod(period, event) {
      if (!period || !period.snapshotCount) {
        this.tooltipPeriod = null;
        return;
      }
      this.tooltipPeriod = period;

      this.$nextTick(function() {
        const tooltipContentsEl = document.querySelector('.period-tooltip div');
        if (!tooltipContentsEl) {
          return;
        }

        const periodTooltipStyle = window.getComputedStyle(tooltipContentsEl);
        const tooltipWidth = parseInt(periodTooltipStyle.width);
        const tooltipHeight = parseInt(periodTooltipStyle.height);
        const spacing = 10;
        if (window.innerWidth < event.x + (spacing*2) + tooltipWidth) {
          this.tooltipPeriodPos.x = event.x - (tooltipWidth + spacing);
        } else {
          this.tooltipPeriodPos.x = event.x + spacing;
        }
        this.tooltipPeriodPos.y = event.y - (spacing + tooltipHeight);
      });
      event.stopPropagation();
      return false;
    }
  }
};
</script>


<style>
    .timeline {
        position: relative;
        display: flex;
        width: auto;
        height: 60px;
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
        line-height: 60px;
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

    .timeline .period .inner {
        display: block;
        position: absolute;
        bottom: 0;
        left: 0;
        width: 100%;
        height: 20px;
        background-color: white;
        border-top: 1px solid gray;
        white-space: nowrap;
    }
    .timeline .period .label {
      width: 100%;
      font-weight: bold;
      font-size: 14px;
      transition: background-color 500ms ease-in;
    }
    .timeline .period:hover .label {
      position: absolute;
      z-index: 20;
      background-color: lightgrey;
    }

    .timeline .period .histo {
        display: flex;
        position: absolute;
        top: 1px;
        left: 0;
        width: 100%;
        height: 39px;
        align-items: flex-end;
        justify-content: space-between;
        text-align: left;
    }

    .timeline .period .histo .line {
        position: relative;
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
    }

        /* update line color on hover*/
        .timeline .period .histo .line:hover {
            background-color: #f5a6eb;
        }

        /* Period that contains ONE snapshot only will show snapshot info*/
        .timeline .period-tooltip {
            position: fixed;
            z-index: 100;
            /*left or right set programmatically*/
            display: block;
            background-color: white;
            border: 1px solid gray;
            padding: 2px;
            white-space: nowrap; /*no wrapping allowed*/
        }
            /*show on hover*/
            .timeline .period-tooltip.show {
                display: block;
            }

</style>