import { spawnSync } from "node:child_process";
import { readFile } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { buildAuditModel } from "./audit_model.js";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..", "..");
const PORT = Number(process.env.NEXORA_MONITOR_PORT || 8765);
const REPO = "Clopezgg/Gesti-n-de-Construcci-n-Residencial";
const BRANCH = "nexora-continuidad-total";
const PR_NUMBER = 12;

const PATHS = {
	matrix: join(ROOT, "docs", "nexora", "MATRIZ_REQUISITOS.md"),
	auditResults: join(ROOT, "docs", "nexora", "AUDIT_RESULTS.json"),
	defects: join(ROOT, "docs", "nexora", "DEFECTS.json"),
	live: join(ROOT, "docs", "nexora", "LIVE_PROGRESS.json"),
	review: join(ROOT, "docs", "nexora", "FINAL_REVIEW_PACKAGE.md"),
	html: join(HERE, "dashboard.html"),
	runtime: join(ROOT, ".nexora-monitor"),
};
PATHS.log = join(PATHS.runtime, "opencode-live.log");
PATHS.session = join(PATHS.runtime, "session.json");

const FAILED_CONCLUSIONS = new Set([
	"failure",
	"cancelled",
	"timed_out",
	"action_required",
	"startup_failure",
	"stale",
]);

function nowIso() {
	return new Date().toISOString();
}

function command(program, args = [], timeout = 5000) {
	try {
		const result = spawnSync(program, args, {
			cwd: ROOT,
			encoding: "utf8",
			windowsHide: true,
			timeout,
			env: process.env,
		});
		const stdout = String(result.stdout || "").trim();
		const stderr = String(result.stderr || "").trim();
		const error = result.error ? String(result.error.message || result.error) : "";
		return {
			ok: result.status === 0 && !result.error,
			code: result.status ?? -1,
			text: stdout || stderr || error,
		};
	} catch (error) {
		return { ok: false, code: -1, text: String(error) };
	}
}

async function readText(path, fallback = "") {
	try {
		return await readFile(path, "utf8");
	} catch {
		return fallback;
	}
}

async function readJson(path, fallback) {
	try {
		return JSON.parse(await readText(path));
	} catch {
		return fallback;
	}
}

async function exists(path) {
	try {
		await readFile(path);
		return true;
	} catch {
		return false;
	}
}

function classifyLine(line) {
	const lower = String(line || "").toLowerCase();
	if (/error|failed|failure|traceback|exception|fatal|no cumple/.test(lower)) return "technical_error";
	if (/mismatch|objetivo|no coincide/.test(lower)) return "objective_mismatch";
	if (/blocked|bloquead/.test(lower)) return "blocked";
	if (/decision|required|requiere decisión/.test(lower)) return "decision_required";
	if (/passed|success|ok\b|completed|certified|green/.test(lower)) return "certified";
	if (/running|executing|starting|working|in progress|corrigiendo/.test(lower)) return "running";
	return "pending";
}

async function consoleState() {
	const text = await readText(PATHS.log);
	const all = text.split(/\r?\n/).filter(Boolean);
	const recent = all.slice(-260).map((line) => ({ line, level: classifyLine(line) }));
	const latestFailure =
		[...recent]
			.reverse()
			.find((item) => ["technical_error", "objective_mismatch"].includes(item.level)) || null;
	return { totalLines: all.length, lines: recent, latestFailure };
}

function levelForRun(status, conclusion) {
	if (["queued", "in_progress", "waiting", "requested", "pending"].includes(status)) return "running";
	if (conclusion === "success") return "certified";
	if (conclusion === "skipped") return "pending";
	if (FAILED_CONCLUSIONS.has(conclusion)) return "technical_error";
	return "pending";
}

const environment = {
	git: command("git", ["--version"]).text,
	bun: command("bun", ["--version"]).text,
	opencode: command("opencode", ["--version"], 8000).text,
};

let githubCache = {
	at: 0,
	head: "",
	runs: [],
	error: "Sincronizando GitHub Actions...",
	loading: false,
};

async function refreshGithub(head) {
	const current = Date.now();
	if (!head || githubCache.loading) return;
	if (githubCache.head === head && current - githubCache.at < 20000) return;

	githubCache = { ...githubCache, head, loading: true };
	const controller = new AbortController();
	const timer = setTimeout(() => controller.abort(), 8000);
	const endpoint = `https://api.github.com/repos/${REPO}/actions/runs?head_sha=${encodeURIComponent(
		head
	)}&per_page=100`;

	try {
		const response = await fetch(endpoint, {
			signal: controller.signal,
			headers: {
				Accept: "application/vnd.github+json",
				"User-Agent": "NEXORA-layered-audit-monitor",
				"X-GitHub-Api-Version": "2022-11-28",
			},
		});
		if (!response.ok) throw new Error(`GitHub HTTP ${response.status}`);
		const payload = await response.json();
		const latest = new Map();
		for (const run of payload.workflow_runs || []) {
			if (run.head_sha !== head || latest.has(run.name)) continue;
			latest.set(run.name, {
				name: run.name || "Workflow sin nombre",
				status: run.status || "unknown",
				conclusion: run.conclusion,
				level: levelForRun(run.status, run.conclusion),
				runNumber: run.run_number,
				runId: run.id,
				headSha: run.head_sha || "",
				htmlUrl: run.html_url || null,
				updatedAt: run.updated_at || null,
			});
		}
		githubCache = {
			at: Date.now(),
			head,
			runs: [...latest.values()].sort((a, b) => a.name.localeCompare(b.name)),
			error: null,
			loading: false,
		};
	} catch (error) {
		githubCache = {
			at: Date.now(),
			head,
			runs: githubCache.head === head ? githubCache.runs : [],
			error:
				error?.name === "AbortError"
					? "GitHub tardó demasiado; se reintentará automáticamente."
					: String(error),
			loading: false,
		};
	} finally {
		clearTimeout(timer);
	}
}

function summarizeRuns(runs) {
	return {
		total: runs.length,
		certified: runs.filter((run) => run.level === "certified").length,
		technical_error: runs.filter((run) => run.level === "technical_error").length,
		running: runs.filter((run) => run.level === "running").length,
		pending: runs.filter((run) => run.level === "pending").length,
	};
}

let statusCache = {
	generatedAt: nowIso(),
	systemLevel: "pending",
	audit: null,
	live: { agent_status: "idle", tests: [], events: [] },
	session: { status: "starting" },
	console: { totalLines: 0, lines: [], latestFailure: null },
	git: { root: ROOT, branch: "", head: "", dirtyCount: 0, dirtyFiles: [], commit: {} },
	github: { runs: [], error: "Sincronizando GitHub Actions...", summary: summarizeRuns([]), exactHead: "" },
	environment,
	review: { packageExists: false, ready: false, instruction: null },
	safety: {
		targetBranch: BRANCH,
		pullRequest: PR_NUMBER,
		mergeAllowed: false,
		tagAllowed: false,
		deploymentAllowed: false,
	},
};

let refreshing = false;
async function refreshStatus() {
	if (refreshing) return;
	refreshing = true;
	try {
		const [matrixText, auditResults, defects, live, session, console] = await Promise.all([
			readText(PATHS.matrix),
			readJson(PATHS.auditResults, {
				schema_version: 1,
				status: "active",
				active_block: 0,
				requirements: {},
			}),
			readJson(PATHS.defects, { schema_version: 1, defects: [] }),
			readJson(PATHS.live, {
				agent_status: "idle",
				phase: "Sin datos",
				current_block: 0,
				task: "Esperando auditoría",
				detail: "",
				tests: [],
				events: [],
				blocking_issue: null,
			}),
			readJson(PATHS.session, { status: "idle" }),
			consoleState(),
		]);

		const head = command("git", ["rev-parse", "HEAD"]).text;
		const branch = command("git", ["branch", "--show-current"]).text;
		const statusText = command("git", ["status", "--short"]).text;
		const commitText = command("git", ["log", "-1", "--pretty=%s%x1f%an%x1f%cI"]).text;
		const [subject = "", author = "", date = ""] = commitText.split("\x1f");
		const dirtyFiles = statusText ? statusText.split(/\r?\n/).filter(Boolean) : [];

		const audit = buildAuditModel(matrixText, auditResults, defects);
		void refreshGithub(head);
		const github =
			githubCache.head === head
				? githubCache
				: { runs: [], error: "Sincronizando GitHub Actions...", loading: true };
		const githubSummary = summarizeRuns(github.runs || []);
		const allWorkflowsGreen =
			githubSummary.total > 0 &&
			githubSummary.technical_error === 0 &&
			githubSummary.running === 0 &&
			githubSummary.pending === 0;
		const packageExists = await exists(PATHS.review);
		const reviewReady =
			audit.gateReady &&
			allWorkflowsGreen &&
			packageExists &&
			live.agent_status === "awaiting_review" &&
			branch === BRANCH &&
			dirtyFiles.length === 0;

		let systemLevel = "pending";
		if (
			branch !== BRANCH ||
			githubSummary.technical_error > 0 ||
			audit.metrics.technical_error > 0 ||
			session.status === "failed"
		) {
			systemLevel = "technical_error";
		} else if (audit.metrics.objective_mismatch > 0) {
			systemLevel = "objective_mismatch";
		} else if (audit.metrics.blocked > 0) {
			systemLevel = "blocked";
		} else if (
			session.status === "running" ||
			githubSummary.running > 0 ||
			live.agent_status === "working" ||
			audit.metrics.running > 0
		) {
			systemLevel = "running";
		} else if (reviewReady) {
			systemLevel = "certified";
		}

		statusCache = {
			generatedAt: nowIso(),
			systemLevel,
			audit,
			matrix: {
				rowsFound: audit.matrix.rowsFound,
				totalExpected: 166,
				resolved: audit.matrix.finalClaims,
				pending: Math.max(0, 166 - audit.matrix.finalClaims),
				percent: audit.matrix.claimPercent,
				warning: audit.matrix.warning,
			},
			live,
			session,
			tests: Array.isArray(live.tests) ? live.tests : [],
			console,
			git: {
				root: ROOT,
				branch,
				head,
				dirtyCount: dirtyFiles.length,
				dirtyFiles,
				commit: { subject, author, date },
			},
			github: {
				runs: github.runs || [],
				error: github.loading ? "Sincronizando GitHub Actions..." : github.error,
				summary: githubSummary,
				exactHead: head,
			},
			environment,
			review: {
				packageExists,
				ready: reviewReady,
				instruction: reviewReady
					? "Regrese a ChatGPT y escriba: Revisa el paquete final de NEXORA y el HEAD actual del PR #12."
					: null,
			},
			safety: {
				targetBranch: BRANCH,
				pullRequest: PR_NUMBER,
				mergeAllowed: false,
				tagAllowed: false,
				deploymentAllowed: false,
			},
		};
	} catch (error) {
		statusCache = {
			...statusCache,
			generatedAt: nowIso(),
			systemLevel: "technical_error",
			monitorError: String(error),
		};
	} finally {
		refreshing = false;
	}
}

const html = await readText(PATHS.html, "<h1>No se encontró dashboard.html</h1>");
await refreshStatus();
setInterval(() => void refreshStatus(), 1500);

Bun.serve({
	hostname: "127.0.0.1",
	port: PORT,
	idleTimeout: 60,
	fetch(request) {
		const url = new URL(request.url);
		if (url.pathname === "/health") return new Response("ok", { status: 200 });
		if (url.pathname === "/api/status") {
			return Response.json(statusCache, { headers: { "Cache-Control": "no-store" } });
		}
		if (url.pathname === "/" || url.pathname === "/index.html") {
			return new Response(html, {
				headers: { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store" },
			});
		}
		return new Response("Not found", { status: 404 });
	},
});

console.log("NEXORA Layered Audit Monitor activo");
console.log(`Repositorio: ${ROOT}`);
console.log(`Panel: http://127.0.0.1:${PORT}`);
console.log(
	"La matriz ya no certifica por sí sola: manda AUDIT_RESULTS.json + DEFECTS.json + CI del mismo SHA."
);
