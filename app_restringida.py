#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Carga de formatos Wiegand RESTRINGIDA para relojes ZKTeco IN01.

Version para operadores: solo permite elegir uno de los formatos
preconfigurados en ``formatos.json`` y cargarlo en un reloj por SN, con la
secuencia probada (respaldo -> update.sql -> SET OPTIONS -> REBOOT),
verificarlo y deshacerlo. No hay editor de formatos, ni comandos libres, ni
panel crudo: esas rutas del servidor PUSH estan bloqueadas.

Reutiliza ``zk_panel.py`` como transporte PUSH/ADMS (lo que habla con el reloj)
y ``wiegand_tool`` para generar el archivo y los comandos.

Uso:
  python app_restringida.py --port 8080 --myip 192.168.2.103

La interfaz solo responde desde este mismo PC (http://127.0.0.1:<puerto>/);
``--ui-remota`` la abre a la red. El reloj puede conectarse siempre.
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import sys
from http.server import ThreadingHTTPServer
from urllib.parse import urlparse

# El log usa caracteres como ✓; en una consola o salida redirigida que no sea
# UTF-8 eso tiraba la peticion del reloj (UnicodeEncodeError). Se reemplazan.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(errors="replace")
    except (AttributeError, ValueError):
        pass

import zk_panel  # noqa: E402
from wiegand_tool import backup, loader, sqlgen  # noqa: E402
from wiegand_tool.core import FormatError, Parity, WiegandFormat  # noqa: E402

ROOT = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(ROOT, "webapp")
FORMATOS_PATH = os.path.join(ROOT, "formatos.json")
ARCHIVO = "u.sql"  # nombre corto del update.sql servido en /dl/

# Rutas del protocolo PUSH que usa el reloj (todo lo demas de zk_panel se bloquea).
_PUSH_SUFFIXES = ("/cdata", "/getrequest", "/devicecmd", "/fdata", "/ping", "/registry",
                  "/push", "/querydata", "/rtdata")

CONFIG = {"ui_remota": False, "formatos": FORMATOS_PATH}


# --------------------------------------------------------------------------- #
# Formatos preconfigurados
# --------------------------------------------------------------------------- #
def format_from_spec(spec: dict) -> WiegandFormat:
    try:
        parities = [Parity(p["kind"], list(p.get("covers", []))) for p in spec.get("parities", [])]
        fmt = WiegandFormat(
            name=str(spec["name"])[:24],
            card_format=str(spec["card_format"]).upper(),
            parities=parities,
            format_type=int(spec.get("format_type", 3)),
            status=int(spec.get("status", 1)),
            site_code=int(spec.get("site_code", 0)),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise FormatError(f"spec invalido: {exc}") from exc
    fmt.validate()
    return fmt


def cargar_formatos(path: str = None) -> list:
    """Lee formatos.json. Acepta {"formatos": [...]} o una lista (user_presets.json).

    Cada entrada: {"name", "spec", "descripcion"?, "habilitado"?, "estado"?}.
    Devuelve solo las habilitadas y validas, con su indice estable ``id``.
    """
    path = path or CONFIG["formatos"]
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    entries = data.get("formatos", []) if isinstance(data, dict) else data
    out = []
    for i, e in enumerate(entries):
        if not isinstance(e, dict) or not e.get("spec") or not e.get("habilitado", True):
            continue
        fmt = format_from_spec(e["spec"])  # un formato invalido es un error del admin
        out.append({
            "id": i,
            "name": e.get("name") or fmt.name,
            "descripcion": e.get("descripcion", ""),
            "estado": e.get("estado", ""),
            "fmt": fmt,
        })
    return out


def _buscar(fid) -> dict:
    for f in cargar_formatos():
        if f["id"] == fid:
            return f
    raise ValueError("formato no disponible")


def _publico(f: dict) -> dict:
    fmt = f["fmt"]
    return {
        "id": f["id"], "name": f["name"], "descripcion": f["descripcion"],
        "estado": f["estado"], "format_name": fmt.name, "card_bit": fmt.card_bit,
        "card_format": fmt.card_format, "format_type": fmt.format_type,
    }


# --------------------------------------------------------------------------- #
# Secuencia de carga
# --------------------------------------------------------------------------- #
def preparar_carga(fmt: WiegandFormat):
    """Genera el update.sql (fabrica + formato), lo registra en /dl/ y arma los pasos.

    Siempre respalda ZKDB.db primero. Devuelve (pasos, sql, opciones).
    """
    sql = sqlgen.build_rewrite_block([fmt], keep_factory=True)
    opts = sqlgen.rewrite_options([fmt], keep_factory=True)
    payload = sql.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
    md5 = zk_panel.hashlib.md5(payload).hexdigest()
    with zk_panel.LOCK:
        zk_panel.G["file"] = {"name": ARCHIVO, "data": payload, "md5": md5, "size": len(payload)}
    steps = backup.build_backup_sequence()
    steps += loader.build_in01_load_sequence(zk_panel.url_dl(), short_name=ARCHIVO)
    steps = loader.with_options(steps, sqlgen.set_options_command(opts))
    return steps, sql, opts


def _sn_valido(sn: str) -> str:
    sn = (sn or "").strip()
    with zk_panel.LOCK:
        conocidos = set(zk_panel.G["devices"])
    if not sn or sn == "all" or sn not in conocidos:
        raise ValueError("elige un reloj conectado")
    return sn


# --------------------------------------------------------------------------- #
# Handler
# --------------------------------------------------------------------------- #
class Handler(zk_panel.Handler):
    def _ui_permitida(self) -> bool:
        return CONFIG["ui_remota"] or self.client_address[0] in ("127.0.0.1", "::1")

    def _prohibido(self):
        return self._send("acceso no permitido en la version restringida", code=403)

    def _static(self, rel: str, ctype: str):
        path = os.path.join(STATIC_DIR, rel)
        if not os.path.isfile(path):
            return self._send("not found", code=404)
        with open(path, "rb") as fh:
            return self._send(fh.read(), ctype)

    def _es_push(self, p: str) -> bool:
        return p.startswith("/iclock/") or p.endswith(_PUSH_SUFFIXES)

    def do_GET(self):  # noqa: N802
        p = urlparse(self.path).path
        # El reloj: protocolo PUSH y descarga del update.sql.
        if self._es_push(p) or p.startswith("/dl/"):
            return super().do_GET()
        if not self._ui_permitida():
            return self._prohibido()
        if p in ("/", "/index.html"):
            return self._static("index.html", "text/html; charset=utf-8")
        if p == "/app.js":
            return self._static("app.js", "application/javascript; charset=utf-8")
        if p == "/app.css":
            return self._static("app.css", "text/css; charset=utf-8")
        if p == "/api/r/estado":
            return self._json(self._estado())
        if p == "/api/r/formatos":
            try:
                return self._json({"formatos": [_publico(f) for f in cargar_formatos()]})
            except (OSError, ValueError, FormatError) as exc:
                return self._json({"error": f"formatos.json invalido: {exc}"}, 500)
        return self._prohibido()

    def do_POST(self):  # noqa: N802
        p = urlparse(self.path).path
        if self._es_push(p):
            return super().do_POST()
        if not self._ui_permitida() or not p.startswith("/api/r/"):
            return self._prohibido()
        length = int(self.headers.get("Content-Length", 0) or 0)
        try:
            data = json.loads(self.rfile.read(length) or b"{}") if length else {}
        except ValueError:
            return self._json({"error": "json invalido"}, 400)
        try:
            if p == "/api/r/preview":
                return self._preview(data)
            if p == "/api/r/cargar":
                return self._cargar(data)
            if p == "/api/r/verificar":
                return self._verificar(data)
            if p == "/api/r/resultado":
                return self._resultado(data)
            if p == "/api/r/rollback":
                return self._rollback(data)
        except (ValueError, FormatError, loader.LoadError, OSError) as exc:
            return self._json({"error": str(exc)}, 400)
        return self._prohibido()

    # -- endpoints --------------------------------------------------------- #
    def _estado(self):
        with zk_panel.LOCK:
            return {
                "myip": zk_panel.G["myip"],
                "port": zk_panel.G["port"],
                "devices": dict(zk_panel.G["devices"]),
                "log": zk_panel.G["log"][-60:],
            }

    def _preview(self, data):
        f = _buscar(data.get("id"))
        steps, sql, opts = preparar_carga(f["fmt"])
        return self._json({
            "formato": _publico(f),
            "steps": [{"cmd": s.cmd, "descripcion": s.descripcion} for s in steps],
            "opciones": opts,
            "lineas_sql": sql.count("\n"),
        })

    def _cargar(self, data):
        sn = _sn_valido(data.get("sn"))
        f = _buscar(data.get("id"))
        steps, _, _ = preparar_carga(f["fmt"])
        ids = [zk_panel.enqueue(sn, s.cmd) for s in steps]
        zk_panel.log(f"[{sn}] CARGA formato '{f['name']}' ({len(ids)} comandos)")
        return self._json({"queued": len(ids), "sn": sn, "formato": f["name"]})

    def _verificar(self, data):
        sn = _sn_valido(data.get("sn"))
        ids = [zk_panel.enqueue(sn, s.cmd) for s in backup.build_verify_fetch_sequence()]
        return self._json({"queued": len(ids), "sn": sn})

    def _resultado(self, data):
        f = _buscar(data.get("id"))
        fmt = f["fmt"]
        with zk_panel.LOCK:
            caps = [c for c in zk_panel.G["captures"] if c.get("type", "").startswith("SQLite")]
        if not caps:
            return self._json({"error": "todavia no llega la copia de ZKDB.db del reloj"}, 404)
        res = backup.verify_active_formats(caps[-1]["path"], {fmt.format_type: fmt.name})
        return self._json({"ok": res.ok, "activos": res.activos, "problemas": res.problemas})

    def _rollback(self, data):
        sn = _sn_valido(data.get("sn"))
        ids = [zk_panel.enqueue(sn, s.cmd) for s in backup.build_rollback_sequence()]
        zk_panel.log(f"[{sn}] ROLLBACK encolado ({len(ids)} comandos)")
        return self._json({"queued": len(ids), "sn": sn})


# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser(description="Carga restringida de formatos Wiegand (IN01).")
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--myip", help="IP LAN de esta PC (si no se detecta sola)")
    ap.add_argument("--capdir", default="captures")
    ap.add_argument("--formatos", default=FORMATOS_PATH, help="archivo de formatos permitidos")
    ap.add_argument("--ui-remota", action="store_true",
                    help="permitir abrir la interfaz desde otros PCs de la red")
    args = ap.parse_args()

    CONFIG["formatos"] = args.formatos
    CONFIG["ui_remota"] = args.ui_remota
    disponibles = cargar_formatos()  # falla al inicio si formatos.json esta mal

    zk_panel.CAP_DIR = args.capdir
    os.makedirs(args.capdir, exist_ok=True)
    if args.myip:
        ip = args.myip
    else:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
        except OSError:
            ip = "127.0.0.1"
        finally:
            s.close()
    zk_panel.G["myip"] = ip
    zk_panel.G["port"] = args.port

    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    zk_panel.log(f"Carga restringida en  http://127.0.0.1:{args.port}/   "
                 f"({len(disponibles)} formatos habilitados)")
    zk_panel.log(
        f"Apunta el reloj: SET OPTIONS WebServerURLModel=0,WebServerPort={args.port},"
        f"ICLOCKSVRURL={ip},IsSupportSSL=0   y luego REBOOT"
    )
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        zk_panel.log("Cerrando.")
        srv.shutdown()


if __name__ == "__main__":
    main()
