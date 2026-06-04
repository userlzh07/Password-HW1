# Git Push Auto-Retry Script
$branch = "master"
$maxAttempts = 30
$delaySeconds = 5

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Git Push Auto-Retry" -ForegroundColor Cyan
Write-Host "Branch: $branch, Max: $maxAttempts, Interval: ${delaySeconds}s" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

for ($i = 1; $i -le $maxAttempts; $i++) {
    Write-Host "[$i/$maxAttempts] Pushing to origin/$branch ..." -ForegroundColor Yellow
    git push -u origin $branch --force 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "Push Success!" -ForegroundColor Green
        Write-Host ""
        Read-Host "Press Enter to exit"
        exit 0
    }
    
    Write-Host "Failed $i, retry in ${delaySeconds}s..." -ForegroundColor Red
    Write-Host ""
    Start-Sleep -Seconds $delaySeconds
}

Write-Host ""
Write-Host "Max retries reached." -ForegroundColor Red
Read-Host "Press Enter to exit"
