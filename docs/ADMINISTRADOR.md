# Guía del administrador: formatos permitidos

La lista de formatos que el operador puede cargar está en **`formatos.json`**
(raíz del proyecto). El operador no puede cambiarla desde la app: solo el
administrador, editando el archivo o reemplazándolo.

## Estructura de `formatos.json`

```json
{
  "formatos": [
    {
      "name": "Wiegand26a - numero impreso",
      "descripcion": "Texto que ve el operador.",
      "habilitado": true,
      "estado": "probado",
      "spec": {
        "name": "Wiegand26a",
        "card_format": "ESSSSSSSSCCCCCCCCCCCCCCCCO",
        "parities": [
          {"kind": "even", "covers": [1,2,3,4,5,6,7,8,9,10,11,12]},
          {"kind": "odd",  "covers": [13,14,15,16,17,18,19,20,21,22,23,24]}
        ],
        "format_type": 3,
        "status": 1,
        "site_code": 0
      }
    }
  ]
}
```

| Campo | Significado |
|---|---|
| `name` | Nombre que ve el operador en la lista. |
| `descripcion` | Explicación para el operador (qué tarjetas, qué número marca). |
| `habilitado` | `true` = aparece en la app. `false` = queda guardado pero oculto. |
| `estado` | Etiqueta libre: `probado`, `fabrica`, `en prueba`… |
| `spec.name` | `Format_Name` en el reloj (máx. 24 caracteres). Si coincide con uno de fábrica del mismo tipo, lo reemplaza. |
| `spec.card_format` | Mapa de bits: `E`/`O` paridad, `S` site, `C` tarjeta, `F`/`M` otros, `0` fijo. |
| `spec.parities` | Paridades en orden: la 1ª par → `First_Even`, la 2ª → `Second_Even`; igual con las impares. `covers` = índices (desde 0) que cubre cada una. |
| `spec.format_type` | `3` entrada (lector), `1` salida Wiegand, `2` interno. |
| `spec.status` | `1` = queda activo (el único de su tipo). |
| `spec.site_code` | Dejar en `0` (se graba NULL, como los de fábrica). |

Al iniciar, la app **valida** todos los formatos habilitados. Si uno está mal,
no arranca y muestra el error. Así un archivo roto nunca llega a un reloj.

## Agregar un formato nuevo

1. En la **app completa** (`formatos-wiegand-custom`), detecta o arma el formato
   (Lector Arduino → *Usar en el editor*) y **pruébalo en un reloj**.
2. Pulsa **★ Guardar como preconfigurado**: queda en `user_presets.json` de la
   app completa, con la forma `{"name": ..., "spec": {...}}`.
3. Copia esa entrada al arreglo `"formatos"` de este `formatos.json` y agrégale
   `descripcion`, `habilitado` y `estado`.
4. Comprueba que todo está bien:

   ```powershell
   python tests/test_restringida.py
   python -c "import app_restringida as a; print([f['name'] for f in a.cargar_formatos()])"
   ```

5. Reinicia la app restringida (cierra la ventana y vuelve a abrir `iniciar.bat`).

También se puede usar otro archivo sin tocar el del proyecto:
`python app_restringida.py --formatos C:\ruta\mis_formatos.json`. Acepta tanto
`{"formatos": [...]}` como la lista de `user_presets.json` tal cual.

## Habilitar HID Corporate 1000 (35 bits)

Está incluido pero con `"habilitado": false`, porque todavía no se confirmó que
el firmware del IN01 acepte sus paridades cruzadas. Una vez probado en un reloj
con la app completa, cambia a `"habilitado": true` y `"estado": "probado"`.

## Opciones del servidor

| Opción | Uso |
|---|---|
| `--port` | Puerto (= `WebServerPort` del reloj). Por defecto 8080. |
| `--myip` | IP de este PC para la URL de descarga del reloj. |
| `--formatos` | Archivo de formatos permitidos alternativo. |
| `--ui-remota` | Permite abrir la interfaz desde otros PCs (por defecto, solo `127.0.0.1`). |
| `--capdir` | Carpeta donde se guardan las copias que manda el reloj. |

## Qué bloquea la versión restringida

Todas las rutas del panel completo (`/panel`, `/api/raw`, `/api/queue`,
`/api/getfile`, `/api/setfile`, `/api/clear`, `/api/state`, `/captures/…`, el
editor `/api/wg/*`) responden **403**. Quedan abiertas solo:

- el protocolo PUSH del reloj (`/iclock/…`) y la descarga del archivo (`/dl/u.sql`);
- la interfaz y su API `/api/r/*` (formatos, vista previa, cargar, verificar,
  deshacer), siempre contra **un SN conectado** (nunca «all»).

Las pruebas `tests/test_restringida.py` comprueban estos bloqueos.
