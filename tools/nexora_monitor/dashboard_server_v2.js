import { spawnSync } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..", "..");
const PORT = Number(process.env.NEXORA_MONITOR_PORT || 8765);
const REPO = "Clopezgg/Gesti-n-de-Construcci-n-Residencial";
const BRANCH = "nexora-continuidad-total";
const PR_NUMBER = 12;
const TOTAL_REQUIREMENTS = 166;
const MATRIX_PATH = join(ROOT, "docs", "nexora", "MATRIZ_REQUISITOS.md");
const LIVE_PATH = join(ROOT, "docs", "nexora", "LIVE_PROGRESS.json");
const REVIEW_PATH = join(ROOT, "docs", "nexora", "FINAL_REVIEW_PACKAGE.md");
const HTML_PATH = join(HERE, "dashboard.html");
const RUNTIME_DIR = join(ROOT, ".nexora-monitor");
const LOG_PATH = join(RUNTIME_DIR, "opencode-live.log");
const SESSION_PATH = join(RUNTIME_DIR, "session.json");

const FINAL_STATES = new Set(["IMPLEMENTADO Y VALIDADO", "OBSOLETO JUSTIFICADO", "NO APLICA JUSTIFICADO"]);
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

function command(program, args = [], timeout = 4000) {
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
		return await Bun.file(path).text();
	} catch {
		return fallback;
	}
}

async function readJson(path, fallback) {
	try {
		return JSON.parse(await Bun.file(path).text());
	} catch {
		return fallback;
	}
}

async function exists(path) {
	try {
		return await Bun.file(path).exists();
	} catch {
		return false;
	}
}

async function parseMatrix() {
	const text = await readText(MATRIX_PATH);
	const requirements = [];

	for (const raw of text.split(/\r?\n/)) {
		const line = raw.trim();
		if (!/^\|\s*`NXR-[^`]+`\s*\|/.test(line)) continue;
		const columns = line
			.slice(1, -1)
			.split("|")
			.map((item) => item.trim());
		if (columns.length < 4) continue;

		const id = columns[0].replaceAll("`", "");
		const title = columns[1];
		const state = columns[2].toUpperCase();
		const owner = columns[3].toUpperCase();
		const match = owner.match(/BLOQUE\s+(\d+)/);
		const block = match ? Number(match[1]) : null;
		requirements.push({
			id,
			title,
			state,
			owner,
			block,
			resolved: FINAL_STATES.has(state),
		});
	}

	const resolved = requirements.filter((item) => item.resolved).length;
	const blocks = [];
	for (let number = 0; number <= 20; number += 1) {
		const owned = requirements.filter((item) => item.block === number);
		const completed = owned.filter((item) => item.resolved).length;
		let status = "unknown";
		if (owned.length && completed === owned.length) status = "passed";
		else if (owned.length && completed > 0) status = "partial";
		else if (owned.length) status = "pending";

		blocks.push({
			number,
			total: owned.length,
			resolved: completed,
			status,
			unresolved: owned.filter((item) => !item.resolved).map((item) => `${item.id}: ${item.state}`),
		});
	}

	return {
		rowsFound: requirements.length,
		totalExpected: TOTAL_REQUIREMENTS,
		resolved,
		pending: Math.max(0, TOTAL_REQUIREMENTS - resolved),
		percent: Number(((resolved / TOTAL_REQUIREMENTS) * 100).toFixed(1)),
		requirements,
		blocks,
	};
}

function classifyLine(line) {
	const lower = line.toLowerCase();
	if (/error|failed|failure|traceback|exception|fatal/.test(lower)) return "failed";
	if (/warning|warn|pending|skipped/.test(lower)) return "warning";
	if (/passed|success|ok\b|completed|green/.test(lower)) return "passed";
	if (/running|executing|starting|working|in progress/.test(lower)) return "running";
	return "unknown";
}

async function consoleState() {
	const text = await readText(LOG_PATH);
	const all = text.split(/\r?\n/).filter(Boolean);
	const recent = all.slice(-220).map((line) => ({ line, level: classifyLine(line) }));
	const latestFailure = [...recent].reverse().find((item) => item.level === "failed") || null;
	return { totalLines: all.length, lines: recent, latestFailure };
}

function normalizeTests(items) {
	return (Array.isArray(items) ? items : []).map((item) => {
		const status = String(item.status || "unknown").toLowerCase();
		const level =
			{
				passed: "passed",
				success: "passed",
				failed: "failed",
				failure: "failed",
				running: "running",
				queued: "running",
				skipped: "skipped",
				warning: "warning",
			}[status] || "unknown";
		return { ...item, level };
	});
}

function levelForRun(status, conclusion) {
	if (["queued", "in_progress", "waiting", "requested", "pending"].includes(status)) return "running";
	if (conclusion === "success") return "passed";
	if (conclusion === "skipped") return "skipped";
	if (FAILED_CONCLUSIONS.has(conclusion)) return "failed";
	return "unknown";
}

const environment = {
	git: command("git", ["--version"]).text,
	bun: command("bun", ["--version"]).text,
	opencode: command("opencode", ["--version"], 7000).text,
};

let githubCache = {
	at: 0,
	head: "",
	runs: [],
	error: "Sincronizando GitHub Actions...",
	loading: false,
};

let statusCache = {
	generatedAt: nowIso(),
	systemLevel: "warning",
	matrix: {
		rowsFound: 0,
		totalExpected: TOTAL_REQUIREMENTS,
		resolved: 0,
		pending: TOTAL_REQUIREMENTS,
		percent: 0,
		requirements: [],
		blocks: Array.from({ length: 21 }, (_, number) => ({
			number,
			total: 0,
			resolved: 0,
			status: "unknown",
			unresolved: [],
		})),
	},
	live: { agent_status: "idle", tests: [], events: [] },
	session: { status: "starting" },
	tests: [],
	console: { totalLines: 0, lines: [], latestFailure: null },
	git: { root: ROOT, branch: "", head: "", dirtyCount: 0, dirtyFiles: [], commit: {} },
	github: {
		runs: [],
		error: "Sincronizando GitHub Actions...",
		summary: { total: 0, passed: 0, failed: 0, running: 0, skipped: 0 },
		exactHead: "",
	},
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

async function refreshGithub(head) {
	const current = Date.now();
	if (!head || githubCache.loading) return;
	if (githubCache.head === head && current - githubCache.at < 20000) return;

	githubCache = { ...githubCache, head, loading: true };
	const controller = new AbortController();
	const timer = setTimeout(() => controller.abort(), 7000);
	const endpoint = `https://api.github.com/repos/${REPO}/actions/runs?head_sha=${encodeURIComponent(
		head
	)}&per_page=100`;

	try {
		const response = await fetch(endpoint, {
			signal: controller.signal,
			headers: {
				Accept: "application/vnd.github+json",
				"User-Agent": "NEXORA-local-execution-monitor",
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

let refreshing = false;
async function refreshStatus() {
	if (refreshing) return;
	refreshing = true;

	try {
		const [matrix, live, session, console] = await Promise.all([
			parseMatrix(),
			readJson(LIVE_PATH, {
				agent_status: "idle",
				phase: "Sin datos",
				current_block: null,
				task: "Esperando inicio",
				detail: "",
				tests: [],
				events: [],
				block_overrides: {},
				blocking_issue: null,
			}),
			readJson(SESSION_PATH, { status: "idle" }),
			consoleState(),
		]);

		const head = command("git", ["rev-parse", "HEAD"]).text;
		const branch = command("git", ["branch", "--show-current"]).text;
		const statusText = command("git", ["status", "--short"]).text;
		const commitText = command("git", ["log", "-1", "--pretty=%s%x1f%an%x1f%cI"]).text;
		const [subject = "", author = "", date = ""] = commitText.split("\x1f");
		const dirtyFiles = statusText ? statusText.split(/\r?\n/).filter(Boolean) : [];

		void refreshGithub(head);
		const github =
			githubCache.head === head
				? githubCache
				: { runs: [], error: "Sincronizando GitHub Actions...", loading: true };

		const overrides = live.block_overrides || {};
		for (const block of matrix.blocks) {
			const override = overrides[String(block.number)];
			if (["running", "failed", "partial", "pending", "unknown"].includes(override)) {
				block.status = override;
			}
			if (Number(live.current_block) === block.number && live.agent_status === "working") {
				block.status = "running";
			}
		}

		const tests = normalizeTests(live.tests);
		const summary = {
			total: github.runs.length,
			passed: github.runs.filter((run) => run.level === "passed").length,
			failed: github.runs.filter((run) => run.level === "failed").length,
			running: github.runs.filter((run) => run.level === "running").length,
			skipped: github.runs.filter((run) => run.level === "skipped").length,
		};

		const allGreen = summary.total > 0 && summary.failed === 0 && summary.running === 0;
		const reviewReady =
			matrix.resolved === TOTAL_REQUIREMENTS && allGreen && live.agent_status === "awaiting_review";

		let systemLevel = "warning";
		if (
			branch !== BRANCH ||
			matrix.rowsFound !== TOTAL_REQUIREMENTS ||
			summary.failed > 0 ||
			session.status === "failed"
		) {
			systemLevel = "failed";
		} else if (session.status === "running" || summary.running > 0 || live.agent_status === "working") {
			systemLevel = "running";
		} else if (reviewReady) {
			systemLevel = "passed";
		}

		statusCache = {
			generatedAt: nowIso(),
			systemLevel,
			matrix,
			live,
			session,
			tests,
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
				runs: github.runs,
				error: github.loading ? "Sincronizando GitHub Actions..." : github.error,
				summary,
				exactHead: head,
			},
			environment,
			review: {
				packageExists: await exists(REVIEW_PATH),
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
			systemLevel: "failed",
			github: {
				...statusCache.github,
				error: `Error local del monitor: ${String(error)}`,
			},
		};
	} finally {
		refreshing = false;
	}
}

const html = await readText(HTML_PATH, "<h1>No se encontro dashboard.html</h1>");

Bun.serve({
	hostname: "127.0.0.1",
	port: PORT,
	idleTimeout: 60,
	fetch(request) {
		const url = new URL(request.url);
		if (url.pathname === "/health") return new Response("ok", { status: 200 });
		if (url.pathname === "/api/status") {
			return Response.json(statusCache, {
				headers: { "Cache-Control": "no-store" },
			});
		}
		if (url.pathname === "/" || url.pathname === "/index.html") {
			return new Response(html, {
				headers: {
					"Content-Type": "text/html; charset=utf-8",
					"Cache-Control": "no-store",
				},
			});
		}
		return new Response("Not found", { status: 404 });
	},
});

void refreshStatus();
setInterval(() => void refreshStatus(), 2000);

console.log("NEXORA Execution Monitor activo");
console.log(`Repositorio: ${ROOT}`);
console.log(`Panel: http://127.0.0.1:${PORT}`);
console.log("Estado local cada 2 s; GitHub Actions en segundo plano cada 20 s.");
console.log("Mantenga esta ventana abierta mientras OpenCode trabaja.");
