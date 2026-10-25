const zlib = require('zlib');
const fs = require('fs');
const path = require('path');

const SRC = 'C:\\Users\\徐丰哲\\.dsh\\sessions\\--E-Deepseek--\\session-3b54e160-6d42-43a7-b4af-bffba94d76d9\\session.v4.jsonl.zstd';
const OUTDIR = 'E:\\deepseek\\workspace\\_recovery';
fs.mkdirSync(OUTDIR, { recursive: true });
const raw = fs.readFileSync(SRC);
console.log('压缩文件: ' + (raw.length / 1048576).toFixed(2) + ' MB');
let text;
try {
  text = zlib.zstdDecompressSync(raw).toString('utf8');
} catch (e) {
  console.log('zstdDecompressSync 失败: ' + e.message);
  process.exit(1);
}
console.log('解压后: ' + (text.length / 1048576).toFixed(2) + ' M 字符');
const out = path.join(OUTDIR, 'session-3b54e160.jsonl');
fs.writeFileSync(out, text);
console.log('已写入: ' + out);
const lines = text.split('\n').filter((l) => l.trim());
console.log('行数: ' + lines.length);
console.log();
console.log('=== 前 2 行的结构（截断） ===');
for (const l of lines.slice(0, 2)) console.log('  ' + l.slice(0, 400));
console.log();
console.log('=== 关键词命中次数 ===');
for (const kw of ['output-storage-policy', 'storage-policy.json', 'ai-tool-policy', 'Test-StoragePolicy',
                  'Install-GlobalPolicy', 'New-ConversationWorkspace', 'conversation-registry',
                  'rootAllowList', 'imageGenerationBudget', '思考语言', '工作区输出文件存放准则']) {
  let n = 0, i = 0;
  while ((i = text.indexOf(kw, i)) >= 0) { n++; i += kw.length; }
  console.log('  ' + kw.padEnd(30) + n);
}