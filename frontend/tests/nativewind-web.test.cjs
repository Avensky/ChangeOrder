const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const postcss = require('postcss');
const tailwind = require('tailwindcss');

// Run the installed NativeWind web runtime against the project's compiled CSS.
// Model Metro's late CSS injection: the mode flag is absent at initialization,
// then a head mutation makes it available. The observer must not throw.
test('late web stylesheet initializes NativeWind without a color-scheme error', async () => {
  const config = require('../tailwind.config.js');
  const result = await postcss([tailwind({ ...config, content: [{ raw: '<div class="p-4" />' }] })])
    .process('@tailwind base; @tailwind utilities;', { from: undefined });
  const mode = result.css.match(/--css-interop-darkMode:\s*([^;]+);/)?.[1].trim();
  assert.ok(mode, 'NativeWind must emit a color-scheme mode in the web CSS');
  const runtime = path.join(path.dirname(require.resolve('react-native-css-interop/package.json')), 'dist/runtime/web/color-scheme.js');
  let flag;
  let mutation;
  const window = { document: { getElementsByTagName: () => [{}], documentElement: { classList: { contains: () => false, add() {}, remove() {} } } } };
  window.window = window;
  const observable = initial => { let value = initial; return { get: () => value, set: next => { value = next; } }; };
  const exports = {};
  vm.runInNewContext(fs.readFileSync(runtime, 'utf8'), {
    exports, window,
    MutationObserver: class { constructor(callback) { mutation = () => callback([], this); } observe() {} disconnect() {} },
    require(name) {
      if (name === 'react-native') return { Appearance: { getColorScheme: () => 'light', addChangeListener: () => ({ remove() {} }) }, AppState: { currentState: 'active' } };
      if (name === '../../shared') return { INTERNAL_RESET: Symbol('reset') };
      if (name === '../observable') return { observable };
      if (name === './stylesheet') return { StyleSheet: { getFlag: () => flag } };
      throw new Error('Unexpected runtime dependency: ' + name);
    },
  }, { filename: runtime });
  flag = mode;
  assert.doesNotThrow(mutation);
  assert.doesNotThrow(() => exports.colorScheme.set('light'));
});
