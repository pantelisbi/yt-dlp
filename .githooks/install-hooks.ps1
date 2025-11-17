# PowerShell script to install git hooks from .githooks directory

$hooksDir = Join-Path (git rev-parse --show-toplevel) ".githooks"
$gitHooksDir = Join-Path (git rev-parse --git-dir) "hooks"

Write-Host "Installing git hooks..." -ForegroundColor Cyan

# Copy hooks
Copy-Item "$hooksDir\prepare-commit-msg" -Destination "$gitHooksDir\prepare-commit-msg" -Force
Copy-Item "$hooksDir\prepare-commit-msg.ps1" -Destination "$gitHooksDir\prepare-commit-msg.ps1" -Force

Write-Host "Git hooks installed successfully!" -ForegroundColor Green
Write-Host "Commits will now automatically include 'Authored by: <your-github-username>'" -ForegroundColor Green
