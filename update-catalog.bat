@echo off
chcp 65001 >nul
cd /d "%~dp0"
where node >nul 2>nul
if errorlevel 1 (
  echo Node.js не найден. Установите Node.js и повторите запуск.
  pause
  exit /b 1
)
node tools\update-catalog.cjs
if errorlevel 1 (
  echo Исправьте указанные ошибки и запустите этот файл снова.
) else (
  echo Готово. Обновите страницу каталога в браузере.
)
pause
