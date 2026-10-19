@echo off
rem Inicia la carga restringida de formatos y abre el navegador.
rem Ajusta PUERTO (debe ser el WebServerPort del reloj) y, si hace falta, IP.
rem Con IP vacia se detecta sola.
set PUERTO=8080
set IP=

cd /d "%~dp0"
start "" http://127.0.0.1:%PUERTO%/
if "%IP%"=="" (
  python app_restringida.py --port %PUERTO%
) else (
  python app_restringida.py --port %PUERTO% --myip %IP%
)
pause
