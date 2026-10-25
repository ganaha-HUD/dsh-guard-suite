<#
# 说明：本脚本为 2026-10-11 重建版（原件随 E: 盘清空丢失）；结构与功能按原版语义重建，
#       并经语法校验与实际运行验证。
  New-ConversationWorkspace.ps1 - 幂等：为当前对话在六个类别目录下建立统一的子目录。
  规则来源：policy\storage-policy.json（类别、conv-id 命名、登记表）。
  用法：powershell.exe -NoProfile -ExecutionPolicy Bypass -File E:\Deepseek\tools\New-ConversationWorkspace.ps1
#>
param([string]$Root = '')

# 工作区根目录：默认从本脚本位置推断（tools\ 的上一级），因此本脚本可从任意工作区运行。
# 显式传入 -Root 仍可覆盖，向后兼容。
if (-not $Root) { $Root = Split-Path -Parent $PSScriptRoot }
$ErrorActionPreference = 'Stop'

function Read-Utf8Json([string]$Path) {
    return ([System.IO.File]::ReadAllText($Path, [System.Text.Encoding]::UTF8) | ConvertFrom-Json)
}

# 1) 类别来自策略（缺省回退到固定六类）
$policyPath = Join-Path $Root 'policy\storage-policy.json'
if (Test-Path -LiteralPath $policyPath) {
    $policy = Read-Utf8Json -Path $policyPath
    $categories = @($policy.categories | ForEach-Object { $_.folder })
} else {
    $categories = @('deliverables', 'logs', 'scripts', 'workspace', 'data', 'archive')
}

# 2) 解析本对话的 conv-id
#    规则：一个对话只有一个 ID。若登记表里已存在同一 token 的条目，直接复用它的 ID
#    （这样磁盘清空后重建、或跨天继续同一对话，都不会产生第二个 ID）。
$sid = $env:DSH_SESSION_ID
if ($sid -and ($sid -match '([0-9a-fA-F]{8})-')) {
    $token = $Matches[1].ToLower()
} else {
    $token = (Get-Date).ToString('HHmmss')
}
$regPath = Join-Path $Root 'policy\conversation-registry.json'
$registry = $null
if (Test-Path -LiteralPath $regPath) { $registry = Read-Utf8Json -Path $regPath }

$convId = $null
if ($registry) {
    $reuse = @($registry.conversations | Where-Object {
        $_.folder -like ('*-' + $token) -and $_.folder -match '^conv-[0-9]{8}-'
    })
    if ($reuse.Count -gt 0) {
        $convId = [string]$reuse[0].folder
        Write-Output ("reusing registered conversation id: " + $convId)
    }
}
if (-not $convId) { $convId = 'conv-' + (Get-Date).ToString('yyyyMMdd') + '-' + $token }

# 3) 建目录（幂等）
foreach ($c in $categories) {
    $dir = Join-Path $Root ($c + '\' + $convId)
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
}
New-Item -ItemType Directory -Force -Path (Join-Path $Root 'reference_file') | Out-Null

# 4) 登记（已存在则复用，不另建）
if ($registry) {
    $reg = $registry
    $exists = @($reg.conversations | Where-Object { $_.folder -eq $convId }).Count -gt 0
    if (-not $exists) {
        $entry = [pscustomobject]@{
            folder    = $convId
            createdAt = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
            status    = 'active'
            note      = 'created by New-ConversationWorkspace.ps1'
        }
        $reg.conversations = @($reg.conversations) + $entry
        [System.IO.File]::WriteAllText($regPath, (($reg | ConvertTo-Json -Depth 8) + "`r`n"),
            (New-Object System.Text.UTF8Encoding($false)))
        Write-Output ("registered: " + $convId)
    } else {
        Write-Output ("already registered: " + $convId)
    }
}

Write-Output ("conversation folder: " + $convId)
Write-Output ("categories: " + ($categories -join ', '))
