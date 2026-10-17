@echo off
chcp 65001 >nul
setlocal
set "ROOT=%~dp0"
set "SRCDIR=%ROOT%src"

if not exist "%SRCDIR%\server\__main__.py" goto :noapp

rem 解释器优先级（V0.1.0）：随包运行时 > py -3 > python
rem 分布版把 Python 放在 runtime\ 下，接收者无需自行安装；
rem 一律加 -B：不写 __pycache__ —— 程序目录可能只读（Program Files / 网络盘）。
if exist "%ROOT%runtime\python.exe" goto :bundled

py -3 -V >nul 2>nul || goto :syspython
echo [青蔓 QingMan] 正在启动本地服务...
pushd "%SRCDIR%"
py -3 -B -m server
set "RC=%errorlevel%"
popd
goto :done

:syspython
python -V >nul 2>nul || goto :nopy
echo [青蔓 QingMan] 正在启动本地服务...
pushd "%SRCDIR%"
python -B -m server
set "RC=%errorlevel%"
popd
goto :done

:bundled
echo [青蔓 QingMan] 正在启动本地服务（随包运行时）...
pushd "%SRCDIR%"
"%ROOT%runtime\python.exe" -B -m server
set "RC=%errorlevel%"
popd
goto :done

:done
if not "%RC%"=="0" goto :failed
goto :eof

:noapp
echo [错误] 未找到后端入口: "%SRCDIR%\server\__main__.py"
echo        请确认解压完整（不要把 start.bat 单独拷出来）。
pause
exit /b 1

:nopy
echo [错误] 未检测到 Python 3.8+，且未找到随包运行时 runtime\python.exe
echo        请重新解压完整压缩包；或安装 Python 3.8+ 后重试。
pause
exit /b 1

:failed
echo [错误] 服务异常退出，代码 %RC%
pause
exit /b 1
