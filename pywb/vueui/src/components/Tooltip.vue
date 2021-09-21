<template>
  <div class="pywb-tooltip">
    <slot></slot>
  </div>
</template>

<script>
let elStyle = null;
export default {
  name: "Tooltip",
  props: ['position'],
  mounted() {
    this.$watch('position', this.updatePosition);
    this.updatePosition();
  },
  methods: {
    updatePosition() {
      this.$el.style.top = 0;
      this.$el.style.left = 0;
      this.$el.style.maxHeight = 'auto';

      const style = window.getComputedStyle(this.$el);
      const width = parseInt(style.width);
      const height = parseInt(style.height);
      const spacing = 10;
      const [initX, initY] = this.position.split(',').map(s => parseInt(s));
      if (window.innerWidth < initX + (spacing*2) + width) {
        this.$el.style.left = (initX - (width + spacing)) + 'px';
      } else {
        this.$el.style.left = (initX + spacing) + 'px';
      }
      if ((window.innerHeight < initY + (spacing*2) + height) && (initY - (spacing*2) - height < 0) ) {
        if (initY > window.innerHeight / 2) {
          this.$el.style.top = (window.innerHeight - (height + (spacing*2))) + 'px';
        } else {
          this.$el.style.top = (spacing*2) + 'px';
        }
      } else if (window.innerHeight < initY + (spacing*2) + height) {
        this.$el.style.top = (initY - (spacing + height)) + 'px';
      } else {
        this.$el.style.top = initY + 'px';
      }
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