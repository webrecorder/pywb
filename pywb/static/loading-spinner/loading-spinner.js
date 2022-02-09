const smallSize = "75px";


class LoadingSpinner {
  static #instanceCount = 0;

  constructor(config={}) {
    this.config = {initialState:true, animationDuration:500, text:'Loading...', ...config};

    if (LoadingSpinner.#instanceCount > 0) {
      throw new Error('Cannot make a second loading spinner (aka progress indicator)');
    }
    LoadingSpinner.#instanceCount++;


    const uuid = Math.floor(Math.random()*1000);
    this.classes = {
      el: `loading-spinner-${uuid}`,
      mask: `loading-spinner-mask-${uuid}`,
      hidden: `hidden-${uuid}`,
      spinning: `spinning-${uuid}`
    };

    this.state = config.initialState;
    this.addStyles();
    this.addDom();
  }

  toggle() {
    if (this.state) {
      this.setOn();
    } else {
      this.setOff();
    }
  }

  setOn() {
    this.state = true;
    this.el.classList.remove(this.classes.hidden);
    setTimeout(function setSpinning() {
      this.el.classList.add(this.classes.spinning);
    }.bind(this), 10);
  }

  setOff() {
    this.state = false;
    this.el.classList.remove(this.classes.spinning);
    setTimeout(function setHidden() {
      this.el.classList.add(this.classes.hidden);
    }.bind(this), this.config.animationDuration);
  }

  addDom() {
    const text = this.config.text;
    const dom = `
<div class="${this.classes.mask} ${this.classes[this.config.initialState ? 'spinning':'hidden']}">
  <div class="${this.classes.el}">
    <div data-loading-spinner="circle1"></div>
    <div data-loading-spinner="circle2"></div>
    <div data-loading-spinner="circle3"></div>
    <div data-loading-spinner="circle4"></div>
    <span data-loading-spinner="text">${text}</span>
  </div>
</div>`;
    const wrapEl = document.createElement('div');
    wrapEl.innerHTML = dom;
    this.el = wrapEl.firstElementChild;
    document.getElementsByTagName('body')[0].appendChild(this.el);
  }

  addStyles() {
    const duration = this.config.animationDuration;
    const stylesheetEl = document.createElement('style');
    document.head.appendChild(stylesheetEl);

    const rules = [`
.${this.classes.mask} {
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: ${this.config.isSmall ? smallSize : "100vh"};
    z-index: 900;

    display: flex;
    justify-content: center;
    align-items: center;

    background-color: rgba(255,255,255, .85);

    opacity: 0;
    transition: opacity ${duration}ms ease-in;
}`,`
.${this.classes.mask}.${this.classes.spinning} {
    opacity: 1;
}`,`
.${this.classes.mask}.${this.classes.hidden} {
    display: none;
}`,`
.${this.classes.el} {
    position: relative;
    display: flex;
    justify-content: center;
    align-items: center;
    width: ${this.config.isSmall ? smallSize : "200px"};
    height: ${this.config.isSmall ? smallSize : "200px"};
}`,`
[data-loading-spinner^=circle] {
    position: absolute;
    margin: 0;
    border-radius: 50%;
    border-left-color: transparent;
    border-right-color: transparent;
}`,`
[data-loading-spinner=circle1] {
    border: 3px solid #444444;/* #0D4B9F; */
    width: 70%;
    height: 70%;
    animation: rotate 2s cubic-bezier(0.26, 1.36, 0.74, -0.29) infinite;
}`,`
[data-loading-spinner=circle2] {
    border: 3px solid #ddd;/* #E0EDFF; */
    width: 80%;
    height: 80%;
    animation: rotateReverse 2s cubic-bezier(0.26, 1.36, 0.74, -0.29) infinite;
}`,`
[data-loading-spinner=circle3] {
    border: 3px solid #656565;/* #005CDC; */
    width: 90%;
    height: 90%;
    animation: rotate 2s cubic-bezier(0.26, 1.36, 0.74, -0.29) infinite;
}`,`
[data-loading-spinner=circle4] {
    border: 3px solid #aaa; /* #94B6E5; */
    width: 100%;
    height: 100%;
    animation: rotateReverse 2s cubic-bezier(0.26, 1.36, 0.74, -0.29) infinite;
}`,`
@keyframes rotate {
    from {
        transform: rotateZ(-360deg)
    }
    to {
        transform: rotateZ(0deg)
    }
}`,`
@keyframes rotateReverse {
    from {
        transform: rotateZ(360deg)
    }
    to {
        transform: rotateZ(0deg)
    }
}`,`
[data-loading-spinner=text] {
    font-size: 15px;
}`];
      rules.forEach(rule => stylesheetEl.sheet.insertRule(rule));
  }
}
