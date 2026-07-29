(function (root, factory) {
	const api = factory();
	if (typeof module === "object" && module.exports) module.exports = api;
	root.nexora = root.nexora || {};
	root.nexora.guidedOperationsModel = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
	"use strict";

	const BANK_CHANNELS = new Set(["Remittance", "Deposit", "Transfer"]);
	const PRIMARY_FIELDS = Object.freeze({
		101: ["document_date", "project", "origin_or_sender", "channel", "original_amount", "currency"],
		102: ["document_date", "project", "beneficiary", "description", "amount_hnl", "currency"],
	});
	const CONDITIONAL_FIELDS = Object.freeze({
		101: [
			"financial_account",
			"account_name",
			"institution",
			"account_reference",
			"external_reference",
			"exchange_rate",
			"evidence",
		],
		102: [
			"payment_method",
			"financial_account",
			"account_name",
			"institution",
			"account_reference",
			"external_reference",
			"original_amount",
			"exchange_rate",
			"economic_category",
			"cost_center",
			"evidence",
		],
	});
	const ADVANCED_FIELDS = Object.freeze([
		"movement_code",
		"reference_name",
		"requester",
		"approved_by",
	]);

	function text(value) {
		return String(value || "").trim();
	}

	function folded(value) {
		return text(value).toLocaleLowerCase("es");
	}

	function movementDirection(movementCode) {
		return String(movementCode) === "102" ? "Destination" : "Origin";
	}

	function counterpartyField(movementCode) {
		return String(movementCode) === "102" ? "beneficiary" : "origin_or_sender";
	}

	function channelField(movementCode) {
		return String(movementCode) === "102" ? "payment_method" : "channel";
	}

	function accountCompatible(account, context) {
		const requiredDirection = movementDirection(context.movementCode);
		const accountDirection = text(account.direction || "Origin");
		if (![requiredDirection, "Both"].includes(accountDirection)) return false;
		const project = text(context.project);
		if (text(account.project) && text(account.project) !== project) return false;
		const currency = text(context.currency).toUpperCase();
		if (currency && text(account.currency || "HNL").toUpperCase() !== currency) return false;
		const channel = text(context.channel);
		if (channel && text(account.default_channel || "Other") !== channel) return false;
		const counterparty = folded(context.counterparty);
		if (counterparty && folded(account.origin_or_sender) !== counterparty) return false;
		return true;
	}

	function compatibleAccounts(rows, context) {
		return (rows || []).filter((row) => accountCompatible(row, context));
	}

	function deriveInternalMode({ choice, saveForFuture, hasAccounts }) {
		if (choice === "saved" && hasAccounts) return "Existing";
		return saveForFuture ? "New" : "Manual";
	}

	function canonicalAccountSelection(input) {
		const hasAccounts = Boolean(input.hasAccounts);
		const accountMode = deriveInternalMode({
			choice: input.choice,
			saveForFuture: Boolean(input.saveForFuture),
			hasAccounts,
		});
		const movementCode = String(input.movementCode || "101");
		const destination = movementCode === "102";
		return {
			account_mode: accountMode,
			financial_account: accountMode === "Existing" ? text(input.selectedAccount) : "",
			save_financial_account: accountMode === "New" ? 1 : 0,
			account_name: accountMode === "New" ? text(input.accountName) : "",
			direction: movementDirection(movementCode),
			origin_or_sender: text(input.counterparty),
			channel: destination ? text(input.paymentMethod) : text(input.channel),
			payment_method: destination ? text(input.paymentMethod) : "",
			currency: text(input.currency || "HNL").toUpperCase(),
			institution: text(input.institution),
			account_reference: text(input.accountReference),
		};
	}

	function fieldStage(movementCode, fieldname) {
		const code = String(movementCode || "");
		if ((PRIMARY_FIELDS[code] || []).includes(fieldname)) return 1;
		if ((CONDITIONAL_FIELDS[code] || []).includes(fieldname)) return 2;
		if (ADVANCED_FIELDS.includes(fieldname)) return "advanced";
		return 2;
	}

	function conditionalVisibility(context) {
		const movementCode = String(context.movementCode || "101");
		const channel = text(context.channel);
		const currency = text(context.currency || "HNL").toUpperCase();
		const accountMode = text(context.accountMode || "Manual");
		const bank = BANK_CHANNELS.has(channel);
		return {
			showInstitution: bank,
			showAccountReference: bank,
			showExternalReference: channel !== "Cash",
			showExchangeRate: currency !== "HNL",
			showOriginalAmount: movementCode === "101" || currency !== "HNL",
			showAccountName: accountMode === "New",
			showFunds: movementCode === "102",
			showClassification: movementCode === "102",
			showEvidence: ["101", "102"].includes(movementCode),
		};
	}

	return Object.freeze({
		ADVANCED_FIELDS,
		BANK_CHANNELS,
		CONDITIONAL_FIELDS,
		PRIMARY_FIELDS,
		accountCompatible,
		canonicalAccountSelection,
		channelField,
		compatibleAccounts,
		conditionalVisibility,
		counterpartyField,
		deriveInternalMode,
		fieldStage,
		movementDirection,
	});
});
