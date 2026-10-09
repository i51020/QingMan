@echo off
chcp 65001 >nul
setlocal
set "ROOT=%~dp0"
set "SRCDIR=%ROOT%src"

if not exist "%SRCDIR%\server\__main__.py" goto :noapp

set "PY=py -3"
py -3 -V >nul 2>nul || set "PY=python"
python -V >nul 2>nul || goto :nopy

echo [青蔓 QingMan] 正在启动本地服务...
pushd "%SRCDIR%"
%PY% -m server
set "RC=%errorlevel%"
popd
if not "%RC%"=="0" goto :failed
goto :eof

:noapp
echo [错误] 未找到后端入口: "%SRCDIR%\server\__main__.py"
pause
exit /b 1

:nopy
echo [错误] 未检测到 Python 3.8+，请安装后重试
pause
exit /b 1

:failed
echo [错误] 服务异常退出，代码 %RC%
pause
exit /b 1
