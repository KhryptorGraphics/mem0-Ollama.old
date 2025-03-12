# PowerShell script to create a new GitHub repository and push the entire project

# Navigate to the mem0-ollama directory
Set-Location -Path "C:\6\mem0-ollama"

Write-Host "Current directory: $(Get-Location)" -ForegroundColor Green

# Remove the existing remote
Write-Host "Removing existing remote..." -ForegroundColor Yellow
git remote remove origin

# Add new GitHub remote (you'll need to create this repository manually in GitHub first)
Write-Host "Adding new GitHub remote..." -ForegroundColor Yellow
git remote add origin https://github.com/KhryptorGraphics/mem0-ollama.git

# Add all files to staging
Write-Host "Adding all files to staging..." -ForegroundColor Yellow
git add .

# Commit the changes if needed
Write-Host "Committing changes..." -ForegroundColor Yellow
git commit -m "Initial commit for mem0-Ollama project with web chat interface and memory tracking"

# Create and switch to main branch if needed
$currentBranch = git branch --show-current
if ($currentBranch -ne "main") {
    Write-Host "Creating and switching to main branch..." -ForegroundColor Yellow
    git checkout -b main
}

# Force push to the new GitHub repository
Write-Host "Force pushing to new GitHub repository..." -ForegroundColor Yellow
git push -f origin main

Write-Host "Operation completed!" -ForegroundColor Green
Write-Host "Please verify the repository at https://github.com/KhryptorGraphics/mem0-ollama"
