"""Pruebas de la version restringida: formatos, secuencia de carga y rutas bloqueadas.

Levanta el servidor en un puerto libre y simula un reloj por el protocolo PUSH.
Ejecutar:  python tests/test_restringida.py
"""

import json
import os
import socket
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import app_restringida as app  # noqa: E402
import zk_panel  # noqa: E402

REF = os.path.join(ROOT, "tests", "data", "update_herramienta_ok.sql")


def _server():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    zk_panel.CAP_DIR = tempfile.mkdtemp()
    zk_panel.G["myip"] = "127.0.0.1"
    zk_panel.G["port"] = port
    srv = ThreadingHTTPServer(("127.0.0.1", port), app.Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{port}"


def _req(base, path, body=None, method=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(base + path, data=data, method=method or ("POST" if data else "GET"),
                               headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(r, timeout=5) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def test_formatos_json_valido():
    fs = app.cargar_formatos(app.FORMATOS_PATH)
    nombres = [f["fmt"].name for f in fs]
    assert "Wiegand26a" in nombres and "Wiegand26" in nombres
    # El HID 35 bits viene deshabilitado hasta confirmarlo en el reloj.
    assert all(f["fmt"].card_bit != 35 for f in fs)


def test_secuencia_con_respaldo_opciones_y_reboot():
    fmt = [f for f in app.cargar_formatos() if f["fmt"].name == "Wiegand26a"][0]["fmt"]
    zk_panel.G["myip"], zk_panel.G["port"] = "192.168.2.103", 8080
    steps, sql, opts = app.preparar_carga(fmt)
    cmds = [s.cmd for s in steps]
    assert cmds[0] == "shell cp /mnt/mtdblock/data/ZKDB.db /mnt/mtdblock/data/ZKDB.bak"
    assert "shell cd /mnt/mtdblock && wget http://192.168.2.103:8080/dl/u.sql" in cmds
    assert cmds[-3:] == ["SET OPTIONS ExtWGInBitsCount=26,WGOutBitsCount=26", "shell sync", "REBOOT"]
    assert opts == {"ExtWGInBitsCount": 26, "WGOutBitsCount": 26}
    # Mismo encabezado que la herramienta que funciona en el IN01.
    with open(REF, "rb") as fh:
        ref = fh.read().decode("utf-8").splitlines()
    assert sql.splitlines()[:4] == ref[:4]
    assert "'Wiegand26a','ESSSSSSSSCCCCCCCCCCCCCCCCO'" in sql and sql.count(",3,1);") == 1


def test_rutas_bloqueadas_y_flujo_completo():
    srv, base = _server()
    try:
        # Lo que la version completa permite y esta no.
        for path in ("/panel", "/api/state", "/api/preview", "/captures/x/y"):
            assert _req(base, path)[0] == 403, path
        for path in ("/api/raw", "/api/queue", "/api/getfile", "/api/setfile", "/api/clear",
                     "/api/wg/build", "/api/wg/load"):
            assert _req(base, path, {"cmd": "REBOOT", "sn": "all"})[0] == 403, path

        st, body = _req(base, "/api/r/formatos")
        assert st == 200
        fid = [f for f in json.loads(body)["formatos"] if f["format_name"] == "Wiegand26a"][0]["id"]

        # Sin reloj conectado no se puede cargar.
        assert _req(base, "/api/r/cargar", {"sn": "SN1", "id": fid})[0] == 400

        # El reloj se conecta (handshake PUSH) y queda disponible.
        assert _req(base, "/iclock/cdata?SN=SN1&options=all&pushver=2.4.1")[0] == 200
        st, body = _req(base, "/api/r/cargar", {"sn": "SN1", "id": fid})
        assert st == 200 and json.loads(body)["queued"] == 14

        # El reloj recoge los comandos y descarga el archivo.
        st, body = _req(base, "/iclock/getrequest?SN=SN1")
        lineas = body.decode().strip().splitlines()
        assert lineas[0].endswith(":shell cp /mnt/mtdblock/data/ZKDB.db /mnt/mtdblock/data/ZKDB.bak")
        assert lineas[-1].endswith(":REBOOT")
        st, body = _req(base, "/dl/u.sql?SN=SN1")
        assert st == 200 and body.startswith(b"[INSERT]\n{\n")

        # Nunca a "all", ni formatos inexistentes.
        assert _req(base, "/api/r/cargar", {"sn": "all", "id": fid})[0] == 400
        assert _req(base, "/api/r/cargar", {"sn": "SN1", "id": 999})[0] == 400
    finally:
        srv.shutdown()


def test_interfaz_solo_local():
    # Simula un cliente de otra IP: la UI se niega, el protocolo del reloj no.
    class H(app.Handler):
        def __init__(self, *a, **kw):
            super().__init__(*a, **kw)

    h = H.__new__(H)
    h.client_address = ("192.168.2.50", 5000)
    app.CONFIG["ui_remota"] = False
    assert not h._ui_permitida()
    app.CONFIG["ui_remota"] = True
    assert h._ui_permitida()
    app.CONFIG["ui_remota"] = False
    assert h._es_push("/iclock/getrequest") and not h._es_push("/api/raw")


if __name__ == "__main__":
    import traceback

    passed = failed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
                passed += 1
            except Exception:
                print(f"FAIL {name}")
                traceback.print_exc()
                failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
