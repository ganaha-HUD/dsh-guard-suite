<#
# 说明：本脚本为 2026-10-11 重建版（原件随 E: 盘清空丢失）；结构与功能按原版语义重建，
#       并经语法校验与实际运行验证。
  Install-GlobalPolicy.ps1 - 把 policy\deploy\global-agents.md 部署为 %USERPROFILE%\.dsh\AGENTS.md
  （DSH 会把它自动注入到每一个对话、每一个工作区）。带时间戳备份；内容相同则不动。
  用法：powershell.exe -NoProfile -ExecutionPolicy Bypass -File E:\Deepseek\tools\Install-GlobalPolicy.ps1
#>
param([string]$Root = '')

# 工作区根目录：默认从本脚本位置推断（tools\ 的上一级），因此本脚本可从任意工作区运行。
# 显式传入 -Root 仍可覆盖，向后兼容。
if (-not $Root) { $Root = Split-Path -Parent $PSScriptRoot }
$ErrorActionPreference = 'Stop'

$src = Join-Path $Root 'policy\deploy\global-agents.md'
$dstDir = Join-Path $env:USERPROFILE '.dsh'
$dst = Join-Path $dstDir 'AGENTS.md'

if (-not (Test-Path -LiteralPath $src)) { throw ("源文件不存在: " + $src) }
New-Item -ItemType Directory -Force -Path $dstDir | Out-Null

$new = [System.IO.File]::ReadAllText($src, [System.Text.Encoding]::UTF8)

if (Test-Path -LiteralPath $dst) {
    $old = [System.IO.File]::ReadAllText($dst, [System.Text.Encoding]::UTF8)
    if ($old -eq $new) {
        Write-Output 'already up to date, nothing written'
        return
    }
    $bak = $dst + '.bak-' + (Get-Date).ToString('yyyyMMdd-HHmmss')
    Copy-Item -LiteralPath $dst -Destination $bak -Force
    Write-Output ("backup: " + (Split-Path -Leaf $bak))
    Write-Output ("old size: " + $old.Length + " chars / new size: " + $new.Length + " chars")
}

[System.IO.File]::WriteAllText($dst, $new, (New-Object System.Text.UTF8Encoding($false)))
Write-Output 'Deploying the user-global instruction file'
Write-Output ("  source: " + $src)
Write-Output ("  target: " + $dst)
Write-Output '  result: global AGENTS.md deployed; new conversations will load it automatically'
