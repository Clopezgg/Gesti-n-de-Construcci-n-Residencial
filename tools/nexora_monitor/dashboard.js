import { execFileSync } from "node:child_process";
import { existsSync, readFileSync, statSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..", "..");
const MATRIX_PATH = join(ROOT, "docs", "nexora", "MATRIZ_REQUISITOS.md");
const LIVE_PATH = join(ROOT, "docs", "nexora", "LIVE_PROGRESS.json");
const RUNTIME_DIR = join(ROOT, ".nexora-monitor");
const LOG_PATH = join(RUNTIME_DIR, "opencode-live.log");
const SESSION_PATH = join(RUNTIME_DIR, "session.json");
const REPO = "Clopezgg/Gesti-n-de-Construcci-n-Residencial";
const BRANCH = "nexora-continuidad-total";
const PR_NUMBER = 12;
const TOTAL = 166;
const PORT = Number(process.env.NEXORA_MONITOR_PORT || 8765);
const FINAL_STATES = new Set([
  "IMPLEMENTADO Y VALIDADO",
  "OBSOLETO JUSTIFICADO",
  "NO APLICA JUSTIFICADO",
]);
const FAILED_CONCLUSIONS = new Set([
  "failure",
  "cancelled",
  "timed_out",
  "action_required",
  "startup_failure",
  "stale",
]);

let actionsCache = { at: 0, head: "", runs: [], error: null };

function nowIso() {
  return new Date().toISOString();
}

function git(args, fallback = "") {
  try {
    return execFileSync("git", args, {
      cwd: ROOT,
      encoding: "utf8",
      windowsHide: true,
      stdio: ["ignore", "pipe", "pipe"],
      timeout: 20000,
    }).trim();
  } catch (error) {
    return fallback || String(error?.stderr || error?.message || error).trim();
  }
}

function commandVersion(command, args = ["--version"]) {
  try {
    return execFileSync(command, args, {
      cwd: ROOT,
      encoding: "utf8",
      windowsHide: true,
      stdio: ["ignore", "pipe", "pipe"],
      timeout: 10000,
    }).trim().split(/\r?\n/)[0];
  } catch {
    return null;
  }
}

function readText(path, fallback = "") {
  try {
    return readFileSync(path, "utf8");
  } catch {
    return fallback;
  }
}

function readJson(path, fallback) {
  try {
    return JSON.parse(readFileSync(path, "utf8"));
  } catch {
    return fallback;
  }
}

function parseMatrix() {
  const rows = [];
  for (const raw of readText(MATRIX_PATH).split(/\r?\n/)) {
    const line = raw.trim();
    if (!line.startsWith("| `NXR-")) continue;
    const columns = line.slice(1, -1).split("|").map((value) => value.trim());
    if (columns.length < 4) continue;
    const id = columns[0].replaceAll("`", "");
    const title = columns[1];
    const state = columns[2].toUpperCase();
    const owner = columns[3].toUpperCase();
    const match = owner.match(/BLOQUE\s+(\d+)/);
    const block = match ? Number(match[1]) : null;
    rows.push({ id, title, state, owner, block, resolved: FINAL_STATES.has(state) });
  }

  const resolved = rows.filter((row) => row.resolved).length;
  const blocks = Array.from({ length: 21 }, (_, number) => {
    const owned = rows.filter((row) => row.block === number);
    const done = owned.filter((row) => row.resolved).length;
    let status = "unknown";
    if (owned.length && done === owned.length) status = "passed";
    else if (owned.length && done === 0) status = "pending";
    else if (owned.length) status = "partial";
    return {
      number,
      total: owned.length,
      resolved: done,
      status,
      unresolved: owned.filter((row) => !row.resolved).map((row) => `${row.id}: ${row.state}`),
    };
  });

  return {
    rows,
    rowsFound: rows.length,
    totalExpected: TOTAL,
    resolved,
    pending: Math.max(0, TOTAL - resolved),
    percent: TOTAL ? Number(((resolved / TOTAL) * 100).toFixed(1)) : 0,
    blocks,
  };
}

function readConsole() {
  const text = readText(LOG_PATH);
  const all = text.split(/\r?\n/).filter(Boolean);
  const lines = all.slice(-120);
  const classified = lines.map((line) => {
    const lowered = line.toLowerCase();
    let level = "info";
    if (/failed|failure|error|traceback|exception|not found|denied/.test(lowered)) level = "failed";
    else if (/passed|success|\bok\b|completed successfully|green/.test(lowered)) level = "passed";
    else if (/warning|warn|deprecated|skipped/.test(lowered)) level = "warning";
    else if (/running|starting|installing|initializing|executing|checking|loading/.test(lowered)) level = "running";
    return { line, level };
  });
  const latestFailure = [...classified].reverse().find((item) => item.level === "failed") || null;
  let updatedAt = null;
  try {
    updatedAt = statSync(LOG_PATH).mtime.toISOString();
  } catch {}
  return { lines: classified, totalLines: all.length, latestFailure, updatedAt };
}

function normalizeTest(item) {
  const status = String(item?.status || "unknown").toLowerCase();
  let level = "unknown";
  if (["passed", "success", "ok"].includes(status)) level = "passed";
  else if (["failed", "failure", "error"].includes(status)) level = "failed";
  else if (["running", "queued", "started"].includes(status)) level = "running";
  else if (["skipped", "warning"].includes(status)) level = "warning";
  return { ...item, level };
}

async function githubActions(head) {
  if (Date.now() - actionsCache.at < 15000 && actionsCache.head === head) return actionsCache;
  const url = `https://api.github.com/repos/${REPO}/actions/runs?branch=${BRANCH}&per_page=100`;
  try {
    const response = await fetch(url, {
      headers: {
        Accept: "application/vnd.github+json",
        "User-Agent": "NEXORA-local-monitor",
        "X-GitHub-Api-Version": "2022-11-28",
      },
    });
    if (!response.ok) throw new Error(`GitHub HTTP ${response.status}`);
    const payload = await response.json();
    const exact = (payload.workflow_runs || []).filter((run) => run.head_sha === head);
    const latest = new Map();
    for (const run of exact) {
      if (latest.has(run.name)) continue;
      let level = "unknown";
      if (["queued", "in_progress", "waiting", "requested", "pending"].includes(run.status)) level = "running";
      else if (run.conclusion === "success") level = "passed";
      else if (run.conclusion === "skipped") level = "warning";
      else if (FAILED_CONCLUSIONS.has(run.conclusion)) level = "failed";
      latest.set(run.name, {
        name: run.name,
        level,
        status: run.status,
        conclusion: run.conclusion,
        runNumber: run.run_number,
        url: run.html_url,
        createdAt: run.created_at,
        updatedAt: run.updated_at,
        headSha: run.head_sha,
      });
    }
    actionsCache = {
      at: Date.now(),
      head,
      runs: [...latest.values()].sort((a, b) => a.name.localeCompare(b.name)),
      error: exact.length ? null : "Todavía no hay ejecuciones de GitHub Actions para el HEAD local exacto.",
    };
  } catch (error) {
    actionsCache = { at: Date.now(), head, runs: [], error: String(error?.message || error) };
  }
  return actionsCache;
}

async function buildStatus() {
  const matrix = parseMatrix();
  const live = readJson(LIVE_PATH, {
    agent_status: "unknown",
    phase: "Sin reporte del agente",
    current_block: null,
    task: "Esperando actividad de OpenCode",
    detail: "La consola se captura automáticamente aunque LIVE_PROGRESS.json no se actualice.",
    tests: [],
    events: [],
    block_overrides: {},
    blocking_issue: null,
  });
  const session = readJson(SESSION_PATH, { status: "idle", started_at: null, finished_at: null, exit_code: null });
  const head = git(["rev-parse", "HEAD"], "HEAD no disponible");
  const branch = git(["branch", "--show-current"], "Rama no disponible");
  const lastCommit = git(["log", "-1", "--pretty=%H%n%s%n%an%n%aI"], "").split(/\r?\n/);
  const dirtyFiles = git(["status", "--short"], "").split(/\r?\n/).filter(Boolean);
  const consoleData = readConsole();
  const actions = await githubActions(head);
  const tests = (live.tests || []).map(normalizeTest).slice(-100);

  const overrides = live.block_overrides || {};
  for (const block of matrix.blocks) {
    const override = overrides[String(block.number)];
    if (["running", "failed"].includes(override)) block.status = override;
    if (Number(live.current_block) === block.number && live.agent_status === "working") block.status = "running";
  }

  const ciSummary = {
    passed: actions.runs.filter((run) => run.level === "passed").length,
    failed: actions.runs.filter((run) => run.level === "failed").length,
    running: actions.runs.filter((run) => run.level === "running").length,
    warning: actions.runs.filter((run) => run.level === "warning").length,
    total: actions.runs.length,
  };
  const systemLevel =
    branch !== BRANCH || matrix.rowsFound !== TOTAL || ciSummary.failed > 0 || live.blocking_issue
      ? "degraded"
      : session.status === "running" || ciSummary.running > 0
        ? "running"
        : "healthy";

  return {
    generatedAt: nowIso(),
    systemLevel,
    matrix,
    live,
    session,
    tests,
    console: consoleData,
    github: { ...actions, summary: ciSummary },
    git: {
      root: ROOT,
      branch,
      head,
      dirtyFiles: dirtyFiles.slice(0, 50),
      dirtyCount: dirtyFiles.length,
      commit: {
        sha: lastCommit[0] || head,
        subject: lastCommit[1] || "—",
        author: lastCommit[2] || "—",
        date: lastCommit[3] || "—",
      },
    },
    environment: {
      bun: commandVersion("bun"),
      opencode: commandVersion("opencode"),
      git: commandVersion("git", ["--version"]),
      monitor: "Bun local server",
    },
    safety: {
      targetBranch: BRANCH,
      pullRequest: PR_NUMBER,
      mergeAllowed: false,
      tagAllowed: false,
      deploymentAllowed: false,
      productionAllowed: false,
    },
  };
}

const HTML = String.raw`<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>NEXORA Execution Monitor</title>
<style>
:root{color-scheme:dark;--bg:#020a14;--panel:#071524;--panel2:#091a2d;--line:#123a62;--blue:#1397ff;--cyan:#34d7ff;--green:#28d17c;--red:#ff4d57;--amber:#ffb020;--gray:#64748b;--text:#e7f3ff;--muted:#8fa8bf}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 45% -20%,#0d2a48 0,#020a14 48%);color:var(--text);font:13px/1.45 Segoe UI,system-ui,sans-serif;min-height:100vh}main{max-width:1800px;margin:auto;padding:14px}
.top{display:grid;grid-template-columns:1.2fr 1.5fr .8fr;gap:14px;align-items:stretch}.brand,.status,.progressCard,.panel{background:linear-gradient(180deg,rgba(8,27,47,.97),rgba(4,16,29,.97));border:1px solid #174a78;border-radius:12px;box-shadow:0 0 25px rgba(0,110,255,.08),inset 0 0 18px rgba(0,110,255,.03)}
.brand,.status,.progressCard{padding:16px}.brand h1{margin:0;font-size:25px;letter-spacing:.3px}.brand p{margin:3px 0 0;color:var(--cyan);font-size:16px}.status{display:flex;justify-content:space-between;align-items:center}.status b{font-size:17px}.health{display:inline-flex;gap:8px;align-items:center}.orb{width:12px;height:12px;border-radius:50%;background:var(--gray);box-shadow:0 0 12px currentColor}.healthy{color:var(--green)}.degraded{color:var(--red)}.running{color:var(--amber)}
.progressTitle{display:flex;justify-content:space-between;margin-bottom:8px}.barShell{height:18px;border:1px solid #24649b;border-radius:999px;overflow:hidden;background:#03101e}.bar{height:100%;width:0;background:linear-gradient(90deg,#0668f7,#17b9ff);box-shadow:0 0 18px #0f8eff;transition:width .5s}.substats{display:flex;gap:22px;margin-top:8px;color:var(--muted)}
.roadmap{margin-top:12px;padding:13px 18px}.roadmap h3{margin:0 0 10px}.nodes{display:grid;grid-template-columns:repeat(21,1fr);gap:0;align-items:center}.node{position:relative;text-align:center;min-width:0}.node:after{content:"";position:absolute;top:28px;left:55%;right:-45%;height:2px;background:#35526d;z-index:0}.node:last-child:after{display:none}.circle{position:relative;z-index:1;margin:auto;width:27px;height:27px;border-radius:50%;display:grid;place-items:center;border:2px solid var(--gray);background:#0c1c2d;font-weight:800}.node small{display:block;margin-bottom:4px}.node.passed .circle{border-color:var(--green);background:#123b2a;color:#c6ffe2}.node.passed:after{background:var(--green)}.node.failed .circle{border-color:var(--red);background:#47191d}.node.partial .circle,.node.warning .circle{border-color:var(--amber);background:#3b2a0d}.node.running .circle{border-color:var(--blue);box-shadow:0 0 17px var(--blue);animation:pulse 1.2s infinite}.node.pending .circle,.node.unknown .circle{border-color:var(--gray)}
.legend{display:flex;justify-content:center;gap:18px;margin-top:10px;color:var(--muted)}.dot{width:10px;height:10px;border-radius:50%;display:inline-block;margin-right:7px;background:var(--gray);box-shadow:0 0 8px currentColor}.dot.passed{background:var(--green)}.dot.failed{background:var(--red)}.dot.running{background:var(--amber)}.dot.warning{background:var(--amber)}.dot.unknown{background:var(--gray)}
.grid{display:grid;grid-template-columns:1fr 1.25fr 1.1fr;gap:12px;margin-top:12px}.panel{padding:13px;min-height:190px;position:relative;overflow:hidden}.panel h3{margin:0 0 10px;font-size:15px;display:flex;justify-content:space-between}.live{font-size:10px;color:var(--cyan);border:1px solid #165a91;border-radius:5px;padding:2px 7px}.stack{display:grid;gap:12px}.log{font-family:Consolas,ui-monospace,monospace;background:#020b14;border:1px solid #153c5f;border-radius:8px;padding:10px;max-height:260px;overflow:auto;white-space:pre-wrap}.line{padding:1px 0;color:#a9bfd2}.line.passed{color:#44df8c}.line.failed{color:#ff686f}.line.warning{color:#ffc14f}.line.running{color:#46b9ff}.rows{display:grid;gap:6px;max-height:250px;overflow:auto}.row{border:1px solid #143c5f;border-radius:8px;padding:8px;background:#061322}.row.failed{border-color:#7c2430;background:#210b12}.row.passed{border-color:#17583a;background:#061a13}.row.running,.row.warning{border-color:#6c541a;background:#1e1706}.rowTop{display:flex;justify-content:space-between;gap:10px}.muted{color:var(--muted)}code{color:#78d6ff;font-family:Consolas,monospace;word-break:break-all}.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:7px}.kpi{border:1px solid #153c5f;border-radius:8px;padding:8px;text-align:center;background:#05121f}.kpi b{font-size:21px;display:block}.diagnostic{border-color:#7c2430}.diagnostic h3{color:#ff7a82}.footer{margin:12px 0 2px;padding:9px 14px;border:1px solid #153c5f;border-radius:9px;display:flex;justify-content:space-between;gap:12px;color:var(--muted);background:#04101d}.safety{display:grid;grid-template-columns:repeat(2,1fr);gap:7px}.safeItem{padding:7px;border-radius:7px;border:1px solid #29445d}.blocked{color:var(--red)}
@keyframes pulse{50%{transform:scale(1.09);box-shadow:0 0 25px var(--blue)}}
@media(max-width:1200px){.top,.grid{grid-template-columns:1fr}.nodes{grid-template-columns:repeat(7,1fr);gap:12px}.node:after{display:none}}@media(max-width:650px){main{padding:8px}.nodes{grid-template-columns:repeat(4,1fr)}.kpis{grid-template-columns:repeat(2,1fr)}.footer{flex-direction:column}}
</style>
</head>
<body><main>
<div class="top">
  <section class="brand"><h1>〽 NEXORA Execution Monitor</h1><p>OpenCode Live System Trace</p></section>
  <section class="progressCard"><div class="progressTitle"><b id="progressTitle">Avance certificado</b><b id="progressPct">0%</b></div><div class="barShell"><div id="bar" class="bar"></div></div><div class="substats"><span id="resolvedText">0 resueltos</span><span id="pendingText">166 pendientes</span><span id="rowsText">0 filas</span></div></section>
  <section class="status"><div><div class="muted">System Status</div><b id="systemText">CARGANDO</b><div id="clock" class="muted">—</div></div><span id="systemOrb" class="orb"></span></section>
</div>
<section class="panel roadmap"><h3>Execution Roadmap · Bloques 0–20</h3><div id="nodes" class="nodes"></div><div class="legend"><span><i class="dot passed"></i>Completado</span><span><i class="dot running"></i>Activo</span><span><i class="dot failed"></i>Falló</span><span><i class="dot warning"></i>Parcial</span><span><i class="dot unknown"></i>Pendiente</span></div></section>
<div class="grid">
  <div class="stack">
    <section class="panel"><h3><span>1 · Process Launch / Environment</span><span class="live">LIVE</span></h3><div id="environment" class="rows"></div></section>
    <section class="panel"><h3><span>4 · GitHub Actions · HEAD exacto</span><span class="live">LIVE</span></h3><div id="actions" class="rows"></div></section>
    <section class="panel"><h3><span>7 · Branch / PR / Commit</span><span class="live">LIVE</span></h3><div id="gitInfo" class="rows"></div></section>
  </div>
  <div class="stack">
    <section class="panel"><h3><span>2 · OpenCode Core Log</span><span class="live">RUNNING</span></h3><div id="coreLog" class="log"></div></section>
    <section class="panel"><h3><span>6 · Test Results Summary</span><span class="live">LIVE</span></h3><div id="testKpis" class="kpis"></div><div id="tests" class="rows" style="margin-top:9px"></div></section>
  </div>
  <div class="stack">
    <section class="panel"><h3><span>3 · Live Console Log</span><span class="live">LIVE</span></h3><div id="consoleLog" class="log"></div></section>
    <section class="panel diagnostic"><h3><span>5 · Diagnostic Branch Issue</span><span class="live">AUTO</span></h3><div id="diagnostic"></div></section>
    <section class="panel"><h3><span>8 · Deployment & Validation</span><span class="live">PROTECTED</span></h3><div id="validation" class="rows"></div></section>
  </div>
</div>
<div class="footer"><span id="footerLeft">Monitor</span><span>Auto-refresh: ON · 3s</span><span>Data: Git local + OpenCode runtime + GitHub Actions</span></div>
</main>
<script>
const esc=(value)=>String(value??"").replace(/[&<>"']/g,(char)=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[char]));
const dot=(level)=>`<i class="dot ${esc(level)}"></i>`;
function row(title,value,level="unknown",extra=""){return `<div class="row ${esc(level)}"><div class="rowTop"><span>${dot(level)}<b>${esc(title)}</b></span><span>${esc(value??"")}</span></div>${extra?`<div class="muted">${esc(extra)}</div>`:""}</div>`}
function render(data){
  const m=data.matrix,g=data.git,gh=data.github,live=data.live||{},session=data.session||{};
  document.getElementById("progressTitle").textContent=`Overall certified progress: ${m.resolved} / ${m.totalExpected}`;
  document.getElementById("progressPct").textContent=`${m.percent}%`;
  document.getElementById("bar").style.width=`${Math.min(100,m.percent)}%`;
  document.getElementById("resolvedText").textContent=`${m.resolved} finalizados`;
  document.getElementById("pendingText").textContent=`${m.pending} pendientes`;
  document.getElementById("rowsText").textContent=`${m.rowsFound}/${m.totalExpected} filas detectadas`;
  const orb=document.getElementById("systemOrb"),system=document.getElementById("systemText");
  orb.className=`orb ${data.systemLevel}`;system.className=data.systemLevel;system.textContent=data.systemLevel.toUpperCase();
  document.getElementById("clock").textContent=new Date(data.generatedAt).toLocaleString();
  document.getElementById("nodes").innerHTML=m.blocks.map((b)=>`<div class="node ${esc(b.status)}" title="${esc((b.unresolved||[]).join("\n"))}"><small>B${b.number}</small><div class="circle">${b.status==="passed"?"✓":b.status==="failed"?"×":b.status==="running"?"●":b.status==="partial"?"!":""}</div><small>${b.resolved}/${b.total}</small></div>`).join("");
  const env=[
    ["Repositorio encontrado",data.environment.git?"OK":"FALTA",data.environment.git?"passed":"failed"],
    ["Bun runtime",data.environment.bun||"No disponible",data.environment.bun?"passed":"failed"],
    ["OpenCode",data.environment.opencode||"No disponible",data.environment.opencode?"passed":"failed"],
    ["Rama protegida",g.branch,g.branch===data.safety.targetBranch?"passed":"failed"],
    ["Matriz oficial",`${m.rowsFound}/${m.totalExpected}`,m.rowsFound===m.totalExpected?"passed":"failed"],
    ["Sesión OpenCode",session.status||"idle",session.status==="running"?"running":"unknown"],
  ];document.getElementById("environment").innerHTML=env.map((x)=>row(...x)).join("");
  document.getElementById("actions").innerHTML=(gh.runs||[]).length?(gh.runs||[]).map((w)=>row(w.name,w.conclusion||w.status,w.level,`Run ${w.runNumber} · ${(w.headSha||"").slice(0,12)}`)).join(""):row("GitHub Actions",gh.error||"Sin ejecuciones para este HEAD","warning");
  document.getElementById("gitInfo").innerHTML=[
    row("Branch",g.branch,g.branch===data.safety.targetBranch?"passed":"failed"),
    row("Pull Request",`#${data.safety.pullRequest} · abierto`,"running"),
    row("Commit SHA",g.head,"unknown"),
    row("Último commit",g.commit.subject,"unknown",`${g.commit.author} · ${g.commit.date}`),
    row("Cambios sin commit",String(g.dirtyCount),g.dirtyCount?"warning":"passed",(g.dirtyFiles||[]).join(" · ")),
  ].join("");
  const consoleLines=data.console.lines||[];
  const rendered=consoleLines.map((item)=>`<div class="line ${esc(item.level)}">${esc(item.line)}</div>`).join("")||'<div class="line">Esperando salida de OpenCode…</div>';
  document.getElementById("consoleLog").innerHTML=rendered;document.getElementById("coreLog").innerHTML=rendered;
  const testCounts={passed:0,failed:0,running:0,warning:0,unknown:0};for(const t of data.tests||[])testCounts[t.level]=(testCounts[t.level]||0)+1;
  document.getElementById("testKpis").innerHTML=[['Passed',testCounts.passed,'passed'],['Failed',testCounts.failed,'failed'],['Running',testCounts.running,'running'],['CI exacto',gh.summary.total,'unknown']].map(([a,b,c])=>`<div class="kpi"><span class="muted">${a}</span><b class="${c}">${b}</b></div>`).join("");
  document.getElementById("tests").innerHTML=(data.tests||[]).length?[...(data.tests||[])].reverse().slice(0,25).map((t)=>row(t.name||t.command||"Prueba",t.status,t.level,t.detail||t.command||"")).join(""):row("Pruebas estructuradas","Aún no reportadas","warning","La consola real sí se está capturando automáticamente.");
  const fail=data.console.latestFailure||((gh.runs||[]).find((w)=>w.level==="failed")?{line:`Workflow fallido: ${(gh.runs||[]).find((w)=>w.level==="failed").name}`} : null);
  document.getElementById("diagnostic").innerHTML=fail?`<div class="row failed"><b>FALLO DETECTADO</b><div class="log" style="margin-top:8px">${esc(fail.line)}</div><div class="muted">OpenCode debe corregir la causa raíz; no se permite ocultar ni omitir el control.</div></div>`:`<div class="row passed">${dot("passed")}Sin fallo activo detectado en la consola actual.</div>`;
  const allGreen=gh.summary.total>0&&gh.summary.failed===0&&gh.summary.running===0;
  document.getElementById("validation").innerHTML=[
    row("Matriz 166/166",m.resolved===m.totalExpected?"CERTIFICADA":`${m.pending} pendientes`,m.resolved===m.totalExpected?"passed":"warning"),
    row("GitHub Actions del mismo SHA",allGreen?"TODOS VERDES":`${gh.summary.failed} fallidos · ${gh.summary.running} ejecutándose`,allGreen?"passed":gh.summary.failed?"failed":"running"),
    row("Merge", "BLOQUEADO", "failed", "Requiere autorización expresa"),
    row("Tags / Releases", "BLOQUEADO", "failed"),
    row("Producción / AWS / Coolify / DNS", "BLOQUEADO", "failed"),
  ].join("");
  document.getElementById("footerLeft").textContent=`Bun ${data.environment.bun||"—"} · OpenCode ${data.environment.opencode||"—"} · Log ${data.console.totalLines} líneas`;
  for(const id of ["consoleLog","coreLog"]){const el=document.getElementById(id);el.scrollTop=el.scrollHeight}
}
async function tick(){try{const response=await fetch('/api/status',{cache:'no-store'});render(await response.json())}catch(error){document.getElementById('systemText').textContent='DESCONECTADO'}}tick();setInterval(tick,3000);
</script></body></html>`;

Bun.serve({
  hostname: "127.0.0.1",
  port: PORT,
  async fetch(request) {
    const url = new URL(request.url);
    if (url.pathname === "/api/status") {
      return Response.json(await buildStatus(), { headers: { "Cache-Control": "no-store" } });
    }
    if (url.pathname === "/" || url.pathname === "/index.html") {
      return new Response(HTML, { headers: { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store" } });
    }
    return new Response("Not found", { status: 404 });
  },
});

console.log("NEXORA Execution Monitor activo");
console.log(`Repositorio: ${ROOT}`);
console.log(`Panel: http://127.0.0.1:${PORT}`);
console.log("Mantén esta ventana abierta mientras OpenCode trabaja.");
