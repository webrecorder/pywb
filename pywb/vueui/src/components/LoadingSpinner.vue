<template>
  <div class="pywb-loading-spinner-mask" :class="{hidden: isHidden, spinning: isSpinning}" @click="setOff">
    <div class="pywb-loading-spinner">
      <div data-loading-spinner="circle1"></div>
      <div data-loading-spinner="circle2"></div>
      <div data-loading-spinner="circle3"></div>
      <div data-loading-spinner="circle4"></div>
      <span data-loading-spinner="text">{{text}}</span>
    </div>
  </div>
</template>

<script>
let elStyle = null;
export default {
  name: "LoadingSpinner",
  props: ['text', 'isLoading'],
  mounted() {
    this.setOnOff();
    this.$watch('isLoading', this.setOnOff);
  },
  data() {
    return {
      isSpinning: '',
      isHidden: ''
    }
  },
  methods: {
    setOnOff() {
      if (this.isLoading) {
        this.setOn();
      } else {
        this.setOff();
      }
    },
    setOn() {
      this.isHidden = false;
      setTimeout(function setSpinning() {
        this.isSpinning = true;
      }.bind(this), 100);
    },
    setOff() {
      this.isSpinning = false;
      setTimeout(function setHidden() {
        this.isHidden = true;
      }.bind(this), 500);
    }
  }
}
</script>

<style scoped>
.pywb-loading-spinner-mask.spinning {
  opacity: 1;
}
.pywb-loading-spinner-mask.hidden {
  display: none;
}
.pywb-loading-spinner-mask {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  z-index: 900;

  display: flex;
  justify-content: center;
  align-items: center;

  background-color: rgba(255,255,255, .85);

  opacity: 0;
  transition: opacity 500ms ease-in;
}

.pywb-loading-spinner {
  position: relative;
  display: flex;
  justify-content: center;
  align-items: center;
  width: 200px;
  height: 200px;
}
[data-loading-spinner^=circle] {
  position: absolute;
  border: 3px solid #444444;/* #0D4B9F; */
  width: 70%;
  height: 70%;
  margin: 0;
  border-radius: 50%;
  border-left-color: transparent;
  border-right-color: transparent;
  animation: rotate 2s cubic-bezier(0.26, 1.36, 0.74, -0.29) infinite;
}
[data-loading-spinner=circle2] {
  border: 3px solid #ddd;/* #E0EDFF; */
  width: 80%;
  height: 80%;
  border-left-color: transparent;
  border-right-color: transparent;
  animation: rotate2 2s cubic-bezier(0.26, 1.36, 0.74, -0.29) infinite;
}
[data-loading-spinner=circle3] {
  border: 3px solid #656565;/* #005CDC; */
  width: 90%;
  height: 90%;
  border-left-color: transparent;
  border-right-color: transparent;
  animation: rotate 2s cubic-bezier(0.26, 1.36, 0.74, -0.29) infinite;
}
[data-loading-spinner=circle4] {
  border: 3px solid #aaa; /* #94B6E5; */
  width: 100%;
  height: 100%;
  border-left-color: transparent;
  border-right-color: transparent;
  animation: rotate2 2s cubic-bezier(0.26, 1.36, 0.74, -0.29) infinite;
}
@keyframes rotate {
  0% {
    transform: rotateZ(-360deg)
  }
  100% {
    transform: rotateZ(0deg)
  }
}
@keyframes rotate2 {
  0% {
    transform: rotateZ(360deg)
  }
  100% {
    transform: rotateZ(0deg)
  }
}
[data-loading-spinner=text] {
  font-size: 15px;
}
</style>
