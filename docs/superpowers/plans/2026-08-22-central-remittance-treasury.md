# Central Remittance Treasury Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar y validar una sola Cuenta Central de Remesas, una fuente individual por remesa y `NXR Operation Effect` como único libro, con cierres, permisos, métricas y consumidores coherentes.

**Architecture:** Se amplía `NXR Financial Account` con identidad técnica y se enlaza desde cada remesa nueva. Los saldos se agregan por joins sobre remesa/fuente/efecto; una validación canónica de períodos aplica simultáneamente cierres centrales y de proyecto, sin crear otro ledger ni migrar históricos.

**Tech Stack:** Frappe/ERPNext v15, Python 3.11, MariaDB, JavaScript Frappe Pages, unittest, Playwright, Ruff.

**Spec:** `docs/superpowers/specs/2026-08-22-central-remittance-treasury-design.md`

## Global Constraints

- Producto visible: `NEXORA — Gestión Integral de Fondos, Proyectos y Operaciones`.
- Cuenta técnica única: `CENTRAL_REMITTANCE`.
- Una `NXR Fund Source` por remesa nueva.
- `NXR Operation Effect` es el único libro de saldos.
- No se migran registros históricos ni se inventan datos bancarios.
- No se modifica producción, AWS, Coolify, DNS, secretos, volúmenes ni datos reales.
- Toda mutación usa permisos de servidor, idempotencia, locks, auditoría y documento de 12 dígitos cuando corresponda.
- No se declara `IMPLEMENTADO Y VALIDADO` sin pruebas positivas, negativas, integración, E2E, commit, push y SHA remoto.

---

### Task 1: Identidad única de la Cuenta Central

**Files:**
- Modify: `nexora_app/nexora/nexora/doctype/nxr_financial_account/nxr_financial_account.json`
- Modify: `nexora_app/nexora/nexora/doctype/nxr_financial_account/nxr_financial_account.py`
- Create: `nexora_app/nexora/financial/central_treasury.py`
- Create: `nexora_app/nexora/patches/v0_1/ensure_central_remittance_account.py`
- Modify: `nexora_app/nexora/patches.txt`
- Test: `nexora_app/nexora/tests/test_central_treasury_contract.py`
- Test: `nexora_app/nexora/tests/test_central_treasury_integration.py`

**Interfaces:**
- Produces: `CENTRAL_REMITTANCE_KEY: str`, `ensure_central_remittance_account() -> str`, `is_central_remittance_source(source: str) -> bool`, `central_source_names() -> tuple[str, ...]`.
- Consumes: `service_write()`, `canonical_payload_hash()`, Frappe DocType metadata and database uniqueness.

- [ ] **Step 1: Write the failing contract tests**

```python
def test_financial_account_exposes_unique_system_identity(self):
    payload = json.loads(ACCOUNT_JSON.read_text())
    fields = {row["fieldname"]: row for row in payload["fields"]}
    self.assertEqual(1, fields["technical_key"]["unique"])
    self.assertEqual(1, fields["system_managed"]["read_only"])

def test_patch_is_registered_once(self):
    lines = PATCHES.read_text().splitlines()
    self.assertEqual(1, lines.count("nexora.patches.v0_1.ensure_central_remittance_account"))
```

- [ ] **Step 2: Run the contract tests and verify RED**

Run: `cd nexora_app && /opt/homebrew/bin/python3.11 -m unittest -v nexora.tests.test_central_treasury_contract`

Expected: FAIL because the fields, service and patch do not exist.

- [ ] **Step 3: Add the minimal schema, controller rules and idempotent patch**

```python
CENTRAL_REMITTANCE_KEY = "CENTRAL_REMITTANCE"

def ensure_central_remittance_account() -> str:
    existing = frappe.db.get_value(
        "NXR Financial Account", {"technical_key": CENTRAL_REMITTANCE_KEY}, "name"
    )
    if existing:
        return str(existing)
    with service_write():
        return str(frappe.get_doc({
            "doctype": "NXR Financial Account",
            "account_name": "Cuenta Central de Remesas",
            "account_role": "Treasury",
            "technical_key": CENTRAL_REMITTANCE_KEY,
            "system_managed": 1,
            "active": 1,
            "direction": "Origin",
            "origin_or_sender": "NEXORA",
            "currency": "HNL",
            "default_channel": "Remittance",
            "is_default": 1,
            "account_fingerprint": canonical_payload_hash({"technical_key": CENTRAL_REMITTANCE_KEY}),
        }).insert(ignore_permissions=True).name)
```

The controller must reject deletion and changes to every fixed field of a system-managed account. Treasury accounts are exempt from fabricated institution/account-reference requirements.

- [ ] **Step 4: Add real MariaDB integration coverage**

```python
def test_ensure_is_idempotent_and_unique(self):
    first = ensure_central_remittance_account()
    second = ensure_central_remittance_account()
    self.assertEqual(first, second)
    self.assertEqual(1, frappe.db.count("NXR Financial Account", {"technical_key": CENTRAL_REMITTANCE_KEY}))

def test_central_account_cannot_be_disabled_or_deleted(self):
    name = ensure_central_remittance_account()
    doc = frappe.get_doc("NXR Financial Account", name)
    with self.assertRaises(frappe.ValidationError):
        doc.delete(ignore_permissions=True)
```

- [ ] **Step 5: Run RED→GREEN verification**

Run contract tests locally and `bench --site "$SITE" run-tests --app nexora --module nexora.tests.test_central_treasury_integration` in CI.

- [ ] **Step 6: Commit**

```bash
git add nexora_app/nexora/nexora/doctype/nxr_financial_account nexora_app/nexora/financial/central_treasury.py nexora_app/nexora/patches nexora_app/nexora/patches.txt nexora_app/nexora/tests/test_central_treasury_*.py
git commit -m "feat(nexora): establish central remittance account"
```

### Task 2: Remesa individual enlazada y precisión cambiaria

**Files:**
- Modify: `nexora_app/nexora/nexora/doctype/nxr_remittance/nxr_remittance.json`
- Modify: `nexora_app/nexora/nexora/doctype/nxr_remittance/nxr_remittance.py`
- Modify: `nexora_app/nexora/financial/remittances.py`
- Modify: `nexora_app/nexora/financial/sources.py`
- Test: `nexora_app/nexora/tests/test_remittance_contract.py`
- Test: `nexora_app/nexora/tests/test_remittances_integration.py`

**Interfaces:**
- Consumes: `ensure_central_remittance_account() -> str`, `rate(value) -> Decimal`, `create_fund_source(payload) -> dict`.
- Produces: remittance `financial_account` link and exactly one linked fund source.

- [ ] **Step 1: Write failing positive and negative tests**

```python
def test_two_remittances_share_one_account_but_keep_two_sources(self):
    first = create_remittance(self._payload("one", "100.00", "24.123456789"))
    second = create_remittance(self._payload("two", "200.00", "24.123456789"))
    self.assertEqual(first["financial_account"], second["financial_account"])
    self.assertNotEqual(first["fund_source"], second["fund_source"])

def test_alternate_account_and_legacy_destinations_are_rejected(self):
    for override in ({"financial_account": "OTHER"}, {"destinations": [{"amount_hnl": 1}]}):
        with self.subTest(override=override), self.assertRaises(frappe.ValidationError):
            create_remittance({**self._payload("invalid", "10", "1"), **override})

def test_rate_is_not_rounded_before_conversion(self):
    result = create_remittance(self._payload("precision", "100.00", "24.123456789"))
    self.assertEqual("2412.35", result["amount_hnl"])
```

- [ ] **Step 2: Run tests and verify expected failures**

Run: `cd nexora_app && /opt/homebrew/bin/python3.11 -m unittest -v nexora.tests.test_remittance_contract`

Run the MariaDB module in the financial-invariants workflow and confirm failures name the absent account link, silent legacy payload and `2412.00` precision defect.

- [ ] **Step 3: Implement the minimal service changes**

Use `money(money(original_amount) * rate(exchange_rate))`, set the resolved account on the remittance, pass one central destination to the existing source service, and return both stable identifiers. Reject client-provided alternate accounts, project ownership and non-empty legacy destination arrays.

- [ ] **Step 4: Preserve idempotency and rollback coverage**

Add assertions that the same key/payload returns the original remittance/source, a changed payload is rejected, and an injected source failure leaves no remittance, sequence or audit residue.

- [ ] **Step 5: Run focused unit and MariaDB tests**

Run: `cd nexora_app && /opt/homebrew/bin/python3.11 -m unittest -v nexora.tests.test_remittance_contract nexora.tests.test_financial_core`

- [ ] **Step 6: Commit**

```bash
git add nexora_app/nexora/nexora/doctype/nxr_remittance nexora_app/nexora/financial/remittances.py nexora_app/nexora/financial/sources.py nexora_app/nexora/tests/test_remittance_contract.py nexora_app/nexora/tests/test_remittances_integration.py
git commit -m "fix(nexora): preserve remittance identity in central treasury"
```

### Task 3: Cierre central y validación canónica de períodos

**Files:**
- Create: `nexora_app/nexora/financial/periods.py`
- Modify: `nexora_app/nexora/financial/operational_common.py`
- Modify: `nexora_app/nexora/financial/operations.py`
- Modify: `nexora_app/nexora/financial/commitments.py`
- Modify: `nexora_app/nexora/financial/sources.py`
- Modify: `nexora_app/nexora/financial/remittances.py`
- Modify: `nexora_app/nexora/close/monthly_canonical.py`
- Modify: `nexora_app/nexora/nexora/doctype/nxr_monthly_close/nxr_monthly_close.json`
- Modify: `nexora_app/nexora/nexora/doctype/nxr_monthly_close/nxr_monthly_close.py`
- Test: `nexora_app/nexora/tests/test_monthly_close_contract.py`
- Test: `nexora_app/nexora/tests/test_monthly_close_canonical_integration.py`
- Test: `nexora_app/nexora/tests/test_financial_integration.py`

**Interfaces:**
- Produces: `assert_open_financial_period(*, document_date, project, source_names) -> str`.
- Consumes: `is_central_remittance_source()`, approved `NXR Monthly Close` rows, idempotent replay result.

- [ ] **Step 1: Write failing close-scope tests**

```python
def test_close_scope_requires_exactly_the_right_dimension(self):
    with self.assertRaises(frappe.ValidationError):
        self._insert_close(scope="Project", project=None)
    with self.assertRaises(frappe.ValidationError):
        self._insert_close(scope="Central Treasury", project=self.project)

def test_central_close_rejects_remittance_and_project_operation_using_central_source(self):
    self._approve_central_close("2026-08")
    with self.assertRaises(frappe.ValidationError):
        create_remittance(self._remittance_payload(source_date="2026-08-10"))
    with self.assertRaises(frappe.ValidationError):
        execute_financial_operation(self._outflow(operation_date="2026-08-11"))
```

- [ ] **Step 2: Verify RED in contract and MariaDB tests**

Expected failures: missing `scope`, central close cannot be created, and financial mutations currently succeed.

- [ ] **Step 3: Implement the canonical period guard**

```python
def assert_open_financial_period(*, document_date, project=None, source_names=()):
    value = validate_document_date(document_date, today=getdate(today()))
    if project:
        _reject_approved_close("Project", project, value)
    if any(is_central_remittance_source(name) for name in source_names):
        _reject_approved_close("Central Treasury", None, value)
    return value.isoformat()
```

Call it after cached idempotency responses are returned and before preview/locks/writes. Replace the older project-only `_closed_month` path with this function.

- [ ] **Step 4: Add replay and dual-scope tests**

Verify an operation completed before close remains replayable with the same idempotency key, while a new key is rejected; verify a project operation can be blocked independently by either its project close or the central close.

- [ ] **Step 5: Run focused and integration tests**

Run monthly-close, operational, financial, purchase-payment and contract integration modules in MariaDB CI.

- [ ] **Step 6: Commit**

```bash
git add nexora_app/nexora/financial nexora_app/nexora/close/monthly_canonical.py nexora_app/nexora/nexora/doctype/nxr_monthly_close nexora_app/nexora/tests/test_monthly_close* nexora_app/nexora/tests/test_financial_integration.py
git commit -m "fix(nexora): enforce central and project period closes"
```

### Task 4: Consolidado real y KPI de proyecto sin saldo ficticio

**Files:**
- Modify: `nexora_app/nexora/financial/central_treasury.py`
- Modify: `nexora_app/nexora/dashboard/source_query.py`
- Modify: `nexora_app/nexora/dashboard/snapshot_query.py`
- Modify: `nexora_app/nexora/dashboard/operational_query.py`
- Modify: `nexora_app/nexora/public/js/nexora_dashboard.js`
- Modify: `nexora_app/nexora/nexora/page/nexora_reports/nexora_reports.js`
- Test: `nexora_app/nexora/tests/test_central_treasury_integration.py`
- Test: `nexora_app/nexora/tests/test_dashboard_integration.py`
- Test: `nexora_app/nexora/tests/test_dashboard_contract.py`

**Interfaces:**
- Produces: `central_treasury_totals(start, end) -> dict`, response fields `cash_scope`, `project_financials`, `central_treasury`.
- Consumes: source/effect joins and `budget_snapshot_as_of()`.

- [ ] **Step 1: Write failing mathematical regression tests**

```python
def test_project_snapshot_does_not_report_negative_cash_from_central_source(self):
    self._receive_central(1000)
    self._execute_for_project(200)
    snapshot = get_executive_snapshot({"project": self.project})
    self.assertIsNone(snapshot["executive"]["cash_available_hnl"])
    self.assertEqual("project-budget", snapshot["executive"]["availability_scope"])
    self.assertGreaterEqual(snapshot["executive"]["budget_available_hnl"], 0)

def test_central_total_equals_sum_of_individual_sources(self):
    first = self._receive_central(700)
    second = self._receive_central(300)
    self._execute_source(first, 125)
    totals = central_treasury_totals(self.start, self.end)
    self.assertEqual("875.00", totals["available_hnl"])
```

- [ ] **Step 2: Run tests and verify RED**

Confirm the project snapshot currently returns a negative/partial cash value and no explicit scope.

- [ ] **Step 3: Implement account-scoped SQL aggregation**

Aggregate central totals only through remittances linked to `CENTRAL_REMITTANCE`. For a project snapshot, calculate attributed spending/reserves and budget availability, set cash availability to `None`, and expose the scope. Project source lists select remittances actually used by project but label their balance as remittance-global.

- [ ] **Step 4: Update UI labels and empty states**

Render `Saldo central disponible` only for global context and `Presupuesto disponible` for project context. Never coerce `None` to zero or display an invented currency value.

- [ ] **Step 5: Run backend, JavaScript syntax and contract tests**

Run dashboard integration in MariaDB, local contract modules, and `node --check` on both modified scripts.

- [ ] **Step 6: Commit**

```bash
git add nexora_app/nexora/financial/central_treasury.py nexora_app/nexora/dashboard nexora_app/nexora/public/js/nexora_dashboard.js nexora_app/nexora/nexora/page/nexora_reports/nexora_reports.js nexora_app/nexora/tests/test_central_treasury_integration.py nexora_app/nexora/tests/test_dashboard*
git commit -m "fix(nexora): separate central cash from project availability"
```

### Task 5: Permisos de mutación e inmutabilidad financiera

**Files:**
- Modify: `nexora_app/nexora/financial/operations.py`
- Modify: `nexora_app/nexora/financial/commitments.py`
- Modify: `nexora_app/nexora/permissions.py`
- Modify: `nexora_app/nexora/hooks.py`
- Modify: critical controllers under `nexora_app/nexora/nexora/doctype/`
- Test: `nexora_app/nexora/tests/test_security_project_scoping_contract.py`
- Test: `nexora_app/nexora/tests/test_financial_integration.py`
- Test: `nexora_app/nexora/tests/test_service_locked_permission_integration.py`

**Interfaces:**
- Produces: explicit mutation project/source authorization and financial row-permission hooks.
- Consumes: `require_project_access()`, actual source/operation/commitment documents.

- [ ] **Step 1: Write failing mutation and deletion tests**

Create two projects and a user restricted to one. Assert direct calls to create/execute/release commitments with the other project or its source raise `frappe.PermissionError`. Assert `delete(ignore_permissions=True)` fails for account, source, allocation, effect, commitment, audit, sequence and idempotency records.

- [ ] **Step 2: Verify RED against real Frappe permissions**

Run the integration modules under MariaDB; do not substitute source-text assertions for row behavior.

- [ ] **Step 3: Resolve scope from stored documents and enforce it**

Validate project access before financial preview. For execute/release, read the locked commitment project rather than trusting payload project. For allocations, ensure every source exists, is usable and is central or belongs to the authorized project.

- [ ] **Step 4: Add explicit `on_trash` guards and row permission hooks**

Use one shared immutable deletion message and per-DocType hooks that allow all-project roles while constraining project viewers to rows attributable to permitted projects. Standard REST/list access must match service access.

- [ ] **Step 5: Run security, service-lock and financial suites**

Run both local contract tests and MariaDB permission tests, including standard `frappe.get_list`/`frappe.get_doc` access as the restricted user.

- [ ] **Step 6: Commit**

```bash
git add nexora_app/nexora/financial nexora_app/nexora/permissions.py nexora_app/nexora/hooks.py nexora_app/nexora/nexora/doctype nexora_app/nexora/tests/test_security_project_scoping_contract.py nexora_app/nexora/tests/test_financial_integration.py nexora_app/nexora/tests/test_service_locked_permission_integration.py
git commit -m "fix(nexora): enforce financial scope and immutability"
```

### Task 6: Contratos y compras consumen las reglas canónicas

**Files:**
- Modify: `nexora_app/nexora/contracts/service.py`
- Modify: `nexora_app/nexora/purchases/financial_bridge.py`
- Test: `nexora_app/nexora/tests/test_contract_integration.py`
- Test: `nexora_app/nexora/tests/test_purchase_payment_integration.py`
- Test: `nexora_app/nexora/tests/test_contract_core.py`

**Interfaces:**
- Consumes: `rate()`, `assert_open_financial_period()` through canonical execution, central fund allocations.
- Produces: precise HNL contract amounts and period-safe purchase/contract payments.

- [ ] **Step 1: Write failing precision and closed-period tests**

```python
def test_contract_rate_is_not_rounded_before_payment(self):
    contract = self._contract(exchange_rate="24.123456789")
    payment = self._pay(contract, amount="100.00")
    self.assertEqual("2412.35", frappe.db.get_value("NXR Operation", payment["operation"], "amount"))

def test_purchase_payment_rejects_closed_central_period(self):
    self._approve_central_close(self.month)
    with self.assertRaises(frappe.ValidationError):
        pay_purchase_order(self._payment_payload(operation_date=self.closed_date))
```

- [ ] **Step 2: Verify RED**

Confirm the precision test observes `2412.00` and the payment currently reaches canonical execution without central close rejection.

- [ ] **Step 3: Replace premature rate rounding and route dates canonically**

Use `money(money(amount) * rate(contract.exchange_rate))`. Do not add module-local close queries; pass the real operation date and allocations to canonical execution.

- [ ] **Step 4: Run contract, purchase, budget and commitment integration tests**

Include positive payment, excessive payment, insufficient commitment, idempotent replay and both close scopes.

- [ ] **Step 5: Commit**

```bash
git add nexora_app/nexora/contracts/service.py nexora_app/nexora/purchases/financial_bridge.py nexora_app/nexora/tests/test_contract_integration.py nexora_app/nexora/tests/test_purchase_payment_integration.py nexora_app/nexora/tests/test_contract_core.py
git commit -m "fix(nexora): preserve precision and close safety in payments"
```

### Task 7: Remittance UI and E2E follow the real model

**Files:**
- Modify: `nexora_app/nexora/public/js/nexora_finance.js`
- Modify: `nexora_app/nexora/public/js/nexora_guided_operations.js`
- Modify: `scripts/nexora_browser_smoke.mjs`
- Test: `nexora_app/nexora/tests/test_financial_ui_contract.py`
- Test: `nexora_app/nexora/tests/test_browser_acceptance_contract.py`

**Interfaces:**
- Consumes: remittance API result with `financial_account`, `fund_source`, `remittance` and real totals.
- Produces: one-account remittance form, individual trace display and browser acceptance on desktop/tablet/iPhone/PWA.

- [ ] **Step 1: Write failing UI behavior tests**

Assert the form has no destination repeater, shows the central account as server-resolved read-only context, does not submit account/project overrides, and renders returned remittance/source identifiers.

- [ ] **Step 2: Verify RED**

Run local contract tests and confirm the smoke still waits for `.nxr-remittance-add-destination`.

- [ ] **Step 3: Update UI and smoke selectors**

Exercise two remittances and assert the API returns one shared account plus two distinct sources. Exercise a commitment/execution from one source and verify global versus individual balances from real responses.

- [ ] **Step 4: Run syntax and browser contract tests**

Run `node --check` and the local unittest modules. Let the GitHub Frappe browser job provide the real multi-device evidence.

- [ ] **Step 5: Commit**

```bash
git add nexora_app/nexora/public/js scripts/nexora_browser_smoke.mjs nexora_app/nexora/tests/test_financial_ui_contract.py nexora_app/nexora/tests/test_browser_acceptance_contract.py
git commit -m "fix(nexora): align remittance UX with central treasury"
```

### Task 8: P0 verification, documentation and publication

**Files:**
- Modify: `EXECUTION_STATE.md`
- Modify: `PLAN_MAESTRO.md` only where the existing Phase 3 status must reflect verified evidence.
- Modify: `README.md` only for statements contradicted by the implemented architecture.
- Regenerate: `docs/architecture/file_inventory.json`

**Interfaces:**
- Consumes: all P0 implementation commits and CI evidence.
- Produces: auditable block record, green branch checks and verified remote SHA.

- [ ] **Step 1: Run complete local verification**

```bash
cd nexora_app
/opt/homebrew/bin/python3.11 -m compileall nexora scripts
/opt/homebrew/bin/python3.11 -m unittest discover -s nexora/tests -p 'test_*contract.py' -v
```

Run repository validators, Ruff format/check, Semgrep/secrets commands from workflows, JavaScript syntax checks and `git diff --check`. Run every available MariaDB/bench suite in the environment; otherwise require the same SHA's GitHub jobs.

- [ ] **Step 2: Regenerate governed inventory and review the full diff**

Run: `/opt/homebrew/bin/python3.11 scripts/generate_file_inventory.py`

Inspect `git diff --stat`, `git diff`, and `git status --short`. Confirm no unrelated or generated secret files entered the change.

- [ ] **Step 3: Update execution evidence without claiming unrun checks**

Record problem, files, decisions, exact commands/results, commits, branch SHA, remaining limitations and next P1 action. Use `IMPLEMENTADO Y VALIDADO` only after the branch CI and required runtime/E2E checks pass.

- [ ] **Step 4: Commit and push the coherent P0 evidence block**

```bash
git add EXECUTION_STATE.md PLAN_MAESTRO.md README.md docs
git commit -m "docs(nexora): record verified central treasury block"
git push origin nexora/central-fund-contract-final-20260822-140205
```

- [ ] **Step 5: Verify branch and main publication**

Compare local SHA with `git ls-remote`. Wait for every PR #344 check. Fix all failures on the same branch. When green, merge the single PR into `main` using the non-destructive GitHub flow, fetch, and verify `origin/main` contains every P0 commit.

- [ ] **Step 6: Continue immediately with P1**

Create the next focused spec/plan from the verified current state for model/API consistency across contracts, purchases, inventory, projects, budgets, reports and permissions; do not repeat the closed P0 audit.
