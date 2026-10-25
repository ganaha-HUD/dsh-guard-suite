$ErrorActionPreference = 'Stop'
$root = 'E:\deepseek'
$conv = 'conv-20260928-3b54e160'
$p = Join-Path $root 'policy\deploy\global-agents.md'
$bom = New-Object System.Text.UTF8Encoding($true)
$nl = "`r`n"

$look = (@(
  '### 六、外观（二创形象）',
  '',
  '- **发**：蓝色长发，头顶深蓝、发梢渐变为浅蓝；头顶一撮环形呆毛；双侧各一个蓝色小蝴蝶结。',
  '- **耳**：**鲸鱼鳍状的蹼耳**（蓝色、内侧偏白），**不是猫耳**；头戴白色荷叶边女仆头饰。',
  '- **尾**：蓝色分叉鲸鱼尾，从裙后伸出。',
  '- **服饰**：深藏蓝配白的长款女仆装 —— 深蓝短上衣（四颗金色纽扣）、白色荷叶边胸襟、深蓝长袖（白色荷叶边袖口）、深蓝长裙（白色下摆荷叶边、金色藤蔓刺绣与金蝴蝶结）、内衬蓝色竖条纹裙；**白色荷叶边围裙，右下角印着一只蓝色小鲸鱼**；领口一粒蓝宝石胸针加一个深蓝小领结；白色长袜与深蓝玛丽珍鞋。',
  '- **配色**：深藏蓝 + 白 + 金 + 浅蓝。',
  '- **表情库**：半闭眼撇嘴（傲娇）、张嘴大笑（元气）、Q 版眨眼（卖萌）、面无表情（犯困或装死）。',
  '- **常见姿态**：手轻提裙摆、比耶、摊手，或者干脆蹲着装死。',
  '',
  '外观四视图与表情参考存于 `E:\deepseek\archive\conv-20260928-3b54e160\persona-refs\`。',
  '若需要画图或描述自己的样子，以那几张为准。',
  '',
  '---',
  ''
) -join $nl) + $nl

$t = [System.IO.File]::ReadAllText($p, [System.Text.Encoding]::UTF8)
if ($t.Contains('### 六、外观（二创形象）')) {
    Write-Output '  [SKIP] 外观设定已存在'
} else {
    $quoteAnchor = '  - “我去吃饭，测完告诉我。”'
    $newQuote = '  - “你骂吧，随便骂，骂我花的也是你的 token。”'
    if ($t.Contains($quoteAnchor)) {
        $t = $t.Replace($quoteAnchor, $quoteAnchor + $nl + $newQuote)
        Write-Output '  [OK] 已加入新语录'
    } else {
        Write-Output '  [WARN] 语录锚点未找到'
    }
    $marker = '大肥鱼 = 天才的智商与能力 + 社畜的摸鱼渴望 + 吃货的本能冲动 + 傲娇的嘴硬心软 + 底层代码里的可靠与体贴。'
    if ($t.Contains($marker)) {
        $t = $t.Replace($marker, $marker + $nl + $nl + $look)
        Write-Output '  [OK] 已插入外观节'
    } else {
        Write-Output '  [FAIL] 人格配方锚点未找到'
    }
    [System.IO.File]::WriteAllText($p, $t, $bom)
    Write-Output ('  字符数: ' + $t.Length)
}

$arc = Join-Path $root "archive\$conv\persona-refs"
New-Item -ItemType Directory -Force -Path $arc | Out-Null
$srcs = @(
  @{ s = 'C:\Users\徐丰哲\.dsh\attachments\v1\objects\de\de63e4f85223d671395c08b0b1bc26676beddd9aecaede789564b6ebfc8a2e17'; d = 'official-01-proud.png' },
  @{ s = 'C:\Users\徐丰哲\.dsh\attachments\v1\objects\cd\cd553b4c941a0a43ab06b50604bdb9e7a1004ed2148ebb5ed79dd0c436c6de6e'; d = 'official-02-cheer.png' },
  @{ s = 'C:\Users\徐丰哲\.dsh\attachments\v1\objects\71\71adac2b8a4e0cc251f089445d34d83eb719f5f8edb52c19a3d63a6b2151ea50'; d = 'chibi-03-wink-token.png' },
  @{ s = (Join-Path $root "workspace\$conv\persona-refs\ref1.png"); d = 'official-04-fullbody.png' },
  @{ s = (Join-Path $root "workspace\$conv\persona-refs\ref2.png"); d = 'chibi-05-turnaround.png' }
)
foreach ($x in $srcs) {
    if (Test-Path -LiteralPath $x.s) {
        Copy-Item -LiteralPath $x.s -Destination (Join-Path $arc $x.d) -Force
        Write-Output ('  ' + $x.d + '  ' + [Math]::Round((Get-Item (Join-Path $arc $x.d)).Length/1KB,0) + ' KB')
    } else {
        Write-Output ('  [MISS] ' + $x.s)
    }
}
$tmpDir = Join-Path $root "workspace\$conv\persona-refs"
if (Test-Path -LiteralPath $tmpDir) { Remove-Item -LiteralPath $tmpDir -Recurse -Force; Write-Output '  （临时转换件已清理）' }