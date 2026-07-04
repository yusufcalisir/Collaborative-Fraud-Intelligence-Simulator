$ErrorActionPreference = "Stop"

Write-Output "==================================================="
Write-Output "[1/4] Preparing Hugging Face deployment..."
Write-Output "==================================================="

# Backup README.md
Copy-Item README.md README.md.bak -Force

# Create frontmatter using ASCII-safe string construction and code-point emoji conversion
$emoji = [char]::ConvertFromUtf32(0x1F6E1)
$front = "---`n" +
"title: Collaborative Fraud Intelligence Simulator`n" +
"emoji: $emoji`n" +
"colorFrom: indigo`n" +
"colorTo: purple`n" +
"sdk: docker`n" +
"app_port: 7860`n" +
"pinned: false`n" +
"---`n`n"

# Prefix README.md
$body = Get-Content -Raw -Encoding UTF8 README.md.bak
[System.IO.File]::WriteAllText("README.md", $front + $body, (New-Object System.Text.UTF8Encoding($false)))

Write-Output "==================================================="
Write-Output "[2/4] Committing temporary metadata..."
Write-Output "==================================================="

# Git commands
git add README.md
git commit -m "deploy: temporary Hugging Face metadata" --no-verify

Write-Output "==================================================="
Write-Output "[3/4] Pushing to Hugging Face Spaces..."
Write-Output "==================================================="

git push hf main --force

Write-Output "==================================================="
Write-Output "[4/4] Restoring original README.md and git history..."
Write-Output "==================================================="

# Restore README.md
Move-Item README.md.bak README.md -Force -ErrorAction SilentlyContinue
git add README.md
git reset --mixed HEAD~1

Write-Output "==================================================="
Write-Output "Deployment completed! GitHub and local files clean."
Write-Output "==================================================="
