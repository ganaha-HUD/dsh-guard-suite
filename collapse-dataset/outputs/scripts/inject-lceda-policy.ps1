$ErrorActionPreference = 'Stop'
$root = 'E:\deepseek'
$nl = "`r`n"
$noBom = New-Object System.Text.UTF8Encoding($false)
$bom = New-Object System.Text.UTF8Encoding($true)

# ---------- 1) update deployment status in the policy markdown ----------
$mdp = Join-Path $root 'policy\lceda-eda-policy.md'
$lines = [System.IO.File]::ReadAllLines($mdp, [System.Text.Encoding]::UTF8)
$hit = -1
for ($i = 0; $i -lt $lines.Count; $i++) {
    if ($lines[$i].Contains('部署状态：未全局注入')) { $hit = $i; break }
}
if ($hit -ge 0) {
    $lines[$hit] = '- **部署状态：已全局注入**（2026-10-21）。`policy\deploy\global-agents.md` 的规则 9 只放触发条件与四条铁律；'
    if (($hit + 1) -lt $lines.Count -and $lines[$hit + 1].Contains('或人工把它登记进')) {
        $lines[$hit + 1] = '  完整规则按需读取本文件，机器可读版 `policy\lceda-eda.json`'
    }
    [System.IO.File]::WriteAllLines($mdp, $lines, $noBom)
    Write-Output '  [OK] md deployment status updated'
} else {
    Write-Output '  [SKIP] md status anchor not found (already updated?)'
}

# ---------- 2) update deployment field in the json ----------
$jp = Join-Path $root 'policy\lceda-eda.json'
$jt = [System.IO.File]::ReadAllText($jp, [System.Text.Encoding]::UTF8)
$oldj = '"deployment": "NOT injected globally; read this file explicitly or register it in policy\\deploy\\global-agents.md before running Install-GlobalPolicy.ps1"'
$newj = '"deployment": "INJECTED globally 2026-10-21 as rule 9 of policy/deploy/global-agents.md (trigger plus four iron rules only); read this file for the full ruleset"'
if ($jt.Contains($oldj)) {
    $jt = $jt.Replace($oldj, $newj)
    [System.IO.File]::WriteAllText($jp, $jt, $noBom)
    Write-Output '  [OK] json deployment field updated'
} else {
    Write-Output '  [SKIP] json anchor not found (already updated?)'
}

# ---------- 3) append rule 9 to the global layer ----------
$gp = Join-Path $root 'policy\deploy\global-agents.md'
$g = [System.IO.File]::ReadAllText($gp, [System.Text.Encoding]::UTF8)
if ($g.Contains('## 规则 9 · 嘉立创EDA')) {
    Write-Output '  [SKIP] rule 9 already present'
} else {
    $rule = (@(
      '',
      '## 规则 9 · 嘉立创EDA 专业版自动化（按需读取）',
      '',
      '**触发**：任何要操作嘉立创EDA（原理图 / PCB / 网表 / BOM / Gerber / 图片转原理图）的对话。',
      '',
      '**先读**：`E:\Deepseek\policy\lceda-eda-policy.md`（机器可读 `policy\lceda-eda.json`）',
      '—— 含环境前置、invoke 硬约束、版本差异、原理图与 PCB 的 API 用法、**返回 true 却什么都不写的接口清单**、',
      '图片→原理图流程、数据安全、标准工作流与验证清单。细节一律看该文件，不要凭记忆写代码。',
      '',
      '**四条铁律**：',
      '',
      '1. **不要用返回值 `true` 判断成功**：`pcb_Document.importChanges()` 与 `pcb_Net.setNetlist()` 都返回 true 而实际不写；',
      '   `sch_Netlist.getNetlist()` 已废弃、一调就卡满 60 s。必须用 `getAll()` 数量与磁盘文件大小交叉验证。',
      '2. **不在用户真实工程上做实验**：一律新建测试工程；**升级客户端前先备份 `projects`**（实测升级会整目录清空，旧目录进回收站）。',
      '3. **不自己算引脚/焊盘坐标**：一律用 `getAllPinsByPrimitiveId()` 读回。',
      '4. **调用 CLI 前必须清除 `ELECTRON_RUN_AS_NODE`**（本机 shell 默认就设着它），编辑器须已打开且 `doctor` 返回 `connected:true`；',
      '   PCB 写入类操作要求 **4.1.78+**（本机即为 4.1.78）。',
      ''
    ) -join $nl) + $nl
    [System.IO.File]::WriteAllText($gp, ($g.TrimEnd() + $nl + $rule), $bom)
    Write-Output '  [OK] rule 9 appended to global layer'
}
Write-Output ('  global layer chars: ' + ([System.IO.File]::ReadAllText($gp, [System.Text.Encoding]::UTF8)).Length)