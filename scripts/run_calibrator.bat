@echo off
setlocal
set EXE=HSVCalibrator.exe
if exist "%~dp0..\dist\%EXE%" (
  pushd "%~dp0..\dist"
  "%EXE%" %*
  popd
) else if exist "%~dp0..\%EXE%" (
  pushd "%~dp0..\"
  "%EXE%" %*
  popd
) else (
  echo Could not find %EXE%. If you downloaded a zip, open dist/ and run it there.
  exit /b 1
)
endlocal
