import * as path from 'path';

const basePywbOutput = path.join(__dirname, '..', 'pywb', 'static');

const noStrict = {
  renderChunk(code) {
    return code.replace("'use strict';", '');
  }
};

const watchOptions = {
  exclude: 'node_modules/**',
  chokidar: {
    alwaysStat: true,
    usePolling: true
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
  watch: watchOptions,
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
  watch: watchOptions,
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
  watch: watchOptions,
  plugins: [noStrict]
};

const wombatAutoFetchWorker = {
  input: 'src/autoFetchWorker.js',
  output: {
    name: 'autoFetchWorker',
    file: path.join(basePywbOutput, 'autoFetchWorker.js'),
    format: 'es',
    sourcemap: false,
    exports: 'none'
  },
  watch: watchOptions,
  plugins: [
    {
      renderChunk(code) {
        if (!code.startsWith("'use strict';")) {
          return "'use strict';\n" + code;
        }
        return code;
      }
    }
  ]
};

let config;

if (process.env.ALL) {
  config = [wombat, wombatProxyMode, wombatWorker, wombatAutoFetchWorker];
} else if (process.env.PROXY) {
  config = wombatProxyMode;
} else if (process.env.WORKER) {
  config = wombatProxyMode;
} else if (process.env.AUTO_WORKER) {
  config = wombatAutoFetchWorker;
} else {
  config = wombat;
}

export default config;
