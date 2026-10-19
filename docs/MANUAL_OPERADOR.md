# Manual del operador

Cómo cargar un formato de tarjeta en un reloj ZKTeco IN01 con la versión
restringida. Si el PC todavía no tiene la app instalada, sigue primero
[INSTALACION.md](INSTALACION.md).

---

## Antes de empezar

- El reloj debe estar **apuntado a este PC**: misma red, con la IP y el puerto de
  este PC configurados en el reloj (ver [INSTALACION.md](INSTALACION.md), paso 6).
- Debes saber **qué formato** usar. Si no lo sabes, consulta al administrador.

## 1. Iniciar la app

Doble clic en **`iniciar.bat`** (en la carpeta `carga-de-formatos-restringidos`).
Se abre una ventana negra (el servidor) y el navegador en
`http://127.0.0.1:8080/`.

- **No cierres la ventana negra** mientras trabajas: es la que habla con el reloj.
- Para terminar, cierra esa ventana o pulsa `Ctrl + C` en ella.

Alternativa por consola:

```powershell
cd $HOME\Downloads\carga-de-formatos-restringidos
python app_restringida.py --port 8080 --myip <IP_de_este_PC>
```

## 2. Elegir el reloj (paso 1 de la pantalla)

En *Reloj destino* aparecen los relojes conectados (SN · IP). Elige el que vas a
modificar. Si la lista dice *(ningún reloj conectado)*, espera 1–2 minutos; si
sigue vacía, revisa la sección *Problemas* al final.

## 3. Elegir el formato (paso 2)

Marca uno de la lista. Cada uno indica cuántos bits tiene y qué número va a
registrar el reloj:

- **Wiegand26a — número impreso**: tarjetas de 26 bits; el reloj marca el número
  que trae impreso la tarjeta (ej. 6132).
- **Wiegand26 — número completo (fábrica)**: el formato original del reloj; marca
  site y número juntos (ej. 9443572). Úsalo para volver al estado de fábrica.

## 4. Cargar (paso 3)

1. (Opcional) **Ver qué se va a hacer**: muestra la lista exacta de pasos que se
   enviarán al reloj.
2. **Cargar en el reloj (se reinicia)** y confirma.
3. En *Actividad* verás cómo el reloj recoge los comandos (`ENTREGA`), descarga
   el archivo (`DESCARGA del archivo`) y responde `ÉXITO`.
4. El reloj **se reinicia solo** y vuelve en 1–2 minutos.

Antes de cambiar nada, la app guarda una copia de la base del reloj
(`ZKDB.bak`), así que siempre se puede deshacer.

## 5. Verificar (paso 4)

Cuando el reloj vuelva a aparecer conectado:

1. **1. Pedir copia al reloj**.
2. Espera a que en *Actividad* aparezca `CAPTURADO … ZKDB.db`.
3. **2. Comprobar formato activo** → debe decir *Correcto*.
4. Pasa una tarjeta por el reloj y confirma que marca el número esperado.

## 6. Deshacer

Si el reloj no lee o marca números incorrectos: **Deshacer última carga** y
confirma. Se restaura la copia guardada antes de la carga y el reloj se reinicia.

> Deshacer restaura la copia de la **última** carga. Si cargaste dos veces
> seguidas, la copia corresponde al estado previo a la segunda.

---

## Problemas

| Síntoma | Qué hacer |
|---|---|
| Al abrir la página sale «acceso no permitido» | Ábrela en el mismo PC con `http://127.0.0.1:8080/`, no con la IP de red |
| No aparece ningún reloj | Revisa en el reloj la IP y el puerto del servidor; misma red; firewall de Windows (ver INSTALACION.md) |
| «elige un reloj conectado» | Selecciona un reloj de la lista antes de cargar |
| Se cargó pero el reloj no lee | Verifica (paso 5). Si el formato no es el correcto para esas tarjetas, **Deshacer** y consulta al administrador |
| La lista de formatos está vacía o da error | `formatos.json` está mal o no tiene formatos habilitados: avisa al administrador |
| La ventana negra muestra «Address already in use» | Ya hay otra app usando el puerto: ciérrala (ver INSTALACION.md) |
