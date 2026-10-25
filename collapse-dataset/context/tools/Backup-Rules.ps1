<#
  Backup-Rules.ps1 - 把规则本体备份到系统盘（与 E 盘物理分离）。
  备份对象：AGENTS.md、README.md、policy\**、tools\**（**不含**对话产物）
  目标    ：%USERPROFILE%\Documents\Deepseek-rules-backup\<yyyyMMdd-HHmmss>\
  校验    ：逐文件 SHA-256 比对源与副本，任何不一致即 FAIL
  保留    ：默认最近 5 份，更旧的自动清理（-Keep 可调）

  规则依据：policy\output-storage-policy.md §12、AGENTS.md 规则 8
  运行条件：**需要非只读模式**（workspace-write 或 danger-full-access）：
            只读模式下 PowerShell 处于 ConstrainedLanguage，本脚本无法写 C 盘。
  用法    ：powershell.exe -NoProfile -ExecutionPolicy Bypass -File E:\Deepseek\tools\Backup-Rules.ps1
#>
param(
    [string]$Root = '',
    [string]$DestBase = (Join-Path $env:USERPROFILE 'Documents\Deepseek-rules-backup'),
    [int]$Keep = 5
)

# 工作区根目录：默认从本脚本位置推断（tools\ 的上一级），因此本脚本可从任意工作区运行。
# 显式传入 -Root 仍可覆盖，向后兼容。
if (-not $Root) { $Root = Split-Path -Parent $PSScriptRoot }
$ErrorActionPreference = 'Stop'
$stamp = (Get-Date).ToString('yyyyMMdd-HHmmss')
$dest = Join-Path $DestBase $stamp
Write-Output ('[info] Root=' + $Root + ' DestBase=' + $DestBase)

# 1) 建目录并复制规则本体
New-Item -ItemType Directory -Force -Path (Join-Path $dest 'policy\deploy') | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $dest 'tools') | Out-Null
Copy-Item -LiteralPath (Join-Path $Root 'AGENTS.md') -Destination $dest -Force
Copy-Item -LiteralPath (Join-Path $Root 'README.md') -Destination $dest -Force
Copy-Item -Path ([System.IO.Path]::Combine($Root, 'policy\*')) -Destination ([System.IO.Path]::Combine($dest, 'policy')) -Recurse -Force
Copy-Item -Path ([System.IO.Path]::Combine($Root, 'tools\*')) -Destination ([System.IO.Path]::Combine($dest, 'tools')) -Recurse -Force

# 2) 附上还原说明（模板复制，避免写入时的编码/BOM 问题）
$tpl = [System.IO.Path]::Combine($Root, 'tools\backup-readme-template.md')
if (Test-Path -LiteralPath $tpl) {
    Copy-Item -LiteralPath $tpl -Destination (Join-Path $dest 'BACKUP-README.md') -Force
} else {
    Write-Output '[WARN] template missing: tools\backup-readme-template.md'
}

# 3) 校验：逐文件 SHA-256
$checked = 0
$failed = 0
foreach ($f in (Get-ChildItem -LiteralPath $dest -Recurse -File)) {
    if ($f.Name -eq 'BACKUP-README.md') { continue }
    $rel = $f.FullName.Substring($dest.Length + 1)
    $src = Join-Path $Root $rel
    if (-not (Test-Path -LiteralPath $src)) {
        Write-Output ('[FAIL] source missing: ' + $rel)
        $failed++
        continue
    }
    $h1 = (Get-FileHash -LiteralPath $f.FullName -Algorithm SHA256).Hash
    $h2 = (Get-FileHash -LiteralPath $src -Algorithm SHA256).Hash
    $checked++
    if ($h1 -ne $h2) {
        Write-Output ('[FAIL] checksum mismatch: ' + $rel)
        $failed++
    }
}
Write-Output ('[verify] checked ' + $checked + ' files, failures ' + $failed)
Write-Output ('[dest]   ' + $dest)

# 4) 保留策略
$all = @(Get-ChildItem -LiteralPath $DestBase -Directory | Sort-Object Name -Descending)
if ($all.Count -gt $Keep) {
    foreach ($old in ($all | Select-Object -Skip $Keep)) {
        Remove-Item -LiteralPath $old.FullName -Recurse -Force
        Write-Output ('[pruned] ' + $old.Name)
    }
    $all = @(Get-ChildItem -LiteralPath $DestBase -Directory | Sort-Object Name -Descending)
}
Write-Output ('[kept]   ' + $all.Count + ' backup(s), newest first: ' + ($all | Select-Object -First 3 | ForEach-Object { $_.Name }) -join ', ')

if ($failed -gt 0) { exit 1 } else { exit 0 }