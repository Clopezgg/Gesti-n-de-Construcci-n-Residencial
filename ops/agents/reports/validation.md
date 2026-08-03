# Validation Report

## Fecha
2026-08-03T16:57:18+00:00

## Python version
Python 3.12.1

## Node version
v24.14.0

## npm version
11.9.0

## Pytest collection
============================= test session starts ==============================
platform linux -- Python 3.12.1, pytest-9.0.2, pluggy-1.6.0
rootdir: /workspaces/Gesti-n-de-Construcci-n-Residencial/nexora_app
configfile: pyproject.toml
plugins: anyio-4.12.1
collected 507 items / 19 errors

<Dir nexora_app>
  <Package nexora>
    <Package tests>
      <Module test_analytics_history_contract.py>
        <UnitTestCase TestAnalyticsHistoryContract>
          <TestCaseFunction test_cancelled_sources_are_not_left_as_unreconciled_alerts>
          <TestCaseFunction test_expense_analytics_uses_canonical_effect_ledger>
          <TestCaseFunction test_historical_source_pages_exclude_future_sources>
          <TestCaseFunction test_projection_does_not_double_subtract_reserved_obligations>
          <TestCaseFunction test_reversals_are_reported_once_not_reclassified_as_normal_flow>
      <Module test_app_contract.py>
        <UnitTestCase TestNexoraAppContract>
          <TestCaseFunction test_apps_registry_change_invalidates_frappe_module_cache>
          <TestCaseFunction test_apps_registry_is_idempotent_without_trailing_newline>
          <TestCaseFunction test_catalog_seed_runs_only_after_doctype_sync>
          <TestCaseFunction test_daily_income_and_expense_flows_are_simple_and_canonical>
          <TestCaseFunction test_doctype_package_and_module_declarations_are_installable>
          <TestCaseFunction test_identity_and_dependency_are_explicit>
          <TestCaseFunction test_month_key_accepts_date_datetime_and_iso_text>
          <TestCaseFunction test_month_key_rejects_invalid_text_with_domain_error>
          <TestCaseFunction test_new_app_has_no_legacy_import_or_visible_brand>
          <TestCaseFunction test_required_scaffold_exists>
          <TestCaseFunction test_roles_and_workspace_are_consistent>
          <TestCaseFunction test_visible_vocabulary_and_feedback_are_shared>
      <Module test_browser_acceptance_contract.py>
        <UnitTestCase TestBrowserAcceptanceContract>
          <TestCaseFunction test_browser_network_calls_and_process_have_explicit_deadlines>
          <TestCaseFunction test_browser_suite_calculates_but_does_not_persist_a_weekly_close>
          <TestCaseFunction test_browser_suite_covers_executive_surfaces>
          <TestCaseFunction test_browser_suite_executes_search_correction_and_idempotent_replay>
          <TestCaseFunction test_dashboard_gate_requires_context_actions_and_clean_console>
          <TestCaseFunction test_global_context_observer_is_idempotent_and_frame_coalesced>
          <TestCaseFunction test_global_navigation_never_reuses_a_page_product_shell>
          <TestCaseFunction test_guided_review_waits_for_stable_network_and_idempotent_rendering>
          <TestCaseFunction test_quick_actions_use_the_current_single_handler_contract>
          <TestCaseFunction test_route_wait_uses_rendered_state_and_publishes_diagnostics>
          <TestCaseFunction test_runtime_image_does_not_patch_application_source>
      <Module test_budget_as_of_contract.py>
        <UnitTestCase TestBudgetAsOfContract>
          <TestCaseFunction test_budget_snapshot_uses_the_applicable_version_and_ledger_effects>
          <TestCaseFunction test_close_helper_can_return_summary_without_duplicate_financial_logic>
          <TestCaseFunction test_filtered_snapshot_builds_historical_budget_and_pending_values_directly>
      <Module test_budget_contract.py>
        <UnitTestCase TestBudgetContract>
          <TestCaseFunction test_budget_controller_enforces_boundary>
          <TestCaseFunction test_budget_core_exists>
          <TestCaseFunction test_budget_doctype_is_defined>
          <TestCaseFunction test_budget_line_has_balance_fields>
          <TestCaseFunction test_budget_line_is_table>
          <TestCaseFunction test_budget_module_exists>
          <TestCaseFunction test_budget_service_exists>
      <Module test_budget_core.py>
        <UnitTestCase TestBudgetCore>
          <TestCaseFunction test_active_can_be_amended>
          <TestCaseFunction test_active_can_be_closed>
          <TestCaseFunction test_all_states_have_transitions>
          <TestCaseFunction test_compute_budget_totals>
          <TestCaseFunction test_compute_line_balances>
          <TestCaseFunction test_compute_line_balances_fully_consumed>
          <TestCaseFunction test_compute_line_balances_zero>
          <TestCaseFunction test_draft_can_be_activated>
          <TestCaseFunction test_draft_can_be_cancelled>
          <TestCaseFunction test_invalid_transition_raises>
          <TestCaseFunction test_overspend_at_exact_boundary>
          <TestCaseFunction test_overspend_raises>
          <TestCaseFunction test_terminal_states_have_no_outgoing>
          <TestCaseFunction test_unknown_state_is_rejected>
          <TestCaseFunction test_valid_commitment_exact_available>
          <TestCaseFunction test_valid_commitment_passes>
          <TestCaseFunction test_validate_line_amount_negative_raises>
          <TestCaseFunction test_validate_line_amount_positive>
          <TestCaseFunction test_validate_line_amount_zero_raises>
      <Module test_build_info_contract.py>
        <UnitTestCase TestBuildInfoContract>
          <TestCaseFunction test_build_info_endpoint_requires_authentication>
      <Module test_canonical_report_views_contract.py>
        <UnitTestCase TestCanonicalReportViewsContract>
          <TestCaseFunction test_public_report_methods_are_overridden_by_filtered_views>
          <TestCaseFunction test_views_use_filtered_snapshot_and_server_permissions>
      <Module test_close_contract.py>
        <UnitTestCase TestCloseContract>
          <TestCaseFunction test_close_core_exists>
          <TestCaseFunction test_close_module_exists>
          <TestCaseFunction test_close_service_exists>
          <TestCaseFunction test_monthly_close_controller_enforces_boundary>
          <TestCaseFunction test_monthly_close_doctype_is_defined>
          <TestCaseFunction test_monthly_close_has_status_field>
      <Module test_close_core.py>
        <UnitTestCase TestCloseCore>
          <TestCaseFunction test_approved_is_terminal>
          <TestCaseFunction test_cancelled_is_terminal>
          <TestCaseFunction test_draft_to_cancelled>
          <TestCaseFunction test_draft_to_in_review>
          <TestCaseFunction test_in_review_to_approved>
          <TestCaseFunction test_in_review_to_rejected>
          <TestCaseFunction test_invalid_transition_raises>
          <TestCaseFunction test_reconcile_passes_with_empty_dicts>
          <TestCaseFunction test_reconcile_passes_with_equal_values>
          <TestCaseFunction test_reconcile_raises_with_mismatched_values>
          <TestCaseFunction test_reconcile_raises_with_missing_key>
          <TestCaseFunction test_rejected_to_draft>
          <TestCaseFunction test_terminal_states_have_no_outgoing>
          <TestCaseFunction test_unknown_state_raises>
      <Module test_contract_contract.py>
        <UnitTestCase TestContractContract>
          <TestCaseFunction test_controllers_enforce_service_only_immutability>
          <TestCaseFunction test_doctypes_are_real_and_reuse_entity_finance_and_evidence>
          <TestCaseFunction test_permissions_page_workspace_and_hooks_are_connected>
          <TestCaseFunction test_service_exposes_transactional_contract_lifecycle>
          <TestCaseFunction test_workflow_executes_contract_runtime_and_concurrency>
      <Module test_contract_core.py>
        <UnitTestCase TestContractCore>
          <TestCaseFunction test_amendment_cannot_reduce_below_execution>
          <TestCaseFunction test_amendment_types_enforce_signs_dates_and_status>
          <TestCaseFunction test_available_and_money_are_exact>
          <TestCaseFunction test_estimate_amounts_concile_manual_deductions>
          <TestCaseFunction test_line_amounts_reject_duplicates_and_mismatch>
          <TestCaseFunction test_line_amounts_separate_labor_and_materials>
          <TestCaseFunction test_transitions_and_periods_are_strict>
      <Module test_dashboard_compensation_contract.py>
        <UnitTestCase TestDashboardCompensationContract>
          <TestCaseFunction test_dashboard_exposes_net_income_and_preserves_reversal_audit>
          <TestCaseFunction test_dashboard_keeps_certified_identity_and_refresh_contract>
      <Module test_dashboard_contract.py>
        <UnitTestCase TestDashboardContract>
          <TestCaseFunction test_dashboard_and_search_pages_exist>
          <TestCaseFunction test_dashboard_context_is_consumed_by_related_pages>
          <TestCaseFunction test_dashboard_exposes_direct_income_and_expense_actions>
          <TestCaseFunction test_dashboard_handles_loading_failures_with_actionable_copy>
          <TestCaseFunction test_dashboard_integrates_complete_operational_summary>
          <TestCaseFunction test_dashboard_is_the_canonical_desk_home>
          <TestCaseFunction test_dashboard_keeps_project_control_reference>
          <TestCaseFunction test_dashboard_module_and_service_exist>
          <TestCaseFunction test_dashboard_service_reconciles_against_canonical_effect_ledger>
          <TestCaseFunction test_dashboard_snapshot_uses_native_deadline_instead_of_frappe_thenable>
          <TestCaseFunction test_dashboard_styles_cover_mobile_composition>
          <TestCaseFunction test_dashboard_translates_technical_operation_values>
          <TestCaseFunction test_dashboard_uses_official_product_identity>
          <TestCaseFunction test_financial_report_sends_resolved_payload>
          <TestCaseFunction test_global_navigation_uses_canonical_nexora_pages>
          <TestCaseFunction test_service_has_whitelisted_permission_checked_functions>
          <TestCaseFunction test_workspace_has_dashboard_and_search_shortcuts>
      <Module test_dashboard_email_regressions.py>
        <UnitTestCase TestDashboardFundsLayoutContract>
          <TestCaseFunction test_funds_fix_does_not_hide_or_truncate_the_card>
          <TestCaseFunction test_funds_list_overrides_legacy_balance_grid>
          <TestCaseFunction test_global_context_and_decision_dashboard_are_connected>
        <UnitTestCase TestGenericEmailPromptPolicy>
          <TestCaseFunction test_boot_hook_changes_no_email_or_user_records>
          <TestCaseFunction test_boot_hook_preserves_real_email_password_validation>
          <TestCaseFunction test_boot_hook_suppresses_only_known_generic_account>
          <TestCaseFunction test_generic_pending_email_removes_only_current_user>
          <TestCaseFunction test_real_or_mixed_pending_email_is_never_suppressed>
        <UnitTestCase TestNexoraActiveContext>
          <TestCaseFunction test_context_change_persists_only_after_project_permission>
          <TestCaseFunction test_invalid_period_is_rejected_without_persisting>
          <TestCaseFunction test_restricted_user_cannot_clear_required_project>
          <TestCaseFunction test_saved_project_period_user_and_role_are_returned>
      <Module test_dashboard_net_income.py>
        <UnitTestCase TestDashboardNetIncome>
          <TestCaseFunction test_net_income_subtracts_cancelled_received_effects>
          <TestCaseFunction test_period_can_report_negative_net_income_when_cancellation_is_later>
          <TestCaseFunction test_unrelated_reversals_are_not_passed_as_income_reversals>
      <Module test_dashboard_net_income_contract.py>
        <UnitTestCase TestDashboardNetIncomeContract>
          <TestCaseFunction test_backend_deducts_only_reversals_linked_to_received_effects>
          <TestCaseFunction test_backend_exposes_bounded_ledger_presentation_metadata>
          <TestCaseFunction test_dashboard_preserves_correction_alert_and_audit_link>
          <TestCaseFunction test_dashboard_shows_net_income_without_reversal_metric_card>
          <TestCaseFunction test_dashboard_uses_financial_business_colors>
          <TestCaseFunction test_recent_operations_use_human_labels_and_strike_voided_amounts>
      <Module test_directory_contract.py>
        <UnitTestCase TestDirectoryContract>
          <TestCaseFunction test_all_directory_models_are_real_nexora_doctypes_with_controllers>
          <TestCaseFunction test_entity_and_related_records_are_service_write_only_and_non_deletable>
          <TestCaseFunction test_page_and_workspace_are_connected_to_real_services>
          <TestCaseFunction test_permanent_workflows_include_directory_runtime_and_pure_tests>
          <TestCaseFunction test_permissions_are_enforced_by_action_and_sensitive_read_is_restricted>
          <TestCaseFunction test_public_api_exports_complete_server_side_directory>
          <TestCaseFunction test_sensitive_child_values_are_password_fields_and_not_exportable>
          <TestCaseFunction test_service_and_page_parse_without_syntax_errors>
      <Module test_directory_core.py>
        <UnitTestCase TestDirectoryCore>
          <TestCaseFunction test_consolidation_cycle_is_rejected>
          <TestCaseFunction test_contacts_normalize_email_phone_and_whatsapp>
          <TestCaseFunction test_duplicate_score_prioritizes_exact_identifiers_and_users>
          <TestCaseFunction test_entity_role_and_compliance_transitions>
          <TestCaseFunction test_fingerprints_are_namespaced_and_deterministic>
          <TestCaseFunction test_identifiers_normalize_rtn_passport_and_email>
          <TestCaseFunction test_masks_never_return_full_sensitive_value>
          <TestCaseFunction test_names_are_accent_insensitive_and_whitespace_stable>
          <TestCaseFunction test_period_validation_and_overlap_are_inclusive>
          <TestCaseFunction test_unique_nonempty_ignores_blank_values_but_rejects_duplicates>
      <Module test_evidence_contract.py>
        <UnitTestCase TestEvidenceContract>
          <TestCaseFunction test_evidence_doctype_is_private_immutable_and_non_deletable>
          <TestCaseFunction test_evidence_services_are_exported_and_ui_connected>
          <TestCaseFunction test_executed_operation_has_state_and_field_immutability>
          <TestCaseFunction test_main_is_the_permanent_ci_target>
          <TestCaseFunction test_policy_requires_canonical_whatsapp_record_for_special_authorization>
      <Module test_evidence_core.py>
        <UnitTestCase TestEvidenceCore>
          <TestCaseFunction test_cash_threshold_is_exact>
          <TestCaseFunction test_deposit_and_transfer_always_require_evidence>
          <TestCaseFunction test_evidence_state_machine_rejects_regression>
          <TestCaseFunction test_negative_amount_is_rejected>
          <TestCaseFunction test_profile_requirement_overrides_optional_cash>
          <TestCaseFunction test_sha256_is_deterministic>
          <TestCaseFunction test_special_category_requires_external_authorization>
      <Module test_executive_analytics.py>
        <UnitTestCase TestExecutiveAnalytics>
          <TestCaseFunction test_as_of_balances_separate_opening_closing_and_current>
          <TestCaseFunction test_internal_transfer_does_not_become_expense>
          <TestCaseFunction test_payload_hash_is_order_independent>
          <TestCaseFunction test_period_rejects_inverted_dates>
          <TestCaseFunction test_reversal_is_explicit_and_preserves_received_history>
      <Module test_executive_improvements_contract.py>
        <UnitTestCase TestExecutiveImprovementsContract>
          <TestCaseFunction test_analytics_uses_effect_ledger_and_pagination>
          <TestCaseFunction test_dashboard_keeps_certified_contract_and_premium_panels>
          <TestCaseFunction test_exports_are_server_authorized_excel_and_pdf>
          <TestCaseFunction test_weekly_close_is_canonical_and_immutable>
          <TestCaseFunction test_workspace_exposes_reporting_and_closing>
      <Module test_expense_filter_contract.py>
        <UnitTestCase TestExpenseFilterContract>
          <TestCaseFunction test_endpoint_and_export_share_the_same_fi02_query>
          <TestCaseFunction test_fi02_filters_the_effect_rows_before_aggregation>
          <TestCaseFunction test_query_enforces_financial_details_and_project_scope>
      <Module test_filtered_snapshot_contract.py>
        <UnitTestCase TestFilteredSnapshotContract>
          <TestCaseFunction test_contract_totals_apply_the_same_co01_filters>
          <TestCaseFunction test_operational_sections_have_explicit_limits>
          <TestCaseFunction test_pending_query_is_ledger_based_paginated_and_aggregates_alerts>
          <TestCaseFunction test_snapshot_composes_bounded_canonical_queries_without_eager_full_summary>
          <TestCaseFunction test_source_contract_budget_and_pending_kpis_respect_filters>
          <TestCaseFunction test_whitelisted_snapshot_is_replaced_by_filter_adapter>
      <Module test_financial_core.py>
        <UnitTestCase TestFinancialCore>
          <TestCaseFunction test_01_create_hnl_remittance>
          <TestCaseFunction test_02_foreign_currency_conversion>
          <TestCaseFunction test_03_cash_does_not_require_bank>
          <TestCaseFunction test_04_transfer_requires_reference>
          <TestCaseFunction test_05_multisource_outflow>
          <TestCaseFunction test_06_reject_allocation_mismatch>
          <TestCaseFunction test_07_reject_overdraw>
          <TestCaseFunction test_08_concurrent_execution_serializes_source>
          <TestCaseFunction test_09_same_key_same_payload_returns_same_result>
          <TestCaseFunction test_10_same_key_different_payload_is_rejected>
          <TestCaseFunction test_11_failure_on_second_allocation_rolls_back_all_sources>
          <TestCaseFunction test_12_commitment_reserves_without_executing>
          <TestCaseFunction test_13_commitment_execution_does_not_double_consume_available>
          <TestCaseFunction test_14_release_commitment_restores_available>
          <TestCaseFunction test_15_reclassification_does_not_restore_funds>
          <TestCaseFunction test_16_real_return_restores_only_proven_amount>
          <TestCaseFunction test_17_all_document_numbers_have_twelve_digits>
      <Module test_financial_model_contract.py>
        <UnitTestCase TestFinancialModelContract>
          <TestCaseFunction test_all_canonical_doctypes_exist>
          <TestCaseFunction test_document_sequence_is_unique_and_read_only>
          <TestCaseFunction test_document_substitution_zero_value_is_supported_by_controller>
          <TestCaseFunction test_mariadb_counter_is_native_auto_increment>
          <TestCaseFunction test_no_legacy_inventory_ledger_is_written>
          <TestCaseFunction test_single_canonical_effect_ledger_is_preserved>
          <TestCaseFunction test_technical_operation_types_are_read_only_and_reference_fields_exist>
      <Module test_financial_service_contract.py>
        <UnitTestCase TestFinancialServiceContract>
          <TestCaseFunction test_canonical_documents_require_orchestrator_context>
          <TestCaseFunction test_idempotency_payload_conflict_is_rejected>
          <TestCaseFunction test_no_legacy_ledger_write_and_no_partial_commit>
          <TestCaseFunction test_permissions_are_server_side_and_auditor_cannot_execute>
          <TestCaseFunction test_reference_metadata_and_source_relationship_are_persisted>
          <TestCaseFunction test_server_services_are_post_only_and_permission_guarded>
          <TestCaseFunction test_stable_locking_and_savepoint_rollback_are_explicit>
      <Module test_financial_ui_contract.py>
        <UnitTestCase TestFinancialUIContract>
          <TestCaseFunction test_dashboard_launch_context_is_consumed>
          <TestCaseFunction test_execute_is_disabled_until_server_preview>
          <TestCaseFunction test_operation_type_is_catalog_derived_and_profile_drives_fields>
          <TestCaseFunction test_page_calls_real_preview_execute_and_source_services>
          <TestCaseFunction test_workspace_links_to_real_page>
      <Module test_guided_account_progressive_contract.py>
        <UnitTestCase TestGuidedAccountProgressiveContract>
          <TestCaseFunction test_assets_are_loaded_after_canonical_operation_engine>
          <TestCaseFunction test_common_expense_does_not_require_segregated_actors>
          <TestCaseFunction test_human_account_choice_hides_internal_modes>
          <TestCaseFunction test_model_rejects_incompatible_accounts_and_maps_human_choice>
          <TestCaseFunction test_progressive_flow_uses_four_stages_and_same_canonical_buttons>
          <TestCaseFunction test_responsive_and_accessibility_contract>
          <TestCaseFunction test_shared_account_component_requests_server_compatibility_filters>
      <Module test_guided_operation_correction_contract.py>
        <UnitTestCase TestGuidedOperationCorrectionContract>
          <TestCaseFunction test_controlled_flags_do_not_open_free_form_edits>
          <TestCaseFunction test_dashboard_header_and_rows_are_repaired_after_base_rerender>
          <TestCaseFunction test_evidence_is_optional_and_amount_change_is_guarded>
          <TestCaseFunction test_service_is_server_backed_and_exported>
          <TestCaseFunction test_ui_starts_with_document_number_and_loads_editable_data>
      <Module test_integrations_contract.py>
        <UnitTestCase TestIntegrationsContract>
          <TestCaseFunction test_integration_controller_enforces_boundary>
          <TestCaseFunction test_integration_doctype_is_defined>
          <TestCaseFunction test_integration_log_has_level_field>
          <TestCaseFunction test_integration_log_is_table>
          <TestCaseFunction test_integrations_core_exists>
          <TestCaseFunction test_integrations_module_exists>
          <TestCaseFunction test_integrations_service_exists>
      <Module test_integrations_core.py>
        <UnitTestCase TestIntegrationsCore>
          <TestCaseFunction test_integration_statuses_are_correct>
          <TestCaseFunction test_redact_credentials_hides_api_key>
          <TestCaseFunction test_redact_credentials_hides_password>
          <TestCaseFunction test_redact_credentials_hides_secret>
          <TestCaseFunction test_redact_credentials_hides_token>
          <TestCaseFunction test_redact_credentials_passes_clean_text>
          <TestCaseFunction test_validate_endpoint_invalid_empty_raises>
          <TestCaseFunction test_validate_endpoint_invalid_no_scheme_raises>
          <TestCaseFunction test_validate_endpoint_invalid_random_text_raises>
          <TestCaseFunction test_validate_endpoint_valid_http>
          <TestCaseFunction test_validate_endpoint_valid_https>
      <Module test_inventory_contract.py>
        <UnitTestCase TestInventoryContract>
          <TestCaseFunction test_inventory_core_exists>
          <TestCaseFunction test_inventory_module_exists>
          <TestCaseFunction test_inventory_service_exists>
          <TestCaseFunction test_stock_transaction_controller_enforces_boundary>
          <TestCaseFunction test_stock_transaction_doctype_is_defined>
          <TestCaseFunction test_stock_transaction_line_has_tracking_fields>
          <TestCaseFunction test_stock_transaction_line_is_table>
          <TestCaseFunction test_warehouse_controller_enforces_boundary>
          <TestCaseFunction test_warehouse_doctype_is_defined>
      <Module test_inventory_core.py>
        <UnitTestCase TestInventoryCore>
          <TestCaseFunction test_all_states_have_transitions>
          <TestCaseFunction test_cancelled_is_terminal>
          <TestCaseFunction test_completed_is_terminal>
          <TestCaseFunction test_draft_can_be_cancelled>
          <TestCaseFunction test_draft_can_be_completed>
          <TestCaseFunction test_invalid_money_is_rejected>
          <TestCaseFunction test_money_rounds_to_two_decimals>
          <TestCaseFunction test_quantity_rounds_to_six_decimals>
          <TestCaseFunction test_stock_balance_add_and_remove>
          <TestCaseFunction test_stock_balance_insufficient_raises>
          <TestCaseFunction test_stock_balance_returns_zero_for_missing>
          <TestCaseFunction test_stock_transaction_types_are_defined>
          <TestCaseFunction test_unknown_state_is_rejected>
          <TestCaseFunction test_validate_item_balance_allows_sufficient>
          <TestCaseFunction test_validate_item_balance_blocks_negative>
      <Module test_ledger_contract.py>
        <UnitTestCase TestCentralLedgerContract>
          <TestCaseFunction test_catalog_adapter_uses_existing_transactional_kernel>
          <TestCaseFunction test_catalog_doctypes_and_analytic_dimensions_exist>
          <TestCaseFunction test_internal_transfer_uses_allocation_roles_and_no_second_ledger>
          <TestCaseFunction test_referenced_corrections_and_advance_guards_are_server_side>
          <TestCaseFunction test_ui_calls_real_central_ledger_services>
      <Module test_ledger_core.py>
        <UnitTestCase TestCentralLedgerCatalog>
          <TestCaseFunction test_advance_disbursement_requires_responsible_date_and_due_date>
          <TestCaseFunction test_advance_settlement_recognizes_cost_without_consuming_funds>
          <TestCaseFunction test_catalog_covers_required_real_operation_families>
          <TestCaseFunction test_cost_center_divisions_must_sum_exactly>
          <TestCaseFunction test_document_substitution_requires_zero_amount_and_evidence>
          <TestCaseFunction test_internal_transfer_is_net_zero_and_uses_distinct_destination>
          <TestCaseFunction test_maximum_account_reduces_funds_and_increases_savings_not_cost>
          <TestCaseFunction test_other_project_records_investment_on_target_project>
          <TestCaseFunction test_reclassification_is_net_zero_and_has_no_funds>
          <TestCaseFunction test_reversal_without_cash_derives_dimensions_and_never_changes_funds>
          <TestCaseFunction test_special_payment_requires_authorizer_method_date_and_reference>
      <Module test_notifications_contract.py>
        <UnitTestCase TestNotificationsContract>
          <TestCaseFunction test_notification_controller_enforces_boundary>
          <TestCaseFunction test_notification_core_exists>
          <TestCaseFunction test_notification_doctype_is_defined>
          <TestCaseFunction test_notification_module_exists>
          <TestCaseFunction test_notification_preference_has_user_field>
          <TestCaseFunction test_notification_preference_is_table>
          <TestCaseFunction test_notification_service_exists>
      <Module test_notifications_core.py>
        <UnitTestCase TestNotificationsCore>
          <TestCaseFunction test_notification_channels_are_known>
          <TestCaseFunction test_notification_priorities_are_known>
          <TestCaseFunction test_render_template_multiple>
          <TestCaseFunction test_render_template_no_variables>
          <TestCaseFunction test_render_template_simple>
          <TestCaseFunction test_validate_channel_empty_raises>
          <TestCaseFunction test_validate_channel_invalid_raises>
          <TestCaseFunction test_validate_channel_valid_email>
          <TestCaseFunction test_validate_channel_valid_inbox>
          <TestCaseFunction test_validate_channel_valid_pwa>
          <TestCaseFunction test_validate_priority_invalid_raises>
          <TestCaseFunction test_validate_priority_valid_critical>
          <TestCaseFunction test_validate_priority_valid_high>
          <TestCaseFunction test_validate_priority_valid_low>
          <TestCaseFunction test_validate_priority_valid_normal>
      <Module test_operational_console_contract.py>
        <UnitTestCase TestOperationalConsoleContract>
          <TestCaseFunction test_account_selection_is_human_visible_and_server_safe>
          <TestCaseFunction test_accounts_and_operation_codes_are_canonical_service_records>
          <TestCaseFunction test_compensating_operation_updates_only_the_original_status>
          <TestCaseFunction test_dashboard_routes_daily_actions_and_compacts_cards>
          <TestCaseFunction test_income_and_expense_entry_points_use_single_operational_engine>
          <TestCaseFunction test_numeric_movement_console_is_real_and_server_backed>
          <TestCaseFunction test_page_and_assets_are_registered>
          <TestCaseFunction test_progressive_layout_hides_internal_tabs_but_preserves_canonical_model>
          <TestCaseFunction test_server_preserves_audit_and_never_physically_deletes_posted_operations>
      <Module test_operational_dates.py>
        <UnitTestCase TestOperationalDates>
          <TestCaseFunction test_correction_cannot_precede_original_document>
          <TestCaseFunction test_future_date_is_rejected>
          <TestCaseFunction test_historical_document_date_is_preserved>
          <TestCaseFunction test_missing_date_uses_only_explicit_fallback>
      <Module test_order_contract.py>
        <Class TestPurchaseOrderContract>
          <Function test_order_state_machine_is_defined>
          <Function test_order_doctype_is_defined>
          <Function test_order_line_doctype_is_defined>
          <Function test_order_controller_enforces_boundary>
          <Function test_order_service_exposes_lifecycle>
          <Function test_order_service_has_whitelist_decorators>
          <Function test_order_doctype_has_tax_and_discount_fields>
      <Module test_order_core.py>
        <UnitTestCase TestPurchaseOrderCore>
          <TestCaseFunction test_approved_can_be_sent>
          <TestCaseFunction test_cancelled_is_terminal>
          <TestCaseFunction test_completed_is_terminal>
          <TestCaseFunction test_confirmed_can_be_approved>
          <TestCaseFunction test_direct_approval_is_rejected>
          <TestCaseFunction test_draft_can_be_cancelled>
          <TestCaseFunction test_draft_can_be_confirmed>
          <TestCaseFunction test_empty_lines_are_rejected>
          <TestCaseFunction test_line_amounts_are_exact>
          <TestCaseFunction test_line_amounts_with_charge>
          <TestCaseFunction test_line_amounts_with_discount>
          <TestCaseFunction test_negative_net_amount_is_rejected>
          <TestCaseFunction test_negative_quantity_is_rejected>
          <TestCaseFunction test_negative_unit_rate_is_rejected>
          <TestCaseFunction test_sent_can_be_completed>
          <TestCaseFunction test_tolerance_custom_range>
          <TestCaseFunction test_tolerance_default_range>
      <Module test_predeploy_certification_contract.py>
        <UnitTestCase TestPredeployCertificationContract>
          <TestCaseFunction test_browser_smoke_executes_guided_income_and_expense>
          <TestCaseFunction test_clean_install_mariadb_browser_and_pwa_are_permanent>
          <TestCaseFunction test_every_main_head_runs_every_permanent_certification_gate>
          <TestCaseFunction test_quality_workflow_runs_precommit_twice_semgrep_and_secret_scan>
          <TestCaseFunction test_receipt_requires_every_mandatory_gate>
      <Module test_progress_contract.py>
        <UnitTestCase TestProgressContract>
          <TestCaseFunction test_progress_core_exists>
          <TestCaseFunction test_progress_module_exists>
          <TestCaseFunction test_progress_record_controller_enforces_boundary>
          <TestCaseFunction test_progress_record_doctype_is_defined>
          <TestCaseFunction test_progress_service_exists>
          <TestCaseFunction test_quality_check_controller_enforces_boundary>
          <TestCaseFunction test_quality_check_doctype_is_defined>
      <Module test_progress_core.py>
        <UnitTestCase TestProgressCore>
          <TestCaseFunction test_all_states_have_transitions>
          <TestCaseFunction test_approved_can_be_corrected>
          <TestCaseFunction test_cancelled_has_no_outgoing>
          <TestCaseFunction test_corrected_can_be_approved>
          <TestCaseFunction test_draft_can_be_cancelled>
          <TestCaseFunction test_draft_can_be_submitted>
          <TestCaseFunction test_invalid_direct_approval_raises>
          <TestCaseFunction test_invalid_transition_raises>
          <TestCaseFunction test_money_invalid_raises>
          <TestCaseFunction test_money_negative>
          <TestCaseFunction test_money_rounds_half_down>
          <TestCaseFunction test_money_rounds_half_up>
          <TestCaseFunction test_money_zero>
          <TestCaseFunction test_progress_percent_fifty>
          <TestCaseFunction test_progress_percent_invalid_raises>
          <TestCaseFunction test_progress_percent_negative_raises>
          <TestCaseFunction test_progress_percent_one_hundred>
          <TestCaseFunction test_progress_percent_over_one_hundred_raises>
          <TestCaseFunction test_progress_percent_zero>
          <TestCaseFunction test_rejected_can_be_corrected>
          <TestCaseFunction test_submitted_can_be_approved>
          <TestCaseFunction test_submitted_can_be_rejected>
          <TestCaseFunction test_terminal_states_contains_cancelled>
          <TestCaseFunction test_unknown_state_is_rejected>
      <Module test_purchase_contract.py>
        <UnitTestCase TestPurchaseContract>
          <TestCaseFunction test_controller_and_permissions_enforce_server_boundary>
          <TestCaseFunction test_financial_workflow_executes_purchase_runtime>
          <TestCaseFunction test_purchase_request_reuses_canonical_financial_dimensions>
          <TestCaseFunction test_purchase_request_service_is_controlled_and_audited>
          <TestCaseFunction test_supplier_page_and_workspace_are_connected>
          <TestCaseFunction test_supplier_profile_reuses_canonical_directory_and_compliance>
          <TestCaseFunction test_supplier_service_exposes_controlled_lifecycle>
      <Module test_purchase_core.py>
        <UnitTestCase TestPurchaseCore>
          <TestCaseFunction test_supplier_classification_is_normalized>
          <TestCaseFunction test_supplier_profile_transitions_are_closed>
          <TestCaseFunction test_unknown_supplier_classification_is_rejected>
      <Module test_purchase_request_core.py>
        <UnitTestCase TestPurchaseRequestCore>
          <TestCaseFunction test_duplicate_and_mismatched_lines_are_rejected>
          <TestCaseFunction test_fractional_quantities_preserve_six_decimal_places>
          <TestCaseFunction test_multiline_amounts_are_exact>
          <TestCaseFunction test_request_dates_and_transitions_are_strict>
      <Module test_pwa_contract.py>
        <UnitTestCase TestPWAContract>
          <TestCaseFunction test_client_registers_worker_manifest_and_offline_state>
          <TestCaseFunction test_manifest_is_installable_and_uses_real_icons>
          <TestCaseFunction test_manifest_shortcuts_open_nexora_flows>
          <TestCaseFunction test_mobile_styles_include_safe_area_and_touch_targets>
          <TestCaseFunction test_worker_never_caches_business_or_private_data>
      <Module test_quick_flows_contract.py>
        <UnitTestCase TestQuickFlowsContract>
          <TestCaseFunction test_context_period_and_duplicate_submission_are_guarded>
          <TestCaseFunction test_controlled_corrections_require_three_distinct_users>
          <TestCaseFunction test_dashboard_currency_guard_remains_active>
          <TestCaseFunction test_document_actions_preserve_original_and_use_audited_services>
          <TestCaseFunction test_frappe_thenables_are_awaited_without_chained_finally>
          <TestCaseFunction test_guided_expense_preserves_server_preview_and_multifund_ui>
          <TestCaseFunction test_income_and_expense_accesses_converge_on_operational_engine>
          <TestCaseFunction test_mobile_cards_preserve_desktop_tables_and_accessibility>
          <TestCaseFunction test_search_endpoints_are_overridden_with_permission_aware_queries>
          <TestCaseFunction test_search_is_consolidated_and_vocabulary_is_consistent>
          <TestCaseFunction test_shared_coordinator_is_loaded_after_primary_product_script>
      <Module test_quotation_contract.py>
        <UnitTestCase TestQuotationContract>
          <TestCaseFunction test_quotation_controller_enforces_boundary>
          <TestCaseFunction test_quotation_doctype_is_defined>
          <TestCaseFunction test_quotation_line_doctype_is_defined>
          <TestCaseFunction test_quotation_page_is_connected>
          <TestCaseFunction test_quotation_service_exposes_lifecycle>
          <TestCaseFunction test_workflow_references_quotation_tests>
      <Module test_quotation_core.py>
        <UnitTestCase TestQuotationCore>
          <TestCaseFunction test_accepted_is_terminal>
          <TestCaseFunction test_direct_acceptance_is_rejected>
          <TestCaseFunction test_draft_can_be_cancelled>
          <TestCaseFunction test_draft_can_be_submitted>
          <TestCaseFunction test_expired_is_terminal>
          <TestCaseFunction test_rejected_can_be_cancelled>
          <TestCaseFunction test_rejected_cannot_be_accepted>
          <TestCaseFunction test_submitted_can_be_accepted>
      <Module test_receipt_contract.py>
        <Class TestGoodsReceiptContract>
          <Function test_receipt_state_machine_is_defined>
          <Function test_receipt_doctype_is_defined>
          <Function test_receipt_line_doctype_is_defined>
          <Function test_receipt_controller_enforces_boundary>
          <Function test_receipt_service_exposes_lifecycle>
          <Function test_receipt_line_tracks_ordered_and_received>
      <Module test_receipt_core.py>
        <UnitTestCase TestGoodsReceiptCore>
          <TestCaseFunction test_all_transitions_are_defined>
          <TestCaseFunction test_cancelled_is_terminal>
          <TestCaseFunction test_completed_is_terminal>
          <TestCaseFunction test_draft_can_be_cancelled>
          <TestCaseFunction test_draft_can_be_completed>
          <TestCaseFunction test_negative_quantity_rejected>
          <TestCaseFunction test_negative_rejected_rejected>
          <TestCaseFunction test_no_purchase_order_line_ref_rejected>
          <TestCaseFunction test_unknown_source_is_rejected>
          <TestCaseFunction test_validate_receipt_lines_exceeds_tolerance>
          <TestCaseFunction test_validate_receipt_lines_within_tolerance>
      <Module test_reference_rules.py>
        <UnitTestCase TestReferenceRules>
          <TestCaseFunction test_advance_balance_prevents_duplicate_or_excessive_settlement>
          <TestCaseFunction test_advance_requires_valid_date_and_due_date>
          <TestCaseFunction test_real_return_blocks_duplicate_original_source_and_excess>
          <TestCaseFunction test_real_return_supports_partial_same_source_and_explicit_relation>
          <TestCaseFunction test_reclassification_generates_negative_old_and_positive_new_effects>
          <TestCaseFunction test_reclassification_is_limited_by_effect_balance>
          <TestCaseFunction test_reversal_derives_original_dimensions_without_funds>
          <TestCaseFunction test_segregation_applies_to_every_required_profile>
      <Module test_report_export_guard_contract.py>
        <UnitTestCase TestReportExportGuardContract>
          <TestCaseFunction test_browser_uses_the_canonical_server_endpoint>
          <TestCaseFunction test_export_endpoint_is_overridden_by_size_guard>
          <TestCaseFunction test_export_uses_filtered_snapshot_and_fi02_query>
          <TestCaseFunction test_paginated_exports_are_rejected_instead_of_truncated>
      <Module test_report_filter_ui_contract.py>
        <UnitTestCase TestReportFilterUIContract>
          <TestCaseFunction test_all_filters_are_sent_to_preview_detail_export_and_saved_reports>
          <TestCaseFunction test_interface_discloses_active_filter_count>
          <TestCaseFunction test_report_center_exposes_financial_and_contract_filters>
      <Module test_reports_contract.py>
        <UnitTestCase TestReportsContract>
          <TestCaseFunction test_reports_core_exists>
          <TestCaseFunction test_reports_module_exists>
          <TestCaseFunction test_reports_page_js_exists>
          <TestCaseFunction test_reports_page_json_exists>
          <TestCaseFunction test_reports_service_exists>
          <TestCaseFunction test_service_has_report_functions>
          <TestCaseFunction test_service_uses_require_action>
      <Module test_reports_core.py>
        <UnitTestCase TestReportsCore>
          <TestCaseFunction test_format_statement_rows_empty>
          <TestCaseFunction test_format_statement_rows_running_balance>
          <TestCaseFunction test_money_rejects_invalid>
          <TestCaseFunction test_money_rounds_to_two_decimals>
          <TestCaseFunction test_reconcile_amounts_all_inflows>
          <TestCaseFunction test_reconcile_amounts_mixed>
          <TestCaseFunction test_reconcile_empty>
          <TestCaseFunction test_reconcile_real_return_included>
      <Module test_safe_archive_contract.py>
        <UnitTestCase TestSafeArchiveContract>
          <TestCaseFunction test_fi01_exposes_safe_cancellation_without_deletion>
          <TestCaseFunction test_fund_source_cancellation_is_compensatory_and_audited>
          <TestCaseFunction test_saved_report_archive_has_real_interface_and_is_loaded>
          <TestCaseFunction test_saved_report_archive_is_owner_scoped_idempotent_and_audited>
          <TestCaseFunction test_saved_reports_cannot_be_hard_deleted>
      <Module test_security_contract.py>
        <UnitTestCase TestSecurityContract>
          <TestCaseFunction test_fixture_has_correct_roles>
          <TestCaseFunction test_fixture_role_exists>
          <TestCaseFunction test_fixture_roles_have_desk_access>
          <TestCaseFunction test_permissions_module_uses_same_roles>
      <Module test_security_core.py>
        <UnitTestCase TestSecurityCore>
          <TestCaseFunction test_access_roles_are_comprehensive>
          <TestCaseFunction test_action_roles_has_all_expected_actions>
          <TestCaseFunction test_action_roles_has_approve>
          <TestCaseFunction test_action_roles_has_preview>
          <TestCaseFunction test_approve_excludes_auditor>
          <TestCaseFunction test_approve_excludes_operator>
          <TestCaseFunction test_approve_excludes_project_viewer>
          <TestCaseFunction test_approve_requires_manager>
          <TestCaseFunction test_create_source_is_operator>
          <TestCaseFunction test_execute_requires_operator>
          <TestCaseFunction test_manage_entity_compliance_is_manager>
          <TestCaseFunction test_manager_roles_are_correct>
          <TestCaseFunction test_operator_roles_are_correct>
          <TestCaseFunction test_preview_allows_all_roles>
          <TestCaseFunction test_preview_includes_project_viewer>
          <TestCaseFunction test_read_sensitive_entity_has_auditor>
      <Module test_weekly_close_canonical_contract.py>
        <UnitTestCase TestWeeklyCloseCanonicalContract>
          <TestCaseFunction test_adapter_only_delegates_without_patching_a_second_engine>
          <TestCaseFunction test_closing_ui_requires_project_and_preserves_historical_context>
          <TestCaseFunction test_correction_is_compensatory_and_never_deletes_the_original>
          <TestCaseFunction test_internal_service_is_the_single_v3_engine>
          <TestCaseFunction test_public_weekly_endpoints_use_the_canonical_adapter>
          <TestCaseFunction test_snapshot_hash_excludes_only_the_volatile_generation_timestamp>
      <Module test_weekly_close_history_contract.py>
        <UnitTestCase TestWeeklyCloseHistoryContract>
          <TestCaseFunction test_budget_cutoff_selects_latest_effective_version>
          <TestCaseFunction test_snapshot_discloses_non_historical_contract_and_reconciliation_basis>
          <TestCaseFunction test_weekly_close_uses_the_single_versioned_historical_engine>

==================================== ERRORS ====================================
________ ERROR collecting nexora/tests/test_budget_as_of_integration.py ________
ImportError while importing test module '/workspaces/Gesti-n-de-Construcci-n-Residencial/nexora_app/nexora/tests/test_budget_as_of_integration.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/local/python/3.12.1/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
nexora_app/nexora/tests/test_budget_as_of_integration.py:6: in <module>
    import frappe
E   ModuleNotFoundError: No module named 'frappe'
__________ ERROR collecting nexora/tests/test_contract_integration.py __________
ImportError while importing test module '/workspaces/Gesti-n-de-Construcci-n-Residencial/nexora_app/nexora/tests/test_contract_integration.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/local/python/3.12.1/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
nexora_app/nexora/tests/test_contract_integration.py:6: in <module>
    import frappe
E   ModuleNotFoundError: No module named 'frappe'
_________ ERROR collecting nexora/tests/test_dashboard_integration.py __________
ImportError while importing test module '/workspaces/Gesti-n-de-Construcci-n-Residencial/nexora_app/nexora/tests/test_dashboard_integration.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/local/python/3.12.1/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
nexora_app/nexora/tests/test_dashboard_integration.py:8: in <module>
    import frappe
E   ModuleNotFoundError: No module named 'frappe'
____ ERROR collecting nexora/tests/test_dashboard_net_income_integration.py ____
ImportError while importing test module '/workspaces/Gesti-n-de-Construcci-n-Residencial/nexora_app/nexora/tests/test_dashboard_net_income_integration.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/local/python/3.12.1/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
nexora_app/nexora/tests/test_dashboard_net_income_integration.py:5: in <module>
    import frappe
E   ModuleNotFoundError: No module named 'frappe'
_________ ERROR collecting nexora/tests/test_directory_integration.py __________
ImportError while importing test module '/workspaces/Gesti-n-de-Construcci-n-Residencial/nexora_app/nexora/tests/test_directory_integration.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/local/python/3.12.1/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
nexora_app/nexora/tests/test_directory_integration.py:5: in <module>
    import frappe
E   ModuleNotFoundError: No module named 'frappe'
__________ ERROR collecting nexora/tests/test_evidence_integration.py __________
ImportError while importing test module '/workspaces/Gesti-n-de-Construcci-n-Residencial/nexora_app/nexora/tests/test_evidence_integration.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/local/python/3.12.1/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
nexora_app/nexora/tests/test_evidence_integration.py:5: in <module>
    import frappe
E   ModuleNotFoundError: No module named 'frappe'
____ ERROR collecting nexora/tests/test_executive_reporting_integration.py _____
ImportError while importing test module '/workspaces/Gesti-n-de-Construcci-n-Residencial/nexora_app/nexora/tests/test_executive_reporting_integration.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/local/python/3.12.1/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
nexora_app/nexora/tests/test_executive_reporting_integration.py:6: in <module>
    import frappe
E   ModuleNotFoundError: No module named 'frappe'
_____ ERROR collecting nexora/tests/test_filtered_snapshot_integration.py ______
ImportError while importing test module '/workspaces/Gesti-n-de-Construcci-n-Residencial/nexora_app/nexora/tests/test_filtered_snapshot_integration.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/local/python/3.12.1/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
nexora_app/nexora/tests/test_filtered_snapshot_integration.py:5: in <module>
    import frappe
E   ModuleNotFoundError: No module named 'frappe'
_________ ERROR collecting nexora/tests/test_financial_integration.py __________
ImportError while importing test module '/workspaces/Gesti-n-de-Construcci-n-Residencial/nexora_app/nexora/tests/test_financial_integration.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/local/python/3.12.1/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
nexora_app/nexora/tests/test_financial_integration.py:5: in <module>
    import frappe
E   ModuleNotFoundError: No module named 'frappe'
_______ ERROR collecting nexora/tests/test_fund_selector_integration.py ________
ImportError while importing test module '/workspaces/Gesti-n-de-Construcci-n-Residencial/nexora_app/nexora/tests/test_fund_selector_integration.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/local/python/3.12.1/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
nexora_app/nexora/tests/test_fund_selector_integration.py:5: in <module>
    import frappe
E   ModuleNotFoundError: No module named 'frappe'
_ ERROR collecting nexora/tests/test_guided_account_progressive_integration.py _
ImportError while importing test module '/workspaces/Gesti-n-de-Construcci-n-Residencial/nexora_app/nexora/tests/test_guided_account_progressive_integration.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/local/python/3.12.1/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
nexora_app/nexora/tests/test_guided_account_progressive_integration.py:5: in <module>
    import frappe
E   ModuleNotFoundError: No module named 'frappe'
_ ERROR collecting nexora/tests/test_guided_operation_correction_integration.py _
ImportError while importing test module '/workspaces/Gesti-n-de-Construcci-n-Residencial/nexora_app/nexora/tests/test_guided_operation_correction_integration.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/local/python/3.12.1/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
nexora_app/nexora/tests/test_guided_operation_correction_integration.py:5: in <module>
    import frappe
E   ModuleNotFoundError: No module named 'frappe'
______________ ERROR collecting nexora/tests/test_installation.py ______________
ImportError while importing test module '/workspaces/Gesti-n-de-Construcci-n-Residencial/nexora_app/nexora/tests/test_installation.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/local/python/3.12.1/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
nexora_app/nexora/tests/test_installation.py:3: in <module>
    import frappe
E   ModuleNotFoundError: No module named 'frappe'
___________ ERROR collecting nexora/tests/test_ledger_integration.py ___________
ImportError while importing test module '/workspaces/Gesti-n-de-Construcci-n-Residencial/nexora_app/nexora/tests/test_ledger_integration.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/local/python/3.12.1/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
nexora_app/nexora/tests/test_ledger_integration.py:6: in <module>
    import frappe
E   ModuleNotFoundError: No module named 'frappe'
________ ERROR collecting nexora/tests/test_operational_integration.py _________
ImportError while importing test module '/workspaces/Gesti-n-de-Construcci-n-Residencial/nexora_app/nexora/tests/test_operational_integration.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/local/python/3.12.1/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
nexora_app/nexora/tests/test_operational_integration.py:6: in <module>
    import frappe
E   ModuleNotFoundError: No module named 'frappe'
__________ ERROR collecting nexora/tests/test_purchase_integration.py __________
ImportError while importing test module '/workspaces/Gesti-n-de-Construcci-n-Residencial/nexora_app/nexora/tests/test_purchase_integration.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/local/python/3.12.1/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
nexora_app/nexora/tests/test_purchase_integration.py:5: in <module>
    import frappe
E   ModuleNotFoundError: No module named 'frappe'
______ ERROR collecting nexora/tests/test_purchase_request_integration.py ______
ImportError while importing test module '/workspaces/Gesti-n-de-Construcci-n-Residencial/nexora_app/nexora/tests/test_purchase_request_integration.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/local/python/3.12.1/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
nexora_app/nexora/tests/test_purchase_request_integration.py:5: in <module>
    import frappe
E   ModuleNotFoundError: No module named 'frappe'
_________ ERROR collecting nexora/tests/test_quotation_integration.py __________
ImportError while importing test module '/workspaces/Gesti-n-de-Construcci-n-Residencial/nexora_app/nexora/tests/test_quotation_integration.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/local/python/3.12.1/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
nexora_app/nexora/tests/test_quotation_integration.py:5: in <module>
    import frappe
E   ModuleNotFoundError: No module named 'frappe'
___ ERROR collecting nexora/tests/test_weekly_close_canonical_integration.py ___
ImportError while importing test module '/workspaces/Gesti-n-de-Construcci-n-Residencial/nexora_app/nexora/tests/test_weekly_close_canonical_integration.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/local/python/3.12.1/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
nexora_app/nexora/tests/test_weekly_close_canonical_integration.py:5: in <module>
    import frappe
E   ModuleNotFoundError: No module named 'frappe'
=========================== short test summary info ============================
ERROR nexora_app/nexora/tests/test_budget_as_of_integration.py
ERROR nexora_app/nexora/tests/test_contract_integration.py
ERROR nexora_app/nexora/tests/test_dashboard_integration.py
ERROR nexora_app/nexora/tests/test_dashboard_net_income_integration.py
ERROR nexora_app/nexora/tests/test_directory_integration.py
ERROR nexora_app/nexora/tests/test_evidence_integration.py
ERROR nexora_app/nexora/tests/test_executive_reporting_integration.py
ERROR nexora_app/nexora/tests/test_filtered_snapshot_integration.py
ERROR nexora_app/nexora/tests/test_financial_integration.py
ERROR nexora_app/nexora/tests/test_fund_selector_integration.py
ERROR nexora_app/nexora/tests/test_guided_account_progressive_integration.py
ERROR nexora_app/nexora/tests/test_guided_operation_correction_integration.py
ERROR nexora_app/nexora/tests/test_installation.py
ERROR nexora_app/nexora/tests/test_ledger_integration.py
ERROR nexora_app/nexora/tests/test_operational_integration.py
ERROR nexora_app/nexora/tests/test_purchase_integration.py
ERROR nexora_app/nexora/tests/test_purchase_request_integration.py
ERROR nexora_app/nexora/tests/test_quotation_integration.py
ERROR nexora_app/nexora/tests/test_weekly_close_canonical_integration.py
!!!!!!!!!!!!!!!!!!! Interrupted: 19 errors during collection !!!!!!!!!!!!!!!!!!!
=================== 507 tests collected, 19 errors in 1.15s ====================

## npm test
