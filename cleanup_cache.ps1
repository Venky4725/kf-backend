# PowerShell cleanup script to remove Python cache files and directories

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Cleaning up Python cache files..." -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Remove __pycache__ directories from git tracking
Write-Host "Removing __pycache__ from git tracking..." -ForegroundColor Yellow

$pycacheDirs = @(
    "app/__pycache__",
    "app/api/__pycache__",
    "app/core/__pycache__",
    "app/db/__pycache__",
    "app/models/__pycache__",
    "app/routers/__pycache__",
    "app/schemas/__pycache__",
    "app/services/__pycache__",
    "scripts/__pycache__"
)

foreach ($dir in $pycacheDirs) {
    if (Test-Path $dir) {
        git rm -r --cached $dir 2>$null
        Write-Host "  - Removed $dir from git" -ForegroundColor Green
    }
}

# Remove __pycache__ directories from filesystem
Write-Host ""
Write-Host "Removing __pycache__ directories from filesystem..." -ForegroundColor Yellow
Get-ChildItem -Path . -Recurse -Force -Directory -Filter "__pycache__" | ForEach-Object {
    Remove-Item -Path $_.FullName -Recurse -Force
    Write-Host "  - Deleted $($_.FullName)" -ForegroundColor Green
}

# Remove .pyc and .pyo files
Write-Host ""
Write-Host "Removing .pyc and .pyo files..." -ForegroundColor Yellow
Get-ChildItem -Path . -Recurse -Force -Include "*.pyc","*.pyo" | ForEach-Object {
    Remove-Item -Path $_.FullName -Force
    Write-Host "  - Deleted $($_.Name)" -ForegroundColor Green
}

# Remove .DS_Store files (Mac)
Write-Host ""
Write-Host "Removing .DS_Store files..." -ForegroundColor Yellow
Get-ChildItem -Path . -Recurse -Force -Filter ".DS_Store" | ForEach-Object {
    Remove-Item -Path $_.FullName -Force
    Write-Host "  - Deleted $($_.FullName)" -ForegroundColor Green
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "✅ Cleanup complete!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Review changes: git status" -ForegroundColor White
Write-Host "2. Add updated .gitignore: git add .gitignore" -ForegroundColor White
Write-Host "3. Commit changes: git commit -m 'chore: update .gitignore and remove cache files'" -ForegroundColor White
Write-Host "4. Push to GitHub: git push" -ForegroundColor White
Write-Host ""
