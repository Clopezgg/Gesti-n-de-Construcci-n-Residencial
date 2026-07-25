const FINAL_MATRIX_STATES = new Set([
	"IMPLEMENTADO Y VALIDADO",
	"OBSOLETO JUSTIFICADO",
	"NO APLICA JUSTIFICADO",
]);

const AUDIT_STATES = new Set([
	"pending",
	"running",
	"certified",
	"technical_error",
	"objective_mismatch",
	"blocked",
	"decision_required",
	"not_applicable",
]);

const MUTATING_PREFIXES = new Set(["FND", "LCO", "CCO", "CON", "COM", "INV", "PRE", "CIE"]);
const FINANCIAL_PREFIXES = new Set(["FND", "LCO", "CCO", "CON", "COM", "INV", "PRE", "CIE", "REP"]);
const SECURITY_PREFIXES = new Set(["GOV", "USR", "ENT", "DOC", "INF", "QA"]);

function safeString(value) {
	return String(value ?? "").trim();
}

function splitMatrixRow(line) {
	const body = line.trim().replace(/^\|/, "").replace(/\|$/, "");
	return body.split("|").map((item) => item.trim());
}

function requirementPrefix(id) {
	const match = safeString(id).match(/^NXR-([A-Z]+)-/);
	return match ? match[1] : "GEN";
}

export function parseMatrixMarkdown(text) {
	const requirements = [];
	for (const raw of safeString(text).split(/\r?\n/)) {
		const line = raw.trim();
		if (!/^\|\s*`NXR-[^`]+`\s*\|/.test(line)) continue;
		const columns = splitMatrixRow(line);
		if (columns.length < 9) continue;
		const id = columns[0].replaceAll("`", "");
		const owner = columns[3].toUpperCase();
		const blockMatch = owner.match(/BLOQUE\s+(\d+)/);
		requirements.push({
			id,
			title: columns[1],
			matrixState: columns[2].toUpperCase(),
			owner,
			block: blockMatch ? Number(blockMatch[1]) : null,
			machine: columns[4],
			controls: columns[5],
			decisions: columns[6],
			dependencies: columns[7],
			acceptance: columns.slice(8).join(" | "),
			prefix: requirementPrefix(id),
			matrixFinalClaim: FINAL_MATRIX_STATES.has(columns[2].toUpperCase()),
		});
	}
	return requirements;
}

function validation(id, label, category, required = true) {
	return { id, label, category, required };
}

export function validationProfile(requirement) {
	const prefix = requirement.prefix;
	const text = `${requirement.title} ${requirement.controls} ${requirement.acceptance}`.toLowerCase();
	const validations = [
		validation("objective_alignment", "Coincide con el objetivo original", "functional"),
		validation("implementation_trace", "Implementación real localizada", "implementation"),
		validation("positive_test", "Prueba positiva reproducible", "testing"),
		validation("negative_test", "Prueba negativa reproducible", "testing"),
		validation("evidence_same_sha", "Evidencia ligada al mismo SHA completo", "evidence"),
		validation("documentation_consistency", "Código, matriz y documentos coherentes", "governance"),
		validation("regression", "Regresión del bloque y dependencias", "testing"),
	];

	if (/perm|rol|usuario|autoriz|acceso|segregaci/.test(text) || SECURITY_PREFIXES.has(prefix)) {
		validations.push(validation("server_permission", "Permiso aplicado en servidor", "security"));
	}
	if (/idempot/.test(text) || MUTATING_PREFIXES.has(prefix)) {
		validations.push(validation("idempotency", "Idempotencia demostrada", "integrity"));
	}
	if (FINANCIAL_PREFIXES.has(prefix) || /saldo|financ|contab|presup|pago|costo|inventario/.test(text)) {
		validations.push(
			validation("financial_integrity", "Integridad financiera y conciliación", "integrity")
		);
	}
	if (MUTATING_PREFIXES.has(prefix) || /concurr|lock|simult/.test(text)) {
		validations.push(validation("concurrency", "Concurrencia y bloqueo demostrados", "integrity"));
		validations.push(validation("rollback", "Rollback ante fallo demostrado", "integrity"));
	}
	if (requirement.block === 20 || prefix === "INF") {
		validations.push(validation("install_migrate", "Instalación y migración limpias", "runtime"));
		validations.push(validation("uninstall_reinstall", "Desinstalación y reinstalación", "runtime"));
		validations.push(validation("backup_restore", "Backup y restauración aislada", "runtime"));
	}
	if (requirement.block === 18 || prefix === "UX") {
		validations.push(validation("mobile_iphone", "UX móvil/iPhone demostrada", "ux"));
		validations.push(validation("pwa", "PWA instalable y funcional", "ux"));
	}
	if (requirement.block === 19 || prefix === "QA") {
		validations.push(validation("linters", "Linters y pre-commit dos veces", "quality"));
		validations.push(validation("semgrep", "Semgrep sin hallazgos no justificados", "quality"));
		validations.push(validation("github_actions", "Workflows obligatorios verdes", "quality"));
	}

	const unique = new Map();
	for (const item of validations) unique.set(item.id, item);
	return [...unique.values()];
}

function normalizedValidationResult(raw) {
	const status = AUDIT_STATES.has(raw?.status) ? raw.status : "pending";
	return {
		status,
		detail: safeString(raw?.detail),
		command: safeString(raw?.command),
		evidence: Array.isArray(raw?.evidence) ? raw.evidence : [],
		files: Array.isArray(raw?.files) ? raw.files : [],
		sha: safeString(raw?.sha),
		runId: raw?.run_id ?? null,
		jobId: raw?.job_id ?? null,
		updatedAt: safeString(raw?.updated_at),
		attempts: Number.isFinite(Number(raw?.attempts)) ? Number(raw.attempts) : 0,
	};
}

function summarizeStatuses(statuses) {
	const summary = {
		total: statuses.length,
		pending: 0,
		running: 0,
		certified: 0,
		technical_error: 0,
		objective_mismatch: 0,
		blocked: 0,
		decision_required: 0,
		not_applicable: 0,
	};
	for (const status of statuses) {
		if (Object.hasOwn(summary, status)) summary[status] += 1;
		else summary.pending += 1;
	}
	summary.executed = summary.total - summary.pending;
	return summary;
}

function aggregateState(summary) {
	if (summary.technical_error > 0) return "technical_error";
	if (summary.objective_mismatch > 0) return "objective_mismatch";
	if (summary.blocked > 0) return "blocked";
	if (summary.decision_required > 0) return "decision_required";
	if (summary.running > 0) return "running";
	if (summary.total > 0 && summary.certified + summary.not_applicable === summary.total) return "certified";
	return "pending";
}

function percent(part, total) {
	return total > 0 ? Number(((part / total) * 100).toFixed(1)) : 0;
}

function normalizeDefect(raw) {
	const allowed = new Set(["open", "diagnosing", "correcting", "retesting", "blocked", "resolved"]);
	return {
		id: safeString(raw?.id),
		block: Number.isFinite(Number(raw?.block)) ? Number(raw.block) : null,
		requirementId: safeString(raw?.requirement_id),
		category: safeString(raw?.category || "technical_error"),
		severity: safeString(raw?.severity || "high"),
		status: allowed.has(raw?.status) ? raw.status : "open",
		title: safeString(raw?.title || "Defecto sin título"),
		expected: safeString(raw?.expected),
		found: safeString(raw?.found),
		rootCause: safeString(raw?.root_cause),
		files: Array.isArray(raw?.files) ? raw.files : [],
		evidence: Array.isArray(raw?.evidence) ? raw.evidence : [],
		attempts: Number.isFinite(Number(raw?.attempts)) ? Number(raw.attempts) : 0,
		latestResult: safeString(raw?.latest_result),
		assignedTo: safeString(raw?.assigned_to || "OpenCode"),
		updatedAt: safeString(raw?.updated_at),
	};
}

export function buildAuditModel(matrixText, rawResults = {}, rawDefects = {}) {
	const requirements = parseMatrixMarkdown(matrixText);
	const resultMap =
		rawResults?.requirements && typeof rawResults.requirements === "object"
			? rawResults.requirements
			: {};
	const defects = (Array.isArray(rawDefects?.defects) ? rawDefects.defects : [])
		.map(normalizeDefect)
		.filter((item) => item.id);

	const requirementModels = requirements.map((requirement) => {
		const rawRequirement = resultMap[requirement.id] || {};
		const profile = validationProfile(requirement);
		const validations = profile.map((spec) => {
			const result = normalizedValidationResult(rawRequirement?.validations?.[spec.id]);
			return { ...spec, ...result };
		});
		const validationSummary = summarizeStatuses(validations.map((item) => item.status));
		const relatedDefects = defects.filter(
			(item) => item.requirementId === requirement.id && item.status !== "resolved"
		);
		if (relatedDefects.some((item) => item.category === "objective_mismatch")) {
			validationSummary.objective_mismatch += 1;
			validationSummary.total += 1;
			validationSummary.executed += 1;
		}
		if (relatedDefects.some((item) => item.category !== "objective_mismatch")) {
			validationSummary.technical_error += 1;
			validationSummary.total += 1;
			validationSummary.executed += 1;
		}
		return {
			...requirement,
			objectiveSummary: safeString(rawRequirement?.objective_summary),
			implementationFiles: Array.isArray(rawRequirement?.implementation_files)
				? rawRequirement.implementation_files
				: [],
			validations,
			validationSummary,
			auditState: aggregateState(validationSummary),
			defects: relatedDefects.map((item) => item.id),
			lastUpdate: safeString(rawRequirement?.last_update),
		};
	});

	const blocks = [];
	for (let number = 0; number <= 20; number += 1) {
		const blockRequirements = requirementModels.filter((item) => item.block === number);
		const validationStatuses = blockRequirements.flatMap((item) =>
			item.validations.map((validation) => validation.status)
		);
		const summary = summarizeStatuses(validationStatuses);
		const blockDefects = defects.filter((item) => item.block === number && item.status !== "resolved");
		const mismatchDefects = blockDefects.filter((item) => item.category === "objective_mismatch");
		const technicalDefects = blockDefects.filter((item) => item.category !== "objective_mismatch");
		summary.objective_mismatch += mismatchDefects.length;
		summary.technical_error += technicalDefects.length;
		summary.total += blockDefects.length;
		summary.executed += blockDefects.length;
		blocks.push({
			number,
			state: aggregateState(summary),
			requirementsTotal: blockRequirements.length,
			requirementsCertified: blockRequirements.filter((item) => item.auditState === "certified").length,
			summary,
			auditPercent: percent(summary.executed, summary.total),
			certificationPercent: percent(summary.certified + summary.not_applicable, summary.total),
			defects: blockDefects,
			requirements: blockRequirements,
		});
	}

	const allValidationStatuses = requirementModels.flatMap((item) =>
		item.validations.map((validation) => validation.status)
	);
	const totals = summarizeStatuses(allValidationStatuses);
	const openDefects = defects.filter((item) => item.status !== "resolved");
	totals.objective_mismatch += openDefects.filter((item) => item.category === "objective_mismatch").length;
	totals.technical_error += openDefects.filter((item) => item.category !== "objective_mismatch").length;
	totals.total += openDefects.length;
	totals.executed += openDefects.length;

	const activeBlockCandidate = Number(rawResults?.active_block);
	const activeBlock =
		Number.isInteger(activeBlockCandidate) && activeBlockCandidate >= 0 && activeBlockCandidate <= 20
			? activeBlockCandidate
			: blocks.find((block) => block.state !== "certified")?.number ?? 20;

	const matrixFinalClaims = requirements.filter((item) => item.matrixFinalClaim).length;
	const requirementsCertified = requirementModels.filter((item) => item.auditState === "certified").length;
	const auditPercent = percent(totals.executed, totals.total);
	const certificationPercent = percent(totals.certified + totals.not_applicable, totals.total);
	const gateReady =
		requirements.length === 166 &&
		requirementsCertified === 166 &&
		totals.technical_error === 0 &&
		totals.objective_mismatch === 0 &&
		totals.blocked === 0 &&
		totals.decision_required === 0 &&
		totals.pending === 0 &&
		totals.running === 0;

	return {
		schemaVersion: 1,
		mode: "objective-first-layered-audit",
		sourceHead: safeString(rawResults?.source_head),
		status: safeString(rawResults?.status || "active"),
		activeBlock,
		startedAt: safeString(rawResults?.started_at),
		lastUpdate: safeString(rawResults?.last_update),
		matrix: {
			rowsFound: requirements.length,
			finalClaims: matrixFinalClaims,
			claimPercent: percent(matrixFinalClaims, requirements.length),
			warning: "Los estados de la matriz son afirmaciones documentales; no certifican por sí solos.",
		},
		metrics: {
			...totals,
			auditPercent,
			certificationPercent,
			requirementsTotal: requirements.length,
			requirementsCertified,
			blocksTotal: blocks.length,
			blocksCertified: blocks.filter((item) => item.state === "certified").length,
			defectsOpen: openDefects.length,
			defectsResolved: defects.filter((item) => item.status === "resolved").length,
		},
		gateReady,
		blocks,
		requirements: requirementModels,
		defects,
	};
}

export function validateAuditResults(matrixText, results, defects) {
	const model = buildAuditModel(matrixText, results, defects);
	const errors = [];
	if (model.matrix.rowsFound !== 166)
		errors.push(`Se esperaban 166 requisitos y se encontraron ${model.matrix.rowsFound}.`);
	for (const requirement of model.requirements) {
		for (const validationItem of requirement.validations) {
			if (validationItem.status === "certified") {
				if (!validationItem.detail)
					errors.push(`${requirement.id}/${validationItem.id}: falta detalle.`);
				if (!validationItem.sha || !/^[0-9a-f]{40}$/i.test(validationItem.sha)) {
					errors.push(
						`${requirement.id}/${validationItem.id}: falta SHA completo de 40 caracteres.`
					);
				}
				if (!validationItem.evidence.length)
					errors.push(`${requirement.id}/${validationItem.id}: falta evidencia.`);
			}
		}
	}
	return { ok: errors.length === 0, errors, model };
}
