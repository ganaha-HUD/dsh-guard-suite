<#
  Check-GuardPlugin.ps1 - 检查 dsh-guard-repeat-output 是否装上、启用，以及是否真的拦过。
  用法：
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File E:\Deepseek\scripts\conv-20260928-3b54e160\check-guard-plugin.ps1
  判据：
    安装 = package.json 的 dependencies 含该包，且 node_modules 下有包体
    启用 = package.json 的 dsh.profile.bundles 含该包（cordis.yml：树先由 bundles 组合，再是 profile patch）
    生效 = ~/.dsh/logs/dsh-guard-repeat-output.log 或 ~/.dsh/logs/guard-repeat-output-pruned\ 出现内容
#>
param(
    [string]$Profile = (Join-Path $env:USERPROFILE '.dsh\profiles\desktop'),
    [string]$DshHome = (Join-Path $env:USERPROFILE '.dsh')
)

$pkgName = 'dsh-guard-repeat-output'
$pj = Join-Path $Profile 'package.json'
if (-not (Test-Path -LiteralPath $pj)) { Write-Output ('[FAIL] missing ' + $pj); exit 2 }
$j = [System.IO.File]::ReadAllText($pj, [System.Text.Encoding]::UTF8) | ConvertFrom-Json

$depValue = 'MISSING'
if ($j.dependencies) {
    $p = $j.dependencies.PSObject.Properties[$pkgName]
    if ($p) { $depValue = [string]$p.Value }
}
Write-Output ('[1] dependency      : ' + $depValue)

$bundles = @()
if ($j.dsh -and $j.dsh.profile -and $j.dsh.profile.bundles) { $bundles = @($j.dsh.profile.bundles) }
$enabled = $bundles -contains $pkgName
Write-Output ('[2] enabled in bundle: ' + $enabled)
Write-Output ('    bundles          : ' + ($bundles -join ', '))

$pkgDir = Join-Path $Profile ('node_modules\' + $pkgName)
$installed = Test-Path -LiteralPath $pkgDir
$fileCount = 0
$ver = '?'
if ($installed) {
    $fileCount = @(Get-ChildItem -LiteralPath $pkgDir -Recurse -File).Count
    $pj2 = Join-Path $pkgDir 'package.json'
    if (Test-Path -LiteralPath $pj2) { $ver = ([System.IO.File]::ReadAllText($pj2, [System.Text.Encoding]::UTF8) | ConvertFrom-Json).version }
}
Write-Output ('[3] package on disk : ' + $installed + '   version ' + $ver + '   files ' + $fileCount)

$log = Join-Path $DshHome 'logs\dsh-guard-repeat-output.log'
if (Test-Path -LiteralPath $log) {
    $li = Get-Item -LiteralPath $log
    Write-Output ('[4] conviction log  : present  ' + [Math]::Round($li.Length / 1KB, 1) + ' KB  last ' + $li.LastWriteTime)
} else {
    Write-Output '[4] conviction log  : not yet (nothing intercepted so far)'
}
$pruned = Join-Path $DshHome 'logs\guard-repeat-output-pruned'
if (Test-Path -LiteralPath $pruned) {
    $pc = @(Get-ChildItem -LiteralPath $pruned -File).Count
    Write-Output ('[5] discarded copies: present  ' + $pc + ' file(s)')
} else {
    Write-Output '[5] discarded copies: not yet (same reason)'
}

$proc = @(Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.ProcessName -eq 'DeepSeek Harness' })
$verdict = 'NOT ready - install and enable it in the DSH Plugins page, then restart DSH.'
if ($depValue -ne 'MISSING' -and $enabled -and $installed) {
    $verdict = 'OK - installed and enabled.'
    if ($proc.Count -gt 0) {
        $start = ($proc | Sort-Object StartTime | Select-Object -First 1).StartTime
        $pkgTime = (Get-Item -LiteralPath (Join-Path $pkgDir 'package.json')).LastWriteTime
        if ($pkgTime -gt $start) {
            $verdict = 'WARNING - package is NEWER than the running process; restart DSH to load it.'
        }
        Write-Output ('[6] dsh process     : started ' + $start + '   package ' + $pkgTime)
    }
}
Write-Output ''
Write-Output ('VERDICT: ' + $verdict)