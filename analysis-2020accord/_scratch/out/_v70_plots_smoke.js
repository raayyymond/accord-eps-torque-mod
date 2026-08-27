// Smoke-test the rendered chart script against a minimal DOM shim: catches runtime errors and,
// more importantly, NaN/Infinity in any emitted SVG geometry attribute.
const fs = require('fs');
const path = require('path');

const html = fs.readFileSync(path.join(__dirname, '..', 'docs', 'v70-plots.html'), 'utf8');
const js = html.match(/<script>([\s\S]*)<\/script>/)[1];

const bad = [];
const GEOM = new Set(['x', 'y', 'x1', 'x2', 'y1', 'y2', 'cx', 'cy', 'r', 'width', 'height', 'd']);

function mkEl(tag) {
  const e = {
    tagName: tag, attrs: {}, children: [], _text: '', style: {}, _html: '',
    setAttribute(k, v) {
      if (GEOM.has(k) && /NaN|Infinity|undefined/.test(String(v))) {
        bad.push(`${tag}[${k}] = ${v}`);
      }
      this.attrs[k] = v;
    },
    getAttribute(k) { return this.attrs[k]; },
    appendChild(c) { this.children.push(c); return c; },
    addEventListener() {},
    getBoundingClientRect() { return { left: 0, top: 0, width: 1000, height: 400 }; },
    set textContent(v) { if (String(v).includes('undefined')) bad.push(`${tag} text: ${v}`); this._text = v; },
    get textContent() { return this._text; },
    set innerHTML(v) { if (String(v).includes('undefined')) bad.push(`${tag} html: ${String(v).slice(0, 120)}`); this._html = v; this.children = []; },
    get innerHTML() { return this._html; },
  };
  return e;
}

const ids = {};
for (const id of ['tiles', 'lg1', 'lg2', 'lg3', 'lg5', 'c1', 'c2', 'c3', 'c4', 'c5', 'c6', 'tbl', 'tip']) {
  ids[id] = mkEl(id.startsWith('c') && id.length === 2 ? 'svg' : 'div');
}
// viewBox values must match the HTML so the charts compute real geometry
const VB = { c1: '0 0 1000 380', c2: '0 0 1000 380', c3: '0 0 1000 400', c4: '0 0 1000 250', c5: '0 0 1000 290', c6: '0 0 1000 250' };
for (const k in VB) ids[k].attrs.viewBox = VB[k];

const CSSVARS = {
  '--surface-1': '#fcfcfb', '--plane': '#f9f9f7', '--text-primary': '#0b0b0b',
  '--text-secondary': '#52514e', '--muted': '#898781', '--grid': '#e1e0d9',
  '--baseline': '#c3c2b7', '--border': 'rgba(11,11,11,0.10)',
  '--s1': '#2a78d6', '--s2': '#eb6834', '--s3': '#1baf7a', '--s4': '#eda100',
  '--critical': '#d03b3b', '--good': '#0ca30c', '--warning': '#fab219',
};

global.document = {
  createElementNS: (ns, tag) => mkEl(tag),
  getElementById: (id) => ids[id] || null,
  querySelector: () => ({}),
};
global.getComputedStyle = () => ({
  getPropertyValue: (n) => {
    if (!(n in CSSVARS)) bad.push(`unknown css var ${n}`);
    return CSSVARS[n] || '';
  },
});
global.innerWidth = 1400;
global.innerHeight = 900;

new Function(js)();

const counts = Object.fromEntries(
  ['c1', 'c2', 'c3', 'c4', 'c5', 'c6'].map(k => [k, ids[k].children.length]));

console.log('svg child counts:', JSON.stringify(counts));
console.log('tiles html len :', ids.tiles.innerHTML.length);
console.log('table html len :', ids.tbl.innerHTML.length);
console.log('legend lg1     :', ids.lg1.innerHTML.slice(0, 90));

let fail = false;
for (const [k, v] of Object.entries(counts)) {
  if (v < 8) { console.log(`FAIL ${k} rendered only ${v} nodes`); fail = true; }
}
if (bad.length) { console.log('FAIL bad attrs/text:'); bad.slice(0, 20).forEach(b => console.log('  ', b)); fail = true; }
console.log(fail ? 'SMOKE FAIL' : 'SMOKE PASS');
process.exit(fail ? 1 : 0);
