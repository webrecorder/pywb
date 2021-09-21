<template>
  <div class="pywb-tooltip" :style="{left: x+'px', top: y+'px'}">
    <slot></slot>
  </div>
</template>

<script>
let elStyle = null;
export default {
  name: "Tooltip",
  props: ['position'],
  data() {
    return {
      x: 0,
      y: 0
    }
  },
  mounted() {
    this.$watch('position', this.updatePosition);
    this.updatePosition();
  },
  methods: {
    updatePosition() {
      const style = window.getComputedStyle(this.$el);
      const width = parseInt(style.width);
      const height = parseInt(style.height);
      const spacing = 10;
      const [initX, initY] = this.position.split(',').map(s => parseInt(s));
      if (window.innerWidth < initX + (spacing*2) + width) {
        this.x = initX - (width + spacing);
      } else {
        this.x = initX + spacing;
      }
      this.y = initY - (spacing + height);
    }
  }
}
</script>

<style scoped>
.pywb-tooltip {
  position: fixed;
  top: 0;
  left: 0;
  z-index: 40;
  background-color: white;
  border: 1px solid grey;
  border-radius: 5px;
}
</style>