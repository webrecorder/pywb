const { launch } = require('just-launch-chrome');

const winPos = !process.env.NO_MOVE_WINDOW ? '--window-position=2000,0' : '';

/**
 *
 * @return {Promise<{chromeProcess: ChildProcess, killChrome: function(): void}>}
 */
function initChrome(headless = false) {
  return launch({
    headless,
    args: [
      '--force-color-profile=srgb',
      '--disable-background-networking',
      '--disable-background-timer-throttling',
      '--disable-renderer-backgrounding',
      '--disable-backgrounding-occluded-windows',
      '--disable-ipc-flooding-protection',
      '--enable-features=NetworkService,NetworkServiceInProcess',
      '--disable-client-side-phishing-detection',
      '--disable-default-apps',
      '--disable-extensions',
      '--disable-popup-blocking',
      '--disable-hang-monitor',
      '--disable-prompt-on-repost',
      '--disable-sync',
      '--disable-domain-reliability',
      '--disable-infobars',
      '--disable-features=site-per-process,TranslateUI',
      '--disable-breakpad',
      '--disable-backing-store-limit',
      '--metrics-recording-only',
      '--no-first-run',
      '--safebrowsing-disable-auto-update',
      '--mute-audio',
      '--autoplay-policy=no-user-gesture-required',
      winPos
    ]
  });
}

module.exports = initChrome;
