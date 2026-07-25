import { readFile } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { validateAuditResults } from "./audit_model.js";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..", "..");
const paths = {
	matrix: join(ROOT, "docs", "nexora", "MATRIZ_REQUISITOS.md"),
	results: join(ROOT, "docs", "nexora", "AUDIT_RESULTS.json"),
	defects: join(ROOT, "docs", "nexora", "DEFECTS.json"),
	live: join(ROOT, "docs", "nexora", "LIVE_PROGRESS.json"),
	html: join(HERE, "dashboard.html"),
	server: join(HERE, "dashboard_server_v3.js"),
	cli: join(HERE, "audit_cli.js"),
	update: join(HERE, "audit_update.js"),
	finalGate: join(HERE, "final_gate_check.js"),
};

const errors = [];
async function text(path) {
	try {
		return await readFile(path, "utf8");
	} catch (error) {
		errors.push(`No se pudo leer ${path}: ${error.message}`);
		return "";
	}
}
async function json(path) {
	const raw = await text(path);
	try {
		return JSON.parse(raw);
	} catch (error) {
		errors.push(`JSON invalido ${path}: ${error.message}`);
		return {};
	}
}

const [matrixText, results, defects, live, html] = await Promise.all([
	text(paths.matrix),
	json(paths.results),
	json(paths.defects),
	json(paths.live),
	text(paths.html),
]);

if (live && typeof live !== "object") errors.push("LIVE_PROGRESS.json no contiene un objeto.");
const auditValidation = validateAuditResults(matrixText, results, defects);
errors.push(...auditValidation.errors);
if (auditValidation.model.matrix.rowsFound !== 166)
	errors.push(`La matriz contiene ${auditValidation.model.matrix.rowsFound} requisitos, no 166.`);

const requiredIds = [
	"auditBar",
	"certBar",
	"metrics",
	"nodes",
	"blockTitle",
	"greenList",
	"orangeList",
	"redList",
	"defects",
	"currentTask",
	"activity",
	"requirements",
	"actions",
	"gate",
	"gateMessage",
];
for (const id of requiredIds) {
	if (!html.includes(`id="${id}"`)) errors.push(`dashboard.html no contiene #${id}.`);
}
const scriptMatches = [...html.matchAll(/<script>([\s\S]*?)<\/script>/gi)];
if (scriptMatches.length !== 1)
	errors.push(`dashboard.html debe contener un script principal; encontrados ${scriptMatches.length}.`);
else {
	try {
		new Function(scriptMatches[0][1]);
	} catch (error) {
		errors.push(`JavaScript del dashboard invalido: ${error.message}`);
	}
}

const build = await Bun.build({
	entrypoints: [paths.server, paths.cli, paths.update, paths.finalGate],
	target: "bun",
	format: "esm",
	write: false,
});
if (!build.success) {
	for (const log of build.logs) errors.push(`Bun build: ${log.message || String(log)}`);
}

if (errors.length) {
	console.error("NEXORA monitor self-check FAILED");
	for (const error of errors) console.error(`- ${error}`);
	process.exit(1);
}

console.log("NEXORA monitor self-check OK");
console.log(`Requisitos: ${auditValidation.model.matrix.rowsFound}`);
console.log(`Auditoria: ${auditValidation.model.metrics.auditPercent}%`);
console.log(`Certificacion: ${auditValidation.model.metrics.certificationPercent}%`);
console.log(`Defectos abiertos: ${auditValidation.model.metrics.defectsOpen}`);
console.log("Puerta final: sintaxis verificada, ejecucion bloqueada hasta 100% real.");
