import json

policy = {
    "policyVersion": "1.3.0",
    "updatedAt": "2026-10-05",
    "rebuiltAt": "2026-10-11",
    "rebuiltNote": ("重建版：原文件随 E: 盘清空丢失；本文件按 2026-10-05 审计后的 v1.3.0 结构与内容重建，"
                    "字段结构与规则语义一致，个别英文描述文字为重新撰写。"),
    "workspaceRoot": "E:\\Deepseek",
    "policyDoc": "policy\\output-storage-policy.md",
    "globalAgentsSource": "policy\\deploy\\global-agents.md",
    "naming": {
        "charset": "ASCII only: A-Z a-z 0-9 . _ -",
        "case": "lowercase",
        "wordSeparator": "-",
        "forbidden": ["CJK characters", "spaces", "emoji", "full-width characters",
                      "Windows reserved names (CON PRN AUX NUL COM1-9 LPT1-9)"],
        "maxFileNameLength": 100,
        "timestampFormat": "yyyyMMdd-HHmmss",
        "note": "user-provided files inside reference_file are exempt from the ASCII rule (CJK allowed)"
    },
    "categories": [
        {"key": "deliverables", "folder": "deliverables", "labelZh": "交付",
         "purpose": "final artifacts handed to the user", "filePattern": "<topic>-<version>.<ext>"},
        {"key": "logs", "folder": "logs", "labelZh": "日志",
         "purpose": "command output, run logs, session metadata", "filePattern": "<yyyyMMdd-HHmmss>-<tool>.log"},
        {"key": "scripts", "folder": "scripts", "labelZh": "执行脚本",
         "purpose": "scripts written for this conversation", "filePattern": "<verb>-<noun>.ps1/.py/.sh/.bat"},
        {"key": "workspace", "folder": "workspace", "labelZh": "中间产物",
         "purpose": "temporary files and build intermediates", "filePattern": "free, still subject to naming"},
        {"key": "data", "folder": "data", "labelZh": "输入数据",
         "purpose": "input datasets, samples, fixtures", "filePattern": "free, still subject to naming"},
        {"key": "archive", "folder": "archive", "labelZh": "归档",
         "purpose": "superseded versions and closed-out material", "filePattern": "free, still subject to naming"}
    ],
    "sharedFolders": [
        {"folder": "policy", "purpose": "this standard: documents, machine-readable config, deploy staging"},
        {"folder": "tools", "purpose": "workspace-level tooling of the standard itself (not conversation scoped)"}
    ],
    "referenceFolder": {
        "folder": "reference_file",
        "scope": "shared across conversations (not conversation scoped)",
        "purpose": "user-provided reference material: datasheets, papers, images, samples",
        "owner": "user only",
        "agentAccess": "read-only",
        "rules": [
            "the agent must never delete, move, rename or overwrite anything inside this folder",
            "user-provided files are exempt from the ASCII naming rule (CJK names allowed)",
            "files the agent creates here must still follow the naming rule",
            "subfolders are allowed; reads are recursive",
            "cleanup or archiving happens only on an explicit user request"
        ]
    },
    "rootAllowList": ["AGENTS.md", "README.md", "policy", "tools", "reference_file",
                      "deliverables", "logs", "scripts", "workspace", "data", "archive"],
    "conversationFolder": {
        "pattern": "conv-<yyyyMMdd>-<token>",
        "tokenSource": "first 8 lowercase hex chars of $env:DSH_SESSION_ID UUID; fallback local time HHmmss",
        "regex": "^conv-[0-9]{8}-([0-9a-f]{8}|[0-9]{6})(-[a-z0-9]{2,32})?$",
        "sharedAcrossCategories": True,
        "registry": "policy\\conversation-registry.json",
        "note": "one conversation uses the SAME folder name under every category; reuse if already registered"
    },
    "runtimeEnvironment": {
        "root": "D:\\program_runtime_environment",
        "layout": "<root>\\<category>[\\<version>]\\...",
        "categoryRule": ("one top-level folder per language/tool family, lowercase English, no spaces; "
                         "never mix two environments in one folder"),
        "categories": ["nodejs", "python", "java", "dotnet", "go", "rust", "cli", "browsers", "databases", "caches"],
        "downloads": "_downloads",
        "packageCaches": "_caches\\<tool>",
        "verification": "verify the vendor SHA-256 and the Authenticode signature (must be Valid) before installing",
        "registry": "D:\\program_runtime_environment\\registry.json",
        "registryTool": "D:\\program_runtime_environment\\tools\\Add-RuntimeEnvironment.ps1"
    },
    "aiRoot": {
        "root": "D:\\AI_file",
        "scope": "all local-AI deployment files (user-designated)",
        "layout": ("runtime\\<family>\\<version>, tools\\<name>\\<version>, envs\\<purpose>, models, datasets, "
                   "outputs, logs, workspace, mcp (MCP servers), _downloads, _caches"),
        "rootFiles": ["README.md", "registry.json"],
        "registry": "D:\\AI_file\\registry.json",
        "rule": "AI runtimes, models, datasets and venvs never go into program_runtime_environment"
    },
    "outputRules": [
        "no output files in the workspace root; the root only holds AGENTS.md, README.md, policy, tools, the reference_file drop folder and the category folders",
        "every generated file lives under <category>\\<conversation-id>\\",
        "logs longer than about 50 lines go to logs\\<conv-id>\\; the chat shows only the path and a summary",
        "when a deliverable is superseded, move the old version into archive\\<conv-id>\\ instead of overwriting it",
        "shared tooling belongs in tools\\, not in scripts\\"
    ],
    "environmentConstraints": {
        "workspaceVolume": "exFAT removable volume (no hardlink support)",
        "impact": "the DSH write/edit file tools fail with EISDIR on this volume; create and update files through PowerShell instead",
        "shell": "Windows PowerShell 5.1 (no pwsh)",
        "encoding": "write UTF-8 without BOM via [System.IO.File]::WriteAllText with UTF8Encoding($false); read with explicit UTF-8",
        "tls": "Invoke-WebRequest and curl.exe fail inside the sandbox; download with node instead",
        "temp": "point $env:TEMP/$env:TMP at a folder inside the workspace before running pip/venv",
        "elevation": "writes outside the workspace need the danger-full-access escalation"
    }
}
p = r"E:\deepseek\policy\storage-policy.json"
open(p, "w", encoding="utf-8", newline="\r\n").write(json.dumps(policy, ensure_ascii=False, indent=2) + "\n")
print("[OK] storage-policy.json  " + str(len(json.dumps(policy))) + " 字符")