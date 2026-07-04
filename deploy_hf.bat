@echo off
chcp 65001 > nul
echo ===================================================
echo [1/4] Preparing Hugging Face deployment...
echo ===================================================

set "TMPPS1=%~dp0.hftmp.ps1"

(
  echo $emoji = [char]::ConvertFromUtf32^(0x1F6E1^)
  echo $sep = [Environment]::NewLine
  echo $front = "---" + $sep + "title: Collaborative Fraud Intelligence Simulator" + $sep + "emoji: " + $emoji + $sep + "colorFrom: indigo" + $sep + "colorTo: purple" + $sep + "sdk: docker" + $sep + "app_port: 7860" + $sep + "pinned: false" + $sep + "---" + $sep + $sep
  echo Copy-Item README.md README.md.bak -Force
  echo $body = Get-Content -Raw -Encoding UTF8 README.md.bak
  echo [System.IO.File]::WriteAllText^("README.md", $front + $body, ^(New-Object System.Text.UTF8Encoding^($false^)^)^)
) > "%TMPPS1%"

powershell -NoProfile -ExecutionPolicy Bypass -File "%TMPPS1%"
del "%TMPPS1%" > nul 2>&1

echo ===================================================
echo [2/4] Committing temporary metadata...
echo ===================================================
git add README.md
git commit -m "deploy: temporary Hugging Face metadata" --no-verify > nul

echo ===================================================
echo [3/4] Pushing to Hugging Face Spaces...
echo ===================================================
git push hf main --force

echo ===================================================
echo [4/4] Restoring original README.md and git history...
echo ===================================================
move /y README.md.bak README.md > nul
git add README.md
git reset --mixed HEAD~1 > nul

echo ===================================================
echo Deployment completed! GitHub and local files clean.
echo ===================================================