<style>
    .full-view {
        position: absolute;
        top: 130px;
        left: 0;
        height: 80vh;
        width: 100%;
        background-color: white;
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
</style>

<template>
    <div class="full-view">
        <h2>{{year.snapshotCount}} captures in {{year.id}}</h2>
        <div class="months">
            <CalendarMonth
                    v-for="month in year.children"
                    :key="month.id"
                    :month="month"
                    :year="year"
                    :is-current="month === currentMonth"
                    @goto-period="$emit('goto-period', $event)"
            ></CalendarMonth>
        </div>
    </div>
</template>

<script>
import CalendarMonth from "./CalendarMonth.vue";
import { PywbPeriod } from "../model.js";

export default {
  components: {CalendarMonth},
  props: ["period"],
  data: function() {
    return {};
  },
  computed: {
    year() {
      let year = null;
      if (this.period.type === PywbPeriod.Type.all) {
        year = this.period.children[this.period.children.length-1];
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
    currentMonth() {
      let month = null;
      if (this.period.type === PywbPeriod.Type.month) {
        month = this.period;
      } else {
        month = this.period.getParents().filter(p => p.type === PywbPeriod.Type.month)[0];
      }
      return month;
    }
  }
};
</script>

