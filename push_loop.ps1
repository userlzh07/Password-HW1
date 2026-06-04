# 循环重试 Push 脚本
# 用法: .\push_loop.ps1 [-Message "提交信息"] [-MaxRetries 10] [-DelaySeconds 5]

param(
    [string]$Message = "update: 优化阅读报告格式与内容",
    [int]$MaxRetries = 20,
    [int]$DelaySeconds = 5
)

$count = 0
$success = $false

Write-Host "========================================"
Write-Host "Git 循环 Push 脚本"
Write-Host "========================================"
Write-Host "提交信息: $Message"
Write-Host "最大重试: $MaxRetries 次"
Write-Host "间隔: $DelaySeconds 秒"
Write-Host ""

# 先检查是否有变更
git diff --cached --quiet
$stagedEmpty = $?
git diff --quiet
$unstagedEmpty = $?

if ($stagedEmpty -and $unstagedEmpty -and (git status --short) -eq "") {
    Write-Host "没有检测到变更，无需提交。" -ForegroundColor Yellow
    exit 0
}

# 添加所有变更
git add -A
if ($LASTEXITCODE -ne 0) {
    Write-Host "git add 失败" -ForegroundColor Red
    exit 1
}

# 提交
git commit -m "$Message"
if ($LASTEXITCODE -ne 0) {
    Write-Host "git commit 失败（可能没有变更可提交）" -ForegroundColor Red
    exit 1
}

Write-Host "已提交: $Message" -ForegroundColor Green
Write-Host ""

# 循环 Push
while ($count -lt $MaxRetries -and -not $success) {
    $count++
    Write-Host "[尝试 $count / $MaxRetries] 正在推送..."
    
    git push
    
    if ($LASTEXITCODE -eq 0) {
        $success = $true
        Write-Host ""
        Write-Host "========================================" -ForegroundColor Green
        Write-Host "Push 成功！" -ForegroundColor Green
        Write-Host "========================================" -ForegroundColor Green
    } else {
        Write-Host "推送失败，${DelaySeconds}秒后重试..." -ForegroundColor Yellow
        Start-Sleep -Seconds $DelaySeconds
    }
}

if (-not $success) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "Push 失败，已达到最大重试次数。" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    exit 1
}
