// Reads a JSON array of {tex, display} on stdin, writes a JSON array of HTML on stdout.
const katex = require('katex');
let src = '';
process.stdin.on('data', d => (src += d));
process.stdin.on('end', () => {
  const out = JSON.parse(src).map(({ tex, display }) => {
    try {
      return katex.renderToString(tex, { displayMode: display, output: 'html', throwOnError: true });
    } catch (e) {
      console.error(`${e.message}\nin: ${tex}`);
      process.exit(1);
    }
  });
  process.stdout.write(JSON.stringify(out));
});
