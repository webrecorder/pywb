<template>
  <div class="timeline-linear">
    <div class="title">
      <div>{{ period.getFullReadableId() }}</div>
      <div>{{ $root._(period.snapshotCount !== 1 ? '{count} captures':'{count} capture', {count: period.snapshotCount}) }}</div>
    </div>

    <div class="list">
      <div v-for="snapshotPeriod in snapshotPeriods">
        <span
          @click="changePeriod(snapshotPeriod)"
          @keyup.enter="changePeriod(snapshotPeriod)"
          class="link"
          tabindex="1">
          {{ snapshotPeriod.snapshot.getTimeFormatted() }}
        </span>
        <span v-if="isCurrentSnapshot(period)" class="current">{{$root._('current')}}</span>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: "TimelineLinear",
  props: ['period', 'currentSnapshot'],
  computed: {
    snapshotPeriods() {
      return this.period.getSnapshotPeriodsFlat();
    },
    containsCurrentSnapshot() {
      return this.currentSnapshot &&
          this.period.contains(this.currentSnapshot);
    }
  },
  methods: {
    isCurrentSnapshot(period) {
      if (!!this.currentSnapshot && !!period.snapshot) {
        return this.currentSnapshot && this.currentSnapshot.id === period.snapshot.id;
      }
      return false;
    },
    changePeriod(period) {
      this.$emit("goto-period", period);
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
  z-index: 1100;
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
.timeline-linear .current {
  background-color: deeppink;
  color: white;
  border-radius: 5px;
}
</style>
