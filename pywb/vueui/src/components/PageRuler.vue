<template>
    <div class="ruler">
      <div class="inner" :class="{hidden: !isShow}">
        <div class="axis x" :style="{width: xAxisWidth}" ref="xAxis">
          <div class="tick x" v-for="x in xTicks" >{{ x ? x : '' }}</div>
          <div class="line x" v-if="xAxisLine" :style="{left: xAxisLine+'px'}"><span>{{xAxisLine}}</span></div>
        </div>
        <div class="axis y" :style="{height: yAxisHeight}" ref="yAxis">
          <div class="tick y" v-for="y in yTicks">{{ y ? y : '' }}</div>
          <div class="line y" v-if="yAxisLine" :style="{top: yAxisLine+'px'}"><span>{{yAxisLine}}</span></div>
        </div>
      </div>
        <span class="toggle" @click="isShow=!isShow">R</span>
    </div>
</template>

<style>
.ruler {
  position: fixed;
  margin: 0;
  padding: 0;
  z-index: 90;
}
.ruler .inner.hidden { display: none; }

  .ruler .toggle {
    cursor: pointer;
    z-index: 91;
    position: fixed;
    top: 0;
    left: 0;
  }
  .ruler .line {
    position: fixed;
    top: 0;
    left: 0;
    width: 10px;
    height: 10px;
  }
  .ruler .line  span {
    color: red;
    font-weight: bold;
    background-color: rgba(255,255,255,.9);
  }

  .ruler .tick {
    font-size: 15px; line-height: 1;
  }

  .ruler .axis {
    background-color: rgba(255,255,255,.9);
    position: fixed;
    top: 0;
    left: 0;
    white-space: nowrap;
    overflow: visible;
  }

  .ruler .axis.x { height: 15px;}
  .ruler .tick.x {
    display: inline-block;
    height: 15px;
    width: 49px;
    border-left: 1px solid black;
  }
  .ruler .axis.y { width: 15px; }
  .ruler .tick.y {
    display: block;
    width: 15px;
    height: 49px;
    border-top: 1px solid black;
  }
  .ruler .line.x {
    height: 100vh;
    border-left: 1px solid red;
  }
  .ruler .line.y {
    width: 100vw;
    border-top: 1px solid red;
  }
</style>

<script>
export default {
  data() {
    return {
      isShow: false,
      xTicks: [],
      xAxisLine: 0,
      yTicks: [],
      yAxisLine: 0,
      increment: 50 //px
    }
  },
  mounted() {
    for (let i = 0; i < 100; i++) {
      this.xTicks.push(i * this.increment);
      this.yTicks.push(i * this.increment);
    }

    const onMouseMoveHandlerFn_ = (event) => {
      if (event.currentTarget === this.$refs.xAxis) {
        this.xAxisLine = event.x;
        console.log(event.x);
      } else if (event.currentTarget === this.$refs.yAxis) {
        this.yAxisLine = event.y;
        console.log(event.y);
      }
    };
    const onMouseMoveHandlerFn = onMouseMoveHandlerFn_.bind(this);
    const toggleHandlers = (event) => {
      if (event.currentTarget === this.$refs.xAxis) {
        if (this.$refs.xAxis.isGuidelineOn) {
          this.$refs.xAxis.isGuidelineOn = false;
          this.xAxisLine = 0;
          this.$refs.xAxis.removeEventListener('mousemove', onMouseMoveHandlerFn, true);
        } else {
          this.$refs.xAxis.isGuidelineOn = true;
          this.xAxisLine = event.x;
          this.$refs.xAxis.addEventListener('mousemove', onMouseMoveHandlerFn, true);
        }
        event.stopPropagation();
      } else if (event.currentTarget === this.$refs.yAxis) {
        if (this.$refs.yAxis.isGuidelineOn) {
          this.$refs.yAxis.isGuidelineOn = false;
          this.yAxisLine = 0;
          this.$refs.yAxis.removeEventListener('mousemove', onMouseMoveHandlerFn, true);
        } else {
          this.$refs.yAxis.isGuidelineOn = true;
          this.yAxisLine = event.y;
          this.$refs.yAxis.addEventListener('mousemove', onMouseMoveHandlerFn, true);
        }
        event.stopPropagation();
      }
    }

    this.$refs.xAxis.addEventListener('click', toggleHandlers.bind(this), true);
    this.$refs.yAxis.addEventListener('click', toggleHandlers.bind(this), true);
  },
  computed: {
    yAxisHeight() {
      return `${this.yTicks.length * this.increment}px`;
    },
    xAxisWidth() {
      return `${this.xTicks.length * this.increment}px`;
    }
  },
  methods: {
  }
};
</script>
