@echo off
setlocal
cd /d %~dp0

set "ANACONDA_HOME=D:\anaconda"
set "PATH=%ANACONDA_HOME%;%ANACONDA_HOME%\Library\bin;%ANACONDA_HOME%\Library\usr\bin;%ANACONDA_HOME%\Scripts;%PATH%"

python -m uvicorn app.main:app --reload

endlocal
