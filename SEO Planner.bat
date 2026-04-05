@echo off
title SEO Planner - Baslatiliyor...
cd /d "%~dp0"

echo [1/3] Python Kontrol Ediliyor...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo HATA: Python yuklu degil veya PATH'e eklenmemis!
    echo Lutfen python.org adresinden Python yukleyin.
    pause
    exit /b
)

echo [2/3] Gerekli Kutuphaneler Kontrol Ediliyor/Yukleniyor...
echo Bu islem internet hiziniza bagli olarak biraz zaman alabilir...
pip install -r requirements.txt --quiet --upgrade
if %errorlevel% neq 0 (
    echo HATA: Kutuphaneler yuklenirken bir sorun Olustu!
    pause
    exit /b
)

echo [3/3] SEO Planner Baslatiliyor...
python src/main.py
pause
