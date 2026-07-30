from __future__ import annotations

import json
import os
import re
import subprocess
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
MATRIX_PATH = ROOT / "docs" / "nexora" / "MATRIZ_REQUISITOS.md"
LIVE_PATH = ROOT / "docs" / "nexora" / "LIVE_PROGRESS.json"
REPO_FULL_NAME = "Clopezgg/Gesti-n-de-Construcci-n-Residencial"
BRANCH = "nexora-continuidad-total"
PORT = int(os.environ.get("NEXORA_MONITOR_PORT", "8765"))
TOTAL_REQUIREMENTS = 166
FINAL_STATES = {
    "IMPLEMENTADO Y VALIDADO",
    "OBSOLETO JUSTIFICADO",
    "NO APLICA JUSTIFICADO",
}
FAILED_CONCLUSIONS = {
    "failure",
    "cancelled",
    "timed_out",
    "action_required",
    "startup_failure",
    "stale",
}

CACHE: dict[str, Any] = {"at": 0.0, "runs": [], "error": None}
CACHE_LOCK = threading.Lock()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_git(*args: str) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=20,
        )
        return (result.stdout or result.stderr).strip()
    except Exception as exc:  # pragma: no cover - monitor must stay alive
        return f"ERROR: {exc}"


def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def parse_matrix() -> dict[str, Any]:
    requirements: list[dict[str, Any]] = []
    if MATRIX_PATH.exists():
        for raw_line in MATRIX_PATH.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw_line.strip()
            if not line.startswith("| `NXR-"):
                continue
            columns = [part.strip() for part in line.strip("|").split("|")]
            if len(columns) < 4:
                continue
            req_id = columns[0].strip("`")
            title = columns[1]
            state = columns[2].upper()
            owner = columns[3].upper()
            match = re.search(r"BLOQUE\s+(\d+)", owner)
            block = int(match.group(1)) if match else None
            requirements.append(
                {
                    "id": req_id,
                    "title": title,
                    "state": state,
                    "owner": owner,
                    "block": block,
                    "resolved": state in FINAL_STATES,
                }
            )

    resolved = sum(1 for item in requirements if item["resolved"])
    denominator = TOTAL_REQUIREMENTS
    percent = round((resolved / denominator) * 100, 1) if denominator else 0.0

    blocks: list[dict[str, Any]] = []
    for block_number in range(21):
        owned = [item for item in requirements if item["block"] == block_number]
        block_resolved = sum(1 for item in owned if item["resolved"])
        unresolved_states = sorted({item["state"] for item in owned if not item["resolved"]})
        if not owned:
            status = "unknown"
        elif block_resolved == len(owned):
            status = "passed"
        elif block_resolved == 0:
            status = "pending"
        else:
            status = "partial"
        blocks.append(
            {
                "number": block_number,
                "total": len(owned),
                "resolved": block_resolved,
                "status": status,
                "unresolved_states": unresolved_states,
            }
        )

    return {
        "total_expected": TOTAL_REQUIREMENTS,
        "rows_found": len(requirements),
        "resolved": resolved,
        "pending": max(0, denominator - resolved),
        "percent": percent,
        "blocks": blocks,
        "requirements": requirements,
        "matrix_exists": MATRIX_PATH.exists(),
    }


def github_runs() -> tuple[list[dict[str, Any]], str | None]:
    now = time.time()
    with CACHE_LOCK:
        if now - float(CACHE["at"]) < 20:
            return list(CACHE["runs"]), CACHE["error"]

    url = (
        f"https://api.github.com/repos/{REPO_FULL_NAME}/actions/runs"
        f"?branch={BRANCH}&per_page=100"
    )
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "NEXORA-local-progress-monitor",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
        latest: dict[str, dict[str, Any]] = {}
        for run in payload.get("workflow_runs", []):
            name = str(run.get("name") or "Workflow sin nombre")
            if name in latest:
                continue
            status = str(run.get("status") or "unknown")
            conclusion = run.get("conclusion")
            if status in {"queued", "in_progress", "waiting", "requested", "pending"}:
                level = "running"
            elif conclusion == "success":
                level = "passed"
            elif conclusion == "skipped":
                level = "skipped"
            elif conclusion in FAILED_CONCLUSIONS:
                level = "failed"
            else:
                level = "unknown"
            latest[name] = {
                "name": name,
                "status": status,
                "conclusion": conclusion,
                "level": level,
                "run_number": run.get("run_number"),
                "head_sha": str(run.get("head_sha") or ""),
                "head_branch": run.get("head_branch"),
                "event": run.get("event"),
                "created_at": run.get("created_at"),
                "updated_at": run.get("updated_at"),
                "html_url": run.get("html_url"),
            }
        runs = sorted(latest.values(), key=lambda item: item["name"].lower())
        error = None
    except urllib.error.HTTPError as exc:
        runs = []
        error = f"GitHub respondió HTTP {exc.code}. El monitor reintentará automáticamente."
    except Exception as exc:  # pragma: no cover
        runs = []
        error = f"No se pudo consultar GitHub Actions: {exc}"

    with CACHE_LOCK:
        CACHE["at"] = now
        CACHE["runs"] = runs
        CACHE["error"] = error
    return runs, error


def build_status() -> dict[str, Any]:
    matrix = parse_matrix()
    live = read_json(
        LIVE_PATH,
        {
            "agent_status": "unknown",
            "phase": "Sin datos",
            "current_block": None,
            "task": "LIVE_PROGRESS.json no está disponible",
            "tests": [],
            "events": [],
            "block_overrides": {},
        },
    )
    runs, github_error = github_runs()
    head = run_git("rev-parse", "HEAD")
    branch = run_git("branch", "--show-current")
    status_lines = [line for line in run_git("status", "--short").splitlines() if line.strip()]
    last_commit = run_git("log", "-1", "--pretty=%h %s")

    overrides = live.get("block_overrides") or {}
    current_block = live.get("current_block")
    for block in matrix["blocks"]:
        override = overrides.get(str(block["number"])) or overrides.get(block["number"])
        if override in {"passed", "partial", "failed", "pending", "running", "unknown"}:
            block["status"] = override
        if current_block == block["number"] and live.get("agent_status") == "working":
            block["status"] = "running"

    failures = [run for run in runs if run["level"] == "failed"]
    running = [run for run in runs if run["level"] == "running"]
    passed = [run for run in runs if run["level"] == "passed"]

    tests = []
    for item in live.get("tests") or []:
        status = str(item.get("status") or "unknown").lower()
        level = {
            "passed": "passed",
            "success": "passed",
            "failed": "failed",
            "failure": "failed",
            "running": "running",
            "queued": "running",
            "skipped": "skipped",
        }.get(status, "unknown")
        tests.append({**item, "level": level})

    return {
        "generated_at": utc_now(),
        "progress": matrix,
        "live": live,
        "git": {
            "root": str(ROOT),
            "branch": branch,
            "head": head,
            "last_commit": last_commit,
            "dirty_count": len(status_lines),
            "dirty_files": status_lines[:30],
        },
        "github": {
            "runs": runs,
            "error": github_error,
            "summary": {
                "passed": len(passed),
                "failed": len(failures),
                "running": len(running),
                "total": len(runs),
            },
        },
        "tests": tests,
        "safety": {
            "merge_allowed": False,
            "tag_allowed": False,
            "production_allowed": False,
            "target_branch": BRANCH,
        },
    }


HTML = r"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>NEXORA — Monitor real</title>
<style>
:root{color-scheme:dark;--bg:#07111d;--panel:#0d1b2a;--line:#294157;--text:#e8f0f7;--muted:#91a8ba;--green:#32d583;--red:#f97066;--amber:#fdb022;--blue:#53b1fd;--gray:#667085}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at top,#112a40 0,#07111d 48%);color:var(--text);font:14px/1.45 system-ui,-apple-system,Segoe UI,sans-serif}
main{max-width:1500px;margin:auto;padding:22px}.top{display:flex;gap:18px;align-items:flex-start;justify-content:space-between;flex-wrap:wrap}.title h1{margin:0;font-size:28px}.title p{margin:4px 0;color:var(--muted)}
.badge{padding:7px 11px;border:1px solid var(--line);border-radius:999px;background:#071624}.grid{display:grid;grid-template-columns:repeat(12,1fr);gap:14px;margin-top:16px}.panel{background:rgba(13,27,42,.94);border:1px solid var(--line);border-radius:16px;padding:16px;box-shadow:0 12px 34px rgba(0,0,0,.22)}
.span12{grid-column:span 12}.span8{grid-column:span 8}.span6{grid-column:span 6}.span4{grid-column:span 4}.metric{font-size:30px;font-weight:800}.muted{color:var(--muted)}
.progress-shell{height:26px;background:#071624;border:1px solid var(--line);border-radius:999px;overflow:hidden;position:relative}.progress-fill{height:100%;width:0;background:linear-gradient(90deg,#1570ef,#32d583);transition:width .6s ease}.progress-label{position:absolute;inset:0;display:grid;place-items:center;font-weight:800;text-shadow:0 1px 3px #000}
.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:12px}.kpi{padding:10px;border:1px solid var(--line);border-radius:12px;background:#091827}.kpi b{display:block;font-size:22px}
#mapWrap{position:relative;min-height:400px}.map{position:relative;z-index:2;display:grid;grid-template-columns:repeat(7,minmax(96px,1fr));gap:22px 14px;padding:18px 6px}.links{position:absolute;inset:0;z-index:1;width:100%;height:100%;pointer-events:none}.links line{stroke:#3c5870;stroke-width:2;stroke-dasharray:5 5}
.node{min-height:86px;padding:10px;border-radius:14px;border:2px solid var(--gray);background:#0a1927;display:flex;flex-direction:column;justify-content:center;text-align:center;position:relative}.node .n{font-size:18px;font-weight:900}.node small{color:var(--muted)}.node.passed{border-color:var(--green)}.node.failed{border-color:var(--red);box-shadow:0 0 18px rgba(249,112,102,.2)}.node.partial{border-color:var(--amber)}.node.running{border-color:var(--blue);animation:pulse 1.4s infinite}.node.pending,.node.unknown{border-color:var(--gray)}
@keyframes pulse{50%{box-shadow:0 0 24px rgba(83,177,253,.45)}}
.dot{width:11px;height:11px;border-radius:50%;display:inline-block;margin-right:9px;background:var(--gray);box-shadow:0 0 0 3px rgba(102,112,133,.12)}.dot.passed{background:var(--green)}.dot.failed{background:var(--red)}.dot.running{background:var(--amber);animation:pulse 1.2s infinite}.dot.skipped{background:var(--gray)}
.list{display:grid;gap:8px;max-height:480px;overflow:auto}.row{padding:10px;border:1px solid var(--line);border-radius:11px;background:#091827}.row-top{display:flex;align-items:center;justify-content:space-between;gap:12px}.row a{color:#84caff;text-decoration:none}.error{border-color:#7a271a;background:#2d100d}.warning{border-color:#7a5d11;background:#2a2008}.ok{border-color:#14532d;background:#082417}
code{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;color:#b9e6fe;word-break:break-all}.footer{margin:18px 0;color:var(--muted);text-align:center}
@media(max-width:1000px){.span8,.span6,.span4{grid-column:span 12}.map{grid-template-columns:repeat(4,1fr)}.kpis{grid-template-columns:repeat(2,1fr)}}
@media(max-width:600px){main{padding:12px}.map{grid-template-columns:repeat(2,1fr)}.kpis{grid-template-columns:1fr}.title h1{font-size:23px}}
</style>
</head>
<body><main>
<div class="top"><div class="title"><h1>NEXORA — Monitor de avance verificable</h1><p>El porcentaje sale de la matriz de 166 requisitos, no de tokens ni de afirmaciones del agente.</p></div><div id="clock" class="badge">Cargando…</div></div>
<div class="grid">
<section class="panel span12"><div class="row-top"><div><div class="muted">Avance real certificado en la matriz</div><div class="metric"><span id="pct">0</span>%</div></div><div style="text-align:right"><b id="count">0/166</b><div class="muted" id="rowsFound"></div></div></div><div class="progress-shell"><div id="bar" class="progress-fill"></div><div id="barLabel" class="progress-label">0%</div></div><div class="kpis"><div class="kpi"><span class="muted">Resueltos</span><b id="resolved">0</b></div><div class="kpi"><span class="muted">Pendientes</span><b id="pending">166</b></div><div class="kpi"><span class="muted">CI fallidos</span><b id="failed">0</b></div><div class="kpi"><span class="muted">CI ejecutándose</span><b id="running">0</b></div></div></section>
<section class="panel span8"><h2>Mapa conectado de Bloques 0–20</h2><div id="mapWrap"><svg id="links" class="links"></svg><div id="map" class="map"></div></div></section>
<section class="panel span4"><h2>Trabajo actual de OpenCode</h2><div id="agentCard" class="row"><div class="row-top"><b id="agentStatus">Sin datos</b><span id="currentBlock" class="badge">Bloque —</span></div><h3 id="task">—</h3><p id="detail" class="muted">—</p><div class="muted">Fase</div><div id="phase">—</div><div class="muted" style="margin-top:10px">Última actualización</div><div id="liveTime">—</div></div><h3>Git local</h3><div class="row"><div>Rama: <code id="branch"></code></div><div>HEAD: <code id="head"></code></div><div>Commit: <code id="commit"></code></div><div>Cambios sin commit: <b id="dirty"></b></div></div></section>
<section class="panel span6"><h2>Pruebas reportadas por OpenCode</h2><div id="tests" class="list"></div></section>
<section class="panel span6"><h2>GitHub Actions y despliegue técnico</h2><div id="githubError"></div><div id="workflows" class="list"></div></section>
<section class="panel span12"><h2>Bloqueos y seguridad</h2><div class="row warning"><b>No fusionar, no crear tags y no desplegar.</b> El monitor solo considera terminado el trabajo cuando los 166 requisitos tienen estado final con evidencia y todos los controles obligatorios pasan sobre el mismo SHA completo.</div><div id="blocking" class="row" style="margin-top:8px"></div></section>
</div><div class="footer">Actualización automática cada 3 segundos · GitHub se consulta como máximo cada 20 segundos · Servidor local 127.0.0.1</div>
</main>
<script>
const esc=s=>String(s??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
function dot(level){return `<span class="dot ${esc(level)}"></span>`}
function drawLinks(){const svg=document.getElementById('links'),wrap=document.getElementById('mapWrap');svg.innerHTML='';const wr=wrap.getBoundingClientRect();for(let i=0;i<20;i++){const a=document.getElementById(`block-${i}`),b=document.getElementById(`block-${i+1}`);if(!a||!b)continue;const ar=a.getBoundingClientRect(),br=b.getBoundingClientRect();const line=document.createElementNS('http://www.w3.org/2000/svg','line');line.setAttribute('x1',ar.left+ar.width/2-wr.left);line.setAttribute('y1',ar.top+ar.height/2-wr.top);line.setAttribute('x2',br.left+br.width/2-wr.left);line.setAttribute('y2',br.top+br.height/2-wr.top);svg.appendChild(line)}}
function render(data){const p=data.progress,live=data.live||{},gh=data.github||{};document.getElementById('clock').textContent=`Actualizado ${data.generated_at}`;document.getElementById('pct').textContent=p.percent.toFixed(1);document.getElementById('bar').style.width=`${Math.min(100,p.percent)}%`;document.getElementById('barLabel').textContent=`${p.percent.toFixed(1)}%`;document.getElementById('count').textContent=`${p.resolved}/${p.total_expected}`;document.getElementById('rowsFound').textContent=`Filas encontradas: ${p.rows_found}`;document.getElementById('resolved').textContent=p.resolved;document.getElementById('pending').textContent=p.pending;document.getElementById('failed').textContent=gh.summary?.failed??0;document.getElementById('running').textContent=gh.summary?.running??0;
const map=document.getElementById('map');map.innerHTML=p.blocks.map(b=>`<div id="block-${b.number}" class="node ${esc(b.status)}" title="${esc((b.unresolved_states||[]).join(', '))}"><div class="n">Bloque ${b.number}</div><small>${b.resolved}/${b.total} requisitos</small><small>${esc(b.status)}</small></div>`).join('');requestAnimationFrame(drawLinks);
document.getElementById('agentStatus').textContent=live.agent_status||'unknown';document.getElementById('currentBlock').textContent=live.current_block===null||live.current_block===undefined?'Bloque —':`Bloque ${live.current_block}`;document.getElementById('task').textContent=live.task||'—';document.getElementById('detail').textContent=live.detail||'—';document.getElementById('phase').textContent=live.phase||'—';document.getElementById('liveTime').textContent=live.last_update||'—';document.getElementById('branch').textContent=data.git.branch;document.getElementById('head').textContent=data.git.head;document.getElementById('commit').textContent=data.git.last_commit;document.getElementById('dirty').textContent=data.git.dirty_count;
const tests=document.getElementById('tests');tests.innerHTML=(data.tests||[]).length?(data.tests||[]).slice().reverse().map(t=>`<div class="row ${t.level==='failed'?'error':''}"><div class="row-top"><div>${dot(t.level)}<b>${esc(t.name||t.command||'Prueba')}</b></div><span>${esc(t.status)}</span></div><div class="muted">${esc(t.detail||t.command||'')}</div></div>`).join(''):'<div class="row muted">OpenCode todavía no ha reportado pruebas en LIVE_PROGRESS.json.</div>';
const ge=document.getElementById('githubError');ge.innerHTML=gh.error?`<div class="row warning">${esc(gh.error)}</div>`:'';const workflows=document.getElementById('workflows');workflows.innerHTML=(gh.runs||[]).length?(gh.runs||[]).map(w=>`<div class="row ${w.level==='failed'?'error':w.level==='passed'?'ok':''}"><div class="row-top"><div>${dot(w.level)}<b>${esc(w.name)}</b></div><span>${esc(w.conclusion||w.status)}</span></div><div class="muted">Run ${esc(w.run_number)} · ${esc((w.head_sha||'').slice(0,12))}</div>${w.html_url?`<a href="${esc(w.html_url)}" target="_blank">Abrir en GitHub</a>`:''}</div>`).join(''):'<div class="row muted">No hay datos de GitHub Actions todavía.</div>';
const block=live.blocking_issue;document.getElementById('blocking').innerHTML=block?`${dot('failed')}<b>${esc(block)}</b>`:`${dot('passed')}Sin bloqueo real reportado por OpenCode.`}
async function tick(){try{const r=await fetch('/api/status',{cache:'no-store'});render(await r.json())}catch(e){document.getElementById('clock').textContent='Monitor desconectado'}}tick();setInterval(tick,3000);window.addEventListener('resize',drawLinks);
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        """Serve the dashboard page and status data for supported GET request paths."""
        if self.path == "/api/status":
            payload = json.dumps(build_status(), ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        if self.path in {"/", "/index.html"}:
            payload = HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        self.send_error(404)

    def log_message(self, _format: str, *args: Any) -> None:
        return


def open_browser() -> None:
    time.sleep(0.8)
    webbrowser.open(f"http://127.0.0.1:{PORT}")


def main() -> None:
    os.chdir(ROOT)
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    threading.Thread(target=open_browser, daemon=True).start()
    print("NEXORA Monitor activo")
    print(f"Repositorio: {ROOT}")
    print(f"Panel: http://127.0.0.1:{PORT}")
    print("Presiona Ctrl+C únicamente cuando quieras cerrar el monitor.")
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        print("\nMonitor cerrado.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
