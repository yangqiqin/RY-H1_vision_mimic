@echo off
echo 编译碰撞盒服务端...

if not exist build mkdir build
cd build

cmake .. -G "Visual Studio 17 2022" -A x64
if errorlevel 1 goto error

cmake --build . --config Release
if errorlevel 1 goto error

echo 编译成功！
echo 输出文件: bin/Release/collision_box_server.exe
goto end

:error
echo 编译失败！
exit /b 1

:end