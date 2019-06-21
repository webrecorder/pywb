import * as path from 'path';

const baseTestOutput = path.join(__dirname, 'test', 'assets');
const noStrict = {
  renderChunk(code) {
    return code.replace("'use strict';", '');
  }
};

export default [
  {
    input: 'src/wbWombat.js',
    output: {
      name: 'wombat',
      file: path.join(baseTestOutput, 'wombat.js'),
      sourcemap: false,
      format: 'iife'
    },
    plugins: [noStrict]
  },
  {
    input: 'src/wbWombatProxyMode.js',
    output: {
      name: 'wombat',
      file: path.join(baseTestOutput, 'wombatProxyMode.js'),
      sourcemap: false,
      format: 'iife'
    },
    plugins: [noStrict]
  },
  {
    input: 'src/wombatWorkers.js',
    output: {
      name: 'wombat',
      file: path.join(baseTestOutput, 'wombatWorkers.js'),
      format: 'es',
      sourcemap: false,
      exports: 'none'
    },
    plugins: [noStrict]
  },
  {
    input: 'src/wbWombat.js',
    output: {
      name: 'wombat',
      file: path.join(baseTestOutput, 'wombatDirect.js'),
      sourcemap: false,
      format: 'es'
    },
    plugins: [
      noStrict,
      {
        renderChunk(code) {
          return code.replace(
            /(this\._wb_wombat\.actual\s=\strue;)/gi,
            `this._wb_wombat.actual = true;
    this.wombat = wombat;`
          );
        }
      }
    ]
  }
];
