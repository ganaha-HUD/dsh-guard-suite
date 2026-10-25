import re

P = r"E:\deepseek\tools\New-ConversationWorkspace.ps1"
t = open(P, encoding="utf-8").read()

old = """# 2) 解析本对话的 conv-id
$sid = $env:DSH_SESSION_ID
if ($sid -and ($sid -match '([0-9a-fA-F]{8})-')) {
    $token = $Matches[1].ToLower()
} else {
    $token = (Get-Date).ToString('HHmmss')
}
$convId = 'conv-' + (Get-Date).ToString('yyyyMMdd') + '-' + $token
"""
new = """# 2) 解析本对话的 conv-id
#    规则：一个对话只有一个 ID。若登记表里已存在同一 token 的条目，直接复用它的 ID
#    （这样磁盘清空后重建、或跨天继续同一对话，都不会产生第二个 ID）。
$sid = $env:DSH_SESSION_ID
if ($sid -and ($sid -match '([0-9a-fA-F]{8})-')) {
    $token = $Matches[1].ToLower()
} else {
    $token = (Get-Date).ToString('HHmmss')
}
$regPath = Join-Path $Root 'policy\\conversation-registry.json'
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
"""
if old in t:
    t = t.replace(old, new, 1)
    print("[OK] 脚本已改为优先复用登记 ID")
else:
    print("[FAIL] 锚点未找到")

# 登记段：改用上面已读出的 $registry，避免重复读取
old2 = """# 4) 登记（已存在则复用，不另建）
$regPath = Join-Path $Root 'policy\\conversation-registry.json'
if (Test-Path -LiteralPath $regPath) {
    $reg = Read-Utf8Json -Path $regPath
"""
new2 = """# 4) 登记（已存在则复用，不另建）
if ($registry) {
    $reg = $registry
"""
if old2 in t:
    t = t.replace(old2, new2, 1)
    print("[OK] 登记段改用已读出的 registry")
else:
    print("[FAIL] 登记段锚点未找到")

open(P, "w", encoding="utf-8", newline="\r\n").write(t)