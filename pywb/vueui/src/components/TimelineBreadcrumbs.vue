<template>
    <div class="breadcrumbs">
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
    .breadcrumbs {
      text-align: center;
    }
    .breadcrumbs .item {
        position: relative;
        display: inline;
        margin: 0 2px 0 0;
        font-size: inherit;
    }
    .breadcrumbs .count {
        vertical-align: middle;
        font-size: inherit;
    }
    .breadcrumbs .count .verbose {
        display: none;
    }
    .breadcrumbs .count:hover .verbose {
        display: inline;
    }

    .breadcrumbs .item .goto {
        margin: 1px;
        cursor: pointer;
        color: darkslateblue;
        text-decoration: underline;
     }
    .breadcrumbs .item .goto:hover {
        background-color: #a6cdf5;
    }
    .breadcrumbs .item.snapshot {
        display: block;
    }

</style>