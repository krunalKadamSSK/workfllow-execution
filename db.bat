@echo off
setlocal EnableExtensions EnableDelayedExpansion

rem Windows helper for Postgres backup/restore (mirrors Makefile db-backup / db-restore).
rem Usage:
rem   db.bat backup [path\to\file.dump]
rem   db.bat restore path\to\file.dump

set "POSTGRES_CONTAINER=workflow_engine_postgres"
set "POSTGRES_USER=workflow"
set "POSTGRES_DB=workflow_engine"
set "BACKUP_DIR=backups"

if "%~1"=="" goto :usage

set "ACTION=%~1"
shift

if /I "%ACTION%"=="backup" goto :backup
if /I "%ACTION%"=="restore" goto :restore
goto :usage

:wait_ready
echo Waiting for PostgreSQL...
:wait_loop
docker exec %POSTGRES_CONTAINER% pg_isready -U %POSTGRES_USER% -d %POSTGRES_DB% >nul 2>&1
if errorlevel 1 (
    timeout /t 1 /nobreak >nul
    goto :wait_loop
)
echo PostgreSQL is ready.
exit /b 0

:backup
call :wait_ready
if errorlevel 1 exit /b 1

if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

if "%~1"=="" (
    rem Build a portable stamp; strip spaces/separators so locale formats still work.
    set "STAMP=%date%_%time:~0,2%%time:~3,2%%time:~6,2%"
    set "STAMP=!STAMP: =0!"
    set "STAMP=!STAMP:/=!"
    set "STAMP=!STAMP:-=!"
    set "STAMP=!STAMP:.=!"
    set "BACKUP_FILE=%BACKUP_DIR%\workflow_engine_!STAMP!.dump"
) else (
    set "BACKUP_FILE=%~1"
)

echo Backing up to !BACKUP_FILE!...
docker exec %POSTGRES_CONTAINER% pg_dump -U %POSTGRES_USER% -d %POSTGRES_DB% -Fc -f /tmp/backup.dump
if errorlevel 1 (
    echo Backup failed: pg_dump error.
    exit /b 1
)

docker cp %POSTGRES_CONTAINER%:/tmp/backup.dump "!BACKUP_FILE!"
if errorlevel 1 (
    echo Backup failed: could not copy dump out of container.
    exit /b 1
)

docker exec %POSTGRES_CONTAINER% rm -f /tmp/backup.dump >nul 2>&1
echo Backup complete: !BACKUP_FILE!
exit /b 0

:restore
if "%~1"=="" (
    echo Usage: db.bat restore path\to\backup.dump
    exit /b 1
)

set "RESTORE_FILE=%~1"
if not exist "!RESTORE_FILE!" (
    echo Backup file not found: !RESTORE_FILE!
    exit /b 1
)

call :wait_ready
if errorlevel 1 exit /b 1

echo Restoring from !RESTORE_FILE!...
docker cp "!RESTORE_FILE!" %POSTGRES_CONTAINER%:/tmp/backup.dump
if errorlevel 1 (
    echo Restore failed: could not copy dump into container.
    exit /b 1
)

docker exec %POSTGRES_CONTAINER% pg_restore -U %POSTGRES_USER% -d %POSTGRES_DB% --clean --if-exists /tmp/backup.dump
set "RC=!errorlevel!"
docker exec %POSTGRES_CONTAINER% rm -f /tmp/backup.dump >nul 2>&1

rem pg_restore exit code 1 is often warnings only; fail only on > 1
if !RC! GTR 1 (
    echo Restore failed with exit code !RC!.
    exit /b !RC!
)

echo Restore complete.
exit /b 0

:usage
echo Usage:
echo   db.bat backup [path\to\file.dump]
echo   db.bat restore path\to\file.dump
echo.
echo Examples:
echo   db.bat backup
echo   db.bat backup backups\my_backup.dump
echo   db.bat restore backups\workflow_engine_20260715_140000.dump
exit /b 1
