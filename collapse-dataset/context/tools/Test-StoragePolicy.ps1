<#
# 说明：本脚本为 2026-10-11 重建版（原件随 E: 盘清空丢失）；结构与功能按原版语义重建，
#       并经语法校验与实际运行验证。
  Test-StoragePolicy.ps1 - 存放准则自检（六段）
    1 策略文件        2 类别目录      3 根目录白名单
    4 登记表 + 对话目录  5 命名合规    6 reference_file 只读性
  用法：
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File E:\Deepseek\tools\Test-StoragePolicy.ps1
    ... -Json   # 以 JSON 输出
#>
param([string]$Root = '', [switch]$Json)

# 工作区根目录：默认从本脚本位置推断（tools\ 的上一级），因此本脚本可从任意工作区运行。
# 显式传入 -Root 仍可覆盖。
if (-not $Root) { $Root = Split-Path -Parent $PSScriptRoot }

$findings = New-Object System.Collections.ArrayList

function Read-Utf8Json([string]$Path) {
    return ([System.IO.File]::ReadAllText($Path, [System.Text.Encoding]::UTF8) | ConvertFrom-Json)
}
function Get-PropertyValue($Object, [string]$Name, $Default = $null) {
    if ($null -eq $Object) { return $Default }
    $p = $Object.PSObject.Properties[$Name]
    if ($p) { return $p.Value }
    return $Default
}
function Test-AsciiName([string]$Name) {
    return ($Name -cmatch '^[A-Za-z0-9._-]+$')
}
function Add-Finding([string]$Status, [string]$Message) {
    [void]$findings.Add([pscustomobject]@{ status = $Status; message = $Message })
}

# ---- 1. 策略文件
$policyPath = Join-Path $Root 'policy\storage-policy.json'
$policy = $null
if (-not (Test-Path -LiteralPath $policyPath)) {
    Add-Finding 'FAIL' 'policy file missing: policy\storage-policy.json'
} else {
    try {
        $policy = Read-Utf8Json -Path $policyPath
        Add-Finding 'PASS' ("policy file parses: policy\storage-policy.json (version " + (Get-PropertyValue $policy 'policyVersion' '?') + ")")
    } catch {
        Add-Finding 'FAIL' ("policy file is not valid JSON: " + $_.Exception.Message)
    }
}

# ---- 2. 类别目录
$categoryObjects = @(Get-PropertyValue $policy 'categories' @())
$categories = @($categoryObjects | ForEach-Object { [string](Get-PropertyValue $_ 'folder') })
if ($categories.Count -eq 0) { $categories = @('deliverables', 'logs', 'scripts', 'workspace', 'data', 'archive') }
foreach ($category in $categories) {
    if (Test-Path -LiteralPath (Join-Path $Root $category)) {
        Add-Finding 'PASS' ("category folder exists: " + $category)
    } else {
        Add-Finding 'FAIL' ("category folder missing: " + $category)
    }
    if (-not (Test-AsciiName -Name $category)) {
        Add-Finding 'FAIL' ("category folder name is not ASCII: " + $category)
    }
}

# ---- 3. 根目录白名单
$allow = New-Object System.Collections.ArrayList
$allowList = Get-PropertyValue $policy 'rootAllowList' $null
if ($allowList) { foreach ($a in @($allowList)) { [void]$allow.Add([string]$a) } }
if ($allow.Count -eq 0) {
    foreach ($a in @('AGENTS.md', 'README.md', 'policy', 'tools', 'reference_file', 'eim_config.toml')) { [void]$allow.Add($a) }
    foreach ($c in $categories) { if (-not $allow.Contains($c)) { [void]$allow.Add($c) } }
}
$stray = New-Object System.Collections.ArrayList
foreach ($item in Get-ChildItem -LiteralPath $Root -Force) {
    if (-not $allow.Contains($item.Name)) { [void]$stray.Add($item.Name) }
}
if ($stray.Count -eq 0) {
    Add-Finding 'PASS' 'workspace root contains only allow-listed entries'
} else {
    Add-Finding 'WARN' ("workspace root has entries outside the allow list: " + ($stray -join ', '))
}

# ---- 4. 登记表 + 对话目录
$regPath = Join-Path $Root 'policy\conversation-registry.json'
if (-not (Test-Path -LiteralPath $regPath)) {
    Add-Finding 'FAIL' 'conversation registry missing: policy\conversation-registry.json'
} else {
    try {
        $registry = Read-Utf8Json -Path $regPath
        $conversations = @(Get-PropertyValue $registry 'conversations' @())
        Add-Finding 'PASS' ("conversation registry parses; registered conversations: " + $conversations.Count)
        $regex = [string](Get-PropertyValue $registry 'regex' '^conv-[0-9]{8}-([0-9a-f]{8}|[0-9]{6})(-[a-z0-9]{2,32})?$')
        foreach ($entry in $conversations) {
            $folder = [string](Get-PropertyValue $entry 'folder')
            $status = [string](Get-PropertyValue $entry 'status' 'active')
            if (-not $folder) { Add-Finding 'FAIL' 'registry entry without a folder name'; continue }
            if ($folder -notmatch $regex) { Add-Finding 'FAIL' ("registry folder does not match the pattern: " + $folder) }
            if ($status -eq 'lost') {
                Add-Finding 'PASS' ("historical conversation recorded as lost (disk wipe), folder check skipped: " + $folder)
                continue
            }
            $missing = New-Object System.Collections.ArrayList
            foreach ($category in $categories) {
                if (-not (Test-Path -LiteralPath (Join-Path (Join-Path $Root $category) $folder))) { [void]$missing.Add($category) }
            }
            if ($missing.Count -eq 0) {
                Add-Finding 'PASS' ("conversation folder present in every category: " + $folder)
            } else {
                Add-Finding 'WARN' ("conversation folder missing in: " + ($missing -join ', ') + " (" + $folder + ")")
            }
        }
    } catch {
        Add-Finding 'FAIL' ("conversation registry is not valid JSON: " + $_.Exception.Message)
    }
}

# ---- 5. 命名合规（类别目录内）
$badNames = New-Object System.Collections.ArrayList
foreach ($category in $categories) {
    $dir = Join-Path $Root $category
    if (-not (Test-Path -LiteralPath $dir)) { continue }
    foreach ($child in Get-ChildItem -LiteralPath $dir -Force -Directory) {
        if (-not (Test-AsciiName -Name $child.Name)) { [void]$badNames.Add($category + '\' + $child.Name) }
    }
    foreach ($file in Get-ChildItem -LiteralPath $dir -Force -File -Recurse -ErrorAction SilentlyContinue) {
        if (-not (Test-AsciiName -Name $file.Name)) { [void]$badNames.Add($category + '\...\' + $file.Name) }
    }
}
if ($badNames.Count -eq 0) {
    Add-Finding 'PASS' 'no non-ASCII names found under the category folders'
} else {
    Add-Finding 'WARN' ("non-ASCII names found (compatibility risk): " + (($badNames | Select-Object -First 10) -join '; '))
}

# ---- 6. reference_file（用户投放目录，Agent 只读）
$refCfg = Get-PropertyValue $policy 'referenceFolder' $null
$referenceFolder = [string](Get-PropertyValue $refCfg 'folder' 'reference_file')
if (-not $referenceFolder) { $referenceFolder = 'reference_file' }
$refPath = Join-Path $Root $referenceFolder
if (-not (Test-Path -LiteralPath $refPath)) {
    Add-Finding 'FAIL' ("reference folder missing: " + $referenceFolder)
} else {
    $refFiles = @(Get-ChildItem -LiteralPath $refPath -Force -File -Recurse -ErrorAction SilentlyContinue)
    Add-Finding 'PASS' ("reference folder present; user-provided files: " + $refFiles.Count)
    $suspicious = New-Object System.Collections.ArrayList
    foreach ($f in $refFiles) {
        if ($f.Name -match '(?i)\.(tmp|part|bak|log)$' -or $f.Name -match '^untitled' -or $f.Name -match '^conv-') {
            [void]$suspicious.Add($f.Name)
        }
    }
    foreach ($d in @(Get-ChildItem -LiteralPath $refPath -Force -Directory -ErrorAction SilentlyContinue)) {
        if ($d.Name -match '^conv-') { [void]$suspicious.Add($d.Name + '\') }
    }
    if ($suspicious.Count -eq 0) {
        Add-Finding 'PASS' 'no agent-generated artifacts detected in the reference folder'
    } else {
        Add-Finding 'WARN' ("possible agent artifacts inside the reference folder (it must stay agent read-only): " + (($suspicious | Select-Object -First 10) -join ', '))
    }
}

# ---- 报告
$fail = @($findings | Where-Object { $_.status -eq 'FAIL' }).Count
$warn = @($findings | Where-Object { $_.status -eq 'WARN' }).Count

if ($Json) {
    [pscustomobject]@{
        workspaceRoot = $Root
        fail          = $fail
        warn          = $warn
        findings      = $findings
    } | ConvertTo-Json -Depth 6
} else {
    foreach ($f in $findings) { Write-Output ('[' + $f.status + '] ' + $f.message) }
    Write-Output ''
    Write-Output ("Summary: FAIL=" + $fail + " WARN=" + $warn)
}

if ($fail -gt 0) { exit 1 } else { exit 0 }
