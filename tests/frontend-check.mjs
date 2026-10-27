// Built-in Node.js checks; no npm packages, no browser global shims.
// Verify the exact frontend escaping code delivered in app.js.
import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
const source = fs.readFileSync(new URL('../app/static/app.js', import.meta.url), 'utf8');
const escMatch = source.match(/^const esc = .*;$/m);
const csvMatch = source.match(/function csvSafe\(value\)\{[\s\S]*?\n\}/);
assert(escMatch && csvMatch, 'Escaping functions must remain present');
const esc = vm.runInNewContext(`${escMatch[0]}\nesc;`);
const csvSafe = vm.runInNewContext(`${csvMatch[0]}\ncsvSafe;`);
assert.equal(esc(`<script>alert("x")</script>&'`), '&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;&amp;&#39;');
assert.equal(csvSafe('=1+1'), '"\'=1+1"');
assert.equal(csvSafe('\u200B=1+1'), '"\'\u200B=1+1"');
assert.equal(csvSafe('\uFEFF+SUM(A1:A3)'), '"\'\uFEFF+SUM(A1:A3)"');
assert.equal(csvSafe('Обычное название'), '"Обычное название"');
assert.equal(csvSafe('Значение";=2+2'), '"Значение"";=2+2"');
console.log('6 frontend safety assertions passed');
