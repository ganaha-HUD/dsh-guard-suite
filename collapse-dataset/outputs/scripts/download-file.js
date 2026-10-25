// download-file.js - fetch a file over HTTPS/HTTP without relying on Windows schannel.
// usage: node download-file.js <url> <outputPath> [expectedBytes] [--resume]
// Follows up to 5 redirects (CDC mirrors redirect to a signed URL), resumes from
// <outputPath>.part with --resume, prints progress every 2 MiB and always exits explicitly.
const fs = require('fs');
const http = require('http');
const https = require('https');
const path = require('path');

const url = process.argv[2];
const out = process.argv[3];
const expected = process.argv[4] ? Number(process.argv[4]) : null;
const resume = process.argv.includes('--resume');

if (!url || !out) {
  console.error('usage: node download-file.js <url> <outputPath> [expectedBytes] [--resume]');
  process.exit(2);
}

fs.mkdirSync(path.dirname(out), { recursive: true });
const tmp = out + '.part';

let start = 0;
if (resume && fs.existsSync(tmp)) {
  start = fs.statSync(tmp).size;
  console.log('resuming from ' + start + ' bytes');
}
if (expected !== null && start === expected && fs.existsSync(tmp)) {
  fs.renameSync(tmp, out);
  console.log('already complete: ' + out);
  process.exit(0);
}

const headers = { 'User-Agent': 'dsh-runtime-installer/1.0' };
if (start > 0) { headers['Range'] = 'bytes=' + start + '-'; }

const started = Date.now();

function fetchTo(target, redirectsLeft) {
  const mod = target.startsWith('http://') ? http : https;
  const req = mod.get(target, { headers: headers, agent: false }, (res) => {
    if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
      if (redirectsLeft <= 0) { console.error('too many redirects'); process.exit(6); }
      const next = new URL(res.headers.location, target).toString();
      console.log('redirect ' + res.statusCode + ' -> ' + next);
      res.resume();
      fetchTo(next, redirectsLeft - 1);
      return;
    }

    let from = start;
    let flags = 'a';
    if (res.statusCode === 200) { from = 0; flags = 'w'; }
    else if (res.statusCode !== 206) {
      console.error('HTTP ' + res.statusCode + ' for ' + target);
      process.exit(4);
    }

    const total = res.headers['content-length'] ? Number(res.headers['content-length']) + from : null;
    console.log('status ' + res.statusCode + ' | total ' + (total === null ? 'unknown' : total) + ' bytes');

    const file = fs.createWriteStream(tmp, { flags: flags });
    let written = from;
    let reported = from;

    res.on('data', (chunk) => {
      written += chunk.length;
      if (written - reported >= 2 * 1024 * 1024) {
        reported = written;
        const pct = total ? (' (' + ((written / total) * 100).toFixed(1) + '%)') : '';
        console.log('progress ' + written + pct);
      }
    });

    res.pipe(file);
    file.on('finish', () => file.close(() => {
      const size = fs.statSync(tmp).size;
      if (expected !== null && size !== expected) {
        console.error('SIZE MISMATCH: got ' + size + ', expected ' + expected + ' (partial file kept)');
        process.exit(3);
      }
      fs.renameSync(tmp, out);
      console.log('downloaded ' + out);
      console.log('bytes ' + size + ' in ' + ((Date.now() - started) / 1000).toFixed(1) + ' s');
      process.exit(0);
    }));
  });

  req.on('error', (e) => { console.error('NETWORK ERROR: ' + e.message + ' (partial file kept for --resume)'); process.exit(1); });
  req.setTimeout(60000, () => { console.error('TIMEOUT: no data for 60 s (partial file kept for --resume)'); req.destroy(); process.exit(5); });
}

fetchTo(url, 5);