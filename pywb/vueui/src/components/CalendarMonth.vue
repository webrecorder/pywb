<style>
    .calendar-month {
        position: relative;
        display: inline-block;
        padding: 5px;
        margin: 0;
        height: 260px;
        width: 220px;
        text-align: center;
        vertical-align: top;
    }
    .calendar-month:hover {
        background-color: #eeeeee;
        border-radius: 10px;
    }
    .calendar-month.current {
        background-color: #fff7ce;
        border-radius: 5px;
    }
    .calendar-month.contains-current-snapshot {
        border: solid 1px red;
    }
    .calendar-month > h3 {
        margin: 0;
        font-size: 16px;
    }
    .calendar-month > .empty {
        position: absolute;
        top: 45%;
        width: 100%;
        color: gray;
    }
    .calendar-month .day {
        position: relative;
        display: inline-block;
        margin: 0;
        text-align: center;
    }
    .calendar-month .day.empty {
        color: gray;
    }
    .calendar-month .day .count {
        display: none;
        position: absolute;
        bottom: 80%;
        left: 80%;
        line-height: 1; /* reset to normal */
        padding: 3px;
        border-radius: 10px;
        border-bottom-left-radius: 0;
        border: 1px solid gray;
        background-color: white;
        z-index: 30;
        white-space: nowrap;
    }
    .calendar-month .day:hover .count {
        display: block;
    }
    .calendar-month .day .size {
        position: absolute;
        box-sizing: border-box;
        background-color: rgba(166, 205, 245, .85);
        z-index: 10;
    }
    .calendar-month .day.contains-current-snapshot .size {
      background-color: rgba(255, 100, 100, .85);
    }

    .calendar-month .day .day-id {
        position: absolute;
        top: 0;
        left: 0;
        z-index: 11;

        display: inline-block;
        width: 100%;
        text-align: center;

        color: black;
    }
    .calendar-month .day:hover .size {
        border: 1px solid black;
    }
    .calendar-month .day:hover {
        cursor: zoom-in;
    }
    .calendar-month .day.empty:hover {
        cursor: not-allowed;
    }
</style>

<template>
    <div class="calendar-month" :class="{current: isCurrent, 'contains-current-snapshot': containsCurrentSnapshot}">
        <h3>{{getLongMonthName(month.id)}} <span v-if="month.snapshotCount">({{ month.snapshotCount }})</span></h3>
        <div v-if="month.snapshotCount">
            <span v-for="(dayInitial) in dayInitials" class="day" :style="dayStyle">{{dayInitial}}</span><br/>
            <span v-for="(day,i) in days"><br v-if="i && i % 7===0"/><span class="day" :class="{empty: !day || !day.snapshotCount, 'contains-current-snapshot':dayContainsCurrentSnapshot(day)}" :style="dayStyle"  @click="gotoDay(day, $event)"><template v-if="day"><span class="size" v-if="day.snapshotCount" :style="getDayCountCircleStyle(day.snapshotCount)"> </span><span class="day-id">{{day.id}}</span><span v-if="day.snapshotCount" class="count">{{ $root._(day.snapshotCount !== 1 ? '{count} captures':'{count} capture', {count: day.snapshotCount}) }}</span></template><template v-else v-html="'&nbsp;'"></template></span></span>
        </div>
        <div v-else class="empty">no captures</div>
    </div>
</template>

<script>
import {PywbI18N} from "../i18n";

export default {
  props: ["month", "year", "isCurrent", "yearContainsCurrentSnapshot", "currentSnapshot"],
  data: function() {
    return {
      maxInDay: 0,
      daySize: 30,
    };
  },
  computed: {
    dayInitials() {
      return PywbI18N.instance.getWeekDays().map(d => d.substr(0,1));
    },
    dayStyle() {
      const s = this.daySize;
      return `height: ${s}px; width: ${s}px; line-height: ${s}px`;
    },
    days() {
      if (!this.month || !this.month.snapshotCount) {
        return [];
      }
      const days = [];
      // Get days in month, and days in the complete weeks before first day and after last day
      const [firstDay, lastDay] = this.month.getChildrenRange();
      const daysBeforeFirst = (new Date(this.year.id, this.month.id-1, firstDay)).getDay();
      const daysAfterLastDay = (6 - (new Date(this.year.id, this.month.id-1, lastDay)).getDay());
      for(let i=0; i<daysBeforeFirst; i++) {
        days.push(null);
      }
      const hasChildren = !!this.month.children.length;
      for(let i=0; i<lastDay; i++) {
        days.push(hasChildren ? this.month.children[i] : null);
      }
      for(let i=0; i<daysAfterLastDay; i++) {
        days.push(null);
      }
      return days;
    },
    containsCurrentSnapshot() {
      return this.currentSnapshot &&
          this.month.contains(this.currentSnapshot);
    }
  },
  methods: {
    getLongMonthName(id) {
      return PywbI18N.instance.getMonth(id);
    },
    gotoDay(day, event) {
      if (!day || !day.snapshotCount) {
        return;
      }
      // upon doing to day, tell timeline to highlight itself
      // this.$root.timelineHighlight = true;
      this.$emit("show-day-timeline", day, event);
    },
    getDayCountCircleStyle(snapshotCount) {
      const size = Math.ceil((snapshotCount/this.year.maxGrandchildSnapshotCount) * this.daySize);
      const scaledSize = size ? (this.daySize*.3 + Math.ceil(size*.7)) : 0;
      const margin = (this.daySize-scaledSize)/2;

      // TEMPORARILY DISABLE AUTO-HUE calculation as it is contributing to better understand of data
      // color hue should go form blue (240deg) to red (360deg)
      // const colorHue = Math.ceil((snapshotCount/this.year.maxGrandchildSnapshotCount) * (360-240));
      // const scaledColorHue = size ? (240 + colorHue) : 240;
      // background-color: hsl(${scaledColorHue}, 100%, 50%, .2)

      return `width: ${scaledSize}px; height: ${scaledSize}px; top: ${margin}px; left: ${margin}px; border-radius: ${scaledSize/2}px;`;
    },
    dayContainsCurrentSnapshot(day) {
      return !!day && day.snapshotCount > 0 && this.containsCurrentSnapshot && day.contains(this.currentSnapshot);
    }
  }
};
</script>

