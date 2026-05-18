@echo off
REM ─────────────────────────────────────────────────────────────────────────────
REM  compile.bat — Build the thesis PDF
REM  Requires: MiKTeX or TeX Live installed and in PATH
REM  Usage: double-click or run from this directory
REM ─────────────────────────────────────────────────────────────────────────────

echo [1/4] pdflatex (first pass)...
pdflatex -interaction=nonstopmode main.tex
if errorlevel 2 (
    echo ERROR: pdflatex failed on first pass (fatal). Check main.log for details.
    pause
    exit /b 1
)
if not exist main.pdf (
    echo ERROR: main.pdf not produced. Check main.log for details.
    pause
    exit /b 1
)

echo [2/4] biber (bibliography)...
biber main
if errorlevel 1 (
    echo WARNING: biber failed or had warnings. Bibliography may be incomplete.
)

echo [3/4] pdflatex (second pass)...
pdflatex -interaction=nonstopmode main.tex

echo [4/4] pdflatex (third pass — cross-references)...
pdflatex -interaction=nonstopmode main.tex

echo.
echo ─────────────────────────────────────────────────
echo  Done. Output: main.pdf
echo  Open with: start main.pdf
echo ─────────────────────────────────────────────────
start main.pdf
pause
