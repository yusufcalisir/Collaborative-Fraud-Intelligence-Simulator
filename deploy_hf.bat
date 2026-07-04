@echo off
chcp 65001 > nul
echo ===================================================
echo [1/4] Preparing Hugging Face deployment...
echo ===================================================
copy README.md README.md.bak > nul

powershell -NoProfile -Command ^
  "$front = @'^

---
title: Collaborative Fraud Intelligence Simulator
emoji: 🛡️
colorFrom: indigo
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
---

'@; $body = Get-Content -Raw -Encoding UTF8 'README.md.bak'; [System.IO.File]::WriteAllText('README.md', $front + $body, (New-Object System.Text.UTF8Encoding($false)))"

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