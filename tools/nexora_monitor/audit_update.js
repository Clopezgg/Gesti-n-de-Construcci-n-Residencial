import { readFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..", "..");
const RESULTS_PATH = resolve(ROOT, "docs", "nexora", "AUDIT_RESULTS.json");
const DEFECTS_PATH = resolve(ROOT, "docs", "nexora", "DEFECTS.json");
const ALLOWED_VALIDATION_STATES = new Set([
	"pending",
	"running",
	"certified",
	"technical_error",
	"objective_mismatch",
	"blocked",
	"decision_required",
	"not_applicable",
]);
const ALLOWED_DEFECT_STATES = new Set([
	"open",
	"diagnosing",
	"correcting",
	"retesting",
	"blocked",
	"resolved",
]);

async function readJson(path, fallback) {
	try {
		return JSON.parse(await readFile(path, "utf8"));
	} catch {
		return fallback;
	}
}

async function writeJson(path, value) {
	await writeFile(path, `${JSON.stringify(value, null, 2)}\n`, "utf8");
}

async function readPayload() {
	const fileIndex = process.argv.indexOf("--file");
	if (fileIndex >= 0) {
		const file = process.argv[fileIndex + 1];
		if (!file) throw new Error("--file requires a path.");
		return JSON.parse(await readFile(resolve(process.cwd(), file), "utf8"));
	}
	const chunks = [];
	for await (const chunk of process.stdin) chunks.push(chunk);
	const text = Buffer.concat(chunks).toString("utf8").trim();
	if (!text) throw new Error("Provide JSON through stdin or --file.");
	return JSON.parse(text);
}

function ensureFullSha(sha, context) {
	if (!/^[0-9a-f]{40}$/i.test(String(sha || "")))
		throw new Error(`${context}: SHA must contain 40 hexadecimal characters.`);
}

function normalizeEvidence(evidence) {
	if (!Array.isArray(evidence)) return [];
	return evidence.filter((item) => item && typeof item === "object");
}

function validateCertified(payload) {
	if (!String(payload.detail || "").trim()) throw new Error("Certified validation requires detail.");
	ensureFullSha(payload.sha, "Certified validation");
	if (!normalizeEvidence(payload.evidence).length)
		throw new Error("Certified validation requires evidence.");
}

async function setValidation(payload) {
	const requirementId = String(payload.requirement_id || "").trim();
	const validationId = String(payload.validation_id || "").trim();
	const status = String(payload.status || "").trim();
	if (!/^NXR-[A-Z]+-\d{4}$/.test(requirementId)) throw new Error("Invalid requirement_id.");
	if (!/^[a-z][a-z0-9_]*$/.test(validationId)) throw new Error("Invalid validation_id.");
	if (!ALLOWED_VALIDATION_STATES.has(status)) throw new Error(`Invalid validation status: ${status}`);
	if (["certified", "not_applicable"].includes(status)) validateCertified(payload);

	const results = await readJson(RESULTS_PATH, {
		schema_version: 1,
		status: "active",
		active_block: 0,
		requirements: {},
	});
	results.requirements ||= {};
	results.requirements[requirementId] ||= { validations: {} };
	results.requirements[requirementId].validations ||= {};
	results.requirements[requirementId].validations[validationId] = {
		status,
		detail: String(payload.detail || ""),
		command: String(payload.command || ""),
		evidence: normalizeEvidence(payload.evidence),
		files: Array.isArray(payload.files) ? payload.files : [],
		sha: String(payload.sha || ""),
		run_id: payload.run_id ?? null,
		job_id: payload.job_id ?? null,
		attempts: Number.isFinite(Number(payload.attempts)) ? Number(payload.attempts) : 0,
		updated_at: new Date().toISOString(),
	};
	if (payload.objective_summary !== undefined)
		results.requirements[requirementId].objective_summary = String(payload.objective_summary || "");
	if (Array.isArray(payload.implementation_files))
		results.requirements[requirementId].implementation_files = payload.implementation_files;
	results.last_update = new Date().toISOString();
	await writeJson(RESULTS_PATH, results);
}

async function setRequirement(payload) {
	const requirementId = String(payload.requirement_id || "").trim();
	if (!/^NXR-[A-Z]+-\d{4}$/.test(requirementId)) throw new Error("Invalid requirement_id.");
	const results = await readJson(RESULTS_PATH, {
		schema_version: 1,
		status: "active",
		active_block: 0,
		requirements: {},
	});
	results.requirements ||= {};
	results.requirements[requirementId] ||= { validations: {} };
	if (payload.objective_summary !== undefined)
		results.requirements[requirementId].objective_summary = String(payload.objective_summary || "");
	if (Array.isArray(payload.implementation_files))
		results.requirements[requirementId].implementation_files = payload.implementation_files;
	results.requirements[requirementId].last_update = new Date().toISOString();
	results.last_update = new Date().toISOString();
	await writeJson(RESULTS_PATH, results);
}

async function setAuditState(payload) {
	const results = await readJson(RESULTS_PATH, {
		schema_version: 1,
		status: "active",
		active_block: 0,
		requirements: {},
	});
	if (payload.active_block !== undefined) {
		const block = Number(payload.active_block);
		if (!Number.isInteger(block) || block < 0 || block > 20)
			throw new Error("active_block must be between 0 and 20.");
		results.active_block = block;
	}
	if (payload.status !== undefined) results.status = String(payload.status || "active");
	if (payload.source_head !== undefined) {
		ensureFullSha(payload.source_head, "source_head");
		results.source_head = payload.source_head;
	}
	results.last_update = new Date().toISOString();
	await writeJson(RESULTS_PATH, results);
}

function validateDefectId(id) {
	if (!/^NXR-DEF-B\d{2}-\d{4}$/.test(id)) throw new Error("Defect id must use NXR-DEF-B00-0001 format.");
}

async function upsertDefect(payload) {
	const id = String(payload.id || "").trim();
	validateDefectId(id);
	const block = Number(payload.block);
	if (!Number.isInteger(block) || block < 0 || block > 20)
		throw new Error("Defect block must be between 0 and 20.");
	const status = String(payload.status || "open");
	if (!ALLOWED_DEFECT_STATES.has(status)) throw new Error(`Invalid defect status: ${status}`);
	const defectsDoc = await readJson(DEFECTS_PATH, { schema_version: 1, defects: [] });
	defectsDoc.defects = Array.isArray(defectsDoc.defects) ? defectsDoc.defects : [];
	const existingIndex = defectsDoc.defects.findIndex((item) => item.id === id);
	const previous = existingIndex >= 0 ? defectsDoc.defects[existingIndex] : {};
	const next = {
		...previous,
		id,
		block,
		requirement_id: String(payload.requirement_id || previous.requirement_id || ""),
		category: String(payload.category || previous.category || "technical_error"),
		severity: String(payload.severity || previous.severity || "high"),
		status,
		title: String(payload.title || previous.title || "Defecto sin titulo"),
		expected: String(payload.expected ?? previous.expected ?? ""),
		found: String(payload.found ?? previous.found ?? ""),
		root_cause: String(payload.root_cause ?? previous.root_cause ?? ""),
		files: Array.isArray(payload.files) ? payload.files : previous.files || [],
		evidence: normalizeEvidence(payload.evidence ?? previous.evidence),
		attempts: Number.isFinite(Number(payload.attempts))
			? Number(payload.attempts)
			: Number(previous.attempts || 0),
		latest_result: String(payload.latest_result ?? previous.latest_result ?? ""),
		assigned_to: String(payload.assigned_to || previous.assigned_to || "OpenCode"),
		updated_at: new Date().toISOString(),
	};
	if (existingIndex >= 0) defectsDoc.defects[existingIndex] = next;
	else defectsDoc.defects.push(next);
	await writeJson(DEFECTS_PATH, defectsDoc);
}

async function resolveDefect(payload) {
	const id = String(payload.id || "").trim();
	validateDefectId(id);
	const defectsDoc = await readJson(DEFECTS_PATH, { schema_version: 1, defects: [] });
	const defect = (defectsDoc.defects || []).find((item) => item.id === id);
	if (!defect) throw new Error(`Defect not found: ${id}`);
	ensureFullSha(payload.sha, "Resolved defect");
	if (!String(payload.latest_result || "").trim())
		throw new Error("Resolved defect requires latest_result.");
	if (!normalizeEvidence(payload.evidence).length) throw new Error("Resolved defect requires evidence.");
	defect.status = "resolved";
	defect.latest_result = String(payload.latest_result);
	defect.resolution_sha = payload.sha;
	defect.evidence = [...normalizeEvidence(defect.evidence), ...normalizeEvidence(payload.evidence)];
	defect.updated_at = new Date().toISOString();
	await writeJson(DEFECTS_PATH, defectsDoc);
}

const operation = process.argv[2];
if (!operation)
	throw new Error(
		"Use set-validation, set-requirement, set-audit-state, upsert-defect, or resolve-defect."
	);
const payload = await readPayload();
if (operation === "set-validation") await setValidation(payload);
else if (operation === "set-requirement") await setRequirement(payload);
else if (operation === "set-audit-state") await setAuditState(payload);
else if (operation === "upsert-defect") await upsertDefect(payload);
else if (operation === "resolve-defect") await resolveDefect(payload);
else throw new Error(`Unknown operation: ${operation}`);
console.log(`${operation}: OK`);
