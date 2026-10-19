# Instalación desde cero (Windows)

Para dejar la carga restringida funcionando en un PC nuevo. Los comandos se
escriben en **PowerShell** (Inicio → escribir `PowerShell` → Enter).

> No hay que instalar librerías: la app usa solo lo que trae Python.

## Resumen rápido

```powershell
winget install -e --id Python.Python.3.13
winget install -e --id Git.Git
# cerrar y volver a abrir PowerShell
cd $HOME\Downloads
git clone https://github.com/Marcelo-Fuentes/carga-de-formatos-restringidos-.git carga-de-formatos-restringidos
cd carga-de-formatos-restringidos
python tests/test_restringida.py
python app_restringida.py --port 8080 --myip <IP_DE_ESTE_PC>
```

---

## 1. Python 3

```powershell
winget install -e --id Python.Python.3.13
```

O con el instalador de https://www.python.org/downloads/windows/, **marcando
«Add python.exe to PATH»**.

Comprobar (en una PowerShell nueva):

```powershell
python --version
```

Si abre la Microsoft Store o no reconoce el comando: prueba `py --version` (y usa
`py` en vez de `python`), o apaga el alias en *Configuración → Aplicaciones →
Configuración avanzada de aplicaciones → Alias de ejecución de aplicaciones →*
`python.exe` / `python3.exe`.

> Si usas `py`, edita también `iniciar.bat` y cambia `python` por `py`.

## 2. Descargar la app

**Con Git** (permite actualizar con `git pull`):

```powershell
winget install -e --id Git.Git
# PowerShell nueva:
cd $HOME\Downloads
git clone https://github.com/Marcelo-Fuentes/carga-de-formatos-restringidos-.git carga-de-formatos-restringidos
```

**Sin Git:** en la página del repositorio, *Code → Download ZIP*, y descomprímelo
en `Descargas\carga-de-formatos-restringidos`.

Actualizar más adelante:

```powershell
cd $HOME\Downloads\carga-de-formatos-restringidos
git pull
```

Comprobar que todo funciona:

```powershell
python tests/test_restringida.py
```

Debe terminar con `4 passed, 0 failed`.

## 3. IP de este PC

```powershell
ipconfig
```

Anota la **Dirección IPv4** del adaptador conectado a la red del reloj (Wi-Fi o
Ethernet), por ejemplo `192.168.2.103`. No uses `127.0.0.1` ni la de una VPN.

## 4. Iniciar

Edita `iniciar.bat` (clic derecho → Editar) si hace falta:

```bat
set PUERTO=8080
set IP=192.168.2.103
```

y ábrelo con doble clic. O por consola:

```powershell
cd $HOME\Downloads\carga-de-formatos-restringidos
python app_restringida.py --port 8080 --myip 192.168.2.103
```

Debe mostrar `Carga restringida en http://127.0.0.1:8080/ (2 formatos habilitados)`.
Abre esa dirección en el navegador **de este mismo PC**.

Si el puerto está ocupado:

```powershell
netstat -ano | findstr :8080
taskkill /PID <número_de_la_última_columna> /F
```

## 5. Firewall de Windows

La primera vez Windows puede preguntar si permitir Python: acepta para la red en
uso. Si no preguntó y el reloj no aparece, crea la regla (PowerShell **como
administrador**):

```powershell
netsh advfirewall firewall add rule name="ZK Push 8080" dir=in action=allow protocol=TCP localport=8080
```

Comprobar que escucha:

```powershell
netstat -ano | findstr :8080
```

(debe salir `0.0.0.0:8080 … LISTENING`)

## 6. Apuntar el reloj a este PC

En el reloj (*Comunicación → Nube/ADMS*) configura:

| Opción | Valor |
|---|---|
| Dirección del servidor | IP de este PC (paso 3) |
| Puerto del servidor | El mismo de la app (8080) |
| Modo de dirección / `WebServerURLModel` | Por IP (`0`) |
| HTTPS / `IsSupportSSL` | Desactivado (`0`) |

Reinicia el reloj. En 1–2 minutos aparece en la app en *Reloj destino*.

Si no aparece: comprueba IP y puerto exactos, que el reloj responda a
`ping <IP_del_reloj>` y el firewall (paso 5).

## Siguiente paso

[MANUAL_OPERADOR.md](MANUAL_OPERADOR.md): cargar, verificar y deshacer un formato.
