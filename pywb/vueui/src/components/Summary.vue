<template>
    <div class="summary">
        <template v-if="parents.length">
            <span class="item">
                <span class="goto" @click="changePeriod(parents[0])">{{parents[0].getReadableId(true)}}</span>
            </span>
            &gt;
            <span v-for="(parent,i) in parents" :key="parent.id" class="item" v-if="i > 0">
                <span class="goto" @click="changePeriod(parent)">{{parent.getReadableId(true)}}</span>
            </span>
        </template>
        <span class="item">
            <span class="current">{{period.getReadableId(true)}}</span>
            <span class="count">({{period.snapshotCount}} capture<span v-if="period.snapshotCount !== 1">s</span>)</span>
        </span>
    </div>
</template>

<script>
export default {
  props: {
    period: {
      required: true
    }
  },
  computed: {
    parents: function() {
      return this.period.getParents();
    }
  },
  methods: {
    changePeriod(period) {
      if (period.snapshotCount) {
        this.$emit("goto-period", period);
      }
    },
  }
};
</script>

<style>
    .summary {
        display: inline-block;
    }

    .summary .item {
        position: relative;
        display: inline;
        margin: 0 2px 0 0;
        font-size: inherit;
    }
    .summary .count {
        vertical-align: middle;
        font-size: inherit;
    }
    .summary .count .verbose {
        display: none;
    }
    .summary .count:hover .verbose {
        display: inline;
    }

    .summary .item .goto {
        margin: 1px;
        cursor: pointer;
        color: darkslateblue;
        text-decoration: underline;
     }
    .summary .item .goto:hover {
        background-color: #a6cdf5;
    }
    .summary .item.snapshot {
        display: block;
    }

</style>