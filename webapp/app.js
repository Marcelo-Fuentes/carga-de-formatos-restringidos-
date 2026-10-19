"use strict";
const $ = (id) => document.getElementById(id);
const esc = (t) => String(t).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const api = async (path, body) => {
  const r = await fetch(path, body ? {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body)
  } : undefined);
  const j = await r.json().catch(() => ({ error: "respuesta inesperada del servidor" }));
  if (!r.ok) throw new Error(j.error || ("HTTP " + r.status));
  return j;
};
const msg = (el, text, kind) => {
  el.textContent = text; el.className = text ? "msg show " + (kind || "") : "msg";
};

let formatos = [];
let elegido = null;   // id del formato elegido

const TIPO = { 3: "entrada", 1: "salida", 2: "interno" };

function renderFormatos() {
  const box = $("formatos"); box.innerHTML = "";
  if (!formatos.length) {
    box.innerHTML = '<div class="hint">No hay formatos habilitados. Pide al administrador que revise formatos.json.</div>';
    return;
  }
  formatos.forEach(f => {
    const d = document.createElement("label");
    d.className = "fmt" + (f.id === elegido ? " sel" : "");
    d.innerHTML = `<input type="radio" name="fmt" value="${f.id}" ${f.id === elegido ? "checked" : ""}>
      <div><div class="nm">${esc(f.name)}
        ${f.estado ? `<span class="badge">${esc(f.estado)}</span>` : ""}</div>
        <div class="meta">${f.card_bit} bits · ${TIPO[f.format_type] || "tipo " + f.format_type}</div>
        <div class="desc">${esc(f.descripcion)}</div></div>`;
    d.querySelector("input").onchange = () => { elegido = f.id; renderFormatos(); $("prevbox").style.display = "none"; };
    box.appendChild(d);
  });
}

function sel() {
  const sn = $("sn").value;
  if (!sn) throw new Error("Elige un reloj conectado.");
  if (elegido === null) throw new Error("Elige un formato.");
  return { sn, id: elegido };
}

async function preview() {
  try {
    if (elegido === null) throw new Error("Elige un formato.");
    const j = await api("/api/r/preview", { id: elegido });
    $("prevbox").style.display = "block";
    $("prevbox").textContent = j.steps.map((s, i) => `${String(i + 1).padStart(2)}. ${s.descripcion}\n    ${s.cmd}`).join("\n");
    msg($("loadmsg"), "", "");
  } catch (e) { msg($("loadmsg"), e.message, "err"); }
}

async function cargar() {
  try {
    const s = sel();
    const f = formatos.find(x => x.id === s.id);
    if (!confirm(`Cargar "${f.name}" en el reloj ${s.sn}.\nEl reloj se reiniciará. ¿Continuar?`)) return;
    const j = await api("/api/r/cargar", s);
    msg($("loadmsg"), `Enviado: ${j.queued} pasos a ${j.sn}. El reloj los ejecuta en su próxima consulta y se reinicia.`, "ok");
  } catch (e) { msg($("loadmsg"), e.message, "err"); }
}

async function verificarPedir() {
  try {
    const { sn } = sel();
    await api("/api/r/verificar", { sn });
    msg($("vmsg"), "Copia solicitada. Espera a ver «CAPTURADO … ZKDB» en Actividad y pulsa 2.", "ok");
  } catch (e) { msg($("vmsg"), e.message, "err"); }
}

async function verificarComprobar() {
  try {
    const { id } = sel();
    const j = await api("/api/r/resultado", { id });
    if (j.ok) msg($("vmsg"), "Correcto: el formato elegido es el activo de entrada.", "ok");
    else msg($("vmsg"), "No coincide: " + (j.problemas || []).join("; "), "err");
  } catch (e) { msg($("vmsg"), e.message, "err"); }
}

async function rollback() {
  try {
    const sn = $("sn").value;
    if (!sn) throw new Error("Elige un reloj conectado.");
    if (!confirm(`Deshacer la última carga en ${sn}: se restaura la copia guardada y el reloj se reinicia. ¿Continuar?`)) return;
    const j = await api("/api/r/rollback", { sn });
    msg($("vmsg"), `Deshacer enviado (${j.queued} pasos) a ${j.sn}.`, "ok");
  } catch (e) { msg($("vmsg"), e.message, "err"); }
}

async function tick() {
  try {
    const s = await api("/api/r/estado");
    const sns = Object.keys(s.devices || {});
    const selEl = $("sn"), cur = selEl.value;
    selEl.innerHTML = sns.length ? sns.map(x => `<option value="${esc(x)}">${esc(x)} · ${esc(s.devices[x].ip)}</option>`).join("")
                                 : '<option value="">(ningún reloj conectado)</option>';
    if (sns.includes(cur)) selEl.value = cur;
    $("devchip").classList.toggle("on", sns.length > 0);
    $("devtxt").textContent = sns.length ? `${sns.length} reloj(es) conectado(s)` : "Esperando relojes…";
    $("hdrsub").textContent = `servidor ${s.myip}:${s.port}`;
    $("logbox").textContent = (s.log || []).slice(-25).join("\n") || "—";
  } catch (e) { $("devtxt").textContent = "Sin conexión con el servidor"; }
}

async function init() {
  try {
    const j = await api("/api/r/formatos");
    formatos = j.formatos;
    if (formatos.length === 1) elegido = formatos[0].id;
  } catch (e) { $("formatos").innerHTML = `<div class="msg show err">${esc(e.message)}</div>`; }
  renderFormatos();
  $("btnprev").onclick = preview;
  $("btnload").onclick = cargar;
  $("btnvfetch").onclick = verificarPedir;
  $("btnvcheck").onclick = verificarComprobar;
  $("btnrollback").onclick = rollback;
  tick(); setInterval(tick, 2000);
}
init();
