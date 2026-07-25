import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { buildAuditModel, validateAuditResults } from "./audit_model.js";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..", "..");
const MATRIX = resolve(ROOT, "docs", "nexora", "MATRIZ_REQUISITOS.md");
const RESULTS = resolve(ROOT, "docs", "nexora", "AUDIT_RESULTS.json");
const DEFECTS = resolve(ROOT, "docs", "nexora", "DEFECTS.json");
const RUNTIME = resolve(ROOT, ".nexora-monitor");
const RESUME_STATE = resolve(RUNTIME, "resume-state.json");

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

async function load() {
	const [matrixText, results, defects] = await Promise.all([
		readText(MATRIX),
		readJson(RESULTS, { schema_version: 1, status: "active", active_block: 0, requirements: {} }),
		readJson(DEFECTS, { schema_version: 1, defects: [] }),
	]);
	return { matrixText, results, defects, model: buildAuditModel(matrixText, results, defects) };
}

function printSummary(model) {
	const m = model.metrics;
	console.log("NEXORA layered audit");
	console.log(`Source HEAD: ${model.sourceHead || "not recorded"}`);
	console.log(`Audit progress: ${m.auditPercent}% (${m.executed}/${m.total})`);
	console.log(`Certification: ${m.certificationPercent}% (${m.certified + m.not_applicable}/${m.total})`);
	console.log(`Requirements certified: ${m.requirementsCertified}/${m.requirementsTotal}`);
	console.log(`Blocks certified: ${m.blocksCertified}/${m.blocksTotal}`);
	console.log(`Technical errors: ${m.technical_error}`);
	console.log(`Objective mismatches: ${m.objective_mismatch}`);
	console.log(`Blocked: ${m.blocked}`);
	console.log(`Decisions required: ${m.decision_required}`);
	console.log(`Pending: ${m.pending}`);
	console.log(`Open defects: ${m.defectsOpen}`);
	console.log(`Gate ready: ${model.gateReady ? "YES" : "NO"}`);
}

function printBlock(model, blockNumber) {
	const block = model.blocks.find((item) => item.number === blockNumber);
	if (!block) throw new Error(`Block ${blockNumber} does not exist.`);
	console.log(`BLOCK ${block.number}`);
	console.log(
		JSON.stringify(
			{
				state: block.state,
				auditPercent: block.auditPercent,
				certificationPercent: block.certificationPercent,
				summary: block.summary,
				defects: block.defects,
				requirements: block.requirements.map((requirement) => ({
					id: requirement.id,
					title: requirement.title,
					matrixState: requirement.matrixState,
					auditState: requirement.auditState,
					validations: requirement.validations.map((item) => ({
						id: item.id,
						label: item.label,
						status: item.status,
					})),
				})),
			},
			null,
			2
		)
	);
}

function isFinalValidation(status) {
	return status === "certified" || status === "not_applicable";
}

function findResumePoint(model, results) {
	for (const block of model.blocks) {
		for (const requirement of block.requirements) {
			const validation = requirement.validations.find((item) => !isFinalValidation(item.status));
			if (validation) {
				return {
					complete: false,
					block: block.number,
					requirement_id: requirement.id,
					requirement_title: requirement.title,
					validation_id: validation.id,
					validation_label: validation.label,
					validation_status: validation.status,
				};
			}
		}
	}

	return {
		complete: model.gateReady,
		block: Number.isInteger(results?.active_block) ? results.active_block : 20,
		requirement_id: null,
		requirement_title: null,
		validation_id: null,
		validation_label: null,
		validation_status: null,
	};
}

function resumePayload(model, results) {
	const metrics = model.metrics;
	return {
		schema_version: 1,
		generated_at: new Date().toISOString(),
		source_head: model.sourceHead || results?.source_head || "",
		baseline_head: results?.baseline_head || "",
		status: results?.status || "active",
		active_block: Number.isInteger(results?.active_block) ? results.active_block : 0,
		last_update: results?.last_update || "",
		gate_ready: model.gateReady,
		metrics: {
			audit_percent: metrics.auditPercent,
			certification_percent: metrics.certificationPercent,
			executed: metrics.executed,
			total: metrics.total,
			certified: metrics.certified + metrics.not_applicable,
			requirements_certified: metrics.requirementsCertified,
			requirements_total: metrics.requirementsTotal,
			blocks_certified: metrics.blocksCertified,
			blocks_total: metrics.blocksTotal,
			pending: metrics.pending,
			technical_errors: metrics.technical_error,
			objective_mismatches: metrics.objective_mismatch,
			blocked: metrics.blocked,
			decisions_required: metrics.decision_required,
			open_defects: metrics.defectsOpen,
		},
		next: findResumePoint(model, results),
	};
}

async function persistResumeState(payload) {
	await mkdir(RUNTIME, { recursive: true });
	await writeFile(RESUME_STATE, `${JSON.stringify(payload, null, 2)}\n`, "utf8");
}

async function initialize(head) {
	const current = await readJson(RESULTS, {});
	const next = {
		schema_version: 1,
		mode: "objective-first-layered-audit",
		baseline_head: current.baseline_head || head || "",
		source_head: head || current.source_head || "",
		status: "active",
		active_block: Number.isInteger(current.active_block) ? current.active_block : 0,
		started_at: current.started_at || new Date().toISOString(),
		last_update: new Date().toISOString(),
		requirements:
			current.requirements && typeof current.requirements === "object" ? current.requirements : {},
	};
	await writeFile(RESULTS, `${JSON.stringify(next, null, 2)}\n`, "utf8");
	console.log(`Initialized ${RESULTS}`);
}

const command = process.argv[2] || "summary";
const { matrixText, results, defects, model } = await load();

if (command === "summary") {
	printSummary(model);
} else if (command === "validate") {
	const validation = validateAuditResults(matrixText, results, defects);
	printSummary(validation.model);
	if (!validation.ok) {
		console.error("Audit data validation failed:");
		for (const error of validation.errors) console.error(`- ${error}`);
		process.exitCode = 1;
	}
} else if (command === "block") {
	const block = Number(process.argv[3]);
	if (!Number.isInteger(block) || block < 0 || block > 20) throw new Error("Use: block <0-20>");
	printBlock(model, block);
} else if (command === "init") {
	await initialize(process.argv[3] || "");
} else if (command === "resume") {
	const validation = validateAuditResults(matrixText, results, defects);
	if (!validation.ok) {
		console.error("Audit data validation failed:");
		for (const error of validation.errors) console.error(`- ${error}`);
		process.exitCode = 1;
	} else {
		const payload = resumePayload(validation.model, results);
		await persistResumeState(payload);
		console.log(JSON.stringify(payload));
	}
} else if (command === "gate") {
	const validation = validateAuditResults(matrixText, results, defects);
	printSummary(validation.model);
	if (!validation.ok || !validation.model.gateReady) process.exitCode = 1;
} else {
	throw new Error(`Unknown command: ${command}`);
}
