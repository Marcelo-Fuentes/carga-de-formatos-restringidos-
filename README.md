# Carga de formatos Wiegand restringida — ZKTeco IN01

Versión **para operadores** de
[formatos-wiegand-custom](https://github.com/Marcelo-Fuentes/formatos-wiegand-custom):
solo permite **elegir uno de los formatos preconfigurados** y cargarlo en un
reloj IN01, verificarlo y deshacerlo. No se pueden crear ni editar formatos ni
mandar comandos libres al reloj.

| | App completa | Esta versión |
|---|---|---|
| Crear / editar formatos | Sí | No |
| Lector Arduino (detectar formato) | Sí | No |
| Panel de comandos libres (`/panel`, shell, GetFile…) | Sí | **Bloqueado** |
| Elegir un formato aprobado y cargarlo | Sí | Sí |
| Respaldo de la base antes de cargar | Opcional | **Siempre** |
| Verificar / deshacer | Sí | Sí |
| Interfaz accesible desde otros PCs | Sí | Solo desde el mismo PC (salvo `--ui-remota`) |

## Uso rápido

```powershell
cd $HOME\Downloads\carga-de-formatos-restringidos
python app_restringida.py --port 8080 --myip 192.168.2.103
```

o doble clic en **`iniciar.bat`**. Luego abrir `http://127.0.0.1:8080/` y seguir
los pasos 1 → 4 de la pantalla.

## Documentación

- [docs/INSTALACION.md](docs/INSTALACION.md) — instalar Python y dejarlo
  funcionando desde cero, y apuntar el reloj a este PC.
- [docs/MANUAL_OPERADOR.md](docs/MANUAL_OPERADOR.md) — cómo cargar, verificar y
  deshacer un formato.
- [docs/ADMINISTRADOR.md](docs/ADMINISTRADOR.md) — cómo se define la lista de
  formatos permitidos (`formatos.json`) y cómo agregar uno nuevo.

## Formatos incluidos

| Formato | Bits | Qué número registra el reloj | Estado |
|---|---|---|---|
| Wiegand26a — número impreso | 26 | El número impreso (card de 16 bits) | Habilitado (probado) |
| Wiegand26 — número completo (fábrica) | 26 | Site y card juntos (ej. 144,6132 → 9443572) | Habilitado (fábrica) |
| HID Corporate 1000 — 35 bits | 35 | El número impreso (20 bits) | **Deshabilitado** hasta confirmarlo en el reloj |

## Qué hace una carga

1. Respalda la base: `ZKDB.db` → `ZKDB.bak`.
2. El reloj descarga el `update.sql`, que deja los 22 formatos de fábrica más el
   elegido como único activo de su tipo. El formato del archivo es el mismo que
   usa la herramienta que funciona en el IN01: `[INSERT]` y reinicio de IDs.
3. Lo coloca en `data/` con los pasos separados que funcionan en el equipo
   (limpiar → descargar → verificar → borrar original → renombrar → permisos →
   mover).
4. `SET OPTIONS ExtWGInBitsCount=…,WGOutBitsCount=…` con el largo del formato.
5. `sync` y `REBOOT`.

## Estructura

```
app_restringida.py   servidor (solo rutas permitidas) + API /api/r/*
zk_panel.py          transporte PUSH/ADMS con el reloj
wiegand_tool/        generación del update.sql y de los comandos
formatos.json        LISTA DE FORMATOS PERMITIDOS (la edita el administrador)
webapp/              interfaz del operador
iniciar.bat          arranque con doble clic
tests/               pruebas (python tests/test_restringida.py)
```

Solo usa la biblioteca estándar de Python 3: no hay que instalar dependencias.
