@echo off
echo ===================================================
echo [1/4] Preparing Hugging Face deployment...
echo ===================================================
copy README.md README.md.bak > nul

(
echo ---
echo title: Collaborative Fraud Intelligence Simulator
echo emoji: 🛡️
echo colorFrom: indigo
echo colorTo: purple
echo sdk: docker
echo app_port: 7860
echo pinned: false
echo ---
echo.
type README.md.bak
) > README.md

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
