// Reads a JSON array of TeX strings on stdin, writes a JSON array of HTML on stdout.
const katex = require('katex');
let src = '';
process.stdin.on('data', d => (src += d));
process.stdin.on('end', () => {
  const out = JSON.parse(src).map(tex =>
    katex.renderToString(tex, { displayMode: true, output: 'html', throwOnError: true }));
  process.stdout.write(JSON.stringify(out));
});
