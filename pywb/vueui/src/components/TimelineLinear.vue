<template>
<div class="timeline-linear">
  <div class="title">
    <div>{{ period.getFullReadableId() }}</div>
    <div>{{ period.snapshotCount }} capture<span v-if="period.snapshotCount > 1">s</span></div>
  </div>

  <div class="list">
    <div v-for="period in snapshotPeriods">
      <span class="link" @click="gotoPeriod(period)">{{period.snapshot.getTimeFormatted()}}</span>
    </div>
  </div>
</div>
</template>

<script>
export default {
  name: "TimelineLinear",
  props: ['period'],
  computed: {
    snapshotPeriods() {
      return this.period.getSnapshotPeriodsFlat();
    }
  },
  methods: {
    gotoPeriod(period) {
      this.$emit('goto-period', period);
    }
  }
}
</script>

<style scoped>
.timeline-linear {
  width: auto;
  padding: 5px;
  background-color: white;
  border: 1px solid gray;
  border-radius: 5px;
}
.timeline-linear .list {
  max-height: 80vh;
  min-height: 50px;
  overflow: scroll;
}
.timeline-linear .title {
  border-bottom: 1px solid black;
  font-weight: bold;
  font-family: Arial, sans-serif;
}
.timeline-linear .link {
  text-decoration: underline;
  color: darkblue;
}
.timeline-linear .link:hover {
  color: lightseagreen;
  cursor: pointer;
}
</style>