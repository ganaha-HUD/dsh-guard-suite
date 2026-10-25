// 多帧 zstd：用流式解压器把整个会话记录取出来
const zlib = require('zlib');
const fs = require('fs');
const path = require('path');

const SRC = 'C:\\Users\\徐丰哲\\.dsh\\sessions\\--E-Deepseek--\\session-3b54e160-6d42-43a7-b4af-bffba94d76d9\\session.v4.jsonl.zstd';
const OUT = 'E:\\deepseek\\workspace\\_recovery\\session-3b54e160-full.jsonl';

const chunks = [];
const dec = zlib.createZstdDecompress();
dec.on('data', (c) => chunks.push(c));
dec.on('error', (e) => console.log('解压错误: ' + e.message));
dec.on('end', () => {
  const buf = Buffer.concat(chunks);
  fs.writeFileSync(OUT, buf);
  const text = buf.toString('utf8');
  console.log('解压后: ' + (buf.length / 1048576).toFixed(2) + ' MB, ' + text.split('\n').length + ' 行');
  console.log('已写入: ' + OUT);
  console.log();
  console.log('=== 关键词命中 ===');
  for (const kw of ['output-storage-policy', 'storage-policy.json', 'ai-tool-policy', 'Test-StoragePolicy',
                    'Install-GlobalPolicy', 'New-ConversationWorkspace', 'conversation-registry',
                    'rootAllowList', 'imageGenerationBudget', '思考语言']) {
    let n = 0, i = 0;
    while ((i = text.indexOf(kw, i)) >= 0) { n++; i += kw.length; }
    console.log('  ' + kw.padEnd(30) + n);
  }
});
fs.createReadStream(SRC).pipe(dec);