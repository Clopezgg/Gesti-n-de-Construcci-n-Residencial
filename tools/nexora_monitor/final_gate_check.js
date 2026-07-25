import { spawnSync } from "node:child_process";
import { readFile, mkdir, writeFile } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { validateAuditResults } from "./audit_model.js";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..", "..");
const REPO = "Clopezgg/Gesti-n-de-Construcci-n-Residencial";
const BRANCH = "nexora-continuidad-total";
const REQUIRED_WORKFLOWS = new Set([
	"NEXORA governance",
	"NEXORA app",
	"NEXORA financial invariants",
	"Linters",
	"Semantic Commits",
	"Documentation Required",
	"Read-only non-Python patch control",
	"Read-only static server control",
	"Patch",
]);
const paths = {
	matrix: join(ROOT, "docs", "nexora", "MATRIZ_REQUISITOS.md"),
	results: join(ROOT, "docs", "nexora", "AUDIT_RESULTS.json"),
	defects: join(ROOT, "docs", "nexora", "DEFECTS.json"),
	review: join(ROOT, "docs", "nexora", "FINAL_REVIEW_PACKAGE.md"),
	runtime: join(ROOT, ".nexora-monitor"),
};
paths.output = join(paths.runtime, "final-gate.json");

function command(program, args = []) {
	const result = spawnSync(program, args, { cwd: ROOT, encoding: "utf8", windowsHide: true });
	return { code: result.status ?? -1, text: String(result.stdout || result.stderr || "").trim() };
}
async function text(path) {
	return readFile(path, "utf8");
}
async function json(path) {
	return JSON.parse(await text(path));
}

const failures = [];
const head = command("git", ["rev-parse", "HEAD"]).text;
const branch = command("git", ["branch", "--show-current"]).text;
const dirty = command("git", ["status", "--porcelain"]).text;
if (!/^[0-9a-f]{40}$/i.test(head)) failures.push("HEAD local no es un SHA completo.");
if (branch !== BRANCH) failures.push(`Rama incorrecta: ${branch}`);
if (dirty) failures.push("El arbol Git no esta limpio.");

const [matrixText, results, defects, review] = await Promise.all([
	text(paths.matrix),
	json(paths.results),
	json(paths.defects),
	text(paths.review),
]);
const audit = validateAuditResults(matrixText, results, defects);
failures.push(...audit.errors);
if (!audit.model.gateReady)
	failures.push("audit_cli gate no esta listo: existen validaciones o defectos pendientes.");
if (!/APTO PARA REVISI[ÓO]N/i.test(review) || /NO APTO PARA REVISI[ÓO]N/i.test(review)) {
	failures.push("FINAL_REVIEW_PACKAGE.md no declara APTO PARA REVISION de forma valida.");
}
if (head && !review.includes(head))
	failures.push("FINAL_REVIEW_PACKAGE.md no contiene el HEAD exacto actual.");

let runs = [];
try {
	const controller = new AbortController();
	const timer = setTimeout(() => controller.abort(), 12000);
	const response = await fetch(
		`https://api.github.com/repos/${REPO}/actions/runs?head_sha=${encodeURIComponent(head)}&per_page=100`,
		{
			signal: controller.signal,
			headers: {
				Accept: "application/vnd.github+json",
				"User-Agent": "NEXORA-final-gate",
				"X-GitHub-Api-Version": "2022-11-28",
			},
		}
	);
	clearTimeout(timer);
	if (!response.ok) throw new Error(`GitHub HTTP ${response.status}`);
	const payload = await response.json();
	const latest = new Map();
	for (const run of payload.workflow_runs || []) {
		if (run.head_sha === head && !latest.has(run.name)) latest.set(run.name, run);
	}
	runs = [...latest.values()];
	for (const name of REQUIRED_WORKFLOWS) {
		const run = latest.get(name);
		if (!run) failures.push(`Falta workflow obligatorio: ${name}`);
		else if (run.status !== "completed" || run.conclusion !== "success") {
			failures.push(`${name}: ${run.status}/${run.conclusion || "sin conclusion"}`);
		}
	}
	for (const run of runs) {
		if (
			["failure", "cancelled", "timed_out", "action_required", "startup_failure", "stale"].includes(
				run.conclusion
			)
		) {
			failures.push(`Workflow fallido adicional: ${run.name}`);
		}
		if (run.status !== "completed") failures.push(`Workflow aun ejecutandose: ${run.name}`);
	}
} catch (error) {
	failures.push(`No se pudo verificar GitHub Actions: ${error.message}`);
}

const gate = {
	schema_version: 1,
	checked_at: new Date().toISOString(),
	head,
	branch,
	passed: failures.length === 0,
	failures,
	audit: audit.model.metrics,
	workflows: runs.map((run) => ({
		name: run.name,
		run_id: run.id,
		status: run.status,
		conclusion: run.conclusion,
		head_sha: run.head_sha,
	})),
	next_authorization: failures.length === 0 ? "AUTORIZO PR12" : null,
};
await mkdir(paths.runtime, { recursive: true });
await writeFile(paths.output, `${JSON.stringify(gate, null, 2)}\n`, "utf8");
if (failures.length) {
	console.error("NEXORA FINAL GATE: BLOCKED");
	for (const failure of failures) console.error(`- ${failure}`);
	process.exit(1);
}
console.log("NEXORA FINAL GATE: PASSED");
console.log(`HEAD: ${head}`);
console.log("La fusion sigue bloqueada hasta autorizacion expresa e independiente.");
