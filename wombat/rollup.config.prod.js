import * as path from 'path';
import minify from 'rollup-plugin-babel-minify';

const license = `/*
Copyright(c) 2013-2018 Rhizome and Contributors. Released under the GNU General Public License.

This file is part of pywb, https://github.com/webrecorder/pywb

pywb is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

pywb is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with pywb.  If not, see <http://www.gnu.org/licenses/>.
 */`;

const basePywbOutput = path.join(__dirname, '..', 'pywb', 'static');

const addLicenceNoStrict = {
  renderChunk(code) {
    return `${license}\n${code.replace("'use strict';", '')}`;
  }
};

const minificationOpts = {
  booleans: false,
  builtIns: false,
  comments: false,
  deadcode: false,
  flipComparisons: false,
  infinity: false,
  keepClassName: true,
  keepFnName: true,
  mangle: false,
  removeUndefined: false,
  simplifyComparisons: false,
  sourceMap: false,
  typeConstructors: false,
  undefinedToVoid: false
};

export default [
  {
    input: 'src/wbWombat.js',
    plugins: [minify(minificationOpts), addLicenceNoStrict],
    output: {
      name: 'wombat',
      file: path.join(basePywbOutput, 'wombat.js'),
      format: 'iife'
    }
  },
  {
    input: 'src/wbWombatProxyMode.js',
    plugins: [minify(minificationOpts), addLicenceNoStrict],
    output: {
      name: 'wombatProxyMode',
      file: path.join(basePywbOutput, 'wombatProxyMode.js'),
      format: 'iife'
    }
  },
  {
    input: 'src/wombatWorkers.js',
    plugins: [minify(minificationOpts), addLicenceNoStrict],
    output: {
      name: 'wombatWorkers',
      file: path.join(basePywbOutput, 'wombatWorkers.js'),
      format: 'es',
      sourcemap: false,
      exports: 'none'
    }
  },
  {
    input: 'src/autoFetchWorker.js',
    plugins: [
      {
        renderChunk(code) {
          if (!code.startsWith("'use strict';")) {
            return "'use strict';\n" + code;
          }
          return code;
        }
      }
    ],
    output: {
      name: 'autoFetchWorker',
      file: path.join(basePywbOutput, 'autoFetchWorker.js'),
      format: 'es',
      sourcemap: false,
      exports: 'none'
    }
  }
];
