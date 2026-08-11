<#
.SYNOPSIS
    Agent 任务完成 QQ 邮箱通知脚本（PowerShell Core / Windows PowerShell 通用）。

.DESCRIPTION
    当任意 AI 智能体（如 Codex / WorkBuddy / Claude 等）完成任务后调用本脚本，
    通过 QQ 邮箱 SMTP（smtp.qq.com）向用户指定的收件箱发送一封完成通知邮件。

    本脚本不依赖任何特定智能体平台，可独立运行。

    配置优先级（从高到低）：
      1. 环境变量 QQ_NOTIFY_*（推荐，便于多机 / CI）
      2. 配置文件 task-done-notify.local.json（默认与脚本同目录）

.PARAMETER Message
    邮件正文。省略时根据 Source / Summary 自动生成。

.PARAMETER Subject
    邮件主题。省略时根据 Source + Summary 自动拼成 "[Source] 任务完成：Summary"。

.PARAMETER Source
    任务来源标识，任意字符串，例如 "Agent" / "Codex" / "WorkBuddy"。用于主题前缀与正文来源标注。

.PARAMETER Summary
    任务摘要（短标题），用于主题与正文。

.PARAMETER ConfigPath
    配置文件路径，默认：脚本同目录下的 task-done-notify.local.json。

.PARAMETER DryRun
    只校验配置并原样输出将要发送的邮件元信息（JSON），不真正发信。
    用于智能体在不确定配置是否就绪时先探测。

.EXAMPLE
    # 真正发信
    powershell -NoProfile -File ./task-done-notify.ps1 -Source "Agent" -Summary "生成周报" -Message "周报已生成：report.md"

    # 仅校验配置就绪
    powershell -NoProfile -File ./task-done-notify.ps1 -DryRun -Source "Agent" -Summary "测试"
#>

param(
    [string]$Message,
    [string]$Subject,
    [string]$Source = "Agent",
    [string]$Summary,
    [string]$ConfigPath = (Join-Path $PSScriptRoot "task-done-notify.local.json"),
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

function Get-OptionalJsonConfig {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) { return $null }
    $raw = Get-Content -Raw -LiteralPath $Path
    if ([string]::IsNullOrWhiteSpace($raw)) { return $null }
    return $raw | ConvertFrom-Json
}

function First-Value {
    param($Primary, $Fallback)
    if ($null -ne $Primary -and "$Primary".Length -gt 0) { return $Primary }
    return $Fallback
}

$config = Get-OptionalJsonConfig -Path $ConfigPath

# 环境变量 QQ_NOTIFY_* 优先，其次本地 JSON 配置。
$smtpServer  = First-Value $env:QQ_NOTIFY_SMTP_SERVER  $config.smtpServer
$smtpPort    = First-Value $env:QQ_NOTIFY_SMTP_PORT    $config.smtpPort
$smtpUser    = First-Value $env:QQ_NOTIFY_SMTP_USER     $config.smtpUser
$smtpPassword= First-Value $env:QQ_NOTIFY_SMTP_PASSWORD $config.smtpPassword
$from        = First-Value $env:QQ_NOTIFY_FROM          $config.from
$to          = First-Value $env:QQ_NOTIFY_TO            $config.to
$cleanSource = if ($Source) { ($Source -replace "[\r\n]+", " ").Trim() } else { "Agent" }
$cleanSummary= if ($Summary) { ($Summary -replace "[\r\n]+", " ").Trim() } else { "" }

$defaultSubject = if ($cleanSummary) { "[$cleanSource] 任务完成：$cleanSummary" } else { "[$cleanSource] 任务完成" }
$summarySubject = if ($cleanSummary) { $defaultSubject } else { "" }
$resolvedSubject = First-Value $Subject (First-Value $env:QQ_NOTIFY_SUBJECT (First-Value $summarySubject (First-Value $config.subject $defaultSubject)))
if ($resolvedSubject.Length -gt 150) { $resolvedSubject = $resolvedSubject.Substring(0, 150) }

$enableSslValue = First-Value $env:QQ_NOTIFY_SMTP_SSL $config.enableSsl
if (-not $smtpPort) { $smtpPort = 587 }
if ($null -eq $enableSslValue -or "$enableSslValue".Length -eq 0) { $enableSsl = $true }
else { $enableSsl = [System.Convert]::ToBoolean($enableSslValue) }
if (-not $from) { $from = $smtpUser }

$resolvedMessage = $Message
if (-not $resolvedMessage) {
    $summaryLine = if ($cleanSummary) { $cleanSummary } else { "（未提供）" }
    $resolvedMessage = @(
        "任务来源：$cleanSource",
        "任务摘要：$summaryLine",
        "完成时间：$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    ) -join "`n"
}

$missing = @()
if (-not $smtpServer)  { $missing += "smtpServer" }
if (-not $smtpUser)    { $missing += "smtpUser" }
if (-not $smtpPassword){ $missing += "smtpPassword" }
if (-not $from)        { $missing += "from" }
if (-not $to)          { $missing += "to" }

if ($missing.Count -gt 0) {
    throw "Email notification is not configured. Missing: $($missing -join ', '). Copy config/task-done-notify.example.json to task-done-notify.local.json and set SMTP values, or use QQ_NOTIFY_SMTP_* environment variables."
}

if ($DryRun) {
    [pscustomobject]@{
        SmtpServer = $smtpServer
        SmtpPort   = [int]$smtpPort
        EnableSsl  = $enableSsl
        From       = $from
        To         = $to
        Subject    = $resolvedSubject
        Source     = $cleanSource
        HasPassword= [bool]$smtpPassword
        Message    = $resolvedMessage
    } | ConvertTo-Json -Depth 3
    exit 0
}

$securePassword = ConvertTo-SecureString $smtpPassword -AsPlainText -Force
$credential = [System.Management.Automation.PSCredential]::new($smtpUser, $securePassword)

Send-MailMessage `
    -SmtpServer $smtpServer `
    -Port ([int]$smtpPort) `
    -UseSsl:$enableSsl `
    -Credential $credential `
    -From $from `
    -To $to `
    -Subject $resolvedSubject `
    -Body $resolvedMessage `
    -Encoding UTF8

Write-Host "Task completion email sent to $to."
