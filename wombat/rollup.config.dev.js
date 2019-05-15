import * as path from 'path';

const basePywbOutput = path.join(__dirname, '..', 'pywb', 'static');

const noStrict = {
  renderChunk(code) {
    return code.replace("'use strict';", '');
  }
};

const wombat = {
  input: 'src/wbWombat.js',
  output: {
    name: 'wombat',
    file: path.join(basePywbOutput, 'wombat.js'),
    sourcemap: false,
    format: 'iife'
  },
  watch: {
    exclude: 'node_modules/**',
    chokidar: {
      alwaysStat: true,
      usePolling: true
    }
  },
  plugins: [noStrict]
};

const wombatProxyMode = {
  input: 'src/wbWombatProxyMode.js',
  output: {
    name: 'wombat',
    file: path.join(basePywbOutput, 'wombatProxyMode.js'),
    sourcemap: false,
    format: 'iife'
  },
  watch: {
    exclude: 'node_modules/**',
    chokidar: {
      alwaysStat: true,
      usePolling: true
    }
  },
  plugins: [noStrict]
};

const wombatWorker = {
  input: 'src/wombatWorkers.js',
  output: {
    name: 'wombatWorkers',
    file: path.join(basePywbOutput, 'wombatWorkers.js'),
    format: 'es',
    sourcemap: false,
    exports: 'none'
  },
  watch: {
    exclude: 'node_modules/**',
    chokidar: {
      alwaysStat: true,
      usePolling: true
    }
  },
  plugins: [noStrict]
};

let config;

if (process.env.ALL) {
  config = [wombat, wombatProxyMode, wombatWorker];
} else if (process.env.PROXY) {
  config = wombatProxyMode;
} else if (process.env.WORKER) {
  config = wombatProxyMode;
} else {
  config = wombat;
}

export default config;
