<template>
    <div class="breadcrumbs">
        <template v-if="parents.length">
            <span class="item">
                <span
                    class="goto"
                    @click="changePeriod(parents[0])"
                    @keyup.enter="changePeriod(parents[0])"
                    :title="getPeriodZoomOutText(parents[0])"
                    tabindex="1">
                  <i class="fa fa-search-minus"></i> {{parents[0].getReadableId(true)}}
                </span>
            </span>
            &gt;
            <span v-for="(parent,i) in parents" :key="parent.id" class="item" v-if="i > 0">
                <span
                    class="goto"
                    @click="changePeriod(parent)"
                    @keyup.enter="changePeriod(parent)"
                    :title="getPeriodZoomOutText(parent)"
                    tabindex="1">
                  {{parent.getReadableId(true)}}
                </span>
            </span>
        </template>
        <span class="item">
            <span class="current">{{period.getReadableId(true)}}</span>
            <span class="count">({{ $root._(period.snapshotCount !== 1 ? '{count} captures':'{count} capture', {count: period.snapshotCount}) }})</span>
        </span>
    </div>
</template>

<script>
import {PywbI18N} from "../i18n";

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
    getPeriodZoomOutText(period) {
      return PywbI18N.instance._("Zoom out to {id} ({count} captures)", {id: period.getReadableId(true), count: period.snapshotCount});
    },
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
        /*vertical-align: middle;*/
        font-size: inherit;
    }

    .breadcrumbs .item .goto {
        display: inline-block;
        margin: 1px;
        padding: 1px;
        cursor: zoom-out;
        border-radius: 5px;
        background-color: #eeeeee;
     }
    .breadcrumbs .item .goto:hover {
        background-color: #a6cdf5;
    }
    .breadcrumbs .item .goto img {
      height: 15px;
    }

    .breadcrumbs .item.snapshot {
        display: block;
    }

</style>
