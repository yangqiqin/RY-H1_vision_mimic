@echo off
rem ============================================================
rem  build_collision_server_msvc.bat —— 真实版(MSVC)一键编译
rem  在 PyCharm Terminal 里运行本脚本前，请确保能调用 cl：
rem    * 安装“Visual Studio Build Tools”(含 MSVC v143 + Windows SDK)
rem    * 并在本脚本所在目录用“适用于 VS 的开发人员命令提示符”执行，
rem      或先执行: "C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere"...
rem    * PyCharm 内可用: cmd /k "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat"
rem ============================================================
setlocal
cd /d %~dp0..\
set ROOT=%CD%
set SDK=%ROOT%\lib\aubo_sdk-0.27.1-rc.4-Windows_AMD64+b46f170
set SRC=%ROOT%\cpp_src\collision_box_server.cpp
set OUTDIR=%ROOT%\bin
if not exist "%OUTDIR%" mkdir "%OUTDIR%"

echo [1/2] 编译真实版(mode=sdk) ...
cl /nologo /EHsc /O2 /DUSE_REAL_AUBO_SDK /I"%SDK%\include" "%SRC%" ^
   /link /LIBPATH:"%SDK%\lib" aubo_sdk.lib robot_proxy.lib ws2_32.lib ^
   /OUT:"%OUTDIR%\collision_box_server.exe"
if errorlevel 1 (
    echo [ERROR] 真实版编译失败。检查：cl 是否可用 / SDK 路径是否存在。
    exit /b 1
)

echo [2/2] 拷贝运行时 dll 到 bin\ ...
copy /Y "%SDK%\lib\aubo_sdk.dll" "%OUTDIR%\" >nul
copy /Y "%SDK%\lib\robot_proxy.dll" "%OUTDIR%\" >nul

echo.
echo 完成：%OUTDIR%\collision_box_server.exe  (mode=sdk)
echo 之后 GUI 启用碰撞盒应显示 "C++ SDK 硬件级保护"。
endlocal
