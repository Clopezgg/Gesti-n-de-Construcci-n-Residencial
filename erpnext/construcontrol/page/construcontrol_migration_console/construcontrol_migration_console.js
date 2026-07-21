frappe.pages["construcontrol-migration-console"].on_page_load = function (wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
		title: "Migración segura de ConstruControl",
		single_column: true,
	});
	const body = $(wrapper).find(".layout-main-section");
	let validationRun = null;

	body.html(`
    <style>
      .cc-mig{max-width:1100px}.cc-step{border:1px solid var(--border-color);border-radius:12px;padding:16px;margin:12px 0;background:var(--card-bg)}.cc-step h3{margin-top:0}.cc-result{white-space:normal}.cc-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px}.cc-chip{padding:10px;border:1px solid var(--border-color);border-radius:9px}.cc-ok{color:var(--green-600)}.cc-bad{color:var(--red-600)}.cc-warning{background:var(--yellow-100);padding:10px;border-radius:8px}.cc-actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}
    </style>
    <div class="cc-mig">
      <div class="cc-step"><h3>1. Seleccionar respaldo</h3><p>Admite la copia lógica de Supabase <b>.tar.gz</b>, SQL o JSON. Las imágenes, fotografías y rutas de Storage se excluyen. Solo se conserva su metadata.</p><button class="btn btn-primary" id="cc-upload">Seleccionar y validar respaldo</button></div>
      <div class="cc-step"><h3>2. Resultado de la validación</h3><div id="cc-validation" class="cc-result text-muted">Aún no se ha validado un archivo.</div></div>
      <div class="cc-step"><h3>3. Migración definitiva</h3><p>Antes de escribir datos, el sistema crea un respaldo comprimido de MariaDB. La importación es idempotente y concilia cada colección. La limpieza demo se inicia únicamente después de una conciliación exitosa.</p><div class="cc-actions"><button class="btn btn-danger" id="cc-migrate" disabled>Migrar y limpiar demo</button><button class="btn btn-default" id="cc-runs">Ver historial</button></div></div>
    </div>
  `);

	body.find("#cc-runs").on("click", () => frappe.set_route("List", "ConstruControl Migration Run"));

	body.find("#cc-upload").on(
		"click",
		() =>
			new frappe.ui.FileUploader({
				method: "erpnext.construcontrol.api.upload_and_validate",
				allow_web_link: false,
				allow_toggle_private: false,
				allow_take_photo: false,
				restrictions: { allowed_file_types: [".tar.gz", ".tgz", ".sql", ".gz", ".json"] },
				on_success: function (_fileDoc, response) {
					const message = response.message || {};
					const validation = message.validation || {};
					validationRun = message.migration_run || null;
					const countEntries = Object.entries(validation.counts || {}).filter(
						([, count]) => count > 0
					);
					const totals = validation.totals || {};
					const issues = [...(validation.errors || []), ...(validation.warnings || [])];

					body.find("#cc-validation").html(`
        <div class="${validation.valid ? "cc-ok" : "cc-bad"}"><b>${
						validation.valid ? "VALIDACIÓN APROBADA" : "VALIDACIÓN BLOQUEADA"
					}</b></div>
        <p>Huella: <code>${frappe.utils.escape_html(message.source_sha256 || "")}</code></p>
        <div class="cc-grid">
          ${countEntries
				.map(
					([key, count]) =>
						`<div class="cc-chip"><span class="text-muted">${frappe.utils.escape_html(
							key
						)}</span><br><b>${count}</b></div>`
				)
				.join("")}
          <div class="cc-chip"><span class="text-muted">Ingresos</span><br><b>${format_currency(
				totals.income_hnl || 0,
				"HNL"
			)}</b></div>
          <div class="cc-chip"><span class="text-muted">Gastos</span><br><b>${format_currency(
				totals.expense_hnl || 0,
				"HNL"
			)}</b></div>
          <div class="cc-chip"><span class="text-muted">Contratos</span><br><b>${format_currency(
				totals.contract_hnl || 0,
				"HNL"
			)}</b></div>
        </div>
        ${
			issues.length
				? `<div class="cc-warning"><b>Observaciones</b><br>${issues
						.map(frappe.utils.escape_html)
						.join("<br>")}</div>`
				: ""
		}
        <p><b>Imágenes a importar: 0.</b> Referencias de evidencia detectadas: ${
			validation.evidence_references || 0
		}.</p>
      `);

					body.find("#cc-migrate").prop("disabled", !validation.valid || !validationRun);
				},
			})
	);

	body.find("#cc-migrate").on("click", function () {
		if (!validationRun) return;
		frappe.prompt(
			[{ fieldname: "confirmation", fieldtype: "Data", label: "Escriba MIGRAR", reqd: 1 }],
			(values) => {
				frappe.dom.freeze("Creando respaldo, migrando y conciliando. No cierre esta pestaña...");
				frappe
					.xcall("erpnext.construcontrol.api.execute_migration", {
						validation_run: validationRun,
						confirmation: values.confirmation,
					})
					.then((result) => {
						frappe.dom.unfreeze();
						const message = result || {};
						frappe.msgprint({
							title: "Migración completada",
							indicator: "green",
							message: `Ejecución: <b>${message.migration_run}</b><br>Respaldo previo: <code>${
								message.backup_reference
							}</code><br>Imágenes importadas: <b>0</b><br>Limpieza demo: <b>${
								message.demo_cleanup?.status || "pendiente"
							}</b>`,
						});
						body.find("#cc-migrate").prop("disabled", true);
						frappe.set_route("construcontrol-dashboard");
					})
					.catch(() => frappe.dom.unfreeze());
			},
			"Confirmación obligatoria",
			"Ejecutar migración"
		);
	});
};
