@echo off
@REM  Milvus v2.6.16 standalone 启动脚本（local storage 模式，无需 MinIO）
@REM  数据持久化到 %cd%\volumes\milvus，重启 Docker / 关机后数据不丢失。
setlocal enabledelayedexpansion

:main
if "%1"=="" (
    echo Usage: standalone.bat start^|stop^|restart^|delete
    exit /b 1
)

if "%1"=="restart" (
    call :stop
    call :start
) else if "%1"=="start" (
    call :start
) else if "%1"=="stop" (
    call :stop
) else if "%1"=="delete" (
    call :delete
) else (
    echo Unknown command: %1
    echo Usage: standalone.bat start^|stop^|restart^|delete
    exit /b 1
)
goto :eof

:run_embed
(
echo listen-client-urls: http://0.0.0.0:2379
echo advertise-client-urls: http://0.0.0.0:2379
echo quota-backend-bytes: 4294967296
echo auto-compaction-mode: revision
echo auto-compaction-retention: '1000'
) > embedEtcd.yaml

(
echo # Extra config to override default milvus.yaml
echo common:
echo   storageType: local
) > user.yaml

if not exist "embedEtcd.yaml" (
    echo embedEtcd.yaml file does not exist. Please try to create it in the current directory.
    exit /b 1
)
if not exist "user.yaml" (
    echo user.yaml file does not exist. Please try to create it in the current directory.
    exit /b 1
)

docker run -d ^
    --name milvus-standalone ^
    --security-opt seccomp:unconfined ^
    -e ETCD_USE_EMBED=true ^
    -e ETCD_DATA_DIR=/var/lib/milvus/etcd ^
    -e ETCD_CONFIG_PATH=/milvus/configs/embedEtcd.yaml ^
    -e COMMON_STORAGETYPE=local ^
    -e DEPLOY_MODE=STANDALONE ^
    -v "%cd%\volumes\milvus:/var/lib/milvus" ^
    -v "%cd%\embedEtcd.yaml:/milvus/configs/embedEtcd.yaml" ^
    -v "%cd%\user.yaml:/milvus/configs/user.yaml" ^
    -p 19530:19530 ^
    -p 9091:9091 ^
    -p 2379:2379 ^
    --health-cmd="curl -f http://localhost:9091/healthz" ^
    --health-interval=30s ^
    --health-start-period=90s ^
    --health-timeout=20s ^
    --health-retries=3 ^
    milvusdb/milvus:v2.6.16 ^
    milvus run standalone >nul
if %errorlevel% neq 0 (
    echo Failed to start Milvus container.
    exit /b 1
)

goto :eof

:wait_for_milvus_running
echo Wait for Milvus Starting...
:wait_loop
for /f "tokens=*" %%A in ('docker ps ^| findstr "milvus-standalone" ^| findstr "healthy"') do set running=1
if "!running!"=="1" (
    echo Start successfully.
    echo Milvus v2.6.16 (local storage, data persistent across restarts).
    goto :eof
)
timeout /t 2 >nul
goto wait_loop

:start
for /f "tokens=*" %%A in ('docker ps ^| findstr "milvus-standalone" ^| findstr "healthy"') do (
    echo Milvus is running.
    exit /b 0
)

for /f "tokens=*" %%A in ('docker ps -a ^| findstr "milvus-standalone"') do set container_exists=1
if defined container_exists (
    docker start milvus-standalone >nul
) else (
    call :run_embed
)

if %errorlevel% neq 0 (
    echo Start failed.
    exit /b 1
)

call :wait_for_milvus_running
goto :eof

:stop
docker stop milvus-standalone >nul
if %errorlevel% neq 0 (
    echo Stop failed.
    exit /b 1
)
echo Stop successfully.
goto :eof

:delete_container
for /f "tokens=*" %%A in ('docker ps ^| findstr "milvus-standalone"') do (
    echo Please stop Milvus service before delete.
    exit /b 1
)
docker rm milvus-standalone >nul
if %errorlevel% neq 0 (
    echo Delete Milvus container failed.
    exit /b 1
)
echo Delete Milvus container successfully.
goto :eof

:delete
set /p check="Confirm delete container AND data? This wipes all Milvus vectors. (y/n) > "
if /i "%check%"=="y" (
    call :delete_container
    rmdir /s /q "%cd%\volumes"
    del /q embedEtcd.yaml
    del /q user.yaml
    echo Delete successfully.
) else (
    echo Exit delete
    exit /b 0
)
goto :eof

:EOF
