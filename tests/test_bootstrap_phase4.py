import importlib.util
import os
import shutil
import unittest
from pathlib import Path


class _TemporaryDirectory:
    _counter = 0

    def __enter__(self):
        type(self)._counter += 1
        self.path = Path('/tmp') / f"paa-test-{os.getpid()}-{type(self)._counter}"
        if self.path.exists():
            shutil.rmtree(self.path)
        self.path.mkdir(parents=True)
        return str(self.path)

    def __exit__(self, exc_type, exc, tb):
        shutil.rmtree(self.path, ignore_errors=True)
        return False


class _TempfileCompat:
    TemporaryDirectory = _TemporaryDirectory


class _PatchObject:
    def __init__(self, target, name, side_effect=None, value=None):
        self.target = target
        self.name = name
        self.side_effect = side_effect
        self.value = value

    def __enter__(self):
        self.original = getattr(self.target, self.name)
        replacement = self.side_effect if self.side_effect is not None else self.value
        setattr(self.target, self.name, replacement)
        return replacement

    def __exit__(self, exc_type, exc, tb):
        setattr(self.target, self.name, self.original)
        return False


class _PatchCompat:
    @staticmethod
    def object(target, name, side_effect=None, **kwargs):
        return _PatchObject(target, name, side_effect=side_effect, value=kwargs.get('new'))


tempfile = _TempfileCompat()
patch = _PatchCompat()

MODULE_PATH = Path(__file__).resolve().parents[1] / "bootstrap" / "setup" / "bootstrap_ai_assets.py"
spec = importlib.util.spec_from_file_location("bootstrap_ai_assets", MODULE_PATH)
bootstrap_ai_assets = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(bootstrap_ai_assets)


class BootstrapPhase4Tests(unittest.TestCase):
    def _valid_phase102_syntax_invalid_evidence_summary(self):
        return {
            "status": "syntax-invalid-failclosed",
            "syntax_invalid_evidence_blocks_completion": True,
            "agent_side_complete": False,
            "machine_side_complete": False,
            "requires_user_code_review": False,
            "external_owner_decision_required": True,
            "human_feedback_pending": True,
            "shares_anything": False,
            "sends_invitations": False,
            "writes_anything": False,
            "writes": 0,
            "executes_anything": False,
            "remote_mutation_allowed": False,
            "credential_validation_allowed": False,
            "auto_approves_release": False,
            "remote_issues_created": 0,
            "issue_backlog_mutation_allowed": False,
            "checks": 5,
            "pass": 5,
            "fail": 0,
            "warn": 0,
        }

    def test_split_sections_handles_markdown_headings(self):
        text = "# One\nalpha\n\n## Two\nbeta\n"
        sections = bootstrap_ai_assets.split_document_sections(text)
        self.assertEqual([section["label"] for section in sections], ["# One", "## Two"])

    def test_compare_sections_detects_missing_and_live_only_blocks(self):
        canonical = "A\n§\nB\n§\nC\n"
        live = "A\n§\nB-local\n§\nD\n"
        comparison = bootstrap_ai_assets.compare_document_sections(canonical, live)
        self.assertIn("C", comparison["canonical_only_labels"])
        self.assertIn("D", comparison["live_only_labels"])

    def test_build_merge_guidance_flags_manual_merge_when_both_sides_changed(self):
        canonical = "# Shared\ncanonical\n\n# Canonical Only\nkeep me\n"
        live = "# Shared\nlive\n\n# Live Only\nkeep local\n"
        analysis = bootstrap_ai_assets.analyze_text_diff(canonical, live)
        self.assertEqual(analysis["merge_guidance"]["strategy"], "manual-merge-preserve-both")
        self.assertTrue(analysis["merge_guidance"]["canonical_missing_sections"])
        self.assertTrue(analysis["merge_guidance"]["live_only_sections"])

    def test_merge_candidate_appends_missing_canonical_sections(self):
        canonical = "A\n§\nB\n§\nC\n"
        live = "A\n§\nB\n"
        analysis = bootstrap_ai_assets.analyze_text_diff(canonical, live)
        merged = bootstrap_ai_assets.render_merge_candidate_text(canonical, live, analysis["merge_guidance"]["strategy"])
        self.assertEqual(merged, "A\n§\nB\n§\nC\n")

    def test_merge_candidate_preserves_canonical_order(self):
        canonical = "# A\n1\n\n# B\n2\n\n# C\n3\n"
        live = "# A\n1\n\n# C\n3\n"
        analysis = bootstrap_ai_assets.analyze_text_diff(canonical, live)
        merged = bootstrap_ai_assets.render_merge_candidate_text(canonical, live, analysis["merge_guidance"]["strategy"])
        self.assertEqual(merged, canonical)

    def test_execute_merge_apply_skips_unmanaged_targets_even_if_strategy_is_low_ambiguity(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            canonical = tmp / "canonical.md"
            live = tmp / "live.md"
            backup_root = tmp / "backups"
            canonical.write_text("A\n§\nB\n§\nC\n", encoding="utf-8")
            live.write_text("A\n§\nB\n", encoding="utf-8")

            entry = {
                "target": "sample-target",
                "state": "present-but-unmanaged",
                "recommended_action": "backup-and-manual-review",
                "risk": "medium",
                "canonical_path": str(canonical),
                "live_path": str(live),
                "canonical_hash": bootstrap_ai_assets.sha256_text(canonical),
                "live_hash": bootstrap_ai_assets.sha256_text(live),
                "analysis": bootstrap_ai_assets.analyze_text_diff(canonical.read_text(), live.read_text()),
            }

            result = bootstrap_ai_assets.execute_merge_apply_entry(entry, backup_root)
            self.assertEqual(result["status"], "skipped")
            self.assertEqual(live.read_text(encoding="utf-8"), "A\n§\nB\n")

    def test_render_manual_merge_candidate_contains_both_sides(self):
        canonical = "# Canonical\nkeep canonical\n"
        live = "# Live\nkeep live\n"
        entry = {
            "target": "manual-target",
            "state": "managed-but-drifted",
            "recommended_action": "review-diff-before-sync",
            "risk": "medium",
            "canonical_path": "/tmp/canonical.md",
            "live_path": "/tmp/live.md",
            "analysis": bootstrap_ai_assets.analyze_text_diff(canonical, live),
        }
        text = bootstrap_ai_assets.render_manual_merge_candidate_text(entry, canonical, live)
        self.assertIn("manual-target", text)
        self.assertIn("keep canonical", text)
        self.assertIn("keep live", text)
        self.assertIn("Manual merge worksheet", text)

    def test_render_suggested_merge_draft_contains_preserve_and_insert_markers(self):
        canonical = "A\n§\nB\n§\nC\n"
        live = "A-live\n§\nB-live\n"
        entry = {
            "target": "manual-target",
            "state": "managed-but-drifted",
            "recommended_action": "review-diff-before-sync",
            "risk": "medium",
            "canonical_path": "/tmp/canonical.md",
            "live_path": "/tmp/live.md",
            "analysis": bootstrap_ai_assets.analyze_text_diff(canonical, live),
        }
        draft = bootstrap_ai_assets.render_suggested_merge_draft_text(entry, canonical, live)
        self.assertIn("PRESERVED FROM LIVE", draft)
        self.assertIn("INSERTED FROM CANONICAL", draft)
        self.assertIn("A-live", draft)
        self.assertIn("C", draft)

    def test_target_aware_hermes_draft_deduplicates_overlapping_memory_facts(self):
        canonical = (
            "User's favorite TV drama is Grey's Anatomy; they watched it in college and stopped following it a long time ago. "
            "In middle and high school, their favorite series was Harry Potter; they bought the books and have nostalgic attachment to the series.\n"
            "§\n"
            "The user's preferred direction is canonical memory outside any single runtime, with tool-specific memories treated as adapter layers rather than sole source of truth.\n"
        )
        live = (
            "User's favorite TV drama is Grey's Anatomy; they watched it in college but stopped following it a long time ago.\n"
            "§\n"
            "In middle and high school, user's favorite was Harry Potter; they bought the books and have nostalgic attachment to the series, though they don't clearly remember whether the first book they bought was Order of the Phoenix or Harry Potter and the Goblet of Fire.\n"
            "§\n"
            "User cares deeply about portable, cross-agent long-term memory and wants a unified AI asset system that preserves memory, skills, plugins, MCPs, and workflows across machines without starting over.\n"
        )
        entry = {
            "target": "hermes-user-memory",
            "state": "managed-but-drifted",
            "recommended_action": "review-diff-before-sync",
            "risk": "medium",
            "canonical_path": "/tmp/canonical.md",
            "live_path": "/tmp/live.md",
            "analysis": bootstrap_ai_assets.analyze_text_diff(canonical, live),
        }
        draft = bootstrap_ai_assets.render_suggested_merge_draft_text(entry, canonical, live)
        self.assertIn("Order of the Phoenix", draft)
        self.assertEqual(draft.count("Grey's Anatomy"), 1)

    def test_target_aware_claude_draft_builds_portable_addendum(self):
        canonical = "## Canonical Memory Priority\n\n- Treat AI-Assets as portable source.\n\n## Workflow Expectations\n\n- Preserve continuity.\n"
        live = "## Workflow Orchestration\n\n- Existing local policy.\n"
        entry = {
            "target": "claude-instructions",
            "state": "managed-but-drifted",
            "recommended_action": "review-diff-before-sync",
            "risk": "medium",
            "canonical_path": "/tmp/canonical.md",
            "live_path": "/tmp/live.md",
            "analysis": bootstrap_ai_assets.analyze_text_diff(canonical, live),
        }
        draft = bootstrap_ai_assets.render_suggested_merge_draft_text(entry, canonical, live)
        self.assertIn("## Portable AI Assets Addendum", draft)
        self.assertIn("Treat AI-Assets as portable source.", draft)
        self.assertIn("Existing local policy.", draft)

    def test_render_normalized_final_draft_removes_markup_comments(self):
        suggested = (
            "# Suggested merged draft: claude-instructions\n\n"
            "<!-- Review carefully before using. -->\n\n"
            "## Workflow Orchestration\n\n- Existing local policy.\n\n"
            "## Portable AI Assets Addendum\n\n"
            "<!-- INSERTED FROM CANONICAL: ## Canonical Memory Priority -->\n"
            "## Canonical Memory Priority\n\n- Treat AI-Assets as portable source.\n"
        )
        normalized = bootstrap_ai_assets.render_normalized_final_draft_text("claude-instructions", suggested)
        self.assertNotIn("<!--", normalized)
        self.assertIn("## Canonical Memory Priority", normalized)
        self.assertNotIn("# Suggested merged draft:", normalized)

    def test_render_reviewed_merge_seed_promotes_reconcile_blocks(self):
        normalized = (
            "## Workflow Orchestration\n\n- Existing local policy.\n\n"
            "## Portable AI Assets Addendum\n\n"
            "### Reconcile: ## Language\n\n"
            "```markdown\n## Language\n\n- Always reply in Chinese (中文), unless the user explicitly asks for another language.\n```\n\n"
            "```markdown\n## Language\n\n- Always reply in Chinese (中文), unless I explicitly ask for another language.\n```\n\n"
            "## Canonical Memory Priority\n\n- Treat AI-Assets as portable source.\n"
        )
        seed = bootstrap_ai_assets.render_reviewed_merge_seed_text("claude-instructions", normalized)
        self.assertIn("## Language", seed)
        self.assertNotIn("```markdown", seed)
        self.assertNotIn("### Reconcile:", seed)

    def test_classify_asset_path_distinguishes_public_private_secret(self):
        self.assertEqual(
            bootstrap_ai_assets.classify_asset_path("/Users/example/AI-Assets/stack/manifest.yaml")["asset_class"],
            "public",
        )
        self.assertEqual(
            bootstrap_ai_assets.classify_asset_path("/Users/example/AI-Assets/sample-assets/adapters/example-runtime/adapter.yaml")["asset_class"],
            "public",
        )
        self.assertEqual(
            bootstrap_ai_assets.classify_asset_path("/Users/example/AI-Assets/memory/profile/user-profile.md")["asset_class"],
            "private",
        )
        self.assertEqual(
            bootstrap_ai_assets.classify_asset_path("/Users/example/.codex/auth.json")["asset_class"],
            "secret",
        )

    def test_build_target_schema_metadata_marks_review_required_targets_as_lossy(self):
        metadata = bootstrap_ai_assets.build_target_schema_metadata("claude-instructions", "managed-but-drifted", "review-diff-before-sync")
        self.assertEqual(metadata["portability"], "lossy-adapter")
        self.assertEqual(metadata["apply_policy"], "human-review-required")

    def test_write_manual_merge_candidate_bundle_writes_candidate_and_sources(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            canonical = tmp / "canonical.md"
            live = tmp / "live.md"
            out_root = tmp / "candidates"
            canonical.write_text("# Canonical\nkeep canonical\n", encoding="utf-8")
            live.write_text("# Live\nkeep live\n", encoding="utf-8")
            entry = {
                "target": "manual-target",
                "state": "managed-but-drifted",
                "recommended_action": "review-diff-before-sync",
                "risk": "medium",
                "canonical_path": str(canonical),
                "live_path": str(live),
                "analysis": bootstrap_ai_assets.analyze_text_diff(canonical.read_text(), live.read_text()),
            }
            result = bootstrap_ai_assets.write_manual_merge_candidate_bundle(entry, out_root)
            self.assertTrue(Path(result["candidate_path"]).is_file())
            self.assertTrue(Path(result["canonical_copy_path"]).is_file())
            self.assertTrue(Path(result["live_copy_path"]).is_file())
            self.assertTrue(Path(result["review_instructions_path"]).is_file())
            self.assertTrue(Path(result["reviewed_merge_template_path"]).is_file())
            self.assertTrue(Path(result["suggested_merge_draft_path"]).is_file())
            self.assertTrue(Path(result["normalized_final_draft_path"]).is_file())
            self.assertTrue(Path(result["reviewed_merge_seed_path"]).is_file())

    def test_execute_review_apply_entry_skips_without_reviewed_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            live = tmp / "live.md"
            backup_root = tmp / "backups"
            state_path = tmp / "managed-state.json"
            bundle_dir = tmp / "bundle"
            bundle_dir.mkdir()
            live.write_text("live\n", encoding="utf-8")
            entry = {
                "target": "manual-target",
                "state": "managed-but-drifted",
                "canonical_path": str(tmp / "canonical.md"),
                "live_path": str(live),
                "canonical_hash": None,
            }
            result = bootstrap_ai_assets.execute_review_apply_entry(entry, bundle_dir, backup_root, state_path=state_path)
            self.assertEqual(result["status"], "skipped")
            self.assertEqual(live.read_text(encoding="utf-8"), "live\n")

    def test_execute_review_apply_entry_applies_reviewed_merge_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            canonical = tmp / "canonical.md"
            live = tmp / "live.md"
            backup_root = tmp / "backups"
            state_path = tmp / "managed-state.json"
            bundle_dir = tmp / "bundle"
            bundle_dir.mkdir()
            canonical.write_text("canonical\n", encoding="utf-8")
            live.write_text("live\n", encoding="utf-8")
            (bundle_dir / "reviewed-merge.md").write_text("reviewed\n", encoding="utf-8")
            entry = {
                "target": "manual-target",
                "state": "managed-but-drifted",
                "canonical_path": str(canonical),
                "live_path": str(live),
                "canonical_hash": bootstrap_ai_assets.sha256_text(canonical),
            }
            result = bootstrap_ai_assets.execute_review_apply_entry(entry, bundle_dir, backup_root, state_path=state_path)
            self.assertEqual(result["status"], "applied")
            self.assertEqual(live.read_text(encoding="utf-8"), "reviewed\n")
            self.assertTrue((backup_root / str(live).lstrip("/")).is_file())
            self.assertIn("manual-target", bootstrap_ai_assets.load_managed_state(state_path)["targets"])

    def test_execute_merge_apply_writes_low_ambiguity_target(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            canonical = tmp / "canonical.md"
            live = tmp / "live.md"
            backup_root = tmp / "backups"
            state_path = tmp / "managed-state.json"
            canonical.write_text("A\n§\nB\n§\nC\n", encoding="utf-8")
            live.write_text("A\n§\nB\n", encoding="utf-8")

            entry = {
                "target": "sample-target",
                "state": "managed-but-drifted",
                "recommended_action": "review-diff-before-sync",
                "risk": "medium",
                "canonical_path": str(canonical),
                "live_path": str(live),
                "canonical_hash": bootstrap_ai_assets.sha256_text(canonical),
                "live_hash": bootstrap_ai_assets.sha256_text(live),
                "analysis": bootstrap_ai_assets.analyze_text_diff(canonical.read_text(), live.read_text()),
            }

            result = bootstrap_ai_assets.execute_merge_apply_entry(entry, backup_root, state_path=state_path)

            self.assertEqual(result["status"], "applied")
            self.assertTrue((backup_root / str(live).lstrip("/")).is_file())
            self.assertEqual(live.read_text(encoding="utf-8"), "A\n§\nB\n§\nC\n")
            state = bootstrap_ai_assets.load_managed_state(state_path)
            self.assertIn("sample-target", state["targets"])

    def test_detect_manifest_schema_identifies_stack_tool_and_bridge_files(self):
        self.assertEqual(
            bootstrap_ai_assets.detect_manifest_schema(Path("/Users/example/AI-Assets/stack/manifest.yaml")),
            "stack-manifest-v1",
        )
        self.assertEqual(
            bootstrap_ai_assets.detect_manifest_schema(Path("/Users/example/AI-Assets/stack/tools/hermes.yaml")),
            "tool-manifest-v1",
        )
        self.assertEqual(
            bootstrap_ai_assets.detect_manifest_schema(Path("/Users/example/AI-Assets/stack/mcp/omx-mempalace-bridge.yaml")),
            "bridge-manifest-v1",
        )

    def test_validate_manifest_payload_accepts_valid_tool_manifest(self):
        payload = {
            "name": "hermes",
            "kind": "agent-runtime",
            "status": "detected",
            "home": "/Users/example/.hermes",
            "paths": {"config": "/Users/example/.hermes/config.yaml"},
            "preserve_in_git": ["AI-Assets/memory"],
            "backup_but_not_git": ["/Users/example/.hermes/state.db"],
            "rebuildable": ["wal files"],
            "restore_notes": ["Treat USER.md as adapter view."],
        }
        result = bootstrap_ai_assets.validate_manifest_payload("tool-manifest-v1", payload)
        self.assertTrue(result["valid"])
        self.assertEqual(result["errors"], [])

    def test_validate_manifest_payload_rejects_missing_required_fields_and_bad_asset_class(self):
        payload = {
            "version": 1,
            "root": "/Users/example/AI-Assets",
            "asset_class": "published-secret",
        }
        result = bootstrap_ai_assets.validate_manifest_payload("stack-manifest-v1", payload)
        self.assertFalse(result["valid"])
        self.assertTrue(any("updated_at" in err for err in result["errors"]))
        self.assertTrue(any("asset_class" in err for err in result["errors"]))

    def test_validate_schema_directory_reports_valid_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            (tmp / "stack" / "tools").mkdir(parents=True)
            schema_dir = tmp / "schemas"
            schema_dir.mkdir()
            manifest = tmp / "stack" / "tools" / "demo.yaml"
            manifest.write_text(
                "name: demo\nkind: agent-runtime\nstatus: detected\nhome: /tmp/demo\npaths:\n  config: /tmp/demo/config.yaml\npreserve_in_git:\n  - AI-Assets/memory\nbackup_but_not_git:\n  - /tmp/demo/state.db\nrebuildable:\n  - cache\nrestore_notes:\n  - restore carefully\n",
                encoding="utf-8",
            )
            (schema_dir / "tool-manifest-v1.json").write_text(
                '{"type":"object","required":["name","kind","status","home","paths","preserve_in_git","backup_but_not_git","rebuildable","restore_notes"]}',
                encoding="utf-8",
            )
            report = bootstrap_ai_assets.validate_schema_directory(tmp, schema_dir=schema_dir)
            self.assertEqual(report["summary"]["invalid"], 0)
            self.assertEqual(report["summary"]["valid"], 1)
            self.assertEqual(report["results"][0]["schema"], "tool-manifest-v1")

    def test_detect_manifest_schema_identifies_adapter_contract_files(self):
        self.assertEqual(
            bootstrap_ai_assets.detect_manifest_schema(Path("/Users/example/AI-Assets/adapters/registry/hermes.yaml")),
            "adapter-contract-v1",
        )
        self.assertEqual(
            bootstrap_ai_assets.detect_manifest_schema(Path("/Users/example/AI-Assets/sample-assets/adapters/example-runtime/adapter.yaml")),
            "adapter-contract-v1",
        )

    def test_validate_manifest_payload_accepts_valid_adapter_contract(self):
        payload = {
            "name": "hermes-user-memory",
            "adapter_version": 1,
            "runtime": "hermes",
            "description": "Projects canonical user memory into Hermes USER.md.",
            "canonical_sources": ["adapters/hermes/USER.md"],
            "live_targets": ["~/.hermes/memories/USER.md"],
            "connector": {"import": "read-file", "export": "write-file"},
            "detection": {"default_paths": ["~/.hermes/memories/USER.md"]},
            "apply_policy": "human-review-required",
        }
        result = bootstrap_ai_assets.validate_manifest_payload("adapter-contract-v1", payload)
        self.assertTrue(result["valid"])
        self.assertEqual(result["errors"], [])

    def test_load_adapter_contracts_and_build_connector_report(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            (tmp / "adapters" / "registry").mkdir(parents=True)
            (tmp / "sample-assets" / "adapters" / "example-runtime").mkdir(parents=True)
            (tmp / "adapters" / "registry" / "hermes.yaml").write_text(
                "name: hermes-user-memory\nadapter_version: 1\nruntime: hermes\ndescription: Export canonical memory into Hermes USER.md\ncanonical_sources:\n  - adapters/hermes/USER.md\nlive_targets:\n  - ~/.hermes/memories/USER.md\nconnector:\n  import: read-file\n  export: write-file\ndetection:\n  default_paths:\n    - ~/.hermes/memories/USER.md\napply_policy: human-review-required\n",
                encoding="utf-8",
            )
            (tmp / "sample-assets" / "adapters" / "example-runtime" / "adapter.yaml").write_text(
                "name: example-runtime-instructions\nadapter_version: 1\nruntime: example-runtime\ndescription: Example public-safe adapter\ncanonical_sources:\n  - sample-assets/adapters/example-runtime/canonical/instructions.md\nlive_targets:\n  - /Users/example/.example-runtime/INSTRUCTIONS.md\nconnector:\n  import: copy-file\n  export: copy-file\ndetection:\n  default_paths:\n    - /Users/example/.example-runtime/INSTRUCTIONS.md\napply_policy: safe-auto-apply\n",
                encoding="utf-8",
            )
            contracts = bootstrap_ai_assets.load_adapter_contracts(tmp)
            self.assertEqual(len(contracts), 2)
            self.assertEqual({contract["schema"] for contract in contracts}, {"adapter-contract-v1"})
            report = bootstrap_ai_assets.build_connector_report(tmp)
            self.assertEqual(report["summary"]["total_adapters"], 2)
            self.assertEqual(report["summary"]["runtimes"], ["example-runtime", "hermes"])
            self.assertEqual(sorted(report["summary"]["export_connectors"]), ["copy-file", "write-file"])

    def test_build_connector_preview_report_shows_builtin_actions_without_writing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            (tmp / "adapters" / "registry").mkdir(parents=True)
            (tmp / "adapters" / "hermes").mkdir(parents=True)
            canonical = tmp / "adapters" / "hermes" / "USER.md"
            canonical.write_text("portable memory\n", encoding="utf-8")
            (tmp / "adapters" / "registry" / "hermes.yaml").write_text(
                "name: hermes-user-memory\nadapter_version: 1\nruntime: hermes\ndescription: Export canonical memory into Hermes USER.md\ncanonical_sources:\n  - adapters/hermes/USER.md\nlive_targets:\n  - ~/.hermes/memories/USER.md\nconnector:\n  import: read-file\n  export: write-file\ndetection:\n  default_paths:\n    - ~/.hermes/memories/USER.md\napply_policy: human-review-required\n",
                encoding="utf-8",
            )
            report = bootstrap_ai_assets.build_connector_preview_report(tmp)
            self.assertEqual(report["summary"]["previewable_adapters"], 1)
            self.assertEqual(report["adapters"][0]["actions"][0]["connector"], "write-file")
            self.assertEqual(report["adapters"][0]["actions"][0]["mode"], "preview")
            self.assertIn("USER.md", report["adapters"][0]["actions"][0]["source"])

    def test_generate_redacted_example_bundle_writes_public_safe_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            reports = tmp / "bootstrap" / "reports"
            reports.mkdir(parents=True)
            connector_report = {
                "mode": "connectors",
                "generated_at": "2026-04-24T08:00:00",
                "root": "/Users/example/AI-Assets",
                "schema_dir": "/Users/example/AI-Assets/schemas",
                "summary": {
                    "total_adapters": 1,
                    "valid_adapters": 1,
                    "invalid_adapters": 0,
                    "runtimes": ["example-runtime"],
                    "import_connectors": ["copy-file"],
                    "export_connectors": ["copy-file"],
                },
                "adapters": [
                    {
                        "name": "example-runtime-instructions",
                        "runtime": "example-runtime",
                        "path": "/Users/example/AI-Assets/sample-assets/adapters/example-runtime/adapter.yaml",
                        "schema": "adapter-contract-v1",
                        "valid": True,
                        "errors": [],
                        "apply_policy": "safe-auto-apply",
                        "canonical_sources": ["sample-assets/adapters/example-runtime/canonical/instructions.md"],
                        "live_targets": ["/Users/example/.example-runtime/INSTRUCTIONS.md"],
                        "connector": {"import": "copy-file", "export": "copy-file"},
                        "asset_class": "public",
                        "shareability": "public-safe",
                    }
                ],
            }
            (reports / "latest-connectors.json").write_text(__import__("json").dumps(connector_report), encoding="utf-8")
            output = bootstrap_ai_assets.generate_redacted_example_bundle(tmp)
            self.assertTrue(Path(output["walkthrough_path"]).is_file())
            self.assertTrue(Path(output["summary_path"]).is_file())
            text = Path(output["walkthrough_path"]).read_text(encoding="utf-8")
            self.assertIn("example-runtime-instructions", text)
            self.assertIn("public-safe", text)
            self.assertNotIn(str(Path.home()), text)

    def test_build_demo_story_report_aggregates_latest_public_artifacts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            reports = tmp / "bootstrap" / "reports"
            reports.mkdir(parents=True)
            (reports / "latest-validate-schemas.json").write_text(
                __import__("json").dumps({"summary": {"total": 3, "valid": 3, "invalid": 0}}),
                encoding="utf-8",
            )
            (reports / "latest-connectors.json").write_text(
                __import__("json").dumps({"summary": {"total_adapters": 2, "runtimes": ["claude-code", "codex"]}}),
                encoding="utf-8",
            )
            (reports / "latest-connector-preview.json").write_text(
                __import__("json").dumps({"summary": {"previewable_adapters": 2}}),
                encoding="utf-8",
            )
            (tmp / "examples" / "redacted").mkdir(parents=True)
            (tmp / "examples" / "redacted" / "connector-walkthrough.example.md").write_text("# Example\n", encoding="utf-8")
            report = bootstrap_ai_assets.build_demo_story_report(tmp)
            self.assertEqual(report["summary"]["validated_manifests"], 3)
            self.assertEqual(report["summary"]["adapter_runtimes"], ["claude-code", "codex"])
            self.assertTrue(Path(report["story_path"]).is_file())
            story = Path(report["story_path"]).read_text(encoding="utf-8")
            self.assertIn("60-second promise", story)
            self.assertIn("AI work environment", story)
            self.assertIn("validate-schemas", story)
            self.assertIn("connector-preview", story)
            self.assertIn("public-safety-scan", story)
            self.assertIn("release-readiness", story)
            self.assertIn("completed-work-review", story)
            self.assertIn("public-demo-pack", story)
            self.assertIn("connector-walkthrough.example.md", story)

    def test_build_public_demo_pack_report_copies_expected_public_artifacts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            reports = tmp / "bootstrap" / "reports"
            reports.mkdir(parents=True)
            (tmp / "docs").mkdir(parents=True)
            (tmp / "examples" / "redacted").mkdir(parents=True)
            (tmp / "README.md").write_text("# Portable AI Assets\n", encoding="utf-8")
            (tmp / "docs" / "architecture.md").write_text("# Architecture\n", encoding="utf-8")
            (tmp / "docs" / "adapter-sdk.md").write_text("# Adapter SDK\n", encoding="utf-8")
            (tmp / "docs" / "public-facing-thesis.md").write_text("# Public Thesis\n", encoding="utf-8")
            (tmp / "docs" / "open-source-demo-story.md").write_text("# Demo Story Doc\n", encoding="utf-8")
            (tmp / "docs" / "open-source-demo-pack.md").write_text("# Demo Pack Doc\n", encoding="utf-8")
            (tmp / "docs" / "reference-coding-agent-workspace-portability.md").write_text("# Reference\n", encoding="utf-8")
            (reports / "latest-validate-schemas.md").write_text("# Validate\n", encoding="utf-8")
            (reports / "latest-connectors.md").write_text("# Connectors\n", encoding="utf-8")
            (reports / "latest-connector-preview.md").write_text("# Preview\n", encoding="utf-8")
            (reports / "latest-public-safety-scan.md").write_text("# Safety\n", encoding="utf-8")
            (reports / "latest-release-readiness.md").write_text("# Release\n", encoding="utf-8")
            (reports / "latest-completed-work-review.md").write_text("# Review\n", encoding="utf-8")
            (tmp / "examples" / "redacted" / "connector-walkthrough.example.md").write_text("# Walkthrough\n", encoding="utf-8")
            (tmp / "examples" / "redacted" / "demo-story.example.md").write_text("# Demo Story\n", encoding="utf-8")
            report = bootstrap_ai_assets.build_public_demo_pack_report(tmp)
            self.assertEqual(report["summary"]["files_in_pack"], 15)
            self.assertTrue(Path(report["pack_dir"]).is_dir())
            self.assertTrue((Path(report["pack_dir"]) / "PACK-INDEX.md").is_file())
            self.assertTrue((Path(report["pack_dir"]) / "MANIFEST.json").is_file())
            manifest = __import__("json").loads((Path(report["pack_dir"]) / "MANIFEST.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["asset_class"], "public")
            self.assertEqual(manifest["file_count"], 15)
            self.assertIn("README.md", manifest["files"])
            self.assertIn("public-facing-thesis.md", manifest["files"])
            self.assertIn("reference-coding-agent-workspace-portability.md", manifest["files"])
            self.assertIn("latest-public-safety-scan.md", manifest["files"])
            self.assertIn("latest-release-readiness.md", manifest["files"])
            self.assertIn("latest-completed-work-review.md", manifest["files"])
            index_text = (Path(report["pack_dir"]) / "PACK-INDEX.md").read_text(encoding="utf-8")
            self.assertIn("latest-connector-preview.md", index_text)
            self.assertIn("demo-story.example.md", index_text)
            self.assertIn("MANIFEST.json", index_text)
            self.assertIn("Portable AI Assets demo arc", index_text)

    def test_build_public_release_pack_report_copies_public_surface_and_redacts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            (tmp / "docs").mkdir(parents=True)
            (tmp / "schemas").mkdir(parents=True)
            (tmp / "bootstrap" / "setup").mkdir(parents=True)
            (tmp / "bootstrap" / "reports").mkdir(parents=True)
            (tmp / "adapters" / "registry").mkdir(parents=True)
            (tmp / "sample-assets").mkdir(parents=True)
            (tmp / "examples" / "redacted").mkdir(parents=True)
            (tmp / "memory" / "profile").mkdir(parents=True)
            private_fixture_path = Path.home() / "private"
            expected_redacted_private_path = "/Users/example/private" if str(private_fixture_path).startswith("/Users/") else "/home/example/private"
            (tmp / "README.md").write_text(f"# Demo\nLocal {private_fixture_path}\n", encoding="utf-8")
            (tmp / "CONTRIBUTING.md").write_text("# Contributing\n", encoding="utf-8")
            (tmp / "docs" / "architecture.md").write_text("# Architecture\n", encoding="utf-8")
            (tmp / "schemas" / "README.md").write_text("# Schemas\n", encoding="utf-8")
            (tmp / "bootstrap" / "setup" / "bootstrap-ai-assets.sh").write_text("#!/usr/bin/env bash\n", encoding="utf-8")
            (tmp / "adapters" / "registry" / "demo.yaml").write_text("name: demo\n", encoding="utf-8")
            (tmp / "sample-assets" / "README.md").write_text("# Samples\n", encoding="utf-8")
            (tmp / "examples" / "redacted" / "README.md").write_text("# Redacted\n", encoding="utf-8")
            (tmp / "memory" / "profile" / "secret.md").write_text("private memory\n", encoding="utf-8")
            (tmp / "bootstrap" / "reports" / "latest-public-safety-scan.json").write_text('{"summary":{"status":"pass"}}', encoding="utf-8")
            (tmp / "bootstrap" / "reports" / "latest-release-readiness.json").write_text('{"summary":{"readiness":"ready"}}', encoding="utf-8")
            report = bootstrap_ai_assets.build_public_release_pack_report(tmp)
            pack_dir = Path(report["pack_dir"])
            self.assertEqual(report["mode"], "public-release-pack")
            self.assertTrue((pack_dir / "MANIFEST.json").is_file())
            self.assertTrue((pack_dir / "CHECKSUMS.sha256").is_file())
            self.assertTrue((pack_dir / "PACK-INDEX.md").is_file())
            self.assertTrue((pack_dir / "README.md").is_file())
            self.assertFalse((pack_dir / "memory" / "profile" / "secret.md").exists())
            self.assertIn(expected_redacted_private_path, (pack_dir / "README.md").read_text(encoding="utf-8"))
            manifest = __import__("json").loads((pack_dir / "MANIFEST.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["pack_kind"], "public-release-pack")
            self.assertEqual(manifest["public_safety_status"], "pass")
            self.assertEqual(manifest["release_readiness"], "ready")

    def test_public_release_archive_and_smoke_test_reports_pass_for_generated_pack(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            (tmp / "docs").mkdir(parents=True)
            (tmp / "schemas").mkdir(parents=True)
            (tmp / "bootstrap" / "setup").mkdir(parents=True)
            (tmp / "bootstrap" / "reports").mkdir(parents=True)
            (tmp / "sample-assets").mkdir(parents=True)
            (tmp / "examples" / "redacted").mkdir(parents=True)
            (tmp / "README.md").write_text("# Demo\n", encoding="utf-8")
            (tmp / "CONTRIBUTING.md").write_text("# Contributing\n", encoding="utf-8")
            (tmp / "schemas" / "README.md").write_text("# Schemas\n", encoding="utf-8")
            source_py = Path(bootstrap_ai_assets.__file__).read_text(encoding="utf-8")
            source_sh = Path(__file__).resolve().parents[1] / "bootstrap" / "setup" / "bootstrap-ai-assets.sh"
            (tmp / "bootstrap" / "setup" / "bootstrap_ai_assets.py").write_text(source_py, encoding="utf-8")
            (tmp / "bootstrap" / "setup" / "bootstrap-ai-assets.sh").write_text(source_sh.read_text(encoding="utf-8"), encoding="utf-8")
            (tmp / "bootstrap" / "setup" / "portable_ai_assets_paths.py").write_text((Path(__file__).resolve().parents[1] / "bootstrap" / "setup" / "portable_ai_assets_paths.py").read_text(encoding="utf-8"), encoding="utf-8")
            (tmp / "bootstrap" / "reports" / "latest-public-safety-scan.json").write_text('{"summary":{"status":"pass"}}', encoding="utf-8")
            (tmp / "bootstrap" / "reports" / "latest-release-readiness.json").write_text('{"summary":{"readiness":"ready"}}', encoding="utf-8")
            pack_report = bootstrap_ai_assets.build_public_release_pack_report(tmp)
            archive_report = bootstrap_ai_assets.build_public_release_archive_report(tmp)
            self.assertTrue(Path(archive_report["archive_path"]).is_file())
            self.assertTrue(Path(archive_report["checksum_path"]).is_file())
            self.assertEqual(archive_report["summary"]["file_count"], pack_report["summary"]["files_in_pack"] + 3)
            smoke_report = bootstrap_ai_assets.build_public_release_smoke_test_report(tmp)
            self.assertEqual(smoke_report["mode"], "public-release-smoke-test")
            self.assertEqual(smoke_report["summary"]["status"], "pass")
            self.assertEqual(smoke_report["summary"]["failed"], 0)

    def test_github_publish_check_generates_materials_and_metadata(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            (tmp / "docs").mkdir(parents=True)
            (tmp / "bootstrap" / "reports").mkdir(parents=True)
            (tmp / "dist").mkdir(parents=True)
            (tmp / "README.md").write_text("# Demo\n", encoding="utf-8")
            (tmp / "CONTRIBUTING.md").write_text("# Contributing\n", encoding="utf-8")
            (tmp / "docs" / "security-model.md").write_text("# Security model\n", encoding="utf-8")
            (tmp / "docs" / "open-source-release-plan.md").write_text("# Release plan\n", encoding="utf-8")
            archive = tmp / "dist" / "portable-ai-assets-public-demo.tar.gz"
            archive.write_bytes(b"demo")
            (tmp / "bootstrap" / "reports" / "latest-public-safety-scan.json").write_text('{"summary":{"status":"pass"}}', encoding="utf-8")
            (tmp / "bootstrap" / "reports" / "latest-release-readiness.json").write_text('{"summary":{"readiness":"ready"}}', encoding="utf-8")
            (tmp / "bootstrap" / "reports" / "latest-public-release-pack.json").write_text('{"summary":{"files_in_pack":1}}', encoding="utf-8")
            (tmp / "bootstrap" / "reports" / "latest-public-release-archive.json").write_text(__import__("json").dumps({"archive_path": str(archive), "summary": {"archive_sha256": "abc"}}), encoding="utf-8")
            (tmp / "bootstrap" / "reports" / "latest-public-release-smoke-test.json").write_text('{"summary":{"status":"pass"}}', encoding="utf-8")
            report = bootstrap_ai_assets.build_github_publish_check_report(tmp)
            self.assertEqual(report["mode"], "github-publish-check")
            self.assertEqual(report["summary"]["status"], "ready")
            self.assertTrue((tmp / "LICENSE").is_file())
            self.assertTrue((tmp / "SECURITY.md").is_file())
            self.assertTrue((tmp / "CHANGELOG.md").is_file())
            self.assertTrue((tmp / "RELEASE_NOTES-v0.1.md").is_file())
            self.assertTrue((tmp / "docs" / "github-publishing.md").is_file())
            self.assertIn("ai-memory", report["github"]["topics"])

    def test_public_repo_staging_builds_git_ready_tree(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            (tmp / "docs").mkdir(parents=True)
            (tmp / "schemas").mkdir(parents=True)
            (tmp / "bootstrap" / "setup").mkdir(parents=True)
            (tmp / "bootstrap" / "reports").mkdir(parents=True)
            (tmp / "sample-assets").mkdir(parents=True)
            (tmp / "examples" / "redacted").mkdir(parents=True)
            (tmp / "memory" / "profile").mkdir(parents=True)
            (tmp / "README.md").write_text("# Demo\n", encoding="utf-8")
            (tmp / "CONTRIBUTING.md").write_text("# Contributing\n", encoding="utf-8")
            (tmp / ".gitignore").write_text("bootstrap/reports/\nmemory/\n", encoding="utf-8")
            (tmp / "schemas" / "README.md").write_text("# Schemas\n", encoding="utf-8")
            (tmp / "docs" / "security-model.md").write_text("# Security\n", encoding="utf-8")
            (tmp / "docs" / "open-source-release-plan.md").write_text("# Release\n", encoding="utf-8")
            (tmp / "memory" / "profile" / "private.md").write_text("private\n", encoding="utf-8")
            (tmp / "bootstrap" / "reports" / "latest-public-safety-scan.json").write_text('{"summary":{"status":"pass"}}', encoding="utf-8")
            (tmp / "bootstrap" / "reports" / "latest-release-readiness.json").write_text('{"summary":{"readiness":"ready"}}', encoding="utf-8")
            (tmp / "bootstrap" / "setup" / "bootstrap_ai_assets.py").write_text(Path(bootstrap_ai_assets.__file__).read_text(encoding="utf-8"), encoding="utf-8")
            repo_root = Path(__file__).resolve().parents[1]
            (tmp / "bootstrap" / "setup" / "bootstrap-ai-assets.sh").write_text((repo_root / "bootstrap" / "setup" / "bootstrap-ai-assets.sh").read_text(encoding="utf-8"), encoding="utf-8")
            (tmp / "bootstrap" / "setup" / "portable_ai_assets_paths.py").write_text((repo_root / "bootstrap" / "setup" / "portable_ai_assets_paths.py").read_text(encoding="utf-8"), encoding="utf-8")
            (tmp / "bin").mkdir(parents=True)
            paa_source = repo_root / "bin" / "paa"
            (tmp / "bin" / "paa").write_text(paa_source.read_text(encoding="utf-8"), encoding="utf-8")
            (tmp / "bin" / "paa").chmod(0o755)
            report = bootstrap_ai_assets.build_public_repo_staging_report(tmp)
            staging_dir = Path(report["staging_dir"])
            self.assertEqual(report["mode"], "public-repo-staging")
            self.assertEqual(report["summary"]["status"], "ready")
            self.assertTrue((staging_dir / ".git").is_dir())
            self.assertTrue((staging_dir / "GITHUB-PUBLISH-CHECKLIST.md").is_file())
            checklist_text = (staging_dir / "GITHUB-PUBLISH-CHECKLIST.md").read_text(encoding="utf-8")
            self.assertIn("paa install", checklist_text)
            self.assertIn("bootstrap/reports/latest-*", checklist_text)
            self.assertIn("static sanitized snapshots", checklist_text)
            self.assertIn("not live GitHub state", checklist_text)
            self.assertTrue((staging_dir / "STAGING-MANIFEST.json").is_file())
            self.assertTrue((staging_dir / "bin" / "paa").is_file())
            self.assertTrue(os.access(staging_dir / "bin" / "paa", os.X_OK))
            self.assertFalse((staging_dir / "memory" / "profile" / "private.md").exists())
            self.assertEqual(report["summary"]["forbidden_findings"], 0)

    def test_public_staging_labels_copied_latest_reports_as_static_snapshots(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            for rel in ["docs", "schemas", "bootstrap/setup", "bootstrap/reports", "sample-assets", "examples/redacted"]:
                (tmp / rel).mkdir(parents=True)
            (tmp / "README.md").write_text("# Demo\n", encoding="utf-8")
            (tmp / "CONTRIBUTING.md").write_text("# Contributing\n", encoding="utf-8")
            (tmp / ".gitignore").write_text("bootstrap/reports/\nmemory/\n", encoding="utf-8")
            (tmp / "schemas" / "README.md").write_text("# Schemas\n", encoding="utf-8")
            (tmp / "docs" / "security-model.md").write_text("# Security\n", encoding="utf-8")
            (tmp / "docs" / "open-source-release-plan.md").write_text("# Release\n", encoding="utf-8")
            reports = tmp / "bootstrap" / "reports"
            (reports / "latest-public-safety-scan.json").write_text('{"summary":{"status":"pass"}}', encoding="utf-8")
            (reports / "latest-release-readiness.json").write_text('{"summary":{"readiness":"ready"}}', encoding="utf-8")
            private_root = str(Path.home() / "AI-Assets")
            (reports / "latest-public-repo-staging-history-preflight.json").write_text(__import__("json").dumps({
                "summary": {"status": "needs-history-reattach", "head_rev": None},
                "root": private_root,
            }), encoding="utf-8")
            (reports / "latest-public-repo-staging-history-preflight.md").write_text("# History preflight\nstatus=needs-history-reattach\n", encoding="utf-8")
            repo_root = Path(__file__).resolve().parents[1]
            (tmp / "bootstrap" / "setup" / "bootstrap_ai_assets.py").write_text(Path(bootstrap_ai_assets.__file__).read_text(encoding="utf-8"), encoding="utf-8")
            (tmp / "bootstrap" / "setup" / "bootstrap-ai-assets.sh").write_text((repo_root / "bootstrap" / "setup" / "bootstrap-ai-assets.sh").read_text(encoding="utf-8"), encoding="utf-8")
            (tmp / "bootstrap" / "setup" / "portable_ai_assets_paths.py").write_text((repo_root / "bootstrap" / "setup" / "portable_ai_assets_paths.py").read_text(encoding="utf-8"), encoding="utf-8")
            (tmp / "bin").mkdir(parents=True)
            (tmp / "bin" / "paa").write_text((repo_root / "bin" / "paa").read_text(encoding="utf-8"), encoding="utf-8")
            (tmp / "bin" / "paa").chmod(0o755)

            report = bootstrap_ai_assets.build_public_repo_staging_report(tmp)
            staging_dir = Path(report["staging_dir"])
            copied_json = __import__("json").loads((staging_dir / "bootstrap" / "reports" / "latest-public-repo-staging-history-preflight.json").read_text(encoding="utf-8"))
            copied_md = (staging_dir / "bootstrap" / "reports" / "latest-public-repo-staging-history-preflight.md").read_text(encoding="utf-8")
            reports_readme = (staging_dir / "bootstrap" / "reports" / "README.md").read_text(encoding="utf-8")

            self.assertEqual(copied_json["summary"]["status"], "needs-history-reattach")
            self.assertTrue(copied_json["public_snapshot_notice"]["static_sanitized_snapshot"])
            self.assertIn("not live GitHub state", copied_json["public_snapshot_notice"]["message"])
            self.assertIn("Public snapshot notice", copied_md)
            self.assertIn("static sanitized snapshots", reports_readme)
            self.assertNotIn(private_root, (staging_dir / "bootstrap" / "reports" / "latest-public-repo-staging-history-preflight.json").read_text(encoding="utf-8"))

    def test_public_roadmap_documents_latest_report_snapshot_clarity(self):
        repo_root = Path(__file__).resolve().parents[1]
        roadmap = (repo_root / "docs" / "public-roadmap.md").read_text(encoding="utf-8")
        self.assertIn("### Phase 135 — Public latest report snapshot clarity ✅", roadmap)
        self.assertIn("static sanitized snapshots", roadmap)
        self.assertIn("not live GitHub state", roadmap)
        self.assertIn("### Phase 136 — Public checklist/report-surface clarity ✅", roadmap)
        self.assertIn("bootstrap/reports/latest-*", roadmap)

    def test_restore_readiness_smoke_plan_documents_private_public_recovery_path(self):
        repo_root = Path(__file__).resolve().parents[1]
        restore_doc = (repo_root / "docs" / "restore-readiness.md").read_text(encoding="utf-8")
        readme = (repo_root / "README.md").read_text(encoding="utf-8")

        required_restore_tokens = [
            "wangtao1025/ai-assets-private",
            "wangtao1025/portable-ai-assets",
            "asset_root",
            "public engine repo",
            "private canonical assets repo",
            "restore smoke test",
            "do not move v0.1.0",
            "do not move v0.1.1",
            "v0.1.2",
            "restore is not release work",
            "v0.1.1",
            "bootstrap/setup/bootstrap-ai-assets.sh --engine-root \"$PWD\" --asset-root \"$PWD\" --completed-work-review --both",
            "python3 -m unittest discover -s tests -p test_bootstrap_phase4.py",
            "--engine-root",
            "--asset-root",
            "--restore-smoke-check --both",
            "--engine-root \"$PWD\" --asset-root \"$PWD\"",
            "fresh clone may report blocked",
            "regenerate prerequisite reports",
        ]
        for token in required_restore_tokens:
            self.assertIn(token, restore_doc)
        self.assertIn("docs/restore-readiness.md", readme)
        self.assertIn("restore smoke", readme)

    def test_restore_readiness_command_snippets_use_both_root_overrides(self):
        repo_root = Path(__file__).resolve().parents[1]
        docs = (repo_root / "docs" / "restore-readiness.md").read_text(encoding="utf-8")
        command_lines = [
            line.strip()
            for line in docs.splitlines()
            if "bootstrap/setup/bootstrap-ai-assets.sh" in line
        ]

        self.assertTrue(command_lines, "restore-readiness.md should document bootstrap command snippets")
        stale_restore_commands = [
            line
            for line in command_lines
            if ("--restore-smoke-check" in line or "--completed-work-review" in line or "--show-config" in line)
            and ("--engine-root \"$PWD\"" not in line or "--asset-root \"$PWD\"" not in line)
        ]

        self.assertEqual([], stale_restore_commands)

    def test_restore_smoke_check_reports_fresh_clone_prerequisite_regeneration(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            (tmp / "docs").mkdir(parents=True)
            (tmp / "bootstrap" / "reports").mkdir(parents=True)
            (tmp / "docs" / "restore-readiness.md").write_text(
                "wangtao1025/ai-assets-private\n"
                "wangtao1025/portable-ai-assets\n"
                "asset_root\n"
                "public engine repo\n"
                "private canonical assets repo\n"
                "restore smoke test\n"
                "do not move v0.1.0\n"
                "v0.1.1\n"
                "bootstrap/setup/bootstrap-ai-assets.sh --completed-work-review --both\n"
                "--engine-root\n"
                "--asset-root\n"
                "--restore-smoke-check --both\n"
                "fresh clone may report blocked\n"
                "regenerate prerequisite reports\n",
                encoding="utf-8",
            )
            previous_paths = dict(bootstrap_ai_assets.CURRENT_RUNTIME_PATHS)
            try:
                bootstrap_ai_assets.configure_runtime_paths(asset_root_override=str(tmp), engine_root_override=str(tmp))
                report = bootstrap_ai_assets.build_restore_smoke_check_report()
            finally:
                bootstrap_ai_assets.configure_runtime_paths(
                    config_path=previous_paths.get("config_path"),
                    asset_root_override=previous_paths.get("asset_root"),
                )

        self.assertEqual(report["mode"], "restore-smoke-check")
        self.assertIn(report["summary"]["status"], [
            "ready-with-prerequisite-regeneration-needed",
            "ready-with-config-redirection-and-prerequisite-regeneration-needed",
        ])
        self.assertFalse(report["summary"]["executes_anything"])
        self.assertTrue(report["restore_readiness_doc"]["present"])
        self.assertIn("latest-completed-work-review.json", report["fresh_clone_prerequisites"]["missing_reports"])
        self.assertTrue(report["fresh_clone_prerequisites"]["missing_reports_expected_in_fresh_clone"])
        recommendations = "\n".join(report["recommendations"])
        self.assertIn("--engine-root", recommendations)
        self.assertIn("--asset-root", recommendations)
        self.assertIn("--restore-smoke-check --both", recommendations)
        self.assertIn("do not move v0.1.0", report["public_release_boundary"])

    def test_restore_smoke_check_reports_config_redirection_even_when_prerequisites_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            engine = tmp / "configured-engine"
            checkout = tmp / "asset-checkout"
            (checkout / "docs").mkdir(parents=True)
            (checkout / "bootstrap" / "reports").mkdir(parents=True)
            (checkout / "docs" / "restore-readiness.md").write_text(
                "wangtao1025/ai-assets-private\n"
                "wangtao1025/portable-ai-assets\n"
                "asset_root\n"
                "restore smoke test\n"
                "do not move v0.1.0\n"
                "v0.1.1\n"
                "--engine-root\n"
                "--asset-root\n"
                "fresh clone may report blocked\n"
                "regenerate prerequisite reports\n",
                encoding="utf-8",
            )
            engine.mkdir(parents=True)
            previous_paths = dict(bootstrap_ai_assets.CURRENT_RUNTIME_PATHS)
            previous_engine = bootstrap_ai_assets.ENGINE_ROOT
            try:
                bootstrap_ai_assets.configure_runtime_paths(asset_root_override=str(checkout))
                bootstrap_ai_assets.ENGINE_ROOT = engine
                report = bootstrap_ai_assets.build_restore_smoke_check_report()
            finally:
                bootstrap_ai_assets.ENGINE_ROOT = previous_engine
                bootstrap_ai_assets.configure_runtime_paths(
                    config_path=previous_paths.get("config_path"),
                    asset_root_override=previous_paths.get("asset_root"),
                )

        self.assertEqual(report["summary"]["status"], "ready-with-config-redirection-and-prerequisite-regeneration-needed")
        self.assertTrue(report["fresh_clone_prerequisites"]["missing_reports_expected_in_fresh_clone"])
        self.assertFalse(report["config_diagnostics"]["engine_root_matches_script_checkout"])
        self.assertIn("--engine-root", "\n".join(report["recommendations"]))

    def test_public_release_pack_and_staging_preserve_markdown_diagnostics_reports(self):
        diagnostics_text = (
            "# Diagnostics\n"
            "- phase102_report_invalid_fields: `['agent_side_complete', 'remote_issues_created', 'warn']`\n"
            "- evidence: invalid_fields=agent_side_complete,remote_issues_created,warn; "
            "agent_side_complete_type=str; remote_issues_created_type=str; warn_type=bool\n"
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            for rel in [
                "docs",
                "schemas",
                "bootstrap/setup",
                "bootstrap/reports",
                "sample-assets",
                "examples/redacted",
            ]:
                (tmp / rel).mkdir(parents=True)
            (tmp / "README.md").write_text("# Demo\n", encoding="utf-8")
            (tmp / "CONTRIBUTING.md").write_text("# Contributing\n", encoding="utf-8")
            (tmp / ".gitignore").write_text("bootstrap/reports/\nmemory/\n", encoding="utf-8")
            (tmp / "schemas" / "README.md").write_text("# Schemas\n", encoding="utf-8")
            (tmp / "docs" / "security-model.md").write_text("# Security\n", encoding="utf-8")
            (tmp / "docs" / "open-source-release-plan.md").write_text("# Release\n", encoding="utf-8")
            reports = tmp / "bootstrap" / "reports"
            (reports / "latest-public-safety-scan.json").write_text('{"summary":{"status":"pass"}}', encoding="utf-8")
            (reports / "latest-release-readiness.json").write_text('{"summary":{"readiness":"ready"}}', encoding="utf-8")
            (reports / "latest-agent-complete-phase102-rollup-evidence-failclosed-review.md").write_text(diagnostics_text, encoding="utf-8")
            (reports / "latest-completed-work-review.md").write_text(diagnostics_text, encoding="utf-8")
            repo_root = Path(__file__).resolve().parents[1]
            (tmp / "bootstrap" / "setup" / "bootstrap_ai_assets.py").write_text(Path(bootstrap_ai_assets.__file__).read_text(encoding="utf-8"), encoding="utf-8")
            (tmp / "bootstrap" / "setup" / "bootstrap-ai-assets.sh").write_text((repo_root / "bootstrap" / "setup" / "bootstrap-ai-assets.sh").read_text(encoding="utf-8"), encoding="utf-8")
            (tmp / "bootstrap" / "setup" / "portable_ai_assets_paths.py").write_text((repo_root / "bootstrap" / "setup" / "portable_ai_assets_paths.py").read_text(encoding="utf-8"), encoding="utf-8")

            pack_report = bootstrap_ai_assets.build_public_release_pack_report(tmp)
            pack_dir = Path(pack_report["pack_dir"])
            staging_report = bootstrap_ai_assets.build_public_repo_staging_report(tmp)
            staging_dir = Path(staging_report["staging_dir"])

            for base in [pack_dir, staging_dir]:
                for report_name in [
                    "latest-agent-complete-phase102-rollup-evidence-failclosed-review.md",
                    "latest-completed-work-review.md",
                ]:
                    copied = base / "bootstrap" / "reports" / report_name
                    self.assertTrue(copied.is_file(), f"missing copied diagnostics report: {copied}")
                    copied_text = copied.read_text(encoding="utf-8")
                    self.assertIn("phase102_report_invalid_fields", copied_text)
                    self.assertIn("invalid_fields=agent_side_complete,remote_issues_created,warn", copied_text)
                    self.assertIn("agent_side_complete_type=str", copied_text)
                    self.assertIn("remote_issues_created_type=str", copied_text)
                    self.assertIn("warn_type=bool", copied_text)

    def test_public_repo_staging_status_and_github_dry_run_are_non_executing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            staging = tmp / "dist" / "github-staging" / "portable-ai-assets"
            staging.mkdir(parents=True)
            (staging / "README.md").write_text("# Demo\n", encoding="utf-8")
            bootstrap_ai_assets.run_git_command(staging, ["init"])
            status_report = bootstrap_ai_assets.build_public_repo_staging_status_report(tmp)
            self.assertEqual(status_report["mode"], "public-repo-staging-status")
            self.assertTrue(status_report["summary"]["git_initialized"])
            self.assertEqual(status_report["summary"]["changed_files"], 1)
            self.assertFalse(status_report["summary"]["remote_configured"])
            dry_run = bootstrap_ai_assets.build_github_publish_dry_run_report(tmp)
            self.assertEqual(dry_run["mode"], "github-publish-dry-run")
            self.assertFalse(dry_run["summary"]["executes_anything"])
            self.assertEqual(dry_run["summary"]["status"], "ready")
            self.assertIn("git commit", "\n".join(command["command"] for command in dry_run["commands"]))
            self.assertTrue(all(command["executes"] is False for command in dry_run["commands"]))

    def test_github_publish_dry_run_uses_new_tag_when_v010_already_points_behind_head(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            staging = tmp / "dist" / "github-staging" / "portable-ai-assets"
            staging.mkdir(parents=True)
            (staging / "README.md").write_text("# Demo\n", encoding="utf-8")
            bootstrap_ai_assets.run_git_command(staging, ["init"])
            bootstrap_ai_assets.run_git_command(staging, ["config", "user.email", "test@example.invalid"])
            bootstrap_ai_assets.run_git_command(staging, ["config", "user.name", "Test User"])
            bootstrap_ai_assets.run_git_command(staging, ["add", "README.md"])
            bootstrap_ai_assets.run_git_command(staging, ["commit", "-m", "Initial public release: Portable AI Assets v0.1.0"])
            bootstrap_ai_assets.run_git_command(staging, ["tag", "v0.1.0"])
            (staging / "README.md").write_text("# Demo\n\nCLI lifecycle polish\n", encoding="utf-8")
            bootstrap_ai_assets.run_git_command(staging, ["add", "README.md"])
            bootstrap_ai_assets.run_git_command(staging, ["commit", "-m", "Update public staging with paa CLI lifecycle polish"])

            dry_run = bootstrap_ai_assets.build_github_publish_dry_run_report(tmp)

            self.assertEqual(dry_run["summary"]["status"], "needs-review")
            self.assertEqual(dry_run["suggested_release_tag"], "v0.1.1")
            self.assertIn("existing-v010-tag-behind-head", [check["name"] for check in dry_run["checks"]])
            self.assertNotIn("git tag v0.1.0", "\n".join(command["command"] for command in dry_run["commands"]))
            self.assertIn("git tag v0.1.1", "\n".join(command["command"] for command in dry_run["commands"]))
            self.assertTrue(all(command["executes"] is False for command in dry_run["commands"]))

    def test_github_publish_dry_run_advances_after_v011_tag_already_points_at_head(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            staging = tmp / "dist" / "github-staging" / "portable-ai-assets"
            staging.mkdir(parents=True)
            (staging / "README.md").write_text("# Demo\n", encoding="utf-8")
            bootstrap_ai_assets.run_git_command(staging, ["init"])
            bootstrap_ai_assets.run_git_command(staging, ["config", "user.email", "test@example.invalid"])
            bootstrap_ai_assets.run_git_command(staging, ["config", "user.name", "Test User"])
            bootstrap_ai_assets.run_git_command(staging, ["add", "README.md"])
            bootstrap_ai_assets.run_git_command(staging, ["commit", "-m", "Initial public release: Portable AI Assets v0.1.0"])
            bootstrap_ai_assets.run_git_command(staging, ["tag", "v0.1.0"])
            (staging / "README.md").write_text("# Demo\n\nPost-main decision packet wording\n", encoding="utf-8")
            bootstrap_ai_assets.run_git_command(staging, ["add", "README.md"])
            bootstrap_ai_assets.run_git_command(staging, ["commit", "-m", "Publish post-main decision packet wording"])
            bootstrap_ai_assets.run_git_command(staging, ["tag", "v0.1.1"])

            dry_run = bootstrap_ai_assets.build_github_publish_dry_run_report(tmp)
            command_text = "\n".join(command["command"] for command in dry_run["commands"])
            checks_by_name = {check["name"]: check for check in dry_run["checks"]}

            self.assertEqual(dry_run["summary"]["status"], "needs-review")
            self.assertEqual(dry_run["suggested_release_tag"], "v0.1.2")
            self.assertEqual(checks_by_name["existing-v011-tag-at-head"]["status"], "warn")
            self.assertNotIn("git tag v0.1.1", command_text)
            self.assertIn("git tag v0.1.2", command_text)
            self.assertIn("v0.1.1 already points at HEAD", "\n".join(dry_run["recommendations"]))
            self.assertTrue(all(command["executes"] is False for command in dry_run["commands"]))

    def test_github_publish_dry_run_advances_after_v011_tag_points_behind_head(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            staging = tmp / "dist" / "github-staging" / "portable-ai-assets"
            staging.mkdir(parents=True)
            (staging / "README.md").write_text("# Demo\n", encoding="utf-8")
            bootstrap_ai_assets.run_git_command(staging, ["init"])
            bootstrap_ai_assets.run_git_command(staging, ["config", "user.email", "test@example.invalid"])
            bootstrap_ai_assets.run_git_command(staging, ["config", "user.name", "Test User"])
            bootstrap_ai_assets.run_git_command(staging, ["add", "README.md"])
            bootstrap_ai_assets.run_git_command(staging, ["commit", "-m", "Initial public release: Portable AI Assets v0.1.0"])
            bootstrap_ai_assets.run_git_command(staging, ["tag", "v0.1.0"])
            (staging / "README.md").write_text("# Demo\n\nv0.1.1 release\n", encoding="utf-8")
            bootstrap_ai_assets.run_git_command(staging, ["add", "README.md"])
            bootstrap_ai_assets.run_git_command(staging, ["commit", "-m", "Portable AI Assets v0.1.1"])
            bootstrap_ai_assets.run_git_command(staging, ["tag", "v0.1.1"])
            (staging / "README.md").write_text("# Demo\n\nRelease-aware packet update\n", encoding="utf-8")
            bootstrap_ai_assets.run_git_command(staging, ["add", "README.md"])
            bootstrap_ai_assets.run_git_command(staging, ["commit", "-m", "Publish release-aware publication packet updates"])

            dry_run = bootstrap_ai_assets.build_github_publish_dry_run_report(tmp)
            command_text = "\n".join(command["command"] for command in dry_run["commands"])
            checks_by_name = {check["name"]: check for check in dry_run["checks"]}

            self.assertEqual(dry_run["suggested_release_tag"], "v0.1.2")
            self.assertEqual(checks_by_name["existing-v011-tag-behind-head"]["status"], "warn")
            self.assertNotIn("git tag v0.1.1", command_text)
            self.assertIn("git tag v0.1.2", command_text)
            self.assertTrue(all(command["executes"] is False for command in dry_run["commands"]))

    def test_github_publish_dry_run_advances_after_v012_tag_already_points_at_head(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            staging = tmp / "dist" / "github-staging" / "portable-ai-assets"
            staging.mkdir(parents=True)
            (staging / "README.md").write_text("# Demo\n", encoding="utf-8")
            bootstrap_ai_assets.run_git_command(staging, ["init"])
            bootstrap_ai_assets.run_git_command(staging, ["config", "user.email", "test@example.invalid"])
            bootstrap_ai_assets.run_git_command(staging, ["config", "user.name", "Test User"])
            bootstrap_ai_assets.run_git_command(staging, ["add", "README.md"])
            bootstrap_ai_assets.run_git_command(staging, ["commit", "-m", "Initial public release: Portable AI Assets v0.1.0"])
            bootstrap_ai_assets.run_git_command(staging, ["tag", "v0.1.0"])
            (staging / "README.md").write_text("# Demo\n\nv0.1.1 release\n", encoding="utf-8")
            bootstrap_ai_assets.run_git_command(staging, ["add", "README.md"])
            bootstrap_ai_assets.run_git_command(staging, ["commit", "-m", "Portable AI Assets v0.1.1"])
            bootstrap_ai_assets.run_git_command(staging, ["tag", "v0.1.1"])
            (staging / "README.md").write_text("# Demo\n\nv0.1.2 release\n", encoding="utf-8")
            bootstrap_ai_assets.run_git_command(staging, ["add", "README.md"])
            bootstrap_ai_assets.run_git_command(staging, ["commit", "-m", "Portable AI Assets v0.1.2"])
            bootstrap_ai_assets.run_git_command(staging, ["tag", "v0.1.2"])

            dry_run = bootstrap_ai_assets.build_github_publish_dry_run_report(tmp)
            command_text = "\n".join(command["command"] for command in dry_run["commands"])
            checks_by_name = {check["name"]: check for check in dry_run["checks"]}

            self.assertEqual(dry_run["suggested_release_tag"], "v0.1.3")
            self.assertEqual(checks_by_name["existing-v012-tag-at-head"]["status"], "warn")
            self.assertNotIn("git tag v0.1.2", command_text)
            self.assertIn("git tag v0.1.3", command_text)
            self.assertIn("v0.1.2 already points at HEAD", "\n".join(dry_run["recommendations"]))
            self.assertTrue(all(command["executes"] is False for command in dry_run["commands"]))

    def test_github_publish_dry_run_advances_after_v012_tag_points_behind_head(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            staging = tmp / "dist" / "github-staging" / "portable-ai-assets"
            staging.mkdir(parents=True)
            (staging / "README.md").write_text("# Demo\n", encoding="utf-8")
            bootstrap_ai_assets.run_git_command(staging, ["init"])
            bootstrap_ai_assets.run_git_command(staging, ["config", "user.email", "test@example.invalid"])
            bootstrap_ai_assets.run_git_command(staging, ["config", "user.name", "Test User"])
            bootstrap_ai_assets.run_git_command(staging, ["add", "README.md"])
            bootstrap_ai_assets.run_git_command(staging, ["commit", "-m", "Initial public release: Portable AI Assets v0.1.0"])
            bootstrap_ai_assets.run_git_command(staging, ["tag", "v0.1.0"])
            (staging / "README.md").write_text("# Demo\n\nv0.1.1 release\n", encoding="utf-8")
            bootstrap_ai_assets.run_git_command(staging, ["add", "README.md"])
            bootstrap_ai_assets.run_git_command(staging, ["commit", "-m", "Portable AI Assets v0.1.1"])
            bootstrap_ai_assets.run_git_command(staging, ["tag", "v0.1.1"])
            (staging / "README.md").write_text("# Demo\n\nv0.1.2 release\n", encoding="utf-8")
            bootstrap_ai_assets.run_git_command(staging, ["add", "README.md"])
            bootstrap_ai_assets.run_git_command(staging, ["commit", "-m", "Portable AI Assets v0.1.2"])
            bootstrap_ai_assets.run_git_command(staging, ["tag", "v0.1.2"])
            (staging / "README.md").write_text("# Demo\n\nPost v0.1.2 hardening\n", encoding="utf-8")
            bootstrap_ai_assets.run_git_command(staging, ["add", "README.md"])
            bootstrap_ai_assets.run_git_command(staging, ["commit", "-m", "Post v0.1.2 hardening"])

            dry_run = bootstrap_ai_assets.build_github_publish_dry_run_report(tmp)
            command_text = "\n".join(command["command"] for command in dry_run["commands"])
            checks_by_name = {check["name"]: check for check in dry_run["checks"]}

            self.assertEqual(dry_run["suggested_release_tag"], "v0.1.3")
            self.assertEqual(checks_by_name["existing-v012-tag-behind-head"]["status"], "warn")
            self.assertNotIn("git tag v0.1.2", command_text)
            self.assertIn("git tag v0.1.3", command_text)
            self.assertTrue(all(command["executes"] is False for command in dry_run["commands"]))

    def test_github_publish_dry_run_uses_new_tag_when_existing_tag_context_lacks_git_history(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            staging = tmp / "dist" / "github-staging" / "portable-ai-assets"
            staging.mkdir(parents=True)
            (staging / "README.md").write_text("# Demo\n", encoding="utf-8")
            (staging / "GITHUB-PUBLISH-CHECKLIST.md").write_text(
                "# Checklist\n- Existing release tag: v0.1.0; do not move it. Use a new tag (for example v0.1.1) for follow-up releases.\n",
                encoding="utf-8",
            )
            bootstrap_ai_assets.run_git_command(staging, ["init"])

            dry_run = bootstrap_ai_assets.build_github_publish_dry_run_report(tmp)

            self.assertEqual(dry_run["summary"]["status"], "needs-review")
            self.assertEqual(dry_run["suggested_release_tag"], "v0.1.1")
            self.assertIn("release-tag-context-without-git-history", [check["name"] for check in dry_run["checks"]])
            self.assertNotIn("git tag v0.1.0", "\n".join(command["command"] for command in dry_run["commands"]))
            self.assertIn("git tag v0.1.1", "\n".join(command["command"] for command in dry_run["commands"]))
            self.assertTrue(all(command["executes"] is False for command in dry_run["commands"]))

    def test_public_repo_staging_history_preflight_blocks_generated_staging_without_history(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            staging = tmp / "dist" / "github-staging" / "portable-ai-assets"
            staging.mkdir(parents=True)
            (staging / "GITHUB-PUBLISH-CHECKLIST.md").write_text(
                "# Checklist\n- Existing release tag: v0.1.0; do not move it. Use a new tag (for example v0.1.1) for follow-up releases.\n",
                encoding="utf-8",
            )
            bootstrap_ai_assets.run_git_command(staging, ["init"])

            report = bootstrap_ai_assets.build_public_repo_staging_history_preflight_report(tmp)
            checks_by_name = {check["name"]: check for check in report["checks"]}

            self.assertEqual(report["mode"], "public-repo-staging-history-preflight")
            self.assertEqual(report["summary"]["status"], "needs-history-reattach")
            self.assertFalse(report["summary"]["executes_anything"])
            self.assertEqual(checks_by_name["staging-head-exists"]["status"], "fail")
            self.assertEqual(checks_by_name["v010-tag-exists"]["status"], "fail")
            self.assertEqual(checks_by_name["existing-tag-context-without-history"]["status"], "warn")
            self.assertIn("reattach public history", "\n".join(report["recommendations"]).lower())
            self.assertTrue(all(step["executes"] is False for step in report["manual_history_context_steps"]))

    def test_public_repo_staging_history_preflight_recognizes_reattached_history(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            staging = tmp / "dist" / "github-staging" / "portable-ai-assets"
            staging.mkdir(parents=True)
            (staging / "README.md").write_text("# Demo\n", encoding="utf-8")
            (staging / "GITHUB-PUBLISH-CHECKLIST.md").write_text(
                "# Checklist\n- Existing release tag: v0.1.0; do not move it. Use a new tag (for example v0.1.1) for follow-up releases.\n",
                encoding="utf-8",
            )
            bootstrap_ai_assets.run_git_command(staging, ["init"])
            bootstrap_ai_assets.run_git_command(staging, ["config", "user.email", "test@example.invalid"])
            bootstrap_ai_assets.run_git_command(staging, ["config", "user.name", "Test User"])
            bootstrap_ai_assets.run_git_command(staging, ["add", "README.md"])
            bootstrap_ai_assets.run_git_command(staging, ["commit", "-m", "Initial public release: Portable AI Assets v0.1.0"])
            bootstrap_ai_assets.run_git_command(staging, ["tag", "v0.1.0"])
            (staging / "README.md").write_text("# Demo\n\nUpdate\n", encoding="utf-8")
            bootstrap_ai_assets.run_git_command(staging, ["add", "README.md"])
            bootstrap_ai_assets.run_git_command(staging, ["commit", "-m", "Update after v0.1.0"])

            report = bootstrap_ai_assets.build_public_repo_staging_history_preflight_report(tmp)
            checks_by_name = {check["name"]: check for check in report["checks"]}

            self.assertEqual(report["summary"]["status"], "ready")
            self.assertEqual(checks_by_name["staging-head-exists"]["status"], "pass")
            self.assertEqual(checks_by_name["v010-tag-exists"]["status"], "pass")
            self.assertEqual(checks_by_name["v010-behind-head"]["status"], "pass")
            self.assertFalse(report["summary"]["remote_configured"])
            self.assertFalse(report["summary"]["executes_anything"])

    def test_public_repo_staging_history_preflight_advances_recommendation_after_v011_exists(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            staging = tmp / "dist" / "github-staging" / "portable-ai-assets"
            staging.mkdir(parents=True)
            (staging / "README.md").write_text("# Demo\n", encoding="utf-8")
            (staging / "GITHUB-PUBLISH-CHECKLIST.md").write_text(
                "# Checklist\n- Existing release tag: v0.1.0; do not move it. v0.1.1 already exists; use v0.1.2 for follow-up releases.\n",
                encoding="utf-8",
            )
            bootstrap_ai_assets.run_git_command(staging, ["init"])
            bootstrap_ai_assets.run_git_command(staging, ["config", "user.email", "test@example.invalid"])
            bootstrap_ai_assets.run_git_command(staging, ["config", "user.name", "Test User"])
            bootstrap_ai_assets.run_git_command(staging, ["add", "README.md"])
            bootstrap_ai_assets.run_git_command(staging, ["commit", "-m", "Initial public release: Portable AI Assets v0.1.0"])
            bootstrap_ai_assets.run_git_command(staging, ["tag", "v0.1.0"])
            (staging / "README.md").write_text("# Demo\n\nRelease v0.1.1\n", encoding="utf-8")
            bootstrap_ai_assets.run_git_command(staging, ["add", "README.md"])
            bootstrap_ai_assets.run_git_command(staging, ["commit", "-m", "Release v0.1.1"])
            bootstrap_ai_assets.run_git_command(staging, ["tag", "v0.1.1"])
            (staging / "README.md").write_text("# Demo\n\nPost v0.1.1 hardening\n", encoding="utf-8")
            bootstrap_ai_assets.run_git_command(staging, ["add", "README.md"])
            bootstrap_ai_assets.run_git_command(staging, ["commit", "-m", "Post v0.1.1 hardening"])

            report = bootstrap_ai_assets.build_public_repo_staging_history_preflight_report(tmp)
            recommendations = "\n".join(report["recommendations"])

            self.assertEqual(report["summary"]["status"], "ready")
            expected_v011 = bootstrap_ai_assets.run_git_command(staging, ["rev-parse", "--verify", "v0.1.1^{commit}"])["output"]
            self.assertEqual(report["summary"]["v011_rev"], expected_v011)
            self.assertIn("v0.1.2", recommendations)
            self.assertIn("Do not move v0.1.1", recommendations)
            self.assertNotIn("new tag such as v0.1.1", recommendations)
            self.assertFalse(report["summary"]["executes_anything"])

    def test_manual_publication_decision_packet_summarizes_options_without_execution(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            reports = tmp / "bootstrap" / "reports"
            reports.mkdir(parents=True)
            (reports / "latest-public-repo-staging-history-preflight.json").write_text(__import__("json").dumps({
                "summary": {"status": "needs-history-reattach", "executes_anything": False, "remote_configured": False, "forbidden_findings": 0, "head_rev": None, "v010_rev": None},
            }), encoding="utf-8")
            (reports / "latest-github-publish-dry-run.json").write_text(__import__("json").dumps({
                "summary": {"status": "needs-review", "executes_anything": False, "fail": 0},
                "suggested_release_tag": "v0.1.1",
            }), encoding="utf-8")
            (reports / "latest-public-safety-scan.json").write_text('{"summary":{"status":"pass","findings":0,"blockers":0}}', encoding="utf-8")
            (reports / "latest-completed-work-review.json").write_text(__import__("json").dumps({
                "summary": {"status": "aligned", "executes_anything": False},
                "review_axes": {"external_learning": {"status": "pass"}},
            }), encoding="utf-8")

            report = bootstrap_ai_assets.build_manual_publication_decision_packet_report(tmp)
            options_by_id = {option["id"]: option for option in report["decision_options"]}

            self.assertEqual(report["mode"], "manual-publication-decision-packet")
            self.assertEqual(report["summary"]["status"], "owner-decision-required")
            self.assertFalse(report["summary"]["executes_anything"])
            self.assertEqual(report["summary"]["suggested_release_tag"], "v0.1.1")
            self.assertIn("keep-local-review", options_by_id)
            self.assertIn("prepare-history-reattachment-main-push", options_by_id)
            self.assertIn("prepare-v011-tag-release", options_by_id)
            self.assertEqual(options_by_id["prepare-history-reattachment-main-push"]["requires_owner_approval"], True)
            self.assertEqual(options_by_id["prepare-v011-tag-release"]["blocked_until"], "history-reattached-and-main-reviewed")
            self.assertTrue(all(step["executes"] is False for option in report["decision_options"] for step in option["steps"]))
            self.assertIn("never move v0.1.0", "\n".join(report["recommendations"]).lower())

    def test_manual_publication_decision_packet_surfaces_restore_smoke_boundary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            reports = tmp / "bootstrap" / "reports"
            reports.mkdir(parents=True)
            (reports / "latest-public-repo-staging-history-preflight.json").write_text(__import__("json").dumps({
                "summary": {"status": "ready", "executes_anything": False, "remote_configured": False, "forbidden_findings": 0, "head_rev": "new", "v010_rev": "old"},
            }), encoding="utf-8")
            (reports / "latest-github-publish-dry-run.json").write_text(__import__("json").dumps({
                "summary": {"status": "needs-review", "executes_anything": False, "fail": 0},
                "suggested_release_tag": "v0.1.1",
            }), encoding="utf-8")
            (reports / "latest-public-safety-scan.json").write_text('{"summary":{"status":"pass","findings":0,"blockers":0}}', encoding="utf-8")
            (reports / "latest-completed-work-review.json").write_text(__import__("json").dumps({
                "summary": {"status": "aligned", "executes_anything": False},
                "review_axes": {"external_learning": {"status": "pass"}},
            }), encoding="utf-8")
            (reports / "latest-restore-smoke-check.json").write_text(__import__("json").dumps({
                "summary": {
                    "status": "ready-with-prerequisite-regeneration-needed",
                    "executes_anything": False,
                    "mutates_repositories": False,
                    "safe_for_fresh_clone": True,
                }
            }), encoding="utf-8")

            report = bootstrap_ai_assets.build_manual_publication_decision_packet_report(tmp)
            checks_by_name = {check["name"]: check for check in report["checks"]}
            recommendations = "\n".join(report["recommendations"])

            self.assertEqual(report["summary"]["status"], "owner-decision-required")
            self.assertEqual(checks_by_name["restore-smoke-boundary-reviewed"]["status"], "pass")
            self.assertEqual(report["source_summaries"]["restore_smoke_check"]["status"], "ready-with-prerequisite-regeneration-needed")
            self.assertIn("restore is not release work", recommendations.lower())
            self.assertIn('--engine-root "$PWD" --asset-root "$PWD" --restore-smoke-check --both', recommendations)

    def test_manual_publication_decision_packet_uses_post_main_language_when_history_ready(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            reports = tmp / "bootstrap" / "reports"
            reports.mkdir(parents=True)
            (reports / "latest-public-repo-staging-history-preflight.json").write_text(__import__("json").dumps({
                "summary": {
                    "status": "ready",
                    "executes_anything": False,
                    "remote_configured": False,
                    "forbidden_findings": 0,
                    "head_rev": "new-main",
                    "v010_rev": "old-release",
                    "v010_behind_head": True,
                },
            }), encoding="utf-8")
            (reports / "latest-github-publish-dry-run.json").write_text(__import__("json").dumps({
                "summary": {"status": "needs-review", "executes_anything": False, "fail": 0},
                "suggested_release_tag": "v0.1.1",
            }), encoding="utf-8")
            (reports / "latest-public-safety-scan.json").write_text('{"summary":{"status":"pass","findings":0,"blockers":0}}', encoding="utf-8")
            (reports / "latest-completed-work-review.json").write_text(__import__("json").dumps({
                "summary": {"status": "aligned", "executes_anything": False},
                "review_axes": {"external_learning": {"status": "pass"}},
            }), encoding="utf-8")
            (reports / "latest-restore-smoke-check.json").write_text(__import__("json").dumps({
                "summary": {
                    "status": "ready",
                    "executes_anything": False,
                    "mutates_repositories": False,
                    "safe_for_fresh_clone": True,
                }
            }), encoding="utf-8")

            report = bootstrap_ai_assets.build_manual_publication_decision_packet_report(tmp)
            options_by_id = {option["id"]: option for option in report["decision_options"]}
            packet_text = __import__("json").dumps(report)

            self.assertEqual(report["summary"]["status"], "owner-decision-required")
            self.assertNotIn("prepare-history-reattachment-main-push", options_by_id)
            self.assertIn("review-public-main-before-release", options_by_id)
            self.assertEqual(options_by_id["prepare-v011-tag-release"]["blocked_until"], "public-main-reviewed-and-owner-approved")
            self.assertNotIn("Phase127", packet_text)
            self.assertNotIn("Public GitHub main remains behind", packet_text)
            self.assertIn("public history is attached", packet_text.lower())
            self.assertNotIn("reattach public history first", packet_text.lower())
            self.assertIn("never move v0.1.0", packet_text.lower())
            self.assertTrue(all(step["executes"] is False for option in report["decision_options"] for step in option["steps"]))

    def test_manual_publication_decision_packet_uses_post_v011_release_language(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            reports = tmp / "bootstrap" / "reports"
            reports.mkdir(parents=True)
            (reports / "latest-public-repo-staging-history-preflight.json").write_text(__import__("json").dumps({
                "summary": {
                    "status": "ready",
                    "executes_anything": False,
                    "remote_configured": False,
                    "forbidden_findings": 0,
                    "head_rev": "v011-main",
                    "v010_rev": "old-release",
                    "v010_behind_head": True,
                },
            }), encoding="utf-8")
            (reports / "latest-github-publish-dry-run.json").write_text(__import__("json").dumps({
                "summary": {"status": "needs-review", "executes_anything": False, "fail": 0},
                "suggested_release_tag": "v0.1.2",
                "checks": [{"name": "existing-v011-tag-at-head", "status": "warn", "detail": "v0.1.1 already points at HEAD; suggested_release_tag=v0.1.2"}],
            }), encoding="utf-8")
            (reports / "latest-public-safety-scan.json").write_text('{"summary":{"status":"pass","findings":0,"blockers":0}}', encoding="utf-8")
            (reports / "latest-completed-work-review.json").write_text(__import__("json").dumps({
                "summary": {"status": "aligned", "executes_anything": False},
                "review_axes": {"external_learning": {"status": "pass"}},
            }), encoding="utf-8")
            (reports / "latest-restore-smoke-check.json").write_text(__import__("json").dumps({
                "summary": {"status": "ready", "executes_anything": False, "mutates_repositories": False, "safe_for_fresh_clone": True}
            }), encoding="utf-8")

            report = bootstrap_ai_assets.build_manual_publication_decision_packet_report(tmp)
            options_by_id = {option["id"]: option for option in report["decision_options"]}
            packet_text = __import__("json").dumps(report)

            self.assertEqual(report["summary"]["suggested_release_tag"], "v0.1.2")
            self.assertEqual(report["summary"]["latest_published_tag"], "v0.1.1")
            self.assertIn("review-post-v011-release", options_by_id)
            self.assertIn("prepare-v012-tag-release", options_by_id)
            self.assertNotIn("prepare-v011-tag-release", options_by_id)
            self.assertIn("v0.1.1 already exists in staging", packet_text)
            self.assertIn("v0.1.2", packet_text)
            self.assertTrue(all(step["executes"] is False for option in report["decision_options"] for step in option["steps"]))

    def test_manual_publication_decision_packet_uses_post_v012_release_language(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            reports = tmp / "bootstrap" / "reports"
            reports.mkdir(parents=True)
            (reports / "latest-public-repo-staging-history-preflight.json").write_text(__import__("json").dumps({
                "summary": {
                    "status": "ready",
                    "executes_anything": False,
                    "remote_configured": False,
                    "forbidden_findings": 0,
                    "head_rev": "v012-main",
                    "v010_rev": "old-release",
                    "v011_rev": "v011-release",
                    "v010_behind_head": True,
                },
            }), encoding="utf-8")
            (reports / "latest-github-publish-dry-run.json").write_text(__import__("json").dumps({
                "summary": {"status": "needs-review", "executes_anything": False, "fail": 0},
                "suggested_release_tag": "v0.1.3",
                "checks": [{"name": "existing-v012-tag-at-head", "status": "warn", "detail": "v0.1.2 already points at HEAD; suggested_release_tag=v0.1.3"}],
            }), encoding="utf-8")
            (reports / "latest-public-safety-scan.json").write_text('{"summary":{"status":"pass","findings":0,"blockers":0}}', encoding="utf-8")
            (reports / "latest-completed-work-review.json").write_text(__import__("json").dumps({
                "summary": {"status": "aligned", "executes_anything": False},
                "review_axes": {"external_learning": {"status": "pass"}},
            }), encoding="utf-8")
            (reports / "latest-restore-smoke-check.json").write_text(__import__("json").dumps({
                "summary": {"status": "ready", "executes_anything": False, "mutates_repositories": False, "safe_for_fresh_clone": True}
            }), encoding="utf-8")

            report = bootstrap_ai_assets.build_manual_publication_decision_packet_report(tmp)
            options_by_id = {option["id"]: option for option in report["decision_options"]}
            packet_text = __import__("json").dumps(report)

            self.assertEqual(report["summary"]["suggested_release_tag"], "v0.1.3")
            self.assertEqual(report["summary"]["latest_published_tag"], "v0.1.2")
            self.assertIn("review-post-v012-release", options_by_id)
            self.assertIn("prepare-v013-tag-release", options_by_id)
            self.assertNotIn("prepare-v012-tag-release", options_by_id)
            self.assertIn("v0.1.2 already exists in staging", packet_text)
            self.assertIn("v0.1.3", packet_text)
            self.assertTrue(all(step["executes"] is False for option in report["decision_options"] for step in option["steps"]))

    def test_github_handoff_pack_collects_public_safe_review_materials(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            staging = tmp / "dist" / "github-staging" / "portable-ai-assets"
            staging.mkdir(parents=True)
            (staging / "README.md").write_text("# Demo\n", encoding="utf-8")
            (staging / "GITHUB-PUBLISH-CHECKLIST.md").write_text("# Checklist\n", encoding="utf-8")
            bootstrap_ai_assets.run_git_command(staging, ["init"])
            (tmp / "bootstrap" / "reports").mkdir(parents=True)
            (tmp / "docs").mkdir(parents=True)
            (tmp / "RELEASE_NOTES-v0.1.md").write_text("# Release\n", encoding="utf-8")
            (tmp / "CHANGELOG.md").write_text("# Changelog\n", encoding="utf-8")
            (tmp / "SECURITY.md").write_text("# Security\n", encoding="utf-8")
            (tmp / "docs" / "github-publishing.md").write_text("# GitHub\n", encoding="utf-8")
            archive = tmp / "dist" / "portable-ai-assets-public-demo.tar.gz"
            archive.write_bytes(b"demo")
            (tmp / "bootstrap" / "reports" / "latest-public-safety-scan.json").write_text('{"summary":{"status":"pass"}}', encoding="utf-8")
            (tmp / "bootstrap" / "reports" / "latest-release-readiness.json").write_text('{"summary":{"readiness":"ready"}}', encoding="utf-8")
            (tmp / "bootstrap" / "reports" / "latest-public-release-smoke-test.json").write_text('{"summary":{"status":"pass"}}', encoding="utf-8")
            (tmp / "bootstrap" / "reports" / "latest-github-publish-check.json").write_text('{"summary":{"status":"ready"}}', encoding="utf-8")
            (tmp / "bootstrap" / "reports" / "latest-agent-complete-phase102-rollup-evidence-failclosed-review.md").write_text("# Phase103\nphase102_report_invalid_fields\ninvalid_fields=agent_side_complete,remote_issues_created,warn\n", encoding="utf-8")
            (tmp / "bootstrap" / "reports" / "latest-completed-work-review.md").write_text("# Completed\ninvalid_fields=agent_side_complete,remote_issues_created,warn\n", encoding="utf-8")
            (tmp / "bootstrap" / "reports" / "latest-manual-reviewer-handoff-freeze-check.md").write_text("# Freeze\n## Diagnostic freeze failures\n- none\n", encoding="utf-8")
            (tmp / "bootstrap" / "reports" / "latest-manual-reviewer-handoff-freeze-check.json").write_text(__import__("json").dumps({"generated_at": "2026-04-27T00:00:00", "summary": {"status": "frozen-for-human-handoff", "fail": 0}}), encoding="utf-8")
            (tmp / "bootstrap" / "reports" / "latest-public-release-archive.json").write_text(__import__("json").dumps({"archive_path": str(archive), "summary": {"archive_sha256": "abc"}}), encoding="utf-8")
            report = bootstrap_ai_assets.build_github_handoff_pack_report(tmp)
            self.assertEqual(report["mode"], "github-handoff-pack")
            self.assertEqual(report["summary"]["status"], "ready")
            self.assertFalse(report["summary"]["executes_anything"])
            handoff_dir = Path(report["handoff_dir"])
            self.assertTrue((handoff_dir / "HANDOFF.md").is_file())
            self.assertTrue((handoff_dir / "HANDOFF.json").is_file())
            self.assertIn("GITHUB-PUBLISH-CHECKLIST.md", report["included_files"])
            self.assertIn("reports/latest-agent-complete-phase102-rollup-evidence-failclosed-review.md", report["included_files"])
            self.assertIn("reports/latest-completed-work-review.md", report["included_files"])
            self.assertIn("reports/latest-manual-reviewer-handoff-freeze-check.md", report["included_files"])
            handoff_text = (handoff_dir / "HANDOFF.md").read_text(encoding="utf-8")
            self.assertIn("reports/latest-agent-complete-phase102-rollup-evidence-failclosed-review.md", handoff_text)
            self.assertIn("reports/latest-completed-work-review.md", handoff_text)
            self.assertIn("reports/latest-manual-reviewer-handoff-freeze-check.md", handoff_text)
            self.assertIn("invalid_fields=agent_side_complete,remote_issues_created,warn", (handoff_dir / "reports" / "latest-completed-work-review.md").read_text(encoding="utf-8"))
            self.assertIn("Diagnostic freeze failures", (handoff_dir / "reports" / "latest-manual-reviewer-handoff-freeze-check.md").read_text(encoding="utf-8"))
            checks_by_name = {check["name"]: check for check in report["checks"]}
            self.assertEqual(checks_by_name["handoff-freeze-report-included"]["status"], "pass")
            self.assertEqual(checks_by_name["handoff-freeze-report-content-match"]["status"], "pass")
            self.assertEqual(checks_by_name["handoff-generated-after-freeze-report"]["status"], "pass")
            self.assertTrue(all(command["executes"] is False for command in report["manual_steps"]))

    def test_github_final_preflight_verifies_release_artifacts_without_execution(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            staging = tmp / "dist" / "github-staging" / "portable-ai-assets"
            staging.mkdir(parents=True)
            (staging / "README.md").write_text("# Demo\n", encoding="utf-8")
            bootstrap_ai_assets.run_git_command(staging, ["init"])
            handoff_dir = tmp / "dist" / "github-handoff" / "portable-ai-assets-handoff-demo"
            handoff_dir.mkdir(parents=True)
            (handoff_dir / "HANDOFF.md").write_text("# Handoff\n", encoding="utf-8")
            (handoff_dir / "HANDOFF.json").write_text("{}\n", encoding="utf-8")
            archive = tmp / "dist" / "portable-ai-assets-public-demo.tar.gz"
            archive.write_bytes(b"demo")
            sha = __import__("hashlib").sha256(archive.read_bytes()).hexdigest()
            checksum = tmp / "dist" / "portable-ai-assets-public-demo.tar.gz.sha256"
            checksum.write_text(f"{sha}  {archive.name}\n", encoding="utf-8")
            (tmp / "bootstrap" / "reports").mkdir(parents=True)
            reports = tmp / "bootstrap" / "reports"
            (reports / "latest-public-safety-scan.json").write_text('{"summary":{"status":"pass"}}', encoding="utf-8")
            (reports / "latest-release-readiness.json").write_text('{"summary":{"readiness":"ready"}}', encoding="utf-8")
            (reports / "latest-public-release-smoke-test.json").write_text('{"summary":{"status":"pass"}}', encoding="utf-8")
            (reports / "latest-github-publish-check.json").write_text('{"summary":{"status":"ready"}}', encoding="utf-8")
            (reports / "latest-public-repo-staging.json").write_text('{"summary":{"status":"ready"}}', encoding="utf-8")
            (reports / "latest-public-release-archive.json").write_text(__import__("json").dumps({"archive_path": str(archive), "checksum_path": str(checksum), "summary": {"archive_sha256": sha}}), encoding="utf-8")
            (reports / "latest-github-handoff-pack.json").write_text(__import__("json").dumps({"handoff_dir": str(handoff_dir), "summary": {"status": "ready", "executes_anything": False, "forbidden_findings": 0}}), encoding="utf-8")
            report = bootstrap_ai_assets.build_github_final_preflight_report(tmp)
            self.assertEqual(report["mode"], "github-final-preflight")
            self.assertEqual(report["summary"]["status"], "ready")
            self.assertFalse(report["summary"]["executes_anything"])
            self.assertFalse(report["summary"]["remote_configured"])
            self.assertEqual(report["artifact_sha256"]["computed"], sha)
            self.assertTrue(all(command["executes"] is False for command in report["command_drafts"]))

    def test_release_provenance_records_artifacts_and_tree_digests(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            pack = tmp / "dist" / "portable-ai-assets-public-demo"
            staging = tmp / "dist" / "github-staging" / "portable-ai-assets"
            handoff_dir = tmp / "dist" / "github-handoff" / "portable-ai-assets-handoff-demo"
            for directory in [pack, staging, handoff_dir, tmp / "bootstrap" / "reports"]:
                directory.mkdir(parents=True)
            (pack / "README.md").write_text("# Pack\n", encoding="utf-8")
            (staging / "README.md").write_text("# Staging\n", encoding="utf-8")
            bootstrap_ai_assets.run_git_command(staging, ["init"])
            (handoff_dir / "HANDOFF.md").write_text("# Handoff\n", encoding="utf-8")
            (handoff_dir / "HANDOFF.json").write_text("{}\n", encoding="utf-8")
            archive = tmp / "dist" / "portable-ai-assets-public-demo.tar.gz"
            archive.write_bytes(b"demo")
            sha = __import__("hashlib").sha256(archive.read_bytes()).hexdigest()
            checksum = tmp / "dist" / "portable-ai-assets-public-demo.tar.gz.sha256"
            checksum.write_text(f"{sha}  {archive.name}\n", encoding="utf-8")
            reports = tmp / "bootstrap" / "reports"
            (reports / "latest-public-safety-scan.json").write_text('{"summary":{"status":"pass"}}', encoding="utf-8")
            (reports / "latest-release-readiness.json").write_text('{"summary":{"readiness":"ready"}}', encoding="utf-8")
            (reports / "latest-public-release-smoke-test.json").write_text('{"summary":{"status":"pass"}}', encoding="utf-8")
            (reports / "latest-public-repo-staging-status.json").write_text(__import__("json").dumps({"staging_dir": str(staging), "summary":{"status":"ready", "remote_configured": False}}), encoding="utf-8")
            (reports / "latest-github-publish-dry-run.json").write_text('{"summary":{"status":"ready", "executes_anything":false}, "commands": []}', encoding="utf-8")
            (reports / "latest-github-handoff-pack.json").write_text(__import__("json").dumps({"handoff_dir": str(handoff_dir), "summary":{"status":"ready", "executes_anything":False, "forbidden_findings":0}}), encoding="utf-8")
            (reports / "latest-github-final-preflight.json").write_text('{"summary":{"status":"ready"}}', encoding="utf-8")
            (reports / "latest-public-release-archive.json").write_text(__import__("json").dumps({"pack_dir": str(pack), "archive_path": str(archive), "checksum_path": str(checksum), "summary":{"archive_sha256": sha}}), encoding="utf-8")
            report = bootstrap_ai_assets.build_release_provenance_report(tmp)
            self.assertEqual(report["mode"], "release-provenance")
            self.assertEqual(report["summary"]["status"], "ready")
            self.assertFalse(report["summary"]["executes_anything"])
            self.assertEqual(report["subject"]["archive_sha256"], sha)
            self.assertTrue(Path(report["provenance_json"]).is_file())
            self.assertTrue(report["tree_digests"]["github_staging"]["sha256"])
            self.assertEqual(report["summary"]["forbidden_findings"], 0)

    def test_release_closure_aggregates_release_candidate_evidence_without_execution(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            reports = tmp / "bootstrap" / "reports"
            reports.mkdir(parents=True)
            ready_reports = {
                "public-safety-scan": {"summary": {"status": "pass", "blockers": 0}},
                "release-readiness": {"summary": {"readiness": "ready", "fail": 0}},
                "public-demo-pack": {"summary": {"status": "ready", "forbidden_findings": 0, "executes_anything": False}},
                "public-release-pack": {"summary": {"status": "ready", "forbidden_findings": 0}},
                "public-release-archive": {"summary": {"status": "ready", "archive_sha256": "abc"}},
                "public-release-smoke-test": {"summary": {"status": "pass", "fail": 0}},
                "github-publish-check": {"summary": {"status": "ready", "fail": 0}},
                "public-repo-staging": {"summary": {"status": "ready", "forbidden_findings": 0}},
                "public-repo-staging-status": {"summary": {"status": "ready", "remote_configured": False}},
                "github-publish-dry-run": {"summary": {"status": "ready", "executes_anything": False}, "commands": [
                    {"step": "commit", "command": "git commit -m demo", "executes": False},
                    {"step": "create repo", "command": "gh repo create portable-ai-assets --public", "executes": False},
                    {"step": "push", "command": "git push -u origin main", "executes": False},
                    {"step": "tag", "command": "git tag v0.1.0", "executes": False},
                ]},
                "github-handoff-pack": {
                    "summary": {"status": "ready", "executes_anything": False, "forbidden_findings": 0},
                    "checks": [{"name": "handoff-generated-after-freeze-report", "status": "pass", "detail": "fresh"}],
                },
                "github-final-preflight": {"summary": {"status": "ready", "executes_anything": False, "remote_configured": False}}, 
                "release-provenance": {"summary": {"status": "ready", "executes_anything": False, "forbidden_findings": 0}, "provenance_kind": "unsigned-release-provenance-v1"},
                "verify-release-provenance": {"summary": {"status": "ready", "executes_anything": False, "forbidden_findings": 0}},
                "manual-reviewer-handoff-freeze-check": {"summary": {"status": "frozen-for-human-handoff", "fail": 0, "executes_anything": False}},
                "completed-work-review": {
                    "summary": {"status": "aligned", "executes_anything": False, "fail": 0},
                    "review_axes": {"external_learning": {"status": "pass"}},
                },
            }
            for prefix, payload in ready_reports.items():
                (reports / f"latest-{prefix}.json").write_text(__import__("json").dumps(payload), encoding="utf-8")
            report = bootstrap_ai_assets.build_release_closure_report(tmp)
            self.assertEqual(report["mode"], "release-closure")
            self.assertEqual(report["summary"]["status"], "ready-for-manual-release-review")
            self.assertFalse(report["summary"]["executes_anything"])
            self.assertFalse(report["summary"]["remote_configured"])
            self.assertIn("public-safety-scan", report["required_evidence"])
            self.assertIn("verify-release-provenance", report["required_evidence"])
            self.assertIn("manual-reviewer-handoff-freeze-check", report["required_evidence"])
            checks_by_name = {check["name"]: check for check in report["checks"]}
            self.assertEqual(checks_by_name["manual-reviewer-handoff-freeze-check-frozen"]["status"], "pass")
            self.assertEqual(checks_by_name["github-handoff-fresh-after-freeze"]["status"], "pass")
            self.assertEqual(checks_by_name["completed-work-external-learning-pass"]["status"], "pass")
            self.assertIn("manual release review", " ".join(report["manual_review_boundary"]).lower())
            self.assertIn("unsigned", " ".join(report["provenance_boundary"]).lower())
            self.assertTrue(all(command["executes"] is False for command in report["command_drafts"]))
            publication_summary = report["publication_command_summary"]
            self.assertEqual(publication_summary["total"], 4)
            self.assertEqual(publication_summary["non_executing"], 4)
            self.assertEqual(publication_summary["manual_review_required"], 4)
            self.assertEqual(publication_summary["by_publication_risk"]["commit"], 1)
            self.assertEqual(publication_summary["by_publication_risk"]["repo-create"], 1)
            self.assertEqual(publication_summary["by_publication_risk"]["push"], 1)
            self.assertEqual(publication_summary["by_publication_risk"]["tag"], 1)
            self.assertIn("copy/paste", " ".join(report["publication_boundary"]).lower())
            self.assertIn("credentials", " ".join(report["publication_boundary"]).lower())

            # Phase118 negative regressions: final release closure must fail closed
            # when freeze, handoff freshness, or anti-closed-door evidence is missing/failing.
            copy = __import__("copy")
            mutated = copy.deepcopy(ready_reports)
            mutated.pop("manual-reviewer-handoff-freeze-check")
            (reports / "latest-manual-reviewer-handoff-freeze-check.json").unlink()
            for prefix, payload in mutated.items():
                (reports / f"latest-{prefix}.json").write_text(__import__("json").dumps(payload), encoding="utf-8")
            missing_freeze = bootstrap_ai_assets.build_release_closure_report(tmp)
            self.assertEqual(missing_freeze["summary"]["status"], "blocked")
            self.assertEqual({check["name"]: check for check in missing_freeze["checks"]}["manual-reviewer-handoff-freeze-check-frozen"]["status"], "fail")

            mutated = copy.deepcopy(ready_reports)
            mutated["github-handoff-pack"]["checks"] = [{"name": "handoff-generated-after-freeze-report", "status": "fail", "detail": "stale"}]
            for prefix, payload in mutated.items():
                (reports / f"latest-{prefix}.json").write_text(__import__("json").dumps(payload), encoding="utf-8")
            stale_handoff = bootstrap_ai_assets.build_release_closure_report(tmp)
            self.assertEqual(stale_handoff["summary"]["status"], "blocked")
            self.assertEqual({check["name"]: check for check in stale_handoff["checks"]}["github-handoff-fresh-after-freeze"]["status"], "fail")

            mutated = copy.deepcopy(ready_reports)
            mutated["completed-work-review"]["review_axes"]["external_learning"]["status"] = "fail"
            for prefix, payload in mutated.items():
                (reports / f"latest-{prefix}.json").write_text(__import__("json").dumps(payload), encoding="utf-8")
            closed_door = bootstrap_ai_assets.build_release_closure_report(tmp)
            self.assertEqual(closed_door["summary"]["status"], "blocked")
            self.assertEqual({check["name"]: check for check in closed_door["checks"]}["completed-work-external-learning-pass"]["status"], "fail")

            for prefix, payload in ready_reports.items():
                (reports / f"latest-{prefix}.json").write_text(__import__("json").dumps(payload), encoding="utf-8")

            (reports / "latest-public-safety-scan.json").write_text('{"summary":{"status":"blocked","blockers":1}}', encoding="utf-8")
            blocked = bootstrap_ai_assets.build_release_closure_report(tmp)
            self.assertEqual(blocked["summary"]["status"], "blocked")
            self.assertGreater(blocked["summary"]["fail"], 0)

    def test_manual_release_reviewer_checklist_collects_human_review_evidence_without_execution(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            reports = tmp / "bootstrap" / "reports"
            reports.mkdir(parents=True)
            release_closure = {
                "mode": "release-closure",
                "summary": {
                    "status": "ready-for-manual-release-review",
                    "executes_anything": False,
                    "remote_configured": False,
                    "command_drafts": 4,
                    "non_executing_command_drafts": 4,
                    "manual_review_required_command_drafts": 4,
                    "forbidden_findings": 0,
                },
                "publication_command_summary": {
                    "total": 4,
                    "non_executing": 4,
                    "manual_review_required": 4,
                    "by_publication_risk": {"commit": 1, "repo-create": 1, "push": 1, "tag": 1},
                },
                "publication_boundary": [
                    "Command drafts are copy/paste reference only.",
                    "Credentials are not validated by this gate.",
                ],
                "manual_review_boundary": ["Human reviewer must approve the release outside this tool."],
                "command_drafts": [
                    {"step": "commit", "command": "git commit -m demo", "executes": False, "manual_review_required": True},
                    {"step": "create repo", "command": "gh repo create portable-ai-assets --public", "executes": False, "manual_review_required": True},
                    {"step": "push", "command": "git push -u origin main", "executes": False, "manual_review_required": True},
                    {"step": "tag", "command": "git tag v0.1.0", "executes": False, "manual_review_required": True},
                ],
            }
            final_preflight = {
                "mode": "github-final-preflight",
                "summary": {"status": "ready", "executes_anything": False, "remote_configured": False, "forbidden_findings": 0, "command_drafts": 2},
                "artifact_checksum": {"recorded_sha256": "abc", "computed_sha256": "abc", "matches": True},
                "command_drafts": [
                    {"step": "git status", "command": "git status --short", "executes": False},
                    {"step": "push", "command": "git push -u origin main", "executes": False},
                ],
            }
            public_safety = {"mode": "public-safety-scan", "summary": {"status": "pass", "blockers": 0, "forbidden_findings": 0}}
            release_readiness = {"mode": "release-readiness", "summary": {"readiness": "ready", "fail": 0}}
            payloads = {
                "release-closure": release_closure,
                "github-final-preflight": final_preflight,
                "public-safety-scan": public_safety,
                "release-readiness": release_readiness,
            }
            for prefix, payload in payloads.items():
                (reports / f"latest-{prefix}.json").write_text(__import__("json").dumps(payload), encoding="utf-8")

            report = bootstrap_ai_assets.build_manual_release_reviewer_checklist_report(tmp)

            self.assertEqual(report["mode"], "manual-release-reviewer-checklist")
            self.assertEqual(report["summary"]["status"], "ready-for-human-review")
            self.assertFalse(report["summary"]["executes_anything"])
            self.assertTrue(report["summary"]["manual_review_required"])
            self.assertFalse(report["summary"]["remote_mutation_allowed"])
            self.assertFalse(report["summary"]["credential_validation_allowed"])
            self.assertEqual(report["summary"]["checklist_items"], len(report["checklist"]))
            checklist_ids = {item["id"] for item in report["checklist"]}
            self.assertIn("release-closure-review", checklist_ids)
            self.assertIn("github-final-preflight-review", checklist_ids)
            self.assertIn("public-safety-review", checklist_ids)
            self.assertIn("release-readiness-review", checklist_ids)
            self.assertIn("publication-boundary-review", checklist_ids)
            self.assertIn("command-drafts-review", checklist_ids)
            self.assertIn("artifact-checksum-review", checklist_ids)
            self.assertTrue(all(item["review_type"] == "manual" for item in report["checklist"]))
            self.assertTrue(all(item["executes_anything"] is False for item in report["checklist"]))
            self.assertTrue(all(item["auto_approves_release"] is False for item in report["checklist"]))
            self.assertEqual(report["publication_command_summary"]["total"], 4)
            self.assertEqual(report["artifact_checksum"]["matches"], True)
            self.assertIn("not publish", " ".join(report["review_boundary"]).lower())
            self.assertIn("credentials", " ".join(report["review_boundary"]).lower())

            (reports / "latest-release-closure.json").write_text(__import__("json").dumps({"summary": {"status": "blocked", "executes_anything": False}}), encoding="utf-8")
            blocked = bootstrap_ai_assets.build_manual_release_reviewer_checklist_report(tmp)
            self.assertEqual(blocked["summary"]["status"], "blocked")
            self.assertGreater(blocked["summary"]["fail"], 0)

    def test_public_package_freshness_review_confirms_phase78_gate_reaches_pack_and_staging_without_execution(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            reports = tmp / "bootstrap" / "reports"
            reports.mkdir(parents=True)
            for directory in [tmp / "docs", tmp / "bootstrap" / "setup", tmp / "dist" / "github-staging" / "portable-ai-assets" / "docs", tmp / "dist" / "github-staging" / "portable-ai-assets" / "bootstrap" / "setup"]:
                directory.mkdir(parents=True)
            release_plan = "# Release plan\n`--manual-release-reviewer-checklist`\n`--public-package-freshness-review`\n"
            shell = "#!/usr/bin/env bash\n--manual-release-reviewer-checklist\n--public-package-freshness-review\n"
            (tmp / "README.md").write_text("# Demo\n", encoding="utf-8")
            (tmp / "docs" / "open-source-release-plan.md").write_text(release_plan, encoding="utf-8")
            (tmp / "bootstrap" / "setup" / "bootstrap-ai-assets.sh").write_text(shell, encoding="utf-8")
            staging = tmp / "dist" / "github-staging" / "portable-ai-assets"
            (staging / "README.md").write_text("# Demo\n", encoding="utf-8")
            (staging / "docs" / "open-source-release-plan.md").write_text(release_plan, encoding="utf-8")
            (staging / "bootstrap" / "setup" / "bootstrap-ai-assets.sh").write_text(shell, encoding="utf-8")
            report_payloads = {
                "public-safety-scan": {"summary": {"status": "pass", "forbidden_findings": 0}},
                "release-readiness": {"summary": {"readiness": "ready", "fail": 0}},
                "release-closure": {"summary": {"status": "ready-for-manual-release-review", "executes_anything": False, "remote_configured": False, "forbidden_findings": 0}},
                "github-final-preflight": {"summary": {"status": "ready", "executes_anything": False, "remote_configured": False, "forbidden_findings": 0}},
                "manual-release-reviewer-checklist": {"summary": {"status": "ready-for-human-review", "executes_anything": False, "manual_review_required": True, "remote_mutation_allowed": False, "credential_validation_allowed": False, "forbidden_findings": 0}},
                "public-repo-staging-status": {"staging_dir": str(staging), "summary": {"status": "ready", "remote_configured": False, "forbidden_findings": 0}},
            }
            for prefix, payload in report_payloads.items():
                (reports / f"latest-{prefix}.json").write_text(__import__("json").dumps(payload), encoding="utf-8")
                (reports / f"latest-{prefix}.md").write_text(f"# {prefix}\n", encoding="utf-8")
            pack_report = bootstrap_ai_assets.build_public_release_pack_report(tmp)
            (reports / "latest-public-release-pack.json").write_text(__import__("json").dumps(pack_report), encoding="utf-8")

            review = bootstrap_ai_assets.build_public_package_freshness_review_report(tmp)

            self.assertEqual(review["mode"], "public-package-freshness-review")
            self.assertEqual(review["summary"]["status"], "ready")
            self.assertFalse(review["summary"]["executes_anything"])
            self.assertFalse(review["summary"]["remote_mutation_allowed"])
            self.assertFalse(review["summary"]["credential_validation_allowed"])
            self.assertEqual(review["summary"]["forbidden_findings"], 0)
            check_names = {check["name"] for check in review["checks"]}
            self.assertIn("public-release-pack:manual-reviewer-json", check_names)
            self.assertIn("public-release-pack:manual-reviewer-md", check_names)
            self.assertIn("github-staging:manual-reviewer-command-doc", check_names)
            self.assertIn("github-staging:freshness-review-command-shell", check_names)
            self.assertTrue(all(check["status"] == "pass" for check in review["checks"]))
            self.assertIn("--public-release-pack --both", " ".join(review["recommendations"]))
            self.assertIn("--public-repo-staging --both", " ".join(review["recommendations"]))

            (Path(pack_report["pack_dir"]) / "bootstrap" / "reports" / "latest-manual-release-reviewer-checklist.json").unlink()
            stale = bootstrap_ai_assets.build_public_package_freshness_review_report(tmp)
            self.assertEqual(stale["summary"]["status"], "stale")
            self.assertGreater(stale["summary"]["fail"], 0)

    def test_public_docs_external_reader_review_scores_first_reader_comprehension_without_execution(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            docs = tmp / "docs"
            setup = tmp / "bootstrap" / "setup"
            reports = tmp / "bootstrap" / "reports"
            docs.mkdir(parents=True)
            setup.mkdir(parents=True)
            reports.mkdir(parents=True)
            (tmp / "README.md").write_text(
                "# Portable AI Assets System\n"
                "> Own your AI work environment instead of rebuilding it every time you change tools, models, clients, or machines.\n\n"
                "Portable AI Assets System is a portable AI assets layer for cross-agent, cross-model, cross-client, and cross-machine continuity.\n"
                "It is not another agent runtime, chat UI, memory SaaS, workflow builder, or MCP host.\n"
                "Core promise: change tools or machines without starting your AI environment from scratch.\n"
                "Typical use cases: Switch agents or clients; Move to a new machine; Share a project/team AI pack safely.\n"
                "Run ./bootstrap/setup/bootstrap-ai-assets.sh --public-docs-external-reader-review --both before manual release review.\n",
                encoding="utf-8",
            )
            (docs / "public-facing-thesis.md").write_text(
                "# Public-facing thesis\n"
                "## One-minute explanation\nPortable AI Assets System is a portability layer for AI work environments.\n"
                "## The core promise\nChange tools, models, clients, or machines without starting your AI environment from scratch.\n"
                "## What this is not\nIt is not an agent runtime, chat UI, model server, memory SaaS, workflow builder, MCP host, credential broker, or universal lossless migration guarantee.\n"
                "## Public/private boundary\nPublic engine and sample assets stay separate from private memory, private project summaries, credentials, tokens, raw runtime databases, logs, caches, embeddings, and private identifiers.\n"
                "## Success criterion\nA new reader should understand within one minute that this protects long-lived AI assets from runtime lock-in with safety gates.\n",
                encoding="utf-8",
            )
            (docs / "open-source-release-plan.md").write_text(
                "# Open-Source Release Plan\n"
                "Public repo includes engine/framework, schemas, adapter framework, samples, docs, and report-only gates.\n"
                "Private by default: real personal memory, private project summaries, raw runtime state, secrets, credentials, tokens.\n"
                "Run --public-docs-external-reader-review --both and --public-package-freshness-review --both.\n"
                "No commit, push, repo, remote, tag, release, provider/API call, credential validation, hook/action/code execution, or runtime/admin/provider mutation.\n",
                encoding="utf-8",
            )
            (docs / "public-roadmap.md").write_text(
                "# Public Roadmap\n"
                "Vision: portable AI assets layer across agents, models, clients, machines.\n"
                "Non-Goals: not a chat UI, not model serving, not workflow builder, not memory backend, not universal lossless migration.\n"
                "Phase 80 — Public docs external-reader comprehension review.\n"
                "Run --public-docs-external-reader-review --both.\n",
                encoding="utf-8",
            )
            (setup / "bootstrap-ai-assets.sh").write_text("#!/usr/bin/env bash\n--public-docs-external-reader-review\n", encoding="utf-8")
            (reports / "latest-public-safety-scan.json").write_text(__import__("json").dumps({"summary": {"status": "pass", "forbidden_findings": 0}}), encoding="utf-8")
            (reports / "latest-release-readiness.json").write_text(__import__("json").dumps({"summary": {"readiness": "ready", "fail": 0}}), encoding="utf-8")

            review = bootstrap_ai_assets.build_public_docs_external_reader_review_report(tmp)

            self.assertEqual(review["mode"], "public-docs-external-reader-review")
            self.assertEqual(review["summary"]["status"], "ready")
            self.assertEqual(review["summary"]["fail"], 0)
            self.assertFalse(review["summary"]["executes_anything"])
            self.assertFalse(review["summary"]["remote_mutation_allowed"])
            self.assertFalse(review["summary"]["credential_validation_allowed"])
            self.assertEqual(review["summary"]["forbidden_findings"], 0)
            check_names = {check["name"] for check in review["checks"]}
            self.assertIn("reader:one-minute-promise", check_names)
            self.assertIn("reader:non-goals-clear", check_names)
            self.assertIn("reader:public-private-boundary", check_names)
            self.assertIn("reader:quickstart-or-review-command", check_names)
            self.assertIn("release-plan:documents-external-reader-review", check_names)
            self.assertIn("shell:external-reader-review-command", check_names)
            self.assertTrue(all(check["status"] == "pass" for check in review["checks"]))
            self.assertIn("not an agent runtime", " ".join(review["reader_questions"]).lower())
            self.assertIn("--public-docs-external-reader-review --both", " ".join(review["recommendations"]))

            (docs / "public-facing-thesis.md").write_text("# Thin\nNo boundary yet.\n", encoding="utf-8")
            stale = bootstrap_ai_assets.build_public_docs_external_reader_review_report(tmp)
            self.assertEqual(stale["summary"]["status"], "needs-docs-review")
            self.assertGreater(stale["summary"]["fail"], 0)

    def test_release_candidate_closure_review_aggregates_final_human_release_evidence_without_execution(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            docs = tmp / "docs"
            setup = tmp / "bootstrap" / "setup"
            reports = tmp / "bootstrap" / "reports"
            docs.mkdir(parents=True)
            setup.mkdir(parents=True)
            reports.mkdir(parents=True)
            (docs / "open-source-release-plan.md").write_text(
                "# Open-Source Release Plan\n"
                "Run --release-candidate-closure-review --both after manual-release-reviewer-checklist, "
                "public-docs-external-reader-review, and public-package-freshness-review.\n"
                "This is report-only: no commit, push, repo, remote, tag, release, provider/API call, credential validation, or hook execution.\n",
                encoding="utf-8",
            )
            (docs / "public-roadmap.md").write_text(
                "# Public Roadmap\nPhase 81 — Release candidate closure review.\n",
                encoding="utf-8",
            )
            (setup / "bootstrap-ai-assets.sh").write_text("#!/usr/bin/env bash\n--release-candidate-closure-review\n", encoding="utf-8")
            payloads = {
                "release-closure": {"summary": {"status": "ready-for-manual-release-review", "executes_anything": False, "remote_configured": False, "forbidden_findings": 0, "command_drafts": 4}},
                "manual-release-reviewer-checklist": {"summary": {"status": "ready-for-human-review", "manual_review_required": True, "executes_anything": False, "remote_mutation_allowed": False, "credential_validation_allowed": False, "forbidden_findings": 0, "checklist_items": 7}},
                "public-docs-external-reader-review": {"summary": {"status": "ready", "executes_anything": False, "remote_mutation_allowed": False, "credential_validation_allowed": False, "remote_configured": False, "forbidden_findings": 0}},
                "public-package-freshness-review": {"summary": {"status": "ready", "executes_anything": False, "remote_mutation_allowed": False, "credential_validation_allowed": False, "remote_configured": False, "forbidden_findings": 0}},
                "public-safety-scan": {"summary": {"status": "pass", "forbidden_findings": 0, "blockers": 0}},
                "release-readiness": {"summary": {"readiness": "ready", "fail": 0}},
                "github-final-preflight": {"summary": {"status": "ready", "executes_anything": False, "remote_configured": False, "forbidden_findings": 0}},
                "completed-work-review": {"summary": {"status": "aligned", "executes_anything": False, "fail": 0}},
            }
            for prefix, payload in payloads.items():
                (reports / f"latest-{prefix}.json").write_text(__import__("json").dumps(payload), encoding="utf-8")

            review = bootstrap_ai_assets.build_release_candidate_closure_review_report(tmp)

            self.assertEqual(review["mode"], "release-candidate-closure-review")
            self.assertEqual(review["summary"]["status"], "ready-for-final-human-review")
            self.assertEqual(review["summary"]["fail"], 0)
            self.assertTrue(review["summary"]["manual_review_required"])
            self.assertFalse(review["summary"]["executes_anything"])
            self.assertFalse(review["summary"]["remote_mutation_allowed"])
            self.assertFalse(review["summary"]["credential_validation_allowed"])
            self.assertFalse(review["summary"]["remote_configured"])
            self.assertEqual(review["summary"]["forbidden_findings"], 0)
            check_names = {check["name"] for check in review["checks"]}
            self.assertIn("evidence:manual-release-reviewer-checklist:ready", check_names)
            self.assertIn("evidence:public-docs-external-reader-review:ready", check_names)
            self.assertIn("evidence:public-package-freshness-review:ready", check_names)
            self.assertIn("docs:release-plan-documents-final-closure", check_names)
            self.assertIn("shell:release-candidate-closure-command", check_names)
            self.assertIn("human-final-review", {item["id"] for item in review["final_review_packet"]})
            self.assertTrue(all(item["executes_anything"] is False for item in review["final_review_packet"]))
            self.assertIn("not automatic publish approval", " ".join(review["review_boundary"]).lower())
            self.assertIn("--release-candidate-closure-review --both", " ".join(review["recommendations"]))

            (reports / "latest-public-package-freshness-review.json").write_text(__import__("json").dumps({"summary": {"status": "stale", "executes_anything": False}}), encoding="utf-8")
            stale = bootstrap_ai_assets.build_release_candidate_closure_review_report(tmp)
            self.assertEqual(stale["summary"]["status"], "blocked")
            self.assertGreater(stale["summary"]["fail"], 0)

    def test_release_reviewer_packet_index_collects_final_artifacts_without_execution(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            docs = tmp / "docs"
            setup = tmp / "bootstrap" / "setup"
            reports = tmp / "bootstrap" / "reports"
            docs.mkdir(parents=True)
            setup.mkdir(parents=True)
            reports.mkdir(parents=True)
            (docs / "open-source-release-plan.md").write_text(
                "# Open-Source Release Plan\n"
                "Run --release-reviewer-packet-index --both after --release-candidate-closure-review.\n"
                "This reviewer packet index is report-only/local-only and does not commit, push, publish, create repos/remotes/tags/releases, validate credentials, call APIs, or execute commands.\n",
                encoding="utf-8",
            )
            (docs / "public-roadmap.md").write_text(
                "# Public Roadmap\nPhase 82 — Release reviewer packet index.\n",
                encoding="utf-8",
            )
            (setup / "bootstrap-ai-assets.sh").write_text("#!/usr/bin/env bash\n--release-reviewer-packet-index\n", encoding="utf-8")
            payloads = {
                "release-candidate-closure-review": {"summary": {"status": "ready-for-final-human-review", "manual_review_required": True, "executes_anything": False, "remote_mutation_allowed": False, "credential_validation_allowed": False, "remote_configured": False, "forbidden_findings": 0}},
                "manual-release-reviewer-checklist": {"summary": {"status": "ready-for-human-review", "manual_review_required": True, "executes_anything": False, "remote_mutation_allowed": False, "credential_validation_allowed": False, "forbidden_findings": 0}},
                "release-closure": {"summary": {"status": "ready-for-manual-release-review", "executes_anything": False, "remote_configured": False, "forbidden_findings": 0}},
                "github-final-preflight": {"summary": {"status": "ready", "executes_anything": False, "remote_configured": False, "forbidden_findings": 0}},
                "public-package-freshness-review": {"summary": {"status": "ready", "executes_anything": False, "remote_mutation_allowed": False, "credential_validation_allowed": False, "remote_configured": False, "forbidden_findings": 0}},
                "public-docs-external-reader-review": {"summary": {"status": "ready", "executes_anything": False, "remote_mutation_allowed": False, "credential_validation_allowed": False, "remote_configured": False, "forbidden_findings": 0}},
                "public-safety-scan": {"summary": {"status": "pass", "forbidden_findings": 0, "blockers": 0}},
                "release-readiness": {"summary": {"readiness": "ready", "fail": 0}},
                "public-release-pack": {"summary": {"status": "ready", "forbidden_findings": 0}},
                "public-release-archive": {"summary": {"status": "ready", "archive_sha256": "abc123"}},
                "public-release-smoke-test": {"summary": {"status": "pass", "fail": 0}},
                "completed-work-review": {"summary": {"status": "aligned", "executes_anything": False, "fail": 0}},
            }
            for prefix, payload in payloads.items():
                (reports / f"latest-{prefix}.json").write_text(__import__("json").dumps(payload), encoding="utf-8")
                (reports / f"latest-{prefix}.md").write_text(f"# {prefix}\n", encoding="utf-8")

            review = bootstrap_ai_assets.build_release_reviewer_packet_index_report(tmp)

            self.assertEqual(review["mode"], "release-reviewer-packet-index")
            self.assertEqual(review["summary"]["status"], "ready")
            self.assertEqual(review["summary"]["fail"], 0)
            self.assertFalse(review["summary"]["executes_anything"])
            self.assertFalse(review["summary"]["remote_mutation_allowed"])
            self.assertFalse(review["summary"]["credential_validation_allowed"])
            self.assertFalse(review["summary"]["remote_configured"])
            self.assertEqual(review["summary"]["forbidden_findings"], 0)
            self.assertGreaterEqual(review["summary"]["packet_items"], 10)
            item_ids = {item["id"] for item in review["packet_index"]}
            self.assertIn("final-release-candidate-review", item_ids)
            self.assertIn("manual-reviewer-checklist", item_ids)
            self.assertIn("public-package-freshness", item_ids)
            self.assertTrue(all(item["exists"] for item in review["packet_index"]))
            self.assertTrue(all(item["executes_anything"] is False for item in review["packet_index"]))
            check_names = {check["name"] for check in review["checks"]}
            self.assertIn("docs:release-plan-documents-reviewer-packet-index", check_names)
            self.assertIn("roadmap:phase82-documented", check_names)
            self.assertIn("shell:release-reviewer-packet-index-command", check_names)
            self.assertIn("--release-reviewer-packet-index --both", " ".join(review["recommendations"]))
            self.assertIn("not publication approval", " ".join(review["review_boundary"]).lower())

            (reports / "latest-release-candidate-closure-review.md").unlink()
            stale = bootstrap_ai_assets.build_release_reviewer_packet_index_report(tmp)
            self.assertEqual(stale["summary"]["status"], "blocked")
            self.assertGreater(stale["summary"]["fail"], 0)

    def test_release_reviewer_decision_log_records_manual_review_template_without_approval(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            docs = tmp / "docs"
            setup = tmp / "bootstrap" / "setup"
            reports = tmp / "bootstrap" / "reports"
            docs.mkdir(parents=True)
            setup.mkdir(parents=True)
            reports.mkdir(parents=True)
            (docs / "open-source-release-plan.md").write_text(
                "# Open-Source Release Plan\n"
                "Run --release-reviewer-decision-log --both after --release-reviewer-packet-index.\n"
                "This reviewer decision log is report-only/local-only; it records a human review template but does not approve, publish, push, create repos/remotes/tags/releases, validate credentials, call APIs, or execute hooks/actions/commands.\n",
                encoding="utf-8",
            )
            (docs / "public-roadmap.md").write_text(
                "# Public Roadmap\nPhase 83 — Release reviewer decision log.\n",
                encoding="utf-8",
            )
            (setup / "bootstrap-ai-assets.sh").write_text("#!/usr/bin/env bash\n--release-reviewer-decision-log\n", encoding="utf-8")
            packet_payload = {
                "summary": {
                    "status": "ready",
                    "manual_review_required": True,
                    "executes_anything": False,
                    "remote_mutation_allowed": False,
                    "credential_validation_allowed": False,
                    "remote_configured": False,
                    "forbidden_findings": 0,
                    "auto_approves_release": False,
                    "packet_items": 12,
                },
                "packet_index": [
                    {"id": "final-release-candidate-review", "exists": True, "status": "ready-for-final-human-review", "executes_anything": False},
                    {"id": "manual-reviewer-checklist", "exists": True, "status": "ready-for-human-review", "executes_anything": False},
                ],
            }
            (reports / "latest-release-reviewer-packet-index.json").write_text(__import__("json").dumps(packet_payload), encoding="utf-8")
            (reports / "latest-release-reviewer-packet-index.md").write_text("# packet index\n", encoding="utf-8")

            review = bootstrap_ai_assets.build_release_reviewer_decision_log_report(tmp)

            self.assertEqual(review["mode"], "release-reviewer-decision-log")
            self.assertEqual(review["summary"]["status"], "needs-human-review")
            self.assertEqual(review["summary"]["fail"], 0)
            self.assertTrue(review["summary"]["manual_review_required"])
            self.assertFalse(review["summary"]["executes_anything"])
            self.assertFalse(review["summary"]["remote_mutation_allowed"])
            self.assertFalse(review["summary"]["credential_validation_allowed"])
            self.assertFalse(review["summary"]["auto_approves_release"])
            self.assertEqual(review["summary"]["decision_recorded"], False)
            self.assertEqual(review["summary"]["decision_log_items"], len(review["decision_log_template"]))
            template_ids = {item["id"] for item in review["decision_log_template"]}
            self.assertIn("reviewer-identity", template_ids)
            self.assertIn("evidence-reviewed", template_ids)
            self.assertIn("public-private-boundary", template_ids)
            self.assertIn("publication-boundary", template_ids)
            self.assertIn("manual-decision", template_ids)
            self.assertTrue(all(item["status"] == "pending-human-entry" for item in review["decision_log_template"]))
            self.assertTrue(all(item["executes_anything"] is False for item in review["decision_log_template"]))
            check_names = {check["name"] for check in review["checks"]}
            self.assertIn("evidence:release-reviewer-packet-index:ready", check_names)
            self.assertIn("docs:release-plan-documents-reviewer-decision-log", check_names)
            self.assertIn("roadmap:phase83-documented", check_names)
            self.assertIn("shell:release-reviewer-decision-log-command", check_names)
            self.assertIn("--release-reviewer-decision-log --both", " ".join(review["recommendations"]))
            self.assertIn("not release approval", " ".join(review["review_boundary"]).lower())

            (reports / "latest-release-reviewer-packet-index.json").write_text(__import__("json").dumps({"summary": {"status": "blocked", "executes_anything": False}}), encoding="utf-8")
            stale = bootstrap_ai_assets.build_release_reviewer_decision_log_report(tmp)
            self.assertEqual(stale["summary"]["status"], "blocked")
            self.assertGreater(stale["summary"]["fail"], 0)

    def test_external_reviewer_quickstart_links_first_ten_minute_review_path_without_execution(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            docs = tmp / "docs"
            setup = tmp / "bootstrap" / "setup"
            reports = tmp / "bootstrap" / "reports"
            demo_pack = tmp / "examples" / "redacted" / "public-demo-pack"
            docs.mkdir(parents=True)
            setup.mkdir(parents=True)
            reports.mkdir(parents=True)
            demo_pack.mkdir(parents=True)
            (tmp / "README.md").write_text(
                "# Portable AI Assets\nStart here: own your AI work environment. This is a portability layer, not a runtime.\n",
                encoding="utf-8",
            )
            (docs / "public-facing-thesis.md").write_text(
                "# Public thesis\nOwn your AI work environment instead of rebuilding it. Public/private boundary stays explicit.\n",
                encoding="utf-8",
            )
            (docs / "open-source-release-plan.md").write_text(
                "# Open-Source Release Plan\n"
                "Run --external-reviewer-quickstart --both after --release-reviewer-decision-log.\n"
                "This quickstart is report-only/local-only and does not approve, publish, push, create repos/remotes/tags/releases, validate credentials, call APIs, upload artifacts, or execute hooks/actions/commands.\n",
                encoding="utf-8",
            )
            (docs / "public-roadmap.md").write_text(
                "# Public Roadmap\nPhase 84 — External reviewer quickstart.\n",
                encoding="utf-8",
            )
            (demo_pack / "PACK-INDEX.md").write_text("# Public demo pack\n", encoding="utf-8")
            (setup / "bootstrap-ai-assets.sh").write_text("#!/usr/bin/env bash\n--external-reviewer-quickstart\n", encoding="utf-8")
            packet_payload = {"summary": {"status": "ready", "manual_review_required": True, "executes_anything": False, "remote_mutation_allowed": False, "credential_validation_allowed": False, "remote_configured": False, "forbidden_findings": 0, "auto_approves_release": False, "packet_items": 12}}
            decision_payload = {"summary": {"status": "needs-human-review", "manual_review_required": True, "decision_recorded": False, "executes_anything": False, "remote_mutation_allowed": False, "credential_validation_allowed": False, "remote_configured": False, "forbidden_findings": 0, "auto_approves_release": False, "decision_log_items": 6}}
            for prefix, payload in {
                "release-reviewer-packet-index": packet_payload,
                "release-reviewer-decision-log": decision_payload,
            }.items():
                (reports / f"latest-{prefix}.json").write_text(__import__("json").dumps(payload), encoding="utf-8")
                (reports / f"latest-{prefix}.md").write_text(f"# {prefix}\n", encoding="utf-8")

            review = bootstrap_ai_assets.build_external_reviewer_quickstart_report(tmp)

            self.assertEqual(review["mode"], "external-reviewer-quickstart")
            self.assertEqual(review["summary"]["status"], "ready")
            self.assertEqual(review["summary"]["fail"], 0)
            self.assertTrue(review["summary"]["manual_review_required"])
            self.assertFalse(review["summary"]["executes_anything"])
            self.assertFalse(review["summary"]["remote_mutation_allowed"])
            self.assertFalse(review["summary"]["credential_validation_allowed"])
            self.assertFalse(review["summary"]["auto_approves_release"])
            self.assertEqual(review["summary"]["quickstart_items"], len(review["quickstart_path"]))
            item_ids = {item["id"] for item in review["quickstart_path"]}
            self.assertIn("readme-start-here", item_ids)
            self.assertIn("public-facing-thesis", item_ids)
            self.assertIn("public-demo-pack", item_ids)
            self.assertIn("reviewer-packet-index", item_ids)
            self.assertIn("decision-log-template", item_ids)
            self.assertTrue(all(item["exists"] for item in review["quickstart_path"]))
            self.assertTrue(all(item["executes_anything"] is False for item in review["quickstart_path"]))
            check_names = {check["name"] for check in review["checks"]}
            self.assertIn("docs:release-plan-documents-external-reviewer-quickstart", check_names)
            self.assertIn("roadmap:phase84-documented", check_names)
            self.assertIn("shell:external-reviewer-quickstart-command", check_names)
            self.assertIn("--external-reviewer-quickstart --both", " ".join(review["recommendations"]))
            self.assertIn("not release approval", " ".join(review["review_boundary"]).lower())

            (reports / "latest-release-reviewer-decision-log.json").write_text(__import__("json").dumps({"summary": {"status": "blocked", "executes_anything": False}}), encoding="utf-8")
            stale = bootstrap_ai_assets.build_external_reviewer_quickstart_report(tmp)
            self.assertEqual(stale["summary"]["status"], "blocked")
            self.assertGreater(stale["summary"]["fail"], 0)

    def test_external_reviewer_feedback_plan_captures_notes_as_non_executing_follow_up_drafts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            docs = tmp / "docs"
            setup = tmp / "bootstrap" / "setup"
            reports = tmp / "bootstrap" / "reports"
            docs.mkdir(parents=True)
            setup.mkdir(parents=True)
            reports.mkdir(parents=True)
            (docs / "open-source-release-plan.md").write_text(
                "# Open-Source Release Plan\n"
                "Run --external-reviewer-feedback-plan --both after --external-reviewer-quickstart and --release-reviewer-decision-log.\n"
                "This feedback plan is report-only/local-only and does not approve, publish, push, create repos/remotes/tags/releases, validate credentials, call APIs, upload artifacts, mutate issues, or execute hooks/actions/commands.\n",
                encoding="utf-8",
            )
            (docs / "public-roadmap.md").write_text(
                "# Public Roadmap\nPhase 85 — External reviewer feedback plan.\n",
                encoding="utf-8",
            )
            (setup / "bootstrap-ai-assets.sh").write_text("#!/usr/bin/env bash\n--external-reviewer-feedback-plan\n", encoding="utf-8")
            quickstart_payload = {"summary": {"status": "ready", "manual_review_required": True, "executes_anything": False, "remote_mutation_allowed": False, "credential_validation_allowed": False, "remote_configured": False, "forbidden_findings": 0, "auto_approves_release": False, "quickstart_items": 5}}
            decision_payload = {"summary": {"status": "needs-human-review", "manual_review_required": True, "decision_recorded": False, "executes_anything": False, "remote_mutation_allowed": False, "credential_validation_allowed": False, "remote_configured": False, "forbidden_findings": 0, "auto_approves_release": False, "decision_log_items": 6}}
            for prefix, payload in {
                "external-reviewer-quickstart": quickstart_payload,
                "release-reviewer-decision-log": decision_payload,
            }.items():
                (reports / f"latest-{prefix}.json").write_text(__import__("json").dumps(payload), encoding="utf-8")
                (reports / f"latest-{prefix}.md").write_text(f"# {prefix}\n", encoding="utf-8")

            review = bootstrap_ai_assets.build_external_reviewer_feedback_plan_report(tmp)

            self.assertEqual(review["mode"], "external-reviewer-feedback-plan")
            self.assertEqual(review["summary"]["status"], "ready-for-feedback-review")
            self.assertEqual(review["summary"]["fail"], 0)
            self.assertTrue(review["summary"]["manual_review_required"])
            self.assertFalse(review["summary"]["decision_recorded"])
            self.assertFalse(review["summary"]["auto_approves_release"])
            self.assertFalse(review["summary"]["executes_anything"])
            self.assertFalse(review["summary"]["remote_mutation_allowed"])
            self.assertFalse(review["summary"]["credential_validation_allowed"])
            self.assertEqual(review["summary"]["feedback_capture_items"], len(review["feedback_capture_template"]))
            self.assertEqual(review["summary"]["follow_up_drafts"], len(review["follow_up_backlog_drafts"]))
            capture_ids = {item["id"] for item in review["feedback_capture_template"]}
            self.assertIn("reviewer-notes-source", capture_ids)
            self.assertIn("follow-up-backlog-entry", capture_ids)
            draft_ids = {item["id"] for item in review["follow_up_backlog_drafts"]}
            self.assertIn("public-private-boundary-follow-up", draft_ids)
            self.assertIn("publication-boundary-follow-up", draft_ids)
            self.assertTrue(all(item["executes_anything"] is False for item in review["feedback_capture_template"]))
            self.assertTrue(all(item["executes"] is False for item in review["follow_up_backlog_drafts"]))
            check_names = {check["name"] for check in review["checks"]}
            self.assertIn("evidence:external-reviewer-quickstart:ready", check_names)
            self.assertIn("evidence:release-reviewer-decision-log:needs-human-review", check_names)
            self.assertIn("docs:release-plan-documents-external-reviewer-feedback-plan", check_names)
            self.assertIn("roadmap:phase85-documented", check_names)
            self.assertIn("shell:external-reviewer-feedback-plan-command", check_names)
            self.assertIn("not release approval", " ".join(review["review_boundary"]).lower())
            self.assertIn("does not mutate issues", " ".join(review["review_boundary"]).lower())

            (reports / "latest-external-reviewer-quickstart.json").write_text(__import__("json").dumps({"summary": {"status": "blocked", "executes_anything": False}}), encoding="utf-8")
            stale = bootstrap_ai_assets.build_external_reviewer_feedback_plan_report(tmp)
            self.assertEqual(stale["summary"]["status"], "blocked")
            self.assertGreater(stale["summary"]["fail"], 0)

    def test_external_reviewer_feedback_status_validates_human_feedback_file_without_mutation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            docs = tmp / "docs"
            setup = tmp / "bootstrap" / "setup"
            reports = tmp / "bootstrap" / "reports"
            feedback_dir = tmp / "bootstrap" / "reviewer-feedback"
            docs.mkdir(parents=True)
            setup.mkdir(parents=True)
            reports.mkdir(parents=True)
            feedback_dir.mkdir(parents=True)
            (docs / "open-source-release-plan.md").write_text(
                "# Open-Source Release Plan\n"
                "Run --external-reviewer-feedback-status --both after --external-reviewer-feedback-plan.\n"
                "This status gate is report-only/local-only and does not approve, publish, push, create repos/remotes/tags/releases, validate credentials, call APIs, upload artifacts, mutate issues, or execute hooks/actions/commands.\n",
                encoding="utf-8",
            )
            (docs / "public-roadmap.md").write_text(
                "# Public Roadmap\nPhase 86 — External reviewer feedback status.\n",
                encoding="utf-8",
            )
            (setup / "bootstrap-ai-assets.sh").write_text("#!/usr/bin/env bash\n--external-reviewer-feedback-status\n", encoding="utf-8")
            plan_payload = {"summary": {"status": "ready-for-feedback-review", "manual_review_required": True, "decision_recorded": False, "executes_anything": False, "remote_mutation_allowed": False, "credential_validation_allowed": False, "remote_configured": False, "forbidden_findings": 0, "auto_approves_release": False, "feedback_capture_items": 5, "follow_up_drafts": 3}}
            (reports / "latest-external-reviewer-feedback-plan.json").write_text(__import__("json").dumps(plan_payload), encoding="utf-8")
            (reports / "latest-external-reviewer-feedback-plan.md").write_text("# feedback plan\n", encoding="utf-8")
            feedback_file = feedback_dir / "external-reviewer-feedback.md"
            feedback_file.write_text(
                "# External Reviewer Feedback\n"
                "reviewer: reviewer-handle\n"
                "reviewed_at: 2026-04-26T10:45:00\n"
                "source_decision_log: bootstrap/reports/latest-release-reviewer-decision-log.md\n"
                "public_private_boundary: no blockers found\n"
                "publication_boundary: no automated publish/push/credential/API issue found\n"
                "first_ten_minutes_usability: clear enough; improve follow-up docs later\n"
                "follow_up_items:\n- tighten quickstart copy\n"
                "approval_recorded: false\n"
                "go_no_go_decision_recorded: false\n",
                encoding="utf-8",
            )

            review = bootstrap_ai_assets.build_external_reviewer_feedback_status_report(tmp)

            self.assertEqual(review["mode"], "external-reviewer-feedback-status")
            self.assertEqual(review["summary"]["status"], "ready-for-follow-up-review")
            self.assertEqual(review["summary"]["fail"], 0)
            self.assertTrue(review["summary"]["manual_review_required"])
            self.assertTrue(review["summary"]["feedback_file_present"])
            self.assertFalse(review["summary"]["decision_recorded"])
            self.assertFalse(review["summary"]["approval_recorded"])
            self.assertFalse(review["summary"]["auto_approves_release"])
            self.assertFalse(review["summary"]["executes_anything"])
            self.assertFalse(review["summary"]["remote_mutation_allowed"])
            self.assertFalse(review["summary"]["credential_validation_allowed"])
            self.assertEqual(review["summary"]["required_fields"], len(review["required_feedback_fields"]))
            self.assertEqual(review["summary"]["present_required_fields"], len(review["required_feedback_fields"]))
            self.assertEqual(review["summary"]["follow_up_items"], 1)
            field_ids = {item["id"] for item in review["required_feedback_fields"]}
            self.assertIn("reviewer", field_ids)
            self.assertIn("publication_boundary", field_ids)
            self.assertTrue(all(item["status"] == "present" for item in review["required_feedback_fields"]))
            self.assertTrue(all(item["executes_anything"] is False for item in review["required_feedback_fields"]))
            self.assertTrue(all(item["executes"] is False for item in review["follow_up_review_items"]))
            check_names = {check["name"] for check in review["checks"]}
            self.assertIn("evidence:external-reviewer-feedback-plan:ready", check_names)
            self.assertIn("feedback-file:present", check_names)
            self.assertIn("feedback-file:no-approval-recorded", check_names)
            self.assertIn("docs:release-plan-documents-external-reviewer-feedback-status", check_names)
            self.assertIn("roadmap:phase86-documented", check_names)
            self.assertIn("shell:external-reviewer-feedback-status-command", check_names)
            self.assertIn("not release approval", " ".join(review["review_boundary"]).lower())
            self.assertIn("does not mutate issues", " ".join(review["review_boundary"]).lower())

            feedback_file.write_text("# incomplete\nreviewer: reviewer-handle\napproval_recorded: true\n", encoding="utf-8")
            stale = bootstrap_ai_assets.build_external_reviewer_feedback_status_report(tmp)
            self.assertEqual(stale["summary"]["status"], "needs-human-feedback")
            self.assertGreater(stale["summary"]["fail"], 0)
            self.assertTrue(stale["summary"]["approval_recorded"])

    def test_external_reviewer_feedback_template_writes_template_without_satisfying_status_gate(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            docs = tmp / "docs"
            setup = tmp / "bootstrap" / "setup"
            reports = tmp / "bootstrap" / "reports"
            docs.mkdir(parents=True)
            setup.mkdir(parents=True)
            reports.mkdir(parents=True)
            (docs / "open-source-release-plan.md").write_text(
                "# Open-Source Release Plan\n"
                "Run --external-reviewer-feedback-template --both before a human fills external-reviewer-feedback.md.\n"
                "This template generator is template-only/report-only and does not approve, publish, push, create repos/remotes/tags/releases, validate credentials, call APIs, upload artifacts, mutate issues, or execute hooks/actions/commands.\n",
                encoding="utf-8",
            )
            (docs / "public-roadmap.md").write_text(
                "# Public Roadmap\nPhase 87 — External reviewer feedback template.\n",
                encoding="utf-8",
            )
            (setup / "bootstrap-ai-assets.sh").write_text("#!/usr/bin/env bash\n--external-reviewer-feedback-template\n", encoding="utf-8")
            status_payload = {"summary": {"status": "needs-human-feedback", "manual_review_required": True, "feedback_file_present": False, "decision_recorded": False, "approval_recorded": False, "executes_anything": False, "remote_mutation_allowed": False, "credential_validation_allowed": False, "remote_configured": False, "forbidden_findings": 0, "auto_approves_release": False, "required_fields": 9, "present_required_fields": 0}}
            (reports / "latest-external-reviewer-feedback-status.json").write_text(__import__("json").dumps(status_payload), encoding="utf-8")
            (reports / "latest-external-reviewer-feedback-status.md").write_text("# feedback status\n", encoding="utf-8")

            review = bootstrap_ai_assets.execute_external_reviewer_feedback_template(tmp)

            template_path = tmp / "bootstrap" / "reviewer-feedback" / "external-reviewer-feedback.md.template"
            final_feedback_path = tmp / "bootstrap" / "reviewer-feedback" / "external-reviewer-feedback.md"
            self.assertEqual(review["mode"], "external-reviewer-feedback-template")
            self.assertEqual(review["summary"]["status"], "template-ready")
            self.assertEqual(review["summary"]["fail"], 0)
            self.assertTrue(review["summary"]["template_written"])
            self.assertFalse(review["summary"]["feedback_file_created"])
            self.assertFalse(final_feedback_path.exists())
            self.assertTrue(template_path.is_file())
            template_text = template_path.read_text(encoding="utf-8")
            self.assertIn("reviewer:", template_text)
            self.assertIn("approval_recorded: false", template_text)
            self.assertIn("go_no_go_decision_recorded: false", template_text)
            self.assertIn("copy this template", template_text.lower())
            self.assertTrue(review["summary"]["manual_review_required"])
            self.assertFalse(review["summary"]["auto_approves_release"])
            self.assertFalse(review["summary"]["executes_anything"])
            self.assertFalse(review["summary"]["remote_mutation_allowed"])
            self.assertFalse(review["summary"]["credential_validation_allowed"])
            self.assertEqual(review["summary"]["template_fields"], len(review["template_fields"]))
            self.assertTrue(all(item["executes_anything"] is False for item in review["template_fields"]))
            check_names = {check["name"] for check in review["checks"]}
            self.assertIn("feedback-status:needs-human-feedback", check_names)
            self.assertIn("template:file-written", check_names)
            self.assertIn("template:final-feedback-not-created", check_names)
            self.assertIn("docs:release-plan-documents-external-reviewer-feedback-template", check_names)
            self.assertIn("roadmap:phase87-documented", check_names)
            self.assertIn("shell:external-reviewer-feedback-template-command", check_names)
            self.assertIn("not release approval", " ".join(review["review_boundary"]).lower())
            self.assertIn("does not mutate issues", " ".join(review["review_boundary"]).lower())

            status_after = bootstrap_ai_assets.build_external_reviewer_feedback_status_report(tmp)
            self.assertEqual(status_after["summary"]["status"], "needs-human-feedback")
            self.assertFalse(status_after["summary"]["feedback_file_present"])

    def test_external_reviewer_feedback_followup_index_links_feedback_artifacts_without_mutation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            docs = tmp / "docs"
            setup = tmp / "bootstrap" / "setup"
            reports = tmp / "bootstrap" / "reports"
            feedback_dir = tmp / "bootstrap" / "reviewer-feedback"
            docs.mkdir(parents=True)
            setup.mkdir(parents=True)
            reports.mkdir(parents=True)
            feedback_dir.mkdir(parents=True)
            (docs / "open-source-release-plan.md").write_text(
                "# Open-Source Release Plan\n"
                "Run --external-reviewer-feedback-followup-index --both after --external-reviewer-feedback-template, --external-reviewer-feedback-status, and --external-reviewer-feedback-plan.\n"
                "This follow-up index is report-only/local-only and does not approve, publish, push, create repos/remotes/tags/releases, validate credentials, call APIs, upload artifacts, mutate issues, or execute hooks/actions/commands.\n",
                encoding="utf-8",
            )
            (docs / "public-roadmap.md").write_text(
                "# Public Roadmap\nPhase 88 — External reviewer feedback follow-up index.\n",
                encoding="utf-8",
            )
            (setup / "bootstrap-ai-assets.sh").write_text("#!/usr/bin/env bash\n--external-reviewer-feedback-followup-index\n", encoding="utf-8")
            summaries = {
                "external-reviewer-feedback-plan": {"status": "ready-for-feedback-review", "manual_review_required": True, "executes_anything": False, "remote_mutation_allowed": False, "credential_validation_allowed": False, "remote_configured": False, "forbidden_findings": 0, "auto_approves_release": False},
                "external-reviewer-feedback-status": {"status": "needs-human-feedback", "manual_review_required": True, "feedback_file_present": False, "decision_recorded": False, "approval_recorded": False, "executes_anything": False, "remote_mutation_allowed": False, "credential_validation_allowed": False, "remote_configured": False, "forbidden_findings": 0, "auto_approves_release": False},
                "external-reviewer-feedback-template": {"status": "template-ready", "manual_review_required": True, "template_written": True, "feedback_file_created": False, "executes_anything": False, "remote_mutation_allowed": False, "credential_validation_allowed": False, "remote_configured": False, "forbidden_findings": 0, "auto_approves_release": False},
            }
            for prefix, summary in summaries.items():
                (reports / f"latest-{prefix}.json").write_text(__import__("json").dumps({"summary": summary}), encoding="utf-8")
                (reports / f"latest-{prefix}.md").write_text(f"# {prefix}\n", encoding="utf-8")
            (feedback_dir / "external-reviewer-feedback.md.template").write_text("# template\n", encoding="utf-8")

            review = bootstrap_ai_assets.build_external_reviewer_feedback_followup_index_report(tmp)

            self.assertEqual(review["mode"], "external-reviewer-feedback-followup-index")
            self.assertEqual(review["summary"]["status"], "ready")
            self.assertEqual(review["summary"]["fail"], 0)
            self.assertTrue(review["summary"]["manual_review_required"])
            self.assertFalse(review["summary"]["feedback_file_present"])
            self.assertFalse(review["summary"]["auto_approves_release"])
            self.assertFalse(review["summary"]["executes_anything"])
            self.assertFalse(review["summary"]["remote_mutation_allowed"])
            self.assertFalse(review["summary"]["credential_validation_allowed"])
            self.assertEqual(review["summary"]["packet_items"], len(review["packet_items"]))
            item_ids = {item["id"] for item in review["packet_items"]}
            self.assertIn("feedback-template", item_ids)
            self.assertIn("feedback-status-report", item_ids)
            self.assertIn("feedback-plan-report", item_ids)
            self.assertIn("optional-filled-feedback-file", item_ids)
            optional_item = [item for item in review["packet_items"] if item["id"] == "optional-filled-feedback-file"][0]
            self.assertFalse(optional_item["required"])
            self.assertFalse(optional_item["exists"])
            self.assertTrue(all(item["executes_anything"] is False for item in review["packet_items"]))
            check_names = {check["name"] for check in review["checks"]}
            self.assertIn("evidence:external-reviewer-feedback-template:template-ready", check_names)
            self.assertIn("evidence:external-reviewer-feedback-status:available", check_names)
            self.assertIn("docs:release-plan-documents-external-reviewer-feedback-followup-index", check_names)
            self.assertIn("roadmap:phase88-documented", check_names)
            self.assertIn("shell:external-reviewer-feedback-followup-index-command", check_names)
            self.assertIn("not release approval", " ".join(review["review_boundary"]).lower())
            self.assertIn("does not mutate issues", " ".join(review["review_boundary"]).lower())

            (reports / "latest-external-reviewer-feedback-template.json").write_text(__import__("json").dumps({"summary": {"status": "blocked", "executes_anything": False}}), encoding="utf-8")
            stale = bootstrap_ai_assets.build_external_reviewer_feedback_followup_index_report(tmp)
            self.assertEqual(stale["summary"]["status"], "blocked")
            self.assertGreater(stale["summary"]["fail"], 0)

    def test_external_reviewer_feedback_followup_candidates_require_ready_human_feedback_and_write_local_only_bundle(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            docs = tmp / "docs"
            setup = tmp / "bootstrap" / "setup"
            reports = tmp / "bootstrap" / "reports"
            feedback_dir = tmp / "bootstrap" / "reviewer-feedback"
            docs.mkdir(parents=True)
            setup.mkdir(parents=True)
            reports.mkdir(parents=True)
            feedback_dir.mkdir(parents=True)
            (docs / "open-source-release-plan.md").write_text(
                "# Open-Source Release Plan\n"
                "Run --external-reviewer-feedback-followup-candidates --both after --external-reviewer-feedback-followup-index and a ready feedback status.\n"
                "This candidate generator is local-only/template-only/report-only and does not approve, publish, push, create repos/remotes/tags/releases, validate credentials, call APIs, upload artifacts, mutate issues, or execute hooks/actions/commands.\n",
                encoding="utf-8",
            )
            (docs / "public-roadmap.md").write_text(
                "# Public Roadmap\nPhase 89 — External reviewer feedback follow-up candidates.\n",
                encoding="utf-8",
            )
            (setup / "bootstrap-ai-assets.sh").write_text("#!/usr/bin/env bash\n--external-reviewer-feedback-followup-candidates\n", encoding="utf-8")
            status_summary = {"status": "ready-for-follow-up-review", "manual_review_required": True, "feedback_file_present": True, "decision_recorded": False, "approval_recorded": False, "executes_anything": False, "remote_mutation_allowed": False, "credential_validation_allowed": False, "remote_configured": False, "forbidden_findings": 0, "auto_approves_release": False}
            index_summary = {"status": "ready", "manual_review_required": True, "feedback_file_present": True, "decision_recorded": False, "approval_recorded": False, "executes_anything": False, "remote_mutation_allowed": False, "credential_validation_allowed": False, "remote_configured": False, "forbidden_findings": 0, "auto_approves_release": False}
            for prefix, summary in {
                "external-reviewer-feedback-status": status_summary,
                "external-reviewer-feedback-followup-index": index_summary,
            }.items():
                (reports / f"latest-{prefix}.json").write_text(__import__("json").dumps({"summary": summary}), encoding="utf-8")
                (reports / f"latest-{prefix}.md").write_text(f"# {prefix}\n", encoding="utf-8")
            (feedback_dir / "external-reviewer-feedback.md").write_text(
                "# External Reviewer Feedback\n"
                "reviewer: reviewer-handle\n"
                "reviewed_at: 2026-04-26T11:20:00\n"
                "source_decision_log: bootstrap/reports/latest-release-reviewer-decision-log.md\n"
                "public_private_boundary: no blockers found\n"
                "publication_boundary: command boundary wording should be clearer\n"
                "first_ten_minutes_usability: quickstart is understandable\n"
                "follow_up_items:\n- Clarify publication boundary wording\n- Add one screenshot-free quickstart example\n"
                "approval_recorded: false\n"
                "go_no_go_decision_recorded: false\n",
                encoding="utf-8",
            )

            review = bootstrap_ai_assets.execute_external_reviewer_feedback_followup_candidates(tmp)

            self.assertEqual(review["mode"], "external-reviewer-feedback-followup-candidates")
            self.assertEqual(review["summary"]["status"], "candidates-generated")
            self.assertEqual(review["summary"]["fail"], 0)
            self.assertTrue(review["summary"]["manual_review_required"])
            self.assertTrue(review["summary"]["feedback_file_present"])
            self.assertEqual(review["summary"]["candidate_files_written"], 2)
            self.assertEqual(review["summary"]["remote_issues_created"], 0)
            self.assertFalse(review["summary"]["auto_approves_release"])
            self.assertFalse(review["summary"]["executes_anything"])
            self.assertFalse(review["summary"]["remote_mutation_allowed"])
            self.assertFalse(review["summary"]["credential_validation_allowed"])
            self.assertTrue(review["candidate_bundle"]["exists"])
            self.assertTrue(all(item["executes"] is False for item in review["candidate_files"]))
            self.assertTrue(all(item["mutates_issues"] is False for item in review["candidate_files"]))
            for item in review["candidate_files"]:
                self.assertTrue((tmp / item["path"]).is_file())
            check_names = {check["name"] for check in review["checks"]}
            self.assertIn("evidence:external-reviewer-feedback-status:ready", check_names)
            self.assertIn("evidence:external-reviewer-feedback-followup-index:ready", check_names)
            self.assertIn("docs:release-plan-documents-external-reviewer-feedback-followup-candidates", check_names)
            self.assertIn("roadmap:phase89-documented", check_names)
            self.assertIn("shell:external-reviewer-feedback-followup-candidates-command", check_names)
            self.assertIn("not release approval", " ".join(review["review_boundary"]).lower())
            self.assertIn("does not create remote issues", " ".join(review["review_boundary"]).lower())

            (reports / "latest-external-reviewer-feedback-status.json").write_text(__import__("json").dumps({"summary": {"status": "needs-human-feedback", "feedback_file_present": False, "executes_anything": False}}), encoding="utf-8")
            skipped = bootstrap_ai_assets.execute_external_reviewer_feedback_followup_candidates(tmp)
            self.assertEqual(skipped["summary"]["status"], "blocked")
            self.assertEqual(skipped["summary"]["candidate_files_written"], 0)
            self.assertGreater(skipped["summary"]["fail"], 0)

    def test_external_reviewer_feedback_followup_candidate_status_scans_local_candidate_bundles_without_mutation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            docs = tmp / "docs"
            setup = tmp / "bootstrap" / "setup"
            reports = tmp / "bootstrap" / "reports"
            bundle = tmp / "bootstrap" / "candidates" / "external-reviewer-feedback-followups-20260426-120000"
            docs.mkdir(parents=True)
            setup.mkdir(parents=True)
            reports.mkdir(parents=True)
            bundle.mkdir(parents=True)
            (docs / "open-source-release-plan.md").write_text(
                "# Open-Source Release Plan\n"
                "Run --external-reviewer-feedback-followup-candidate-status --both after --external-reviewer-feedback-followup-candidates.\n"
                "This scanner is local-only/report-only and does not approve, publish, push, create repos/remotes/tags/releases, validate credentials, call APIs, upload artifacts, mutate issues/backlogs, or execute hooks/actions/commands.\n",
                encoding="utf-8",
            )
            (docs / "public-roadmap.md").write_text(
                "# Public Roadmap\nPhase 90 — External reviewer feedback follow-up candidate status.\n",
                encoding="utf-8",
            )
            (setup / "bootstrap-ai-assets.sh").write_text("#!/usr/bin/env bash\n--external-reviewer-feedback-followup-candidate-status\n", encoding="utf-8")
            (reports / "latest-external-reviewer-feedback-followup-candidates.json").write_text(__import__("json").dumps({"summary": {"status": "candidates-generated", "manual_review_required": True, "candidate_files_written": 2, "remote_issues_created": 0, "executes_anything": False, "remote_mutation_allowed": False, "credential_validation_allowed": False, "remote_configured": False, "forbidden_findings": 0, "auto_approves_release": False}, "candidate_bundle": {"path": "bootstrap/candidates/external-reviewer-feedback-followups-20260426-120000", "exists": True}}), encoding="utf-8")
            (bundle / "REVIEW-INSTRUCTIONS.md").write_text("# Review\nManual review only.\n", encoding="utf-8")
            (bundle / "follow-up-01.candidate.md").write_text(
                "# Follow-up candidate 1\n\nStatus: candidate-needs-human-review\nExecutes: false\nMutates issues: false\nAuto-approves release: false\nHuman decision: create-issue-manually\n",
                encoding="utf-8",
            )
            (bundle / "follow-up-02.candidate.md").write_text(
                "# Follow-up candidate 2\n\nStatus: candidate-deferred\nExecutes: false\nMutates issues: false\nAuto-approves release: false\nHuman decision: defer\n",
                encoding="utf-8",
            )

            review = bootstrap_ai_assets.build_external_reviewer_feedback_followup_candidate_status_report(tmp)

            self.assertEqual(review["mode"], "external-reviewer-feedback-followup-candidate-status")
            self.assertEqual(review["summary"]["status"], "ready-for-manual-follow-up")
            self.assertEqual(review["summary"]["fail"], 0)
            self.assertTrue(review["summary"]["manual_review_required"])
            self.assertEqual(review["summary"]["candidate_files_scanned"], 2)
            self.assertEqual(review["summary"]["human_reviewed_candidates"], 2)
            self.assertEqual(review["summary"]["remote_issues_created"], 0)
            self.assertFalse(review["summary"]["writes_anything"])
            self.assertFalse(review["summary"]["executes_anything"])
            self.assertFalse(review["summary"]["remote_mutation_allowed"])
            self.assertFalse(review["summary"]["credential_validation_allowed"])
            self.assertFalse(review["summary"]["auto_approves_release"])
            self.assertEqual(len(review["candidate_files"]), 2)
            check_names = {check["name"] for check in review["checks"]}
            self.assertIn("evidence:external-reviewer-feedback-followup-candidates:generated", check_names)
            self.assertIn("candidates:all-local-non-executing", check_names)
            self.assertIn("docs:release-plan-documents-external-reviewer-feedback-followup-candidate-status", check_names)
            self.assertIn("roadmap:phase90-documented", check_names)
            self.assertIn("shell:external-reviewer-feedback-followup-candidate-status-command", check_names)
            self.assertIn("does not create remote issues", " ".join(review["review_boundary"]).lower())

            (bundle / "follow-up-03.candidate.md").write_text(
                "# Bad\n\nExecutes: true\nMutates issues: true\nAuto-approves release: true\n",
                encoding="utf-8",
            )
            unsafe = bootstrap_ai_assets.build_external_reviewer_feedback_followup_candidate_status_report(tmp)
            self.assertEqual(unsafe["summary"]["status"], "blocked")
            self.assertGreater(unsafe["summary"]["fail"], 0)
            self.assertFalse(unsafe["summary"]["writes_anything"])

    def test_initial_completion_review_distinguishes_machine_readiness_from_human_feedback(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            docs = tmp / "docs"
            setup = tmp / "bootstrap" / "setup"
            reports = tmp / "bootstrap" / "reports"
            docs.mkdir(parents=True)
            setup.mkdir(parents=True)
            reports.mkdir(parents=True)
            (docs / "open-source-release-plan.md").write_text(
                "# Open-Source Release Plan\n"
                "Run --initial-completion-review --both after release-readiness, public-safety-scan, public-release-pack, public-repo-staging-status, public-package-freshness-review, completed-work-review, external-reviewer-feedback-status, external-reviewer-feedback-followup-candidates, and external-reviewer-feedback-followup-candidate-status.\n"
                "This final local-only/report-only closure review separates machine readiness from human feedback and manual publication; it does not approve, publish, push, create repos/remotes/tags/releases, validate credentials, call APIs, upload artifacts, mutate issues/backlogs, or execute hooks/actions/commands.\n",
                encoding="utf-8",
            )
            (docs / "public-roadmap.md").write_text(
                "# Public Roadmap\n\n### Phase 91 — Initial completion / MVP closure review ✅\nlocal closure gate for machine readiness and human handoff.\n",
                encoding="utf-8",
            )
            (setup / "bootstrap-ai-assets.sh").write_text("#!/usr/bin/env bash\n--initial-completion-review\n", encoding="utf-8")
            report_summaries = {
                "latest-public-safety-scan.json": {"status": "pass", "blockers": 0, "warnings": 0},
                "latest-release-readiness.json": {"readiness": "ready", "fail": 0, "warn": 0},
                "latest-public-release-archive.json": {"file_count": 12, "archive_sha256": "abc123"},
                "latest-public-release-smoke-test.json": {"status": "pass", "failed": 0},
                "latest-public-release-pack.json": {"files_in_pack": 12, "public_safety_status": "pass", "release_readiness": "ready"},
                "latest-public-repo-staging-status.json": {"status": "ready", "remote_configured": False, "remote_push_enabled": False},
                "latest-public-package-freshness-review.json": {"status": "ready", "fail": 0},
                "latest-completed-work-review.json": {"status": "aligned", "fail": 0, "executes_anything": False},
                "latest-external-reviewer-feedback-template.json": {"status": "template-ready", "feedback_file_created": False, "template_written": True, "writes_anything": True, "executes_anything": False},
                "latest-external-reviewer-feedback-status.json": {"status": "needs-human-feedback", "feedback_file_present": False, "executes_anything": False},
                "latest-external-reviewer-feedback-followup-index.json": {"status": "ready", "feedback_file_present": False, "executes_anything": False},
                "latest-external-reviewer-feedback-followup-candidates.json": {"status": "blocked", "candidate_files_written": 0, "remote_issues_created": 0, "executes_anything": False, "remote_mutation_allowed": False, "credential_validation_allowed": False},
                "latest-external-reviewer-feedback-followup-candidate-status.json": {"status": "blocked", "candidate_bundle_present": False, "candidate_files_scanned": 0, "writes_anything": False, "executes_anything": False, "remote_mutation_allowed": False, "credential_validation_allowed": False, "auto_approves_release": False},
            }
            for filename, summary in report_summaries.items():
                (reports / filename).write_text(__import__("json").dumps({"summary": summary}), encoding="utf-8")

            review = bootstrap_ai_assets.build_initial_completion_review_report(tmp)

            self.assertEqual(review["mode"], "initial-completion-review")
            self.assertEqual(review["summary"]["status"], "machine-ready-human-feedback-pending")
            self.assertEqual(review["summary"]["fail"], 0)
            self.assertGreaterEqual(review["summary"]["warn"], 1)
            self.assertTrue(review["summary"]["machine_readiness_ready"])
            self.assertFalse(review["summary"]["human_feedback_complete"])
            self.assertTrue(review["summary"]["human_action_required"])
            self.assertFalse(review["summary"]["writes_anything"])
            self.assertFalse(review["summary"]["executes_anything"])
            self.assertFalse(review["summary"]["remote_mutation_allowed"])
            self.assertFalse(review["summary"]["credential_validation_allowed"])
            self.assertFalse(review["summary"]["auto_approves_release"])
            check_names = {check["name"] for check in review["checks"]}
            self.assertIn("machine-readiness:public-release-gates-ready", check_names)
            self.assertIn("human-feedback:final-feedback-file-status", check_names)
            self.assertIn("docs:release-plan-documents-initial-completion-review", check_names)
            self.assertIn("roadmap:phase91-documented", check_names)
            self.assertIn("shell:initial-completion-review-command", check_names)
            self.assertIn("external-reviewer-feedback-status", review["source_summaries"])
            self.assertIn("manual", " ".join(review["human_handoff_required"]).lower())

            ready_feedback = {"status": "ready", "feedback_file_present": True, "executes_anything": False}
            (reports / "latest-external-reviewer-feedback-status.json").write_text(__import__("json").dumps({"summary": ready_feedback}), encoding="utf-8")
            (reports / "latest-external-reviewer-feedback-followup-candidates.json").write_text(__import__("json").dumps({"summary": {"status": "candidates-generated", "candidate_files_written": 1, "remote_issues_created": 0, "executes_anything": False, "remote_mutation_allowed": False, "credential_validation_allowed": False}}), encoding="utf-8")
            (reports / "latest-external-reviewer-feedback-followup-candidate-status.json").write_text(__import__("json").dumps({"summary": {"status": "ready-for-manual-follow-up", "candidate_bundle_present": True, "candidate_files_scanned": 1, "writes_anything": False, "executes_anything": False, "remote_mutation_allowed": False, "credential_validation_allowed": False, "auto_approves_release": False}}), encoding="utf-8")
            final_review = bootstrap_ai_assets.build_initial_completion_review_report(tmp)
            self.assertEqual(final_review["summary"]["status"], "initial-completion-ready")
            self.assertTrue(final_review["summary"]["human_feedback_complete"])

    def test_human_action_closure_checklist_guides_manual_feedback_without_mutation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            docs = tmp / "docs"
            setup = tmp / "bootstrap" / "setup"
            reports = tmp / "bootstrap" / "reports"
            reviewer_feedback = tmp / "bootstrap" / "reviewer-feedback"
            docs.mkdir(parents=True)
            setup.mkdir(parents=True)
            reports.mkdir(parents=True)
            reviewer_feedback.mkdir(parents=True)
            (docs / "open-source-release-plan.md").write_text(
                "# Open-Source Release Plan\n"
                "Run --human-action-closure-checklist --both after --initial-completion-review --both.\n"
                "The checklist is local-only/report-only and guides human feedback, follow-up candidate review, and manual publication boundaries without approving, publishing, pushing, creating issues/backlogs, validating credentials, calling APIs, uploading, mutating remotes, or executing commands.\n",
                encoding="utf-8",
            )
            (docs / "public-roadmap.md").write_text(
                "# Public Roadmap\n\n### Phase 92 — Human action closure checklist ✅\nmanual checklist after initial completion review.\n",
                encoding="utf-8",
            )
            (setup / "bootstrap-ai-assets.sh").write_text("#!/usr/bin/env bash\n--human-action-closure-checklist\n", encoding="utf-8")
            (reviewer_feedback / "external-reviewer-feedback.md.template").write_text("# External reviewer feedback template\n", encoding="utf-8")
            report_summaries = {
                "latest-initial-completion-review.json": {"status": "machine-ready-human-feedback-pending", "machine_readiness_ready": True, "human_feedback_complete": False, "human_action_required": True, "executes_anything": False, "remote_mutation_allowed": False, "credential_validation_allowed": False, "auto_approves_release": False},
                "latest-external-reviewer-feedback-template.json": {"status": "template-ready", "template_written": True, "feedback_file_created": False, "executes_anything": False},
                "latest-external-reviewer-feedback-status.json": {"status": "needs-human-feedback", "feedback_file_present": False, "executes_anything": False},
                "latest-external-reviewer-feedback-followup-candidates.json": {"status": "blocked", "candidate_files_written": 0, "remote_issues_created": 0, "executes_anything": False, "remote_mutation_allowed": False, "credential_validation_allowed": False},
                "latest-external-reviewer-feedback-followup-candidate-status.json": {"status": "blocked", "candidate_bundle_present": False, "candidate_files_scanned": 0, "writes_anything": False, "executes_anything": False, "remote_mutation_allowed": False, "credential_validation_allowed": False, "auto_approves_release": False},
            }
            for filename, summary in report_summaries.items():
                (reports / filename).write_text(__import__("json").dumps({"summary": summary}), encoding="utf-8")

            checklist = bootstrap_ai_assets.build_human_action_closure_checklist_report(tmp)

            self.assertEqual(checklist["mode"], "human-action-closure-checklist")
            self.assertEqual(checklist["summary"]["status"], "ready-for-human-action")
            self.assertTrue(checklist["summary"]["machine_readiness_ready"])
            self.assertTrue(checklist["summary"]["human_feedback_pending"])
            self.assertTrue(checklist["summary"]["manual_review_required"])
            self.assertFalse(checklist["summary"]["writes_anything"])
            self.assertEqual(checklist["summary"]["writes"], 0)
            self.assertFalse(checklist["summary"]["executes_anything"])
            self.assertFalse(checklist["summary"]["remote_mutation_allowed"])
            self.assertFalse(checklist["summary"]["credential_validation_allowed"])
            self.assertFalse(checklist["summary"]["auto_approves_release"])
            self.assertEqual(checklist["summary"]["remote_issues_created"], 0)
            action_ids = {item["id"] for item in checklist["human_action_checklist"]}
            self.assertIn("copy-fill-external-reviewer-feedback", action_ids)
            self.assertIn("rerun-external-reviewer-feedback-status", action_ids)
            self.assertIn("generate-local-followup-candidates", action_ids)
            self.assertIn("review-followup-candidates-manually", action_ids)
            self.assertIn("manual-publication-decision", action_ids)
            self.assertIn("bootstrap/reviewer-feedback/external-reviewer-feedback.md", " ".join(checklist["human_action_required"]))
            check_names = {check["name"] for check in checklist["checks"]}
            self.assertIn("initial-completion:machine-ready-human-feedback-pending", check_names)
            self.assertIn("docs:release-plan-documents-human-action-closure-checklist", check_names)
            self.assertIn("roadmap:phase92-documented", check_names)
            self.assertIn("shell:human-action-closure-checklist-command", check_names)

    def test_manual_reviewer_execution_packet_indexes_human_runbook_without_execution(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            docs = tmp / "docs"
            setup = tmp / "bootstrap" / "setup"
            reports = tmp / "bootstrap" / "reports"
            reviewer_feedback = tmp / "bootstrap" / "reviewer-feedback"
            docs.mkdir(parents=True)
            setup.mkdir(parents=True)
            reports.mkdir(parents=True)
            reviewer_feedback.mkdir(parents=True)
            (docs / "open-source-release-plan.md").write_text(
                "# Open-Source Release Plan\n"
                "Run --human-action-closure-checklist --both and then --manual-reviewer-execution-packet --both.\n"
                "The manual reviewer execution packet is local-only/report-only and gives a one-page human runbook for feedback, follow-up, and manual publication without approving, publishing, pushing, creating issues/backlogs, validating credentials, calling APIs/providers, uploading, mutating remotes, or executing commands.\n",
                encoding="utf-8",
            )
            (docs / "public-roadmap.md").write_text(
                "# Public Roadmap\n\n### Phase 93 — Manual reviewer execution packet ✅\none-page human-runbook index after the human action closure checklist.\n",
                encoding="utf-8",
            )
            (setup / "bootstrap-ai-assets.sh").write_text("#!/usr/bin/env bash\n--manual-reviewer-execution-packet\n", encoding="utf-8")
            (reviewer_feedback / "external-reviewer-feedback.md.template").write_text("# External reviewer feedback template\n", encoding="utf-8")
            summaries = {
                "latest-human-action-closure-checklist.json": {"status": "ready-for-human-action", "machine_readiness_ready": True, "human_feedback_pending": True, "manual_review_required": True, "followup_candidates_ready": False, "writes_anything": False, "executes_anything": False, "remote_mutation_allowed": False, "credential_validation_allowed": False, "auto_approves_release": False, "remote_issues_created": 0},
                "latest-external-reviewer-feedback-template.json": {"status": "template-ready", "template_written": True, "feedback_file_created": False, "executes_anything": False},
                "latest-external-reviewer-feedback-followup-index.json": {"status": "ready", "writes_anything": False, "executes_anything": False, "remote_mutation_allowed": False, "credential_validation_allowed": False},
                "latest-external-reviewer-quickstart.json": {"status": "ready", "executes_anything": False, "remote_mutation_allowed": False, "credential_validation_allowed": False, "auto_approves_release": False},
                "latest-release-reviewer-packet-index.json": {"status": "ready", "executes_anything": False, "remote_mutation_allowed": False, "credential_validation_allowed": False, "auto_approves_release": False},
                "latest-public-repo-staging-status.json": {"status": "ready", "remote_configured": False, "executes_anything": False, "remote_mutation_allowed": False, "credential_validation_allowed": False},
            }
            for filename, summary in summaries.items():
                (reports / filename).write_text(__import__("json").dumps({"summary": summary}), encoding="utf-8")

            packet = bootstrap_ai_assets.build_manual_reviewer_execution_packet_report(tmp)

            self.assertEqual(packet["mode"], "manual-reviewer-execution-packet")
            self.assertEqual(packet["summary"]["status"], "ready-for-human-runbook")
            self.assertTrue(packet["summary"]["manual_review_required"])
            self.assertTrue(packet["summary"]["human_feedback_pending"])
            self.assertFalse(packet["summary"]["writes_anything"])
            self.assertEqual(packet["summary"]["writes"], 0)
            self.assertFalse(packet["summary"]["executes_anything"])
            self.assertFalse(packet["summary"]["remote_mutation_allowed"])
            self.assertFalse(packet["summary"]["credential_validation_allowed"])
            self.assertFalse(packet["summary"]["auto_approves_release"])
            self.assertEqual(packet["summary"]["remote_issues_created"], 0)
            step_ids = [step["id"] for step in packet["human_runbook_steps"]]
            self.assertEqual(step_ids[:4], [
                "read-one-page-packet",
                "copy-fill-feedback-file",
                "rerun-feedback-status",
                "generate-and-review-local-followups",
            ])
            for step in packet["human_runbook_steps"]:
                self.assertEqual(step["review_type"], "manual")
                self.assertFalse(step["executes_anything"])
                self.assertFalse(step["auto_approves_release"])
            command_text = "\n".join(packet["manual_command_sequence"])
            self.assertIn("--external-reviewer-feedback-status --both", command_text)
            self.assertIn("--human-action-closure-checklist --both", command_text)
            self.assertIn("bootstrap/reviewer-feedback/external-reviewer-feedback.md", " ".join(packet["human_owned_inputs"]))
            check_names = {check["name"] for check in packet["checks"]}
            self.assertIn("evidence:human-action-closure-checklist:ready", check_names)
            self.assertIn("docs:release-plan-documents-manual-reviewer-execution-packet", check_names)
            self.assertIn("roadmap:phase93-documented", check_names)
            self.assertIn("shell:manual-reviewer-execution-packet-command", check_names)

    def test_manual_reviewer_public_surface_freshness_tracks_runbook_pack_and_staging(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            docs = tmp / "docs"
            setup = tmp / "bootstrap" / "setup"
            reports = tmp / "bootstrap" / "reports"
            pack = tmp / "dist" / "portable-ai-assets-public-demo"
            staging = tmp / "dist" / "github-staging" / "portable-ai-assets"
            for directory in [docs, setup, reports, pack / "bootstrap" / "reports", staging / "bootstrap" / "reports"]:
                directory.mkdir(parents=True)
            release_plan_text = (
                "# Open-Source Release Plan\n"
                "Run --manual-reviewer-execution-packet --both and --manual-reviewer-public-surface-freshness --both.\n"
                "Phase 94 is a local-only/report-only freshness and coverage check for the human runbook across public pack and GitHub staging surfaces; it does not approve, publish, push, execute, call APIs/providers, validate credentials, or mutate issues/backlogs.\n"
            )
            roadmap_text = "# Public Roadmap\n\n### Phase 94 — Manual reviewer public surface freshness ✅\nChecks Phase 93 runbook coverage in public pack and staging without executing or publishing.\n"
            shell_text = "#!/usr/bin/env bash\n--manual-reviewer-execution-packet\n--manual-reviewer-public-surface-freshness\n"
            for base in [tmp, pack, staging]:
                (base / "docs").mkdir(parents=True, exist_ok=True)
                (base / "bootstrap" / "setup").mkdir(parents=True, exist_ok=True)
                (base / "docs" / "open-source-release-plan.md").write_text(release_plan_text, encoding="utf-8")
                (base / "docs" / "public-roadmap.md").write_text(roadmap_text, encoding="utf-8")
                (base / "bootstrap" / "setup" / "bootstrap-ai-assets.sh").write_text(shell_text, encoding="utf-8")
            manual_packet_summary = {
                "status": "ready-for-human-runbook",
                "manual_review_required": True,
                "human_feedback_pending": True,
                "followup_candidates_ready": False,
                "one_page_runbook_ready": True,
                "writes_anything": False,
                "executes_anything": False,
                "remote_mutation_allowed": False,
                "credential_validation_allowed": False,
                "auto_approves_release": False,
                "remote_issues_created": 0,
                "issue_backlog_mutation_allowed": False,
            }
            (reports / "latest-manual-reviewer-execution-packet.json").write_text(__import__("json").dumps({"summary": manual_packet_summary}), encoding="utf-8")
            (reports / "latest-public-release-pack.json").write_text(__import__("json").dumps({"pack_dir": str(pack), "summary": {"files_in_pack": 10}}), encoding="utf-8")
            (reports / "latest-public-repo-staging-status.json").write_text(__import__("json").dumps({"staging_dir": str(staging), "summary": {"status": "ready", "remote_configured": False, "forbidden_findings": 0}}), encoding="utf-8")
            for base in [pack, staging]:
                (base / "bootstrap" / "reports" / "latest-manual-reviewer-execution-packet.json").write_text(__import__("json").dumps({"summary": manual_packet_summary}), encoding="utf-8")
                (base / "bootstrap" / "reports" / "latest-manual-reviewer-execution-packet.md").write_text("# Manual Reviewer Execution Packet\n", encoding="utf-8")

            report = bootstrap_ai_assets.build_manual_reviewer_public_surface_freshness_report(tmp)

            self.assertEqual(report["mode"], "manual-reviewer-public-surface-freshness")
            self.assertEqual(report["summary"]["status"], "ready")
            self.assertTrue(report["summary"]["manual_review_required"])
            self.assertTrue(report["summary"]["human_feedback_pending"])
            self.assertFalse(report["summary"]["executes_anything"])
            self.assertFalse(report["summary"]["remote_mutation_allowed"])
            self.assertFalse(report["summary"]["credential_validation_allowed"])
            self.assertFalse(report["summary"]["auto_approves_release"])
            self.assertEqual(report["summary"]["remote_issues_created"], 0)
            self.assertFalse(report["summary"]["issue_backlog_mutation_allowed"])
            self.assertIn("manual-reviewer-execution-packet", report["required_reports"])
            self.assertIn("public-release-pack", report["required_reports"])
            self.assertIn("public-repo-staging-status", report["required_reports"])
            check_names = {check["name"] for check in report["checks"]}
            self.assertIn("source:manual-reviewer-execution-packet:ready", check_names)
            self.assertIn("public-pack:manual-reviewer-execution-packet-json", check_names)
            self.assertIn("public-pack:manual-reviewer-execution-packet-md", check_names)
            self.assertIn("public-pack:manual-reviewer-public-surface-freshness-command", check_names)
            self.assertIn("github-staging:manual-reviewer-execution-packet-json", check_names)
            self.assertIn("github-staging:manual-reviewer-execution-packet-md", check_names)
            self.assertIn("github-staging:manual-reviewer-public-surface-freshness-command", check_names)
            self.assertIn("docs:release-plan-documents-phase94", check_names)
            self.assertIn("roadmap:phase94-documented", check_names)
            self.assertIn("shell:manual-reviewer-public-surface-freshness-command", check_names)

    def test_manual_reviewer_handoff_readiness_summarizes_ready_surfaces_without_sharing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            reports = tmp / "bootstrap" / "reports"
            pack = tmp / "dist" / "portable-ai-assets-public-demo"
            staging = tmp / "dist" / "github-staging" / "portable-ai-assets"
            for directory in [reports, pack / "bootstrap" / "reports", staging / "bootstrap" / "reports", tmp / "docs", tmp / "bootstrap" / "setup", tmp / "bootstrap" / "reviewer-feedback"]:
                directory.mkdir(parents=True)
            release_plan_text = (
                "# Open-Source Release Plan\n"
                "Run --manual-reviewer-public-surface-freshness --both and --manual-reviewer-handoff-readiness --both.\n"
                "Phase 95 is a local-only/report-only handoff readiness digest for a human operator; it does not approve, share, invite, publish, push, execute, call APIs/providers, validate credentials, or mutate issues/backlogs.\n"
            )
            roadmap_text = "# Public Roadmap\n\n### Phase 95 — Manual reviewer handoff readiness ✅\nSummarizes the ready public reviewer surfaces for a human handoff without sharing, inviting, publishing, or approving.\n"
            shell_text = "#!/usr/bin/env bash\n--manual-reviewer-public-surface-freshness\n--manual-reviewer-handoff-readiness\n"
            (tmp / "docs" / "open-source-release-plan.md").write_text(release_plan_text, encoding="utf-8")
            (tmp / "docs" / "public-roadmap.md").write_text(roadmap_text, encoding="utf-8")
            (tmp / "bootstrap" / "setup" / "bootstrap-ai-assets.sh").write_text(shell_text, encoding="utf-8")
            (tmp / "bootstrap" / "reviewer-feedback" / "external-reviewer-feedback.md.template").write_text("# Feedback Template\n", encoding="utf-8")
            manual_summary = {
                "status": "ready-for-human-runbook",
                "manual_review_required": True,
                "human_feedback_pending": True,
                "followup_candidates_ready": False,
                "one_page_runbook_ready": True,
                "writes_anything": False,
                "executes_anything": False,
                "remote_mutation_allowed": False,
                "credential_validation_allowed": False,
                "auto_approves_release": False,
                "remote_issues_created": 0,
                "issue_backlog_mutation_allowed": False,
            }
            freshness_summary = {
                "status": "ready",
                "checks": 14,
                "pass": 14,
                "fail": 0,
                "manual_review_required": True,
                "human_feedback_pending": True,
                "writes_anything": False,
                "executes_anything": False,
                "remote_mutation_allowed": False,
                "credential_validation_allowed": False,
                "auto_approves_release": False,
                "remote_issues_created": 0,
                "issue_backlog_mutation_allowed": False,
                "remote_configured": False,
            }
            checklist_summary = {
                "status": "ready-for-human-action",
                "manual_review_required": True,
                "human_feedback_pending": True,
                "writes_anything": False,
                "executes_anything": False,
                "remote_mutation_allowed": False,
                "credential_validation_allowed": False,
                "auto_approves_release": False,
                "remote_issues_created": 0,
                "issue_backlog_mutation_allowed": False,
            }
            (reports / "latest-manual-reviewer-execution-packet.json").write_text(__import__("json").dumps({"summary": manual_summary}), encoding="utf-8")
            (reports / "latest-manual-reviewer-execution-packet.md").write_text("# Manual Reviewer Execution Packet\n", encoding="utf-8")
            (reports / "latest-manual-reviewer-public-surface-freshness.json").write_text(__import__("json").dumps({"summary": freshness_summary, "pack_dir": str(pack), "staging_dir": str(staging)}), encoding="utf-8")
            (reports / "latest-manual-reviewer-public-surface-freshness.md").write_text("# Manual Reviewer Public Surface Freshness\n", encoding="utf-8")
            (reports / "latest-human-action-closure-checklist.json").write_text(__import__("json").dumps({"summary": checklist_summary}), encoding="utf-8")
            (pack / "PACK-INDEX.md").write_text("# Pack Index\n", encoding="utf-8")
            (staging / "GITHUB-PUBLISH-CHECKLIST.md").write_text("# Checklist\n", encoding="utf-8")

            report = bootstrap_ai_assets.build_manual_reviewer_handoff_readiness_report(tmp)

            self.assertEqual(report["mode"], "manual-reviewer-handoff-readiness")
            self.assertEqual(report["summary"]["status"], "ready-for-human-handoff")
            self.assertTrue(report["summary"]["manual_review_required"])
            self.assertTrue(report["summary"]["human_feedback_pending"])
            self.assertFalse(report["summary"]["shares_anything"])
            self.assertFalse(report["summary"]["sends_invitations"])
            self.assertFalse(report["summary"]["executes_anything"])
            self.assertFalse(report["summary"]["remote_mutation_allowed"])
            self.assertFalse(report["summary"]["credential_validation_allowed"])
            self.assertFalse(report["summary"]["auto_approves_release"])
            self.assertEqual(report["summary"]["remote_issues_created"], 0)
            self.assertFalse(report["summary"]["issue_backlog_mutation_allowed"])
            self.assertIn("manual-reviewer-public-surface-freshness", report["required_reports"])
            self.assertIn("manual-reviewer-execution-packet", report["required_reports"])
            self.assertIn("human-action-closure-checklist", report["required_reports"])
            artifact_names = {artifact["name"] for artifact in report["handoff_artifacts"]}
            self.assertIn("public-release-pack", artifact_names)
            self.assertIn("github-staging", artifact_names)
            self.assertIn("manual-reviewer-execution-packet", artifact_names)
            self.assertIn("feedback-template", artifact_names)
            check_names = {check["name"] for check in report["checks"]}
            self.assertIn("source:manual-reviewer-public-surface-freshness:ready", check_names)
            self.assertIn("source:manual-reviewer-execution-packet:ready", check_names)
            self.assertIn("source:human-action-closure-checklist:ready", check_names)
            self.assertIn("artifact:public-release-pack", check_names)
            self.assertIn("artifact:github-staging", check_names)
            self.assertIn("artifact:feedback-template", check_names)
            self.assertIn("docs:release-plan-documents-phase95", check_names)
            self.assertIn("roadmap:phase95-documented", check_names)
            self.assertIn("shell:manual-reviewer-handoff-readiness-command", check_names)

    def test_manual_reviewer_handoff_packet_index_crosslinks_human_actions_without_mutation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            reports = tmp / "bootstrap" / "reports"
            pack = tmp / "dist" / "portable-ai-assets-public-demo"
            staging = tmp / "dist" / "github-staging" / "portable-ai-assets"
            for directory in [reports, pack, staging, tmp / "docs", tmp / "bootstrap" / "setup", tmp / "bootstrap" / "reviewer-feedback"]:
                directory.mkdir(parents=True)
            (tmp / "docs" / "open-source-release-plan.md").write_text(
                "# Open-Source Release Plan\n"
                "Run --manual-reviewer-handoff-readiness --both and --manual-reviewer-handoff-packet-index --both.\n"
                "Phase 96 creates a local-only/report-only human handoff packet index/status that cross-links exact human-only next actions and drift checks without sharing, inviting, approving, publishing, executing, calling APIs/providers, validating credentials, or mutating issues/backlogs.\n",
                encoding="utf-8",
            )
            (tmp / "docs" / "public-roadmap.md").write_text(
                "# Public Roadmap\n\n"
                "### Phase 96 — Manual reviewer handoff packet index ✅\n"
                "Cross-links the handoff readiness digest, public pack, staging tree, reviewer runbook, feedback template, and exact human-only next actions without sharing, inviting, publishing, or approving.\n",
                encoding="utf-8",
            )
            (tmp / "bootstrap" / "setup" / "bootstrap-ai-assets.sh").write_text("#!/usr/bin/env bash\n--manual-reviewer-handoff-readiness\n--manual-reviewer-handoff-packet-index\n", encoding="utf-8")
            (tmp / "bootstrap" / "reviewer-feedback" / "external-reviewer-feedback.md.template").write_text("# Feedback Template\n", encoding="utf-8")
            handoff_summary = {
                "status": "ready-for-human-handoff",
                "checks": 11,
                "pass": 11,
                "fail": 0,
                "manual_review_required": True,
                "human_feedback_pending": True,
                "shares_anything": False,
                "sends_invitations": False,
                "writes_anything": False,
                "writes": 0,
                "executes_anything": False,
                "remote_mutation_allowed": False,
                "credential_validation_allowed": False,
                "auto_approves_release": False,
                "remote_issues_created": 0,
                "issue_backlog_mutation_allowed": False,
                "remote_configured": False,
            }
            artifacts = [
                {"name": "public-release-pack", "path": str(pack), "ready": True},
                {"name": "github-staging", "path": str(staging), "ready": True},
                {"name": "manual-reviewer-execution-packet", "path": str(reports / "latest-manual-reviewer-execution-packet.md"), "ready": True},
                {"name": "public-surface-freshness-report", "path": str(reports / "latest-manual-reviewer-public-surface-freshness.md"), "ready": True},
                {"name": "feedback-template", "path": str(tmp / "bootstrap" / "reviewer-feedback" / "external-reviewer-feedback.md.template"), "ready": True},
            ]
            (reports / "latest-manual-reviewer-handoff-readiness.json").write_text(__import__("json").dumps({"summary": handoff_summary, "handoff_artifacts": artifacts, "manual_handoff_sequence": ["Human decides whether to share.", "Human copies/fills feedback only after review."], "review_boundary": ["Does not share artifacts or send invitations."]}), encoding="utf-8")
            (reports / "latest-manual-reviewer-handoff-readiness.md").write_text("# Handoff Readiness\n", encoding="utf-8")
            (reports / "latest-manual-reviewer-execution-packet.md").write_text("# Execution Packet\n", encoding="utf-8")
            (reports / "latest-manual-reviewer-public-surface-freshness.md").write_text("# Freshness\n", encoding="utf-8")
            (staging / "bootstrap" / "reports").mkdir(parents=True)
            (staging / "bootstrap" / "reports" / "latest-agent-complete-phase102-rollup-evidence-failclosed-review.md").write_text("# Phase103 Diagnostics\n", encoding="utf-8")
            (staging / "bootstrap" / "reports" / "latest-completed-work-review.md").write_text("# Completed Work Diagnostics\n", encoding="utf-8")
            (pack / "PACK-INDEX.md").write_text("# Pack Index\n", encoding="utf-8")
            (staging / "GITHUB-PUBLISH-CHECKLIST.md").write_text("# Checklist\n", encoding="utf-8")

            report = bootstrap_ai_assets.build_manual_reviewer_handoff_packet_index_report(tmp)

            self.assertEqual(report["mode"], "manual-reviewer-handoff-packet-index")
            self.assertEqual(report["summary"]["status"], "ready-for-human-handoff-packet")
            self.assertTrue(report["summary"]["manual_review_required"])
            self.assertTrue(report["summary"]["human_feedback_pending"])
            self.assertFalse(report["summary"]["shares_anything"])
            self.assertFalse(report["summary"]["sends_invitations"])
            self.assertFalse(report["summary"]["executes_anything"])
            self.assertFalse(report["summary"]["remote_mutation_allowed"])
            self.assertFalse(report["summary"]["credential_validation_allowed"])
            self.assertFalse(report["summary"]["auto_approves_release"])
            self.assertEqual(report["summary"]["remote_issues_created"], 0)
            self.assertFalse(report["summary"]["issue_backlog_mutation_allowed"])
            self.assertIn("manual-reviewer-handoff-readiness", report["required_reports"])
            index_names = {item["name"] for item in report["packet_index"]}
            self.assertIn("handoff-readiness-digest", index_names)
            self.assertIn("public-release-pack", index_names)
            self.assertIn("github-staging", index_names)
            self.assertIn("phase102-rollup-diagnostics", index_names)
            self.assertIn("completed-work-diagnostics", index_names)
            self.assertIn("feedback-template", index_names)
            action_ids = {item["id"] for item in report["human_only_next_actions"]}
            self.assertIn("human-share-decision", action_ids)
            self.assertIn("human-reviewer-invitation", action_ids)
            self.assertIn("human-feedback-capture", action_ids)
            self.assertTrue(all(item["automation_allowed"] is False for item in report["human_only_next_actions"]))
            drift_check_names = {check["name"] for check in report["drift_checks"]}
            self.assertIn("source:manual-reviewer-handoff-readiness:ready", drift_check_names)
            self.assertIn("docs:release-plan-documents-phase96", drift_check_names)
            self.assertIn("roadmap:phase96-documented", drift_check_names)
            self.assertIn("shell:manual-reviewer-handoff-packet-index-command", drift_check_names)
            self.assertEqual(report["summary"]["fail"], 0)

    def test_manual_reviewer_handoff_freeze_check_confirms_packet_without_mutation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            reports = tmp / "bootstrap" / "reports"
            pack = tmp / "dist" / "portable-ai-assets-public-demo"
            staging = tmp / "dist" / "github-staging" / "portable-ai-assets"
            for directory in [reports, pack, staging, tmp / "docs", tmp / "bootstrap" / "setup", tmp / "bootstrap" / "reviewer-feedback"]:
                directory.mkdir(parents=True)
            (tmp / "docs" / "open-source-release-plan.md").write_text(
                "# Open-Source Release Plan\n"
                "Run --manual-reviewer-handoff-packet-index --both and --manual-reviewer-handoff-freeze-check --both.\n"
                "Phase 97 creates a local-only/report-only handoff freeze check that verifies packet freshness, packet index readiness, and human-only next actions without sharing, inviting, approving, publishing, executing, calling APIs/providers, validating credentials, creating feedback, or mutating issues/backlogs.\n",
                encoding="utf-8",
            )
            (tmp / "docs" / "public-roadmap.md").write_text(
                "# Public Roadmap\n\n"
                "### Phase 97 — Manual reviewer handoff freeze check ✅\n"
                "Verifies the handoff packet index, local artifact pointers, and human-only next actions are frozen and navigable without sharing, inviting, publishing, approving, or creating feedback.\n",
                encoding="utf-8",
            )
            (tmp / "bootstrap" / "setup" / "bootstrap-ai-assets.sh").write_text("#!/usr/bin/env bash\n--manual-reviewer-handoff-packet-index\n--manual-reviewer-handoff-freeze-check\n", encoding="utf-8")
            (tmp / "bootstrap" / "reviewer-feedback" / "external-reviewer-feedback.md.template").write_text("# Feedback Template\n", encoding="utf-8")
            handoff_summary = {
                "status": "ready-for-human-handoff-packet",
                "checks": 11,
                "pass": 11,
                "fail": 0,
                "manual_review_required": True,
                "human_feedback_pending": True,
                "shares_anything": False,
                "sends_invitations": False,
                "writes_anything": False,
                "writes": 0,
                "executes_anything": False,
                "remote_mutation_allowed": False,
                "credential_validation_allowed": False,
                "auto_approves_release": False,
                "remote_issues_created": 0,
                "issue_backlog_mutation_allowed": False,
                "remote_configured": False,
            }
            phase102_diagnostics = staging / "bootstrap" / "reports" / "latest-agent-complete-phase102-rollup-evidence-failclosed-review.md"
            completed_work_diagnostics = staging / "bootstrap" / "reports" / "latest-completed-work-review.md"
            packet_index = [
                {"name": "handoff-readiness-digest", "path": str(reports / "latest-manual-reviewer-handoff-readiness.md"), "ready": True, "review_role": "operator"},
                {"name": "public-release-pack", "path": str(pack), "ready": True, "review_role": "operator/reviewer"},
                {"name": "github-staging", "path": str(staging), "ready": True, "review_role": "operator/reviewer"},
                {"name": "phase102-rollup-diagnostics", "path": str(phase102_diagnostics), "ready": True, "review_role": "operator/reviewer"},
                {"name": "completed-work-diagnostics", "path": str(completed_work_diagnostics), "ready": True, "review_role": "operator/reviewer"},
                {"name": "manual-reviewer-execution-packet", "path": str(reports / "latest-manual-reviewer-execution-packet.md"), "ready": True, "review_role": "operator"},
                {"name": "public-surface-freshness-report", "path": str(reports / "latest-manual-reviewer-public-surface-freshness.md"), "ready": True, "review_role": "operator"},
                {"name": "feedback-template", "path": str(tmp / "bootstrap" / "reviewer-feedback" / "external-reviewer-feedback.md.template"), "ready": True, "review_role": "reviewer"},
            ]
            human_actions = [
                {"id": "human-share-decision", "automation_allowed": False, "requires_human": True},
                {"id": "human-reviewer-invitation", "automation_allowed": False, "requires_human": True},
                {"id": "human-feedback-capture", "automation_allowed": False, "requires_human": True},
                {"id": "human-followup-review", "automation_allowed": False, "requires_human": True},
                {"id": "human-release-go-no-go", "automation_allowed": False, "requires_human": True},
            ]
            (reports / "latest-manual-reviewer-handoff-packet-index.json").write_text(__import__("json").dumps({"summary": handoff_summary, "packet_index": packet_index, "human_only_next_actions": human_actions}), encoding="utf-8")
            (reports / "latest-manual-reviewer-handoff-packet-index.md").write_text("# Handoff Packet Index\n", encoding="utf-8")
            for item in packet_index:
                path = Path(item["path"])
                if path.suffix:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(f"# {item['name']}\n", encoding="utf-8")
                else:
                    path.mkdir(parents=True, exist_ok=True)
            phase102_diagnostics.write_text(
                "# Phase103 Diagnostics\nphase102_report_invalid_fields\ninvalid_fields=agent_side_complete,remote_issues_created,warn\n",
                encoding="utf-8",
            )
            completed_work_diagnostics.write_text(
                "# Completed Work Diagnostics\ninvalid_fields=agent_side_complete,remote_issues_created,warn\n",
                encoding="utf-8",
            )
            (pack / "PACK-INDEX.md").write_text("# Pack Index\n", encoding="utf-8")
            (staging / "GITHUB-PUBLISH-CHECKLIST.md").write_text("# Checklist\n", encoding="utf-8")

            report = bootstrap_ai_assets.build_manual_reviewer_handoff_freeze_check_report(tmp)

            self.assertEqual(report["mode"], "manual-reviewer-handoff-freeze-check")
            self.assertEqual(report["summary"]["status"], "frozen-for-human-handoff")
            self.assertTrue(report["summary"]["manual_review_required"])
            self.assertTrue(report["summary"]["human_feedback_pending"])
            self.assertFalse(report["summary"]["shares_anything"])
            self.assertFalse(report["summary"]["sends_invitations"])
            self.assertFalse(report["summary"]["writes_anything"])
            self.assertEqual(report["summary"]["writes"], 0)
            self.assertFalse(report["summary"]["executes_anything"])
            self.assertFalse(report["summary"]["remote_mutation_allowed"])
            self.assertFalse(report["summary"]["credential_validation_allowed"])
            self.assertFalse(report["summary"]["auto_approves_release"])
            self.assertEqual(report["summary"]["remote_issues_created"], 0)
            self.assertFalse(report["summary"]["issue_backlog_mutation_allowed"])
            self.assertIn("manual-reviewer-handoff-packet-index", report["required_reports"])
            check_names = {check["name"] for check in report["freeze_checks"]}
            self.assertIn("source:manual-reviewer-handoff-packet-index:frozen", check_names)
            self.assertIn("packet:all-indexed-artifacts-present", check_names)
            self.assertIn("diagnostics:phase102-rollup-content-frozen", check_names)
            self.assertIn("diagnostics:completed-work-content-frozen", check_names)
            self.assertIn("diagnostics:all-required-diagnostics-frozen", check_names)
            self.assertIn("actions:human-only-freeze", check_names)
            self.assertIn("docs:release-plan-documents-phase97", check_names)
            self.assertIn("roadmap:phase97-documented", check_names)
            self.assertIn("shell:manual-reviewer-handoff-freeze-check-command", check_names)
            self.assertEqual(report["summary"]["fail"], 0)
            self.assertTrue(all(entry["present"] for entry in report["frozen_packet_entries"]))
            diagnostics_by_name = {entry["name"]: entry for entry in report["diagnostic_freeze_entries"]}
            self.assertEqual(
                diagnostics_by_name["phase102-rollup-diagnostics"]["expected_path"],
                str(phase102_diagnostics.resolve()),
            )
            self.assertEqual(
                diagnostics_by_name["completed-work-diagnostics"]["expected_path"],
                str(completed_work_diagnostics.resolve()),
            )
            self.assertTrue(all(entry["content_tokens_present"] for entry in diagnostics_by_name.values()))

    def test_manual_reviewer_handoff_freeze_check_blocks_duplicate_diagnostic_entries(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            reports = tmp / "bootstrap" / "reports"
            staging = tmp / "dist" / "github-staging" / "portable-ai-assets"
            pack = tmp / "dist" / "portable-ai-assets-public-demo"
            for directory in [reports, staging, pack, tmp / "docs", tmp / "bootstrap" / "setup", tmp / "bootstrap" / "reviewer-feedback"]:
                directory.mkdir(parents=True)
            (tmp / "docs" / "open-source-release-plan.md").write_text(
                "# Open-Source Release Plan\n"
                "Run --manual-reviewer-handoff-packet-index --both and --manual-reviewer-handoff-freeze-check --both.\n"
                "Phase 97 creates a local-only/report-only handoff freeze check that verifies packet freshness, packet index readiness, and human-only next actions without sharing, inviting, approving, publishing, executing, calling APIs/providers, validating credentials, creating feedback, or mutating issues/backlogs.\n",
                encoding="utf-8",
            )
            (tmp / "docs" / "public-roadmap.md").write_text(
                "# Public Roadmap\n\n"
                "### Phase 97 — Manual reviewer handoff freeze check ✅\n"
                "Verifies the handoff packet index, local artifact pointers, and human-only next actions are frozen and navigable without sharing, inviting, publishing, approving, or creating feedback.\n",
                encoding="utf-8",
            )
            (tmp / "bootstrap" / "setup" / "bootstrap-ai-assets.sh").write_text("#!/usr/bin/env bash\n--manual-reviewer-handoff-freeze-check\n", encoding="utf-8")
            phase102_diagnostics = staging / "bootstrap" / "reports" / "latest-agent-complete-phase102-rollup-evidence-failclosed-review.md"
            completed_work_diagnostics = staging / "bootstrap" / "reports" / "latest-completed-work-review.md"
            packet_index = [
                {"name": "handoff-readiness-digest", "path": str(reports / "latest-manual-reviewer-handoff-readiness.md"), "ready": True, "review_role": "operator"},
                {"name": "public-release-pack", "path": str(pack), "ready": True, "review_role": "operator/reviewer"},
                {"name": "github-staging", "path": str(staging), "ready": True, "review_role": "operator/reviewer"},
                {"name": "phase102-rollup-diagnostics", "path": str(phase102_diagnostics), "ready": True, "review_role": "operator/reviewer"},
                {"name": "phase102-rollup-diagnostics", "path": str(phase102_diagnostics), "ready": True, "review_role": "operator/reviewer"},
                {"name": "completed-work-diagnostics", "path": str(completed_work_diagnostics), "ready": True, "review_role": "operator/reviewer"},
            ]
            human_actions = [
                {"id": "human-share-decision", "automation_allowed": False, "requires_human": True},
                {"id": "human-reviewer-invitation", "automation_allowed": False, "requires_human": True},
                {"id": "human-feedback-capture", "automation_allowed": False, "requires_human": True},
                {"id": "human-followup-review", "automation_allowed": False, "requires_human": True},
                {"id": "human-release-go-no-go", "automation_allowed": False, "requires_human": True},
            ]
            summary = {
                "status": "ready-for-human-handoff-packet",
                "fail": 0,
                "human_feedback_pending": True,
                "shares_anything": False,
                "sends_invitations": False,
                "writes_anything": False,
                "writes": 0,
                "executes_anything": False,
                "remote_mutation_allowed": False,
                "credential_validation_allowed": False,
                "auto_approves_release": False,
                "remote_issues_created": 0,
                "issue_backlog_mutation_allowed": False,
            }
            (reports / "latest-manual-reviewer-handoff-packet-index.json").write_text(__import__("json").dumps({"summary": summary, "packet_index": packet_index, "human_only_next_actions": human_actions}), encoding="utf-8")
            (reports / "latest-manual-reviewer-handoff-packet-index.md").write_text("# Handoff Packet Index\n", encoding="utf-8")
            (reports / "latest-manual-reviewer-handoff-readiness.md").write_text("# Readiness\n", encoding="utf-8")
            pack.mkdir(parents=True, exist_ok=True)
            staging.mkdir(parents=True, exist_ok=True)
            phase102_diagnostics.parent.mkdir(parents=True, exist_ok=True)
            phase102_diagnostics.write_text("phase102_report_invalid_fields\ninvalid_fields=none\n", encoding="utf-8")
            completed_work_diagnostics.write_text("invalid_fields=none\n", encoding="utf-8")

            report = bootstrap_ai_assets.build_manual_reviewer_handoff_freeze_check_report(tmp)

            self.assertEqual(report["summary"]["status"], "blocked")
            check_names = {check["name"] for check in report["freeze_checks"]}
            self.assertIn("diagnostics:no-duplicate-diagnostic-entries", check_names)
            duplicate_check = [check for check in report["freeze_checks"] if check["name"] == "diagnostics:no-duplicate-diagnostic-entries"][0]
            self.assertEqual(duplicate_check["status"], "fail")
            self.assertIn("phase102-rollup-diagnostics", report["duplicate_diagnostic_entries"])

    def test_manual_reviewer_handoff_freeze_check_reports_structured_diagnostic_failures(self):
        cases = [
            ("missing-token", "phase102", True, "phase102_report_invalid_fields\n", "invalid_fields=none\n", "missing_tokens"),
            ("wrong-path", "completed", True, "phase102_report_invalid_fields\ninvalid_fields=none\n", "invalid_fields=none\n", "path_mismatch"),
            ("not-ready", "phase102", False, "phase102_report_invalid_fields\ninvalid_fields=none\n", "invalid_fields=none\n", "not_ready"),
        ]
        for label, broken_entry, ready, phase102_text, completed_text, expected_reason in cases:
            with self.subTest(label=label):
                with tempfile.TemporaryDirectory() as tmpdir:
                    tmp = Path(tmpdir)
                    reports = tmp / "bootstrap" / "reports"
                    staging = tmp / "dist" / "github-staging" / "portable-ai-assets"
                    pack = tmp / "dist" / "portable-ai-assets-public-demo"
                    wrong_completed = tmp / "dist" / "github-staging" / "portable-ai-assets" / "bootstrap" / "reports" / "wrong-completed-work-review.md"
                    for directory in [reports, staging, pack, tmp / "docs", tmp / "bootstrap" / "setup"]:
                        directory.mkdir(parents=True)
                    (tmp / "docs" / "open-source-release-plan.md").write_text(
                        "# Open-Source Release Plan\nRun --manual-reviewer-handoff-freeze-check --both.\nlocal-only/report-only handoff freeze check without sharing, inviting, approving, publishing, executing, calling APIs/providers, validating credentials, creating feedback, or mutating issues/backlogs\n",
                        encoding="utf-8",
                    )
                    (tmp / "docs" / "public-roadmap.md").write_text("# Public Roadmap\n\n### Phase 97 — Manual reviewer handoff freeze check ✅\nVerifies the handoff packet index, local artifact pointers, and human-only next actions are frozen and navigable without sharing, inviting, publishing, approving, or creating feedback.\n", encoding="utf-8")
                    (tmp / "bootstrap" / "setup" / "bootstrap-ai-assets.sh").write_text("--manual-reviewer-handoff-freeze-check\n", encoding="utf-8")
                    phase102_diagnostics = staging / "bootstrap" / "reports" / "latest-agent-complete-phase102-rollup-evidence-failclosed-review.md"
                    completed_work_diagnostics = staging / "bootstrap" / "reports" / "latest-completed-work-review.md"
                    completed_path = wrong_completed if broken_entry == "completed" and expected_reason == "path_mismatch" else completed_work_diagnostics
                    packet_index = [
                        {"name": "handoff-readiness-digest", "path": str(reports / "latest-manual-reviewer-handoff-readiness.md"), "ready": True, "review_role": "operator"},
                        {"name": "public-release-pack", "path": str(pack), "ready": True, "review_role": "operator/reviewer"},
                        {"name": "github-staging", "path": str(staging), "ready": True, "review_role": "operator/reviewer"},
                        {"name": "phase102-rollup-diagnostics", "path": str(phase102_diagnostics), "ready": ready if broken_entry == "phase102" else True, "review_role": "operator/reviewer"},
                        {"name": "completed-work-diagnostics", "path": str(completed_path), "ready": ready if broken_entry == "completed" else True, "review_role": "operator/reviewer"},
                    ]
                    human_actions = [
                        {"id": "human-share-decision", "automation_allowed": False, "requires_human": True},
                        {"id": "human-reviewer-invitation", "automation_allowed": False, "requires_human": True},
                        {"id": "human-feedback-capture", "automation_allowed": False, "requires_human": True},
                        {"id": "human-followup-review", "automation_allowed": False, "requires_human": True},
                        {"id": "human-release-go-no-go", "automation_allowed": False, "requires_human": True},
                    ]
                    summary = {"status": "ready-for-human-handoff-packet", "fail": 0, "human_feedback_pending": True, "shares_anything": False, "sends_invitations": False, "writes_anything": False, "writes": 0, "executes_anything": False, "remote_mutation_allowed": False, "credential_validation_allowed": False, "auto_approves_release": False, "remote_issues_created": 0, "issue_backlog_mutation_allowed": False}
                    (reports / "latest-manual-reviewer-handoff-packet-index.json").write_text(__import__("json").dumps({"summary": summary, "packet_index": packet_index, "human_only_next_actions": human_actions}), encoding="utf-8")
                    (reports / "latest-manual-reviewer-handoff-packet-index.md").write_text("# Handoff Packet Index\n", encoding="utf-8")
                    (reports / "latest-manual-reviewer-handoff-readiness.md").write_text("# Readiness\n", encoding="utf-8")
                    pack.mkdir(parents=True, exist_ok=True)
                    phase102_diagnostics.parent.mkdir(parents=True, exist_ok=True)
                    phase102_diagnostics.write_text(phase102_text, encoding="utf-8")
                    completed_work_diagnostics.write_text(completed_text, encoding="utf-8")
                    if completed_path != completed_work_diagnostics:
                        completed_path.write_text(completed_text, encoding="utf-8")

                    report = bootstrap_ai_assets.build_manual_reviewer_handoff_freeze_check_report(tmp)

                    self.assertEqual(report["summary"]["status"], "blocked")
                    failures = report["diagnostic_freeze_failures"]
                    self.assertTrue(any(failure["reason"] == expected_reason for failure in failures), failures)

    def test_agent_owner_delegation_review_records_agent_review_without_external_side_effects(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            reports = tmp / "bootstrap" / "reports"
            for directory in [reports, tmp / "docs", tmp / "bootstrap" / "setup", tmp / "bootstrap" / "reviewer-feedback"]:
                directory.mkdir(parents=True)
            (tmp / "docs" / "open-source-release-plan.md").write_text(
                "# Open-Source Release Plan\n"
                "Run --manual-reviewer-handoff-freeze-check --both and --agent-owner-delegation-review --both.\n"
                "Phase 98 creates a local-only/report-only agent-side owner delegation review that records engineering/code review, testing, safety checks, and product-material self-review are delegated to the agent without sharing, inviting, approving, publishing, executing external commands, calling APIs/providers, validating credentials, creating external feedback, or mutating issues/backlogs.\n",
                encoding="utf-8",
            )
            (tmp / "docs" / "public-roadmap.md").write_text(
                "# Public Roadmap\n\n"
                "### Phase 98 — Agent owner delegation review ✅\n"
                "Records that engineering/code review and verification are delegated to the agent while real external sharing, reviewer invitation, publication, feedback authorship, and final go/no-go remain explicit owner-side external decisions.\n",
                encoding="utf-8",
            )
            (tmp / "bootstrap" / "setup" / "bootstrap-ai-assets.sh").write_text("#!/usr/bin/env bash\n--manual-reviewer-handoff-freeze-check\n--agent-owner-delegation-review\n", encoding="utf-8")
            freeze_summary = {
                "status": "frozen-for-human-handoff",
                "checks": 6,
                "pass": 6,
                "fail": 0,
                "manual_review_required": True,
                "human_feedback_pending": True,
                "shares_anything": False,
                "sends_invitations": False,
                "writes_anything": False,
                "writes": 0,
                "executes_anything": False,
                "remote_mutation_allowed": False,
                "credential_validation_allowed": False,
                "auto_approves_release": False,
                "remote_issues_created": 0,
                "issue_backlog_mutation_allowed": False,
                "remote_configured": False,
            }
            (reports / "latest-manual-reviewer-handoff-freeze-check.json").write_text(__import__("json").dumps({"summary": freeze_summary}), encoding="utf-8")
            (reports / "latest-manual-reviewer-handoff-freeze-check.md").write_text("# Freeze\n", encoding="utf-8")

            report = bootstrap_ai_assets.build_agent_owner_delegation_review_report(tmp)

            self.assertEqual(report["mode"], "agent-owner-delegation-review")
            self.assertEqual(report["summary"]["status"], "agent-review-delegated")
            self.assertTrue(report["summary"]["agent_engineering_review_delegated"])
            self.assertTrue(report["summary"]["agent_code_review_delegated"])
            self.assertTrue(report["summary"]["agent_verification_delegated"])
            self.assertTrue(report["summary"]["agent_product_material_review_delegated"])
            self.assertTrue(report["summary"]["human_feedback_pending"])
            self.assertTrue(report["summary"]["external_owner_decision_required"])
            self.assertFalse(report["summary"]["requires_user_code_review"])
            self.assertFalse(report["summary"]["shares_anything"])
            self.assertFalse(report["summary"]["sends_invitations"])
            self.assertFalse(report["summary"]["writes_anything"])
            self.assertEqual(report["summary"]["writes"], 0)
            self.assertFalse(report["summary"]["executes_anything"])
            self.assertFalse(report["summary"]["remote_mutation_allowed"])
            self.assertFalse(report["summary"]["credential_validation_allowed"])
            self.assertFalse(report["summary"]["auto_approves_release"])
            self.assertEqual(report["summary"]["remote_issues_created"], 0)
            self.assertFalse(report["summary"]["issue_backlog_mutation_allowed"])
            self.assertIn("manual-reviewer-handoff-freeze-check", report["required_reports"])
            delegated = {item["area"] for item in report["delegated_agent_responsibilities"]}
            self.assertIn("engineering-review", delegated)
            self.assertIn("code-review", delegated)
            self.assertIn("verification", delegated)
            self.assertIn("product-material-review", delegated)
            reserved = {item["area"] for item in report["reserved_owner_external_decisions"]}
            self.assertIn("real-sharing", reserved)
            self.assertIn("reviewer-invitation", reserved)
            self.assertIn("publication", reserved)
            self.assertIn("external-feedback-authorship", reserved)
            self.assertIn("final-go-no-go", reserved)
            check_names = {check["name"] for check in report["delegation_checks"]}
            self.assertIn("source:manual-reviewer-handoff-freeze-check:frozen", check_names)
            self.assertIn("delegation:agent-internal-review-owned", check_names)
            self.assertIn("boundary:external-owner-decisions-reserved", check_names)
            self.assertIn("docs:release-plan-documents-phase98", check_names)
            self.assertIn("roadmap:phase98-documented", check_names)
            self.assertIn("shell:agent-owner-delegation-review-command", check_names)
            self.assertEqual(report["summary"]["fail"], 0)

    def test_agent_complete_external_actions_reserved_rollup_summarizes_final_machine_state(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            reports = tmp / "bootstrap" / "reports"
            for directory in [reports, tmp / "docs", tmp / "bootstrap" / "setup"]:
                directory.mkdir(parents=True)
            (tmp / "docs" / "open-source-release-plan.md").write_text(
                "# Open-Source Release Plan\n"
                "Run --agent-owner-delegation-review --both and --agent-complete-external-actions-reserved --both.\n"
                "Phase 99 creates a local-only/report-only agent-complete external-actions-reserved final rollup that records machine-side and agent-side work is complete while real sharing, reviewer invitation, publication, external feedback authorship, and final go/no-go remain explicit external owner decisions without sharing, inviting, approving, publishing, executing external commands, calling APIs/providers, validating credentials, creating external feedback, or mutating issues/backlogs.\n",
                encoding="utf-8",
            )
            (tmp / "docs" / "public-roadmap.md").write_text(
                "# Public Roadmap\n\n"
                "### Phase 99 — Agent-complete external-actions-reserved rollup ✅\n"
                "Summarizes the final machine-side state as agent-complete while reserving real sharing, reviewer invitation, publication, external feedback authorship, and final go/no-go for explicit external owner decisions.\n",
                encoding="utf-8",
            )
            (tmp / "bootstrap" / "setup" / "bootstrap-ai-assets.sh").write_text("#!/usr/bin/env bash\n--agent-owner-delegation-review\n--agent-complete-external-actions-reserved\n", encoding="utf-8")
            delegation_summary = {
                "status": "agent-review-delegated",
                "checks": 6,
                "pass": 6,
                "fail": 0,
                "agent_engineering_review_delegated": True,
                "agent_code_review_delegated": True,
                "agent_verification_delegated": True,
                "agent_product_material_review_delegated": True,
                "requires_user_code_review": False,
                "external_owner_decision_required": True,
                "manual_review_required": True,
                "human_feedback_pending": True,
                "shares_anything": False,
                "sends_invitations": False,
                "writes_anything": False,
                "writes": 0,
                "executes_anything": False,
                "remote_mutation_allowed": False,
                "credential_validation_allowed": False,
                "auto_approves_release": False,
                "remote_issues_created": 0,
                "issue_backlog_mutation_allowed": False,
                "remote_configured": False,
            }
            (reports / "latest-agent-owner-delegation-review.json").write_text(__import__("json").dumps({"summary": delegation_summary}), encoding="utf-8")
            (reports / "latest-agent-owner-delegation-review.md").write_text("# Delegation\n", encoding="utf-8")

            report = bootstrap_ai_assets.build_agent_complete_external_actions_reserved_report(tmp)

            self.assertEqual(report["mode"], "agent-complete-external-actions-reserved")
            self.assertEqual(report["summary"]["status"], "agent-complete-external-actions-reserved")
            self.assertTrue(report["summary"]["agent_side_complete"])
            self.assertTrue(report["summary"]["machine_side_complete"])
            self.assertTrue(report["summary"]["external_owner_decision_required"])
            self.assertTrue(report["summary"]["human_feedback_pending"])
            self.assertFalse(report["summary"]["requires_user_code_review"])
            self.assertFalse(report["summary"]["shares_anything"])
            self.assertFalse(report["summary"]["sends_invitations"])
            self.assertFalse(report["summary"]["writes_anything"])
            self.assertEqual(report["summary"]["writes"], 0)
            self.assertFalse(report["summary"]["executes_anything"])
            self.assertFalse(report["summary"]["remote_mutation_allowed"])
            self.assertFalse(report["summary"]["credential_validation_allowed"])
            self.assertFalse(report["summary"]["auto_approves_release"])
            self.assertEqual(report["summary"]["remote_issues_created"], 0)
            self.assertFalse(report["summary"]["issue_backlog_mutation_allowed"])
            self.assertIn("agent-owner-delegation-review", report["required_reports"])
            check_names = {check["name"] for check in report["rollup_checks"]}
            self.assertIn("source:agent-owner-delegation-review:delegated", check_names)
            self.assertIn("completion:agent-side-complete", check_names)
            self.assertIn("boundary:external-actions-reserved", check_names)
            self.assertIn("docs:release-plan-documents-phase99", check_names)
            self.assertIn("roadmap:phase99-documented", check_names)
            self.assertIn("shell:agent-complete-external-actions-reserved-command", check_names)
            reserved = {item["area"] for item in report["reserved_external_actions"]}
            self.assertIn("real-sharing", reserved)
            self.assertIn("reviewer-invitation", reserved)
            self.assertIn("publication", reserved)
            self.assertIn("external-feedback-authorship", reserved)
            self.assertIn("final-go-no-go", reserved)
            self.assertEqual(report["summary"]["fail"], 0)

    def test_agent_complete_rollup_blocks_completion_booleans_when_delegation_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            (tmp / "bootstrap" / "reports").mkdir(parents=True)
            report = bootstrap_ai_assets.build_agent_complete_external_actions_reserved_report(tmp)
            self.assertEqual(report["mode"], "agent-complete-external-actions-reserved")
            self.assertEqual(report["summary"]["status"], "blocked")
            self.assertGreater(report["summary"]["fail"], 0)
            self.assertFalse(report["summary"]["agent_side_complete"])
            self.assertFalse(report["summary"]["machine_side_complete"])
            self.assertTrue(report["summary"]["external_owner_decision_required"])
            self.assertFalse(report["summary"]["shares_anything"])
            self.assertFalse(report["summary"]["executes_anything"])
            check_names = {check["name"] for check in report["rollup_checks"]}
            self.assertIn("source:agent-owner-delegation-review:delegated", check_names)

    def test_agent_complete_rollup_blocks_malformed_delegation_summary_without_crashing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            reports = tmp / "bootstrap" / "reports"
            reports.mkdir(parents=True)
            (reports / "latest-agent-owner-delegation-review.json").write_text(
                __import__("json").dumps({"summary": {"status": "agent-review-delegated", "fail": "not-int", "remote_configured": "False"}}),
                encoding="utf-8",
            )
            report = bootstrap_ai_assets.build_agent_complete_external_actions_reserved_report(tmp)
            self.assertEqual(report["summary"]["status"], "blocked")
            self.assertGreater(report["summary"]["fail"], 0)
            self.assertFalse(report["summary"]["agent_side_complete"])
            self.assertFalse(report["summary"]["machine_side_complete"])
            self.assertFalse(report["summary"]["remote_configured"])
            self.assertFalse(report["summary"]["shares_anything"])
            self.assertFalse(report["summary"]["executes_anything"])

    def test_agent_complete_rollup_blocks_malformed_writes_without_crashing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            reports = tmp / "bootstrap" / "reports"
            reports.mkdir(parents=True)
            malformed_ready_summary = {
                "status": "agent-review-delegated",
                "fail": 0,
                "agent_engineering_review_delegated": True,
                "agent_code_review_delegated": True,
                "agent_verification_delegated": True,
                "agent_product_material_review_delegated": True,
                "requires_user_code_review": False,
                "external_owner_decision_required": True,
                "human_feedback_pending": True,
                "shares_anything": False,
                "sends_invitations": False,
                "writes_anything": False,
                "writes": "not-int",
                "executes_anything": False,
                "remote_mutation_allowed": False,
                "credential_validation_allowed": False,
                "auto_approves_release": False,
                "remote_issues_created": 0,
                "issue_backlog_mutation_allowed": False,
                "remote_configured": False,
            }
            (reports / "latest-agent-owner-delegation-review.json").write_text(__import__("json").dumps({"summary": malformed_ready_summary}), encoding="utf-8")
            report = bootstrap_ai_assets.build_agent_complete_external_actions_reserved_report(tmp)
            self.assertEqual(report["summary"]["status"], "blocked")
            self.assertGreater(report["summary"]["fail"], 0)
            self.assertFalse(report["summary"]["agent_side_complete"])
            self.assertFalse(report["summary"]["machine_side_complete"])
            self.assertFalse(report["summary"]["shares_anything"])
            self.assertFalse(report["summary"]["executes_anything"])

    def test_agent_complete_failclosed_hardening_review_tracks_phase99_regressions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            reports = tmp / "bootstrap" / "reports"
            for directory in [reports, tmp / "docs", tmp / "bootstrap" / "setup"]:
                directory.mkdir(parents=True)
            (tmp / "docs" / "open-source-release-plan.md").write_text(
                "# Open-Source Release Plan\n"
                "Run --agent-complete-external-actions-reserved --both and --agent-complete-failclosed-hardening-review --both.\n"
                "Phase 100 creates a local-only/report-only fail-closed hardening review for the agent-complete rollup, confirming malformed upstream numeric fields and blocked source evidence cannot claim completion without sharing, inviting, approving, publishing, executing external commands, calling APIs/providers, validating credentials, creating external feedback, or mutating issues/backlogs.\n",
                encoding="utf-8",
            )
            (tmp / "docs" / "public-roadmap.md").write_text(
                "# Public Roadmap\n\n"
                "### Phase 100 — Agent-complete fail-closed hardening review ✅\n"
                "Tracks fail-closed regression coverage for the agent-complete rollup, including missing source evidence and malformed numeric upstream fields, while preserving the external-actions-reserved boundary.\n",
                encoding="utf-8",
            )
            (tmp / "bootstrap" / "setup" / "bootstrap-ai-assets.sh").write_text("#!/usr/bin/env bash\n--agent-complete-external-actions-reserved\n--agent-complete-failclosed-hardening-review\n", encoding="utf-8")
            tests_dir = tmp / "tests"
            tests_dir.mkdir(parents=True)
            (tests_dir / "test_bootstrap_phase4.py").write_text(
                "def test_agent_complete_rollup_blocks_completion_booleans_when_delegation_missing(): pass\n"
                "def test_agent_complete_rollup_blocks_malformed_delegation_summary_without_crashing(): pass\n"
                "def test_agent_complete_rollup_blocks_malformed_writes_without_crashing(): pass\n"
                "def test_agent_complete_rollup_blocks_malformed_remote_issues_without_crashing(): pass\n",
                encoding="utf-8",
            )
            rollup_summary = {
                "status": "agent-complete-external-actions-reserved",
                "checks": 6,
                "pass": 6,
                "fail": 0,
                "agent_side_complete": True,
                "machine_side_complete": True,
                "requires_user_code_review": False,
                "external_owner_decision_required": True,
                "human_feedback_pending": True,
                "shares_anything": False,
                "sends_invitations": False,
                "writes_anything": False,
                "writes": 0,
                "executes_anything": False,
                "remote_mutation_allowed": False,
                "credential_validation_allowed": False,
                "auto_approves_release": False,
                "remote_issues_created": 0,
                "issue_backlog_mutation_allowed": False,
            }
            (reports / "latest-agent-complete-external-actions-reserved.json").write_text(__import__("json").dumps({"summary": rollup_summary}), encoding="utf-8")
            (reports / "latest-agent-complete-external-actions-reserved.md").write_text("# Rollup\n", encoding="utf-8")

            report = bootstrap_ai_assets.build_agent_complete_failclosed_hardening_review_report(tmp)

            self.assertEqual(report["mode"], "agent-complete-failclosed-hardening-review")
            self.assertEqual(report["summary"]["status"], "failclosed-hardened")
            self.assertTrue(report["summary"]["agent_side_complete"])
            self.assertTrue(report["summary"]["machine_side_complete"])
            self.assertTrue(report["summary"]["failclosed_regressions_covered"])
            self.assertTrue(report["summary"]["external_owner_decision_required"])
            self.assertTrue(report["summary"]["human_feedback_pending"])
            self.assertFalse(report["summary"]["requires_user_code_review"])
            self.assertFalse(report["summary"]["shares_anything"])
            self.assertFalse(report["summary"]["sends_invitations"])
            self.assertFalse(report["summary"]["writes_anything"])
            self.assertEqual(report["summary"]["writes"], 0)
            self.assertFalse(report["summary"]["executes_anything"])
            self.assertFalse(report["summary"]["remote_mutation_allowed"])
            self.assertFalse(report["summary"]["credential_validation_allowed"])
            self.assertFalse(report["summary"]["auto_approves_release"])
            self.assertEqual(report["summary"]["remote_issues_created"], 0)
            self.assertFalse(report["summary"]["issue_backlog_mutation_allowed"])
            coverage = {item["scenario"] for item in report["failclosed_regression_coverage"]}
            self.assertIn("missing-delegation-source-blocks-completion", coverage)
            self.assertIn("malformed-fail-blocks-without-crash", coverage)
            self.assertIn("malformed-writes-blocks-without-crash", coverage)
            self.assertIn("malformed-remote-issues-blocks-without-crash", coverage)
            check_names = {check["name"] for check in report["hardening_checks"]}
            self.assertIn("source:agent-complete-external-actions-reserved:complete", check_names)
            self.assertIn("coverage:failclosed-regressions-present", check_names)
            self.assertIn("docs:release-plan-documents-phase100", check_names)
            self.assertIn("roadmap:phase100-documented", check_names)
            self.assertIn("shell:agent-complete-failclosed-hardening-review-command", check_names)
            self.assertEqual(report["summary"]["fail"], 0)

    def test_agent_complete_rollup_blocks_malformed_remote_issues_without_crashing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            reports = tmp / "bootstrap" / "reports"
            reports.mkdir(parents=True)
            malformed_ready_summary = {
                "status": "agent-review-delegated",
                "fail": 0,
                "agent_engineering_review_delegated": True,
                "agent_code_review_delegated": True,
                "agent_verification_delegated": True,
                "agent_product_material_review_delegated": True,
                "requires_user_code_review": False,
                "external_owner_decision_required": True,
                "human_feedback_pending": True,
                "shares_anything": False,
                "sends_invitations": False,
                "writes_anything": False,
                "writes": 0,
                "executes_anything": False,
                "remote_mutation_allowed": False,
                "credential_validation_allowed": False,
                "auto_approves_release": False,
                "remote_issues_created": "not-int",
                "issue_backlog_mutation_allowed": False,
                "remote_configured": False,
            }
            (reports / "latest-agent-owner-delegation-review.json").write_text(__import__("json").dumps({"summary": malformed_ready_summary}), encoding="utf-8")
            report = bootstrap_ai_assets.build_agent_complete_external_actions_reserved_report(tmp)
            self.assertEqual(report["summary"]["status"], "blocked")
            self.assertGreater(report["summary"]["fail"], 0)
            self.assertFalse(report["summary"]["agent_side_complete"])
            self.assertFalse(report["summary"]["machine_side_complete"])
            self.assertFalse(report["summary"]["shares_anything"])
            self.assertFalse(report["summary"]["executes_anything"])

    def test_agent_complete_failclosed_hardening_review_blocks_without_test_evidence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            reports = tmp / "bootstrap" / "reports"
            for directory in [reports, tmp / "docs", tmp / "bootstrap" / "setup"]:
                directory.mkdir(parents=True)
            (tmp / "docs" / "open-source-release-plan.md").write_text(
                "--agent-complete-failclosed-hardening-review --both\nlocal-only/report-only fail-closed hardening review without sharing, inviting, approving, publishing, executing external commands, calling APIs/providers, validating credentials, creating external feedback, or mutating issues/backlogs\n",
                encoding="utf-8",
            )
            (tmp / "docs" / "public-roadmap.md").write_text(
                "### Phase 100 — Agent-complete fail-closed hardening review ✅\nTracks fail-closed regression coverage for the agent-complete rollup, including missing source evidence and malformed numeric upstream fields, while preserving the external-actions-reserved boundary.\n",
                encoding="utf-8",
            )
            (tmp / "bootstrap" / "setup" / "bootstrap-ai-assets.sh").write_text("--agent-complete-failclosed-hardening-review\n", encoding="utf-8")
            (reports / "latest-agent-complete-external-actions-reserved.json").write_text(__import__("json").dumps({"summary": {"status": "agent-complete-external-actions-reserved", "agent_side_complete": True, "machine_side_complete": True, "requires_user_code_review": False, "external_owner_decision_required": True, "human_feedback_pending": True, "shares_anything": False, "sends_invitations": False, "writes_anything": False, "writes": 0, "executes_anything": False, "remote_mutation_allowed": False, "credential_validation_allowed": False, "auto_approves_release": False, "remote_issues_created": 0, "issue_backlog_mutation_allowed": False}}), encoding="utf-8")
            report = bootstrap_ai_assets.build_agent_complete_failclosed_hardening_review_report(tmp)
            self.assertEqual(report["summary"]["status"], "blocked")
            self.assertGreater(report["summary"]["fail"], 0)
            self.assertFalse(report["summary"]["failclosed_regressions_covered"])
            self.assertFalse(all(item["covered"] for item in report["failclosed_regression_coverage"]))

    def test_agent_complete_failclosed_hardening_review_rejects_comment_only_test_names(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            reports = tmp / "bootstrap" / "reports"
            for directory in [reports, tmp / "docs", tmp / "bootstrap" / "setup", tmp / "tests"]:
                directory.mkdir(parents=True)
            (tmp / "docs" / "open-source-release-plan.md").write_text(
                "--agent-complete-failclosed-hardening-review --both\nlocal-only/report-only fail-closed hardening review without sharing, inviting, approving, publishing, executing external commands, calling APIs/providers, validating credentials, creating external feedback, or mutating issues/backlogs\n",
                encoding="utf-8",
            )
            (tmp / "docs" / "public-roadmap.md").write_text(
                "### Phase 100 — Agent-complete fail-closed hardening review ✅\nTracks fail-closed regression coverage for the agent-complete rollup, including missing source evidence and malformed numeric upstream fields, while preserving the external-actions-reserved boundary.\n",
                encoding="utf-8",
            )
            (tmp / "bootstrap" / "setup" / "bootstrap-ai-assets.sh").write_text("--agent-complete-failclosed-hardening-review\n", encoding="utf-8")
            (tmp / "tests" / "test_bootstrap_phase4.py").write_text(
                "# test_agent_complete_rollup_blocks_completion_booleans_when_delegation_missing\n"
                "MENTIONED = 'test_agent_complete_rollup_blocks_malformed_delegation_summary_without_crashing'\n"
                "# test_agent_complete_rollup_blocks_malformed_writes_without_crashing\n"
                "TEXT = 'test_agent_complete_rollup_blocks_malformed_remote_issues_without_crashing'\n",
                encoding="utf-8",
            )
            (reports / "latest-agent-complete-external-actions-reserved.json").write_text(__import__("json").dumps({"summary": {"status": "agent-complete-external-actions-reserved", "agent_side_complete": True, "machine_side_complete": True, "requires_user_code_review": False, "external_owner_decision_required": True, "human_feedback_pending": True, "shares_anything": False, "sends_invitations": False, "writes_anything": False, "writes": 0, "executes_anything": False, "remote_mutation_allowed": False, "credential_validation_allowed": False, "auto_approves_release": False, "remote_issues_created": 0, "issue_backlog_mutation_allowed": False}}), encoding="utf-8")

            report = bootstrap_ai_assets.build_agent_complete_failclosed_hardening_review_report(tmp)

            self.assertEqual(report["summary"]["status"], "blocked")
            self.assertGreater(report["summary"]["fail"], 0)
            self.assertFalse(report["summary"]["failclosed_regressions_covered"])
            self.assertFalse(any(item["covered"] for item in report["failclosed_regression_coverage"]))
            self.assertTrue(all(item["evidence_kind"] == "test-function-definition" for item in report["failclosed_regression_coverage"]))

    def test_agent_complete_regression_evidence_integrity_rejects_multiline_string_test_names(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            reports = tmp / "bootstrap" / "reports"
            for directory in [reports, tmp / "docs", tmp / "bootstrap" / "setup", tmp / "tests"]:
                directory.mkdir(parents=True)
            (tmp / "docs" / "open-source-release-plan.md").write_text(
                "--agent-complete-regression-evidence-integrity --both\nlocal-only/report-only regression evidence integrity audit without sharing, inviting, approving, publishing, executing external commands, calling APIs/providers, validating credentials, creating external feedback, or mutating issues/backlogs\n",
                encoding="utf-8",
            )
            (tmp / "docs" / "public-roadmap.md").write_text(
                "### Phase 101 — Agent-complete regression evidence integrity ✅\nConfirms Phase 100 regression coverage is backed by actual test function definitions rather than comments or string mentions while preserving the external-actions-reserved boundary.\n",
                encoding="utf-8",
            )
            (tmp / "bootstrap" / "setup" / "bootstrap-ai-assets.sh").write_text("--agent-complete-regression-evidence-integrity\n", encoding="utf-8")
            (tmp / "tests" / "test_bootstrap_phase4.py").write_text(
                'DOC = """\n'
                "def test_agent_complete_rollup_blocks_completion_booleans_when_delegation_missing(self): pass\n"
                "def test_agent_complete_rollup_blocks_malformed_delegation_summary_without_crashing(self): pass\n"
                "def test_agent_complete_rollup_blocks_malformed_writes_without_crashing(self): pass\n"
                "def test_agent_complete_rollup_blocks_malformed_remote_issues_without_crashing(self): pass\n"
                '"""\n',
                encoding="utf-8",
            )
            phase100_summary = {
                "status": "failclosed-hardened",
                "checks": 5,
                "pass": 5,
                "fail": 0,
                "agent_side_complete": True,
                "machine_side_complete": True,
                "failclosed_regressions_covered": True,
                "requires_user_code_review": False,
                "external_owner_decision_required": True,
                "human_feedback_pending": True,
                "shares_anything": False,
                "sends_invitations": False,
                "writes_anything": False,
                "writes": 0,
                "executes_anything": False,
                "remote_mutation_allowed": False,
                "credential_validation_allowed": False,
                "auto_approves_release": False,
                "remote_issues_created": 0,
                "issue_backlog_mutation_allowed": False,
            }
            (reports / "latest-agent-complete-failclosed-hardening-review.json").write_text(__import__("json").dumps({"summary": phase100_summary}), encoding="utf-8")

            report = bootstrap_ai_assets.build_agent_complete_regression_evidence_integrity_report(tmp)

            self.assertEqual(report["summary"]["status"], "blocked")
            self.assertFalse(report["summary"]["definition_backed_regressions_covered"])
            self.assertFalse(any(item["covered"] for item in report["regression_evidence"]))

    def test_agent_complete_regression_evidence_integrity_summarizes_definition_backed_phase100_evidence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            reports = tmp / "bootstrap" / "reports"
            for directory in [reports, tmp / "docs", tmp / "bootstrap" / "setup", tmp / "tests"]:
                directory.mkdir(parents=True)
            (tmp / "docs" / "open-source-release-plan.md").write_text(
                "--agent-complete-regression-evidence-integrity --both\nlocal-only/report-only regression evidence integrity audit without sharing, inviting, approving, publishing, executing external commands, calling APIs/providers, validating credentials, creating external feedback, or mutating issues/backlogs\n",
                encoding="utf-8",
            )
            (tmp / "docs" / "public-roadmap.md").write_text(
                "### Phase 101 — Agent-complete regression evidence integrity ✅\nConfirms Phase 100 regression coverage is backed by actual test function definitions rather than comments or string mentions while preserving the external-actions-reserved boundary.\n",
                encoding="utf-8",
            )
            (tmp / "bootstrap" / "setup" / "bootstrap-ai-assets.sh").write_text("--agent-complete-regression-evidence-integrity\n", encoding="utf-8")
            (tmp / "tests" / "test_bootstrap_phase4.py").write_text(
                "def test_agent_complete_rollup_blocks_completion_booleans_when_delegation_missing(self): pass\n"
                "def test_agent_complete_rollup_blocks_malformed_delegation_summary_without_crashing(self): pass\n"
                "def test_agent_complete_rollup_blocks_malformed_writes_without_crashing(self): pass\n"
                "def test_agent_complete_rollup_blocks_malformed_remote_issues_without_crashing(self): pass\n",
                encoding="utf-8",
            )
            phase100_summary = {
                "status": "failclosed-hardened",
                "checks": 5,
                "pass": 5,
                "fail": 0,
                "agent_side_complete": True,
                "machine_side_complete": True,
                "failclosed_regressions_covered": True,
                "requires_user_code_review": False,
                "external_owner_decision_required": True,
                "human_feedback_pending": True,
                "shares_anything": False,
                "sends_invitations": False,
                "writes_anything": False,
                "writes": 0,
                "executes_anything": False,
                "remote_mutation_allowed": False,
                "credential_validation_allowed": False,
                "auto_approves_release": False,
                "remote_issues_created": 0,
                "issue_backlog_mutation_allowed": False,
            }
            (reports / "latest-agent-complete-failclosed-hardening-review.json").write_text(__import__("json").dumps({"summary": phase100_summary}), encoding="utf-8")

            report = bootstrap_ai_assets.build_agent_complete_regression_evidence_integrity_report(tmp)

            self.assertEqual(report["mode"], "agent-complete-regression-evidence-integrity")
            self.assertEqual(report["summary"]["status"], "definition-backed")
            self.assertTrue(report["summary"]["definition_backed_regressions_covered"])
            self.assertFalse(report["summary"]["requires_user_code_review"])
            self.assertTrue(report["summary"]["external_owner_decision_required"])
            self.assertTrue(report["summary"]["human_feedback_pending"])
            self.assertFalse(report["summary"]["shares_anything"])
            self.assertFalse(report["summary"]["sends_invitations"])
            self.assertFalse(report["summary"]["writes_anything"])
            self.assertEqual(report["summary"]["writes"], 0)
            self.assertFalse(report["summary"]["executes_anything"])
            self.assertFalse(report["summary"]["remote_mutation_allowed"])
            self.assertFalse(report["summary"]["credential_validation_allowed"])
            self.assertFalse(report["summary"]["auto_approves_release"])
            self.assertEqual(report["summary"]["remote_issues_created"], 0)
            self.assertFalse(report["summary"]["issue_backlog_mutation_allowed"])
            self.assertTrue(all(item["covered"] and item["evidence_kind"] == "test-function-definition" for item in report["regression_evidence"]))
            check_names = {check["name"] for check in report["integrity_checks"]}
            self.assertIn("source:agent-complete-failclosed-hardening-review:complete", check_names)
            self.assertIn("coverage:test-function-definitions-present", check_names)
            self.assertIn("docs:release-plan-documents-phase101", check_names)
            self.assertIn("roadmap:phase101-documented", check_names)
            self.assertIn("shell:agent-complete-regression-evidence-integrity-command", check_names)
            self.assertEqual(report["summary"]["fail"], 0)

    def test_agent_complete_syntax_invalid_evidence_failclosed_review_summarizes_blocked_syntax_invalid_fixture(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            reports = tmp / "bootstrap" / "reports"
            for directory in [reports, tmp / "docs", tmp / "bootstrap" / "setup", tmp / "tests"]:
                directory.mkdir(parents=True)
            (tmp / "docs" / "open-source-release-plan.md").write_text(
                "--agent-complete-syntax-invalid-evidence-failclosed-review --both\nlocal-only/report-only syntax-invalid evidence fail-closed review without sharing, inviting, approving, publishing, executing external commands, calling APIs/providers, validating credentials, creating external feedback, or mutating issues/backlogs\n",
                encoding="utf-8",
            )
            (tmp / "docs" / "public-roadmap.md").write_text(
                "### Phase 102 — Agent-complete syntax-invalid evidence fail-closed review ✅\nConfirms syntax-invalid regression evidence cannot satisfy definition-backed coverage or claim agent completion while preserving the external-actions-reserved boundary.\n",
                encoding="utf-8",
            )
            (tmp / "bootstrap" / "setup" / "bootstrap-ai-assets.sh").write_text("--agent-complete-syntax-invalid-evidence-failclosed-review\n", encoding="utf-8")
            (tmp / "tests" / "test_bootstrap_phase4.py").write_text(
                "def test_agent_complete_rollup_blocks_completion_booleans_when_delegation_missing(self):\n"
                "    pass\n"
                "def test_agent_complete_rollup_blocks_malformed_delegation_summary_without_crashing(self)\n"
                "    pass\n",
                encoding="utf-8",
            )
            phase101_summary = {
                "status": "definition-backed",
                "checks": 5,
                "pass": 5,
                "fail": 0,
                "agent_side_complete": True,
                "machine_side_complete": True,
                "definition_backed_regressions_covered": True,
                "requires_user_code_review": False,
                "external_owner_decision_required": True,
                "human_feedback_pending": True,
                "shares_anything": False,
                "sends_invitations": False,
                "writes_anything": False,
                "writes": 0,
                "executes_anything": False,
                "remote_mutation_allowed": False,
                "credential_validation_allowed": False,
                "auto_approves_release": False,
                "remote_issues_created": 0,
                "issue_backlog_mutation_allowed": False,
            }
            (reports / "latest-agent-complete-regression-evidence-integrity.json").write_text(__import__("json").dumps({"summary": phase101_summary}), encoding="utf-8")

            report = bootstrap_ai_assets.build_agent_complete_syntax_invalid_evidence_failclosed_review_report(tmp)

            self.assertEqual(report["mode"], "agent-complete-syntax-invalid-evidence-failclosed-review")
            self.assertEqual(report["summary"]["status"], "syntax-invalid-failclosed")
            self.assertTrue(report["summary"]["syntax_invalid_evidence_blocks_completion"])
            self.assertFalse(report["summary"]["agent_side_complete"])
            self.assertFalse(report["summary"]["machine_side_complete"])
            self.assertFalse(any(item["covered"] for item in report["syntax_invalid_regression_evidence"]))
            self.assertFalse(report["summary"]["shares_anything"])
            self.assertFalse(report["summary"]["sends_invitations"])
            self.assertFalse(report["summary"]["writes_anything"])
            self.assertEqual(report["summary"]["writes"], 0)
            self.assertFalse(report["summary"]["executes_anything"])
            self.assertFalse(report["summary"]["remote_mutation_allowed"])
            self.assertFalse(report["summary"]["credential_validation_allowed"])
            self.assertFalse(report["summary"]["auto_approves_release"])
            self.assertEqual(report["summary"]["remote_issues_created"], 0)
            self.assertFalse(report["summary"]["issue_backlog_mutation_allowed"])
            check_names = {check["name"] for check in report["syntax_invalid_checks"]}
            self.assertIn("source:agent-complete-regression-evidence-integrity:complete", check_names)
            self.assertIn("syntax-invalid:coverage-failclosed", check_names)
            self.assertIn("docs:release-plan-documents-phase102", check_names)
            self.assertIn("roadmap:phase102-documented", check_names)
            self.assertIn("shell:agent-complete-syntax-invalid-evidence-failclosed-review-command", check_names)
            self.assertEqual(report["summary"]["checks"], 5)
            self.assertEqual(report["summary"]["pass"], 5)
            self.assertEqual(report["summary"]["fail"], 0)

    def test_agent_complete_syntax_invalid_evidence_failclosed_review_blocks_without_phase101_source(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            reports = tmp / "bootstrap" / "reports"
            reports.mkdir(parents=True)
            docs = tmp / "docs"
            docs.mkdir(parents=True)
            docs.joinpath("open-source-release-plan.md").write_text(
                "--agent-complete-syntax-invalid-evidence-failclosed-review --both\n"
                "local-only/report-only syntax-invalid evidence fail-closed review\n"
                "without sharing, inviting, approving, publishing, executing external commands, calling APIs/providers, validating credentials, creating external feedback, or mutating issues/backlogs\n",
                encoding="utf-8",
            )
            docs.joinpath("public-roadmap.md").write_text(
                "### Phase 102 — Agent-complete syntax-invalid evidence fail-closed review ✅\n"
                "Confirms syntax-invalid regression evidence cannot satisfy definition-backed coverage or claim agent completion while preserving the external-actions-reserved boundary.\n",
                encoding="utf-8",
            )
            shell_dir = tmp / "bootstrap" / "setup"
            shell_dir.mkdir(parents=True)
            shell_dir.joinpath("bootstrap-ai-assets.sh").write_text(
                "--agent-complete-syntax-invalid-evidence-failclosed-review\n",
                encoding="utf-8",
            )

            report = bootstrap_ai_assets.build_agent_complete_syntax_invalid_evidence_failclosed_review_report(tmp)

            self.assertEqual(report["summary"]["status"], "blocked")
            self.assertFalse(report["summary"]["syntax_invalid_evidence_blocks_completion"])
            self.assertFalse(report["summary"]["agent_side_complete"])
            self.assertFalse(report["summary"]["machine_side_complete"])
            self.assertEqual(report["summary"]["checks"], 5)
            self.assertEqual(report["summary"]["pass"], 4)
            self.assertEqual(report["summary"]["fail"], 1)
            self.assertFalse(report["summary"]["shares_anything"])
            self.assertFalse(report["summary"]["executes_anything"])
            source_check = next(check for check in report["syntax_invalid_checks"] if check["name"] == "source:agent-complete-regression-evidence-integrity:complete")
            self.assertEqual(source_check["status"], "fail")

    def test_phase102_syntax_invalid_evidence_helper_validates_strict_latest_report(self):
        valid_summary = {
            "status": "syntax-invalid-failclosed",
            "syntax_invalid_evidence_blocks_completion": True,
            "agent_side_complete": False,
            "machine_side_complete": False,
            "requires_user_code_review": False,
            "external_owner_decision_required": True,
            "human_feedback_pending": True,
            "shares_anything": False,
            "sends_invitations": False,
            "writes_anything": False,
            "writes": 0,
            "executes_anything": False,
            "remote_mutation_allowed": False,
            "credential_validation_allowed": False,
            "auto_approves_release": False,
            "remote_issues_created": 0,
            "issue_backlog_mutation_allowed": False,
            "checks": 5,
            "pass": 5,
            "fail": 0,
            "warn": 0,
        }
        invalid_summary_with_bool_warn = dict(valid_summary)
        invalid_summary_with_bool_warn["warn"] = False
        cases = [
            ({"mode": "agent-complete-syntax-invalid-evidence-failclosed-review", "summary": valid_summary}, True),
            ({"mode": "wrong-mode", "summary": valid_summary}, False),
            ({"mode": "agent-complete-syntax-invalid-evidence-failclosed-review", "summary": invalid_summary_with_bool_warn}, False),
            ({"mode": "agent-complete-syntax-invalid-evidence-failclosed-review", "summary": {"status": "syntax-invalid-failclosed", "checks": "5", "pass": "5", "fail": "0", "warn": "0"}}, False),
            ({}, False),
        ]
        for payload, expected_valid in cases:
            with self.subTest(payload=payload):
                result = bootstrap_ai_assets._validate_phase102_syntax_invalid_evidence_report(payload)
                self.assertEqual(result["valid"], expected_valid)
                self.assertEqual(result["mode"], payload.get("mode"))
                self.assertIn("phase102_report_evidence_valid=", result["evidence"])
                self.assertFalse(result["shares_anything"])
                self.assertFalse(result["executes_anything"])
                self.assertFalse(result["remote_mutation_allowed"])
                self.assertFalse(result["credential_validation_allowed"])
                self.assertFalse(result["auto_approves_release"])
                self.assertFalse(result["issue_backlog_mutation_allowed"])

    def test_phase102_syntax_invalid_evidence_helper_reports_non_dict_payloads_failclosed(self):
        cases = [
            (["not", "a", "report"], "list", "missing"),
            ({"mode": "agent-complete-syntax-invalid-evidence-failclosed-review", "summary": "not-a-summary-dict"}, "dict", "str"),
        ]
        for payload, expected_report_type, expected_summary_type in cases:
            with self.subTest(payload=payload):
                result = bootstrap_ai_assets._validate_phase102_syntax_invalid_evidence_report(payload)
                self.assertFalse(result["valid"])
                self.assertEqual(result["report_type"], expected_report_type)
                self.assertEqual(result["summary_type"], expected_summary_type)
                self.assertIn(f"report_type={expected_report_type}", result["evidence"])
                self.assertIn(f"summary_type={expected_summary_type}", result["evidence"])
                self.assertFalse(result["shares_anything"])
                self.assertFalse(result["executes_anything"])
                self.assertFalse(result["remote_mutation_allowed"])
                self.assertFalse(result["credential_validation_allowed"])
                self.assertFalse(result["auto_approves_release"])
                self.assertFalse(result["issue_backlog_mutation_allowed"])

    def test_phase102_syntax_invalid_evidence_helper_reports_invalid_field_diagnostics(self):
        malformed_summary = self._valid_phase102_syntax_invalid_evidence_summary()
        malformed_summary["agent_side_complete"] = "False"
        malformed_summary["warn"] = False
        malformed_summary["remote_issues_created"] = "0"

        result = bootstrap_ai_assets._validate_phase102_syntax_invalid_evidence_report(
            {"mode": "agent-complete-syntax-invalid-evidence-failclosed-review", "summary": malformed_summary}
        )

        self.assertFalse(result["valid"])
        self.assertEqual(result["invalid_fields"], ["agent_side_complete", "remote_issues_created", "warn"])
        self.assertIn("invalid_fields=agent_side_complete,remote_issues_created,warn", result["evidence"])
        self.assertIn("agent_side_complete_type=str", result["evidence"])
        self.assertIn("remote_issues_created_type=str", result["evidence"])
        self.assertIn("warn_type=bool", result["evidence"])
        self.assertFalse(result["shares_anything"])
        self.assertFalse(result["executes_anything"])
        self.assertFalse(result["remote_mutation_allowed"])
        self.assertFalse(result["credential_validation_allowed"])
        self.assertFalse(result["auto_approves_release"])
        self.assertFalse(result["issue_backlog_mutation_allowed"])

    def test_phase102_syntax_invalid_evidence_helper_is_shared_by_rollup_builders(self):
        original = bootstrap_ai_assets._validate_phase102_syntax_invalid_evidence_report
        try:
            calls = []
            def fake_validator(report):
                calls.append(report)
                return {
                    "valid": False,
                    "summary": {},
                    "mode": report.get("mode") if isinstance(report, dict) else None,
                    "evidence": "phase102_report_evidence_valid=False; sentinel=shared-helper",
                    "shares_anything": False,
                    "executes_anything": False,
                    "remote_mutation_allowed": False,
                    "credential_validation_allowed": False,
                    "auto_approves_release": False,
                    "issue_backlog_mutation_allowed": False,
                }
            bootstrap_ai_assets._validate_phase102_syntax_invalid_evidence_report = fake_validator
            with tempfile.TemporaryDirectory() as tmpdir:
                tmp = Path(tmpdir)
                reports = tmp / "bootstrap" / "reports"
                docs = tmp / "docs"
                shell_dir = tmp / "bootstrap" / "setup"
                reports.mkdir(parents=True)
                docs.mkdir(parents=True)
                shell_dir.mkdir(parents=True)
                reports.joinpath("latest-agent-complete-syntax-invalid-evidence-failclosed-review.json").write_text(
                    __import__("json").dumps({"mode": "agent-complete-syntax-invalid-evidence-failclosed-review", "summary": {"status": "syntax-invalid-failclosed"}}),
                    encoding="utf-8",
                )
                docs.joinpath("open-source-release-plan.md").write_text(
                    "--agent-complete-phase102-rollup-evidence-failclosed-review --both\nlocal-only/report-only Phase102 rollup evidence fail-closed review\n",
                    encoding="utf-8",
                )
                docs.joinpath("public-roadmap.md").write_text(
                    "# Roadmap\n\n## Vision\nportable AI assets layer across agents models clients machines\n\n## Product Thesis\nnot another agent runtime canonical memory adapter projections safe migration reviewable reconciliation\n\n"
                    "### Phase 103 — Agent-complete Phase102 rollup evidence fail-closed review ✅\n"
                    "Confirms downstream completed-work and agent-complete rollups require valid Phase102 report evidence before continuing.\n",
                    encoding="utf-8",
                )
                shell_dir.joinpath("bootstrap-ai-assets.sh").write_text("--agent-complete-phase102-rollup-evidence-failclosed-review\n", encoding="utf-8")

                phase103_report = bootstrap_ai_assets.build_agent_complete_phase102_rollup_evidence_failclosed_review_report(tmp)
                completed_work_report = bootstrap_ai_assets.build_completed_work_review_report(tmp)

                self.assertGreaterEqual(len(calls), 2)
                self.assertFalse(phase103_report["summary"]["phase102_report_evidence_valid"])
                self.assertEqual(phase103_report["summary"]["status"], "blocked")
                self.assertIn("sentinel=shared-helper", "\n".join(completed_work_report["review_axes"]["agent_completion_evidence"]["evidence"]))
                self.assertEqual(completed_work_report["review_axes"]["agent_completion_evidence"]["status"], "fail")
        finally:
            bootstrap_ai_assets._validate_phase102_syntax_invalid_evidence_report = original

    def test_agent_complete_phase102_rollup_evidence_failclosed_review_accepts_valid_phase102_evidence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            reports = tmp / "bootstrap" / "reports"
            reports.mkdir(parents=True)
            reports.joinpath("latest-agent-complete-syntax-invalid-evidence-failclosed-review.json").write_text(
                __import__("json").dumps(
                    {
                        "mode": "agent-complete-syntax-invalid-evidence-failclosed-review",
                        "summary": self._valid_phase102_syntax_invalid_evidence_summary(),
                    }
                ),
                encoding="utf-8",
            )
            docs = tmp / "docs"
            docs.mkdir(parents=True)
            docs.joinpath("open-source-release-plan.md").write_text(
                "--agent-complete-phase102-rollup-evidence-failclosed-review --both\n"
                "local-only/report-only Phase102 rollup evidence fail-closed review\n"
                "without sharing, inviting, approving, publishing, executing external commands, calling APIs/providers, validating credentials, creating external feedback, or mutating issues/backlogs\n",
                encoding="utf-8",
            )
            docs.joinpath("public-roadmap.md").write_text(
                "### Phase 103 — Agent-complete Phase102 rollup evidence fail-closed review ✅\n"
                "Confirms downstream completed-work and agent-complete rollups require valid Phase102 report evidence before continuing.\n",
                encoding="utf-8",
            )
            shell_dir = tmp / "bootstrap" / "setup"
            shell_dir.mkdir(parents=True)
            shell_dir.joinpath("bootstrap-ai-assets.sh").write_text(
                "--agent-complete-phase102-rollup-evidence-failclosed-review\n",
                encoding="utf-8",
            )

            report = bootstrap_ai_assets.build_agent_complete_phase102_rollup_evidence_failclosed_review_report(tmp)

            self.assertEqual(report["mode"], "agent-complete-phase102-rollup-evidence-failclosed-review")
            self.assertEqual(report["summary"]["status"], "phase102-evidence-failclosed")
            self.assertTrue(report["summary"]["phase102_report_evidence_valid"])
            self.assertTrue(report["summary"]["rollup_requires_phase102_report_evidence"])
            self.assertFalse(report["summary"]["agent_side_complete"])
            self.assertFalse(report["summary"]["machine_side_complete"])
            self.assertFalse(report["summary"]["shares_anything"])
            self.assertFalse(report["summary"]["executes_anything"])
            self.assertEqual(report["summary"]["checks"], 5)
            self.assertEqual(report["summary"]["pass"], 5)
            self.assertEqual(report["summary"]["fail"], 0)
            check_names = {check["name"] for check in report["phase102_rollup_checks"]}
            self.assertIn("source:agent-complete-syntax-invalid-evidence-failclosed-review:valid", check_names)
            self.assertIn("rollup:completed-work-requires-phase102-report-evidence", check_names)
            self.assertIn("shell:agent-complete-phase102-rollup-evidence-failclosed-review-command", check_names)

    def test_agent_complete_phase102_rollup_evidence_failclosed_review_blocks_missing_and_malformed_phase102_evidence(self):
        valid_summary_with_bool_count = {
            "status": "syntax-invalid-failclosed",
            "syntax_invalid_evidence_blocks_completion": True,
            "agent_side_complete": False,
            "machine_side_complete": False,
            "requires_user_code_review": False,
            "external_owner_decision_required": True,
            "human_feedback_pending": True,
            "shares_anything": False,
            "sends_invitations": False,
            "writes_anything": False,
            "writes": False,
            "executes_anything": False,
            "remote_mutation_allowed": False,
            "credential_validation_allowed": False,
            "auto_approves_release": False,
            "remote_issues_created": False,
            "issue_backlog_mutation_allowed": False,
            "checks": 5,
            "pass": 5,
            "fail": False,
            "warn": 0,
        }
        valid_summary_with_bool_warn = {
            "status": "syntax-invalid-failclosed",
            "syntax_invalid_evidence_blocks_completion": True,
            "agent_side_complete": False,
            "machine_side_complete": False,
            "requires_user_code_review": False,
            "external_owner_decision_required": True,
            "human_feedback_pending": True,
            "shares_anything": False,
            "sends_invitations": False,
            "writes_anything": False,
            "writes": 0,
            "executes_anything": False,
            "remote_mutation_allowed": False,
            "credential_validation_allowed": False,
            "auto_approves_release": False,
            "remote_issues_created": 0,
            "issue_backlog_mutation_allowed": False,
            "checks": 5,
            "pass": 5,
            "fail": 0,
            "warn": False,
        }
        for payload in [
            None,
            {"mode": "agent-complete-syntax-invalid-evidence-failclosed-review", "summary": {"status": "syntax-invalid-failclosed", "syntax_invalid_evidence_blocks_completion": "true", "checks": "5", "pass": "5", "fail": "0", "warn": "0"}},
            {"mode": "agent-complete-syntax-invalid-evidence-failclosed-review", "summary": valid_summary_with_bool_count},
            {"mode": "agent-complete-syntax-invalid-evidence-failclosed-review", "summary": valid_summary_with_bool_warn},
        ]:
            with self.subTest(payload=payload):
                with tempfile.TemporaryDirectory() as tmpdir:
                    tmp = Path(tmpdir)
                    reports = tmp / "bootstrap" / "reports"
                    reports.mkdir(parents=True)
                    if payload is not None:
                        reports.joinpath("latest-agent-complete-syntax-invalid-evidence-failclosed-review.json").write_text(
                            __import__("json").dumps(payload),
                            encoding="utf-8",
                        )
                    docs = tmp / "docs"
                    docs.mkdir(parents=True)
                    docs.joinpath("open-source-release-plan.md").write_text(
                        "--agent-complete-phase102-rollup-evidence-failclosed-review --both\nlocal-only/report-only Phase102 rollup evidence fail-closed review\n",
                        encoding="utf-8",
                    )
                    docs.joinpath("public-roadmap.md").write_text(
                        "### Phase 103 — Agent-complete Phase102 rollup evidence fail-closed review ✅\n"
                        "Confirms downstream completed-work and agent-complete rollups require valid Phase102 report evidence before continuing.\n",
                        encoding="utf-8",
                    )
                    shell_dir = tmp / "bootstrap" / "setup"
                    shell_dir.mkdir(parents=True)
                    shell_dir.joinpath("bootstrap-ai-assets.sh").write_text(
                        "--agent-complete-phase102-rollup-evidence-failclosed-review\n",
                        encoding="utf-8",
                    )

                    report = bootstrap_ai_assets.build_agent_complete_phase102_rollup_evidence_failclosed_review_report(tmp)

                    self.assertEqual(report["summary"]["status"], "blocked")
                    self.assertFalse(report["summary"]["phase102_report_evidence_valid"])
                    self.assertFalse(report["summary"]["rollup_requires_phase102_report_evidence"])
                    self.assertFalse(report["summary"]["agent_side_complete"])
                    self.assertFalse(report["summary"]["machine_side_complete"])
                    self.assertFalse(report["summary"]["shares_anything"])
                    self.assertFalse(report["summary"]["executes_anything"])
                    self.assertEqual(report["summary"]["fail"], 2)
                    source_check = next(check for check in report["phase102_rollup_checks"] if check["name"] == "source:agent-complete-syntax-invalid-evidence-failclosed-review:valid")
                    self.assertEqual(source_check["status"], "fail")

    def test_phase102_rollup_and_completed_work_preserve_invalid_field_diagnostics(self):
        malformed_summary = self._valid_phase102_syntax_invalid_evidence_summary()
        malformed_summary["agent_side_complete"] = "False"
        malformed_summary["remote_issues_created"] = "0"
        malformed_summary["warn"] = False
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            reports = tmp / "bootstrap" / "reports"
            reports.mkdir(parents=True)
            reports.joinpath("latest-agent-complete-syntax-invalid-evidence-failclosed-review.json").write_text(
                __import__("json").dumps(
                    {
                        "mode": "agent-complete-syntax-invalid-evidence-failclosed-review",
                        "summary": malformed_summary,
                    }
                ),
                encoding="utf-8",
            )
            docs = tmp / "docs"
            docs.mkdir(parents=True)
            docs.joinpath("open-source-release-plan.md").write_text(
                "--agent-complete-phase102-rollup-evidence-failclosed-review --both\n"
                "local-only/report-only Phase102 rollup evidence fail-closed review\n",
                encoding="utf-8",
            )
            docs.joinpath("public-roadmap.md").write_text(
                "# Roadmap\n\n## Vision\nportable AI assets layer across agents models clients machines\n\n"
                "## Product Thesis\nnot another agent runtime canonical memory adapter projections safe migration reviewable reconciliation\n\n"
                "### Phase 103 — Agent-complete Phase102 rollup evidence fail-closed review ✅\n"
                "Confirms downstream completed-work and agent-complete rollups require valid Phase102 report evidence before continuing.\n",
                encoding="utf-8",
            )
            shell_dir = tmp / "bootstrap" / "setup"
            shell_dir.mkdir(parents=True)
            shell_dir.joinpath("bootstrap-ai-assets.sh").write_text(
                "--agent-complete-phase102-rollup-evidence-failclosed-review\n",
                encoding="utf-8",
            )

            rollup_report = bootstrap_ai_assets.build_agent_complete_phase102_rollup_evidence_failclosed_review_report(tmp)
            completed_work_report = bootstrap_ai_assets.build_completed_work_review_report(tmp)

            self.assertEqual(rollup_report["summary"]["status"], "blocked")
            self.assertEqual(
                rollup_report["summary"]["phase102_report_invalid_fields"],
                ["agent_side_complete", "remote_issues_created", "warn"],
            )
            source_check = next(check for check in rollup_report["phase102_rollup_checks"] if check["name"] == "source:agent-complete-syntax-invalid-evidence-failclosed-review:valid")
            self.assertEqual(source_check["invalid_fields"], ["agent_side_complete", "remote_issues_created", "warn"])
            self.assertIn("agent_side_complete_type=str", source_check["detail"])
            self.assertIn("remote_issues_created_type=str", source_check["detail"])
            self.assertIn("warn_type=bool", source_check["detail"])

            agent_axis = completed_work_report["review_axes"]["agent_completion_evidence"]
            self.assertEqual(agent_axis["status"], "fail")
            self.assertEqual(agent_axis["invalid_fields"], ["agent_side_complete", "remote_issues_created", "warn"])
            self.assertIn("invalid_fields=agent_side_complete,remote_issues_created,warn", agent_axis["evidence"])

            rollup_markdown = bootstrap_ai_assets.markdown_for_agent_complete_phase102_rollup_evidence_failclosed_review(rollup_report)
            self.assertIn("phase102_report_invalid_fields", rollup_markdown)
            self.assertIn("agent_side_complete", rollup_markdown)
            self.assertIn("remote_issues_created", rollup_markdown)
            self.assertIn("warn", rollup_markdown)
            self.assertIn("agent_side_complete_type=str", rollup_markdown)
            self.assertIn("remote_issues_created_type=str", rollup_markdown)
            self.assertIn("warn_type=bool", rollup_markdown)

            completed_markdown = bootstrap_ai_assets.markdown_for_completed_work_review(completed_work_report)
            self.assertIn("- invalid_fields: `['agent_side_complete', 'remote_issues_created', 'warn']`", completed_markdown)
            self.assertIn("invalid_fields=agent_side_complete,remote_issues_created,warn", completed_markdown)
            self.assertIn("agent_side_complete_type=str", completed_markdown)
            self.assertIn("remote_issues_created_type=str", completed_markdown)
            self.assertIn("warn_type=bool", completed_markdown)

    def test_verify_release_provenance_matches_current_artifacts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            pack = tmp / "dist" / "portable-ai-assets-public-demo"
            staging = tmp / "dist" / "github-staging" / "portable-ai-assets"
            handoff_dir = tmp / "dist" / "github-handoff" / "portable-ai-assets-handoff-demo"
            provenance_dir = tmp / "dist" / "provenance"
            for directory in [pack, staging, handoff_dir, provenance_dir, tmp / "bootstrap" / "reports"]:
                directory.mkdir(parents=True)
            (pack / "README.md").write_text("# Pack\n", encoding="utf-8")
            (staging / "README.md").write_text("# Staging\n", encoding="utf-8")
            bootstrap_ai_assets.run_git_command(staging, ["init"])
            (handoff_dir / "HANDOFF.md").write_text("# Handoff\n", encoding="utf-8")
            archive = tmp / "dist" / "portable-ai-assets-public-demo.tar.gz"
            archive.write_bytes(b"demo")
            sha = __import__("hashlib").sha256(archive.read_bytes()).hexdigest()
            checksum = tmp / "dist" / "portable-ai-assets-public-demo.tar.gz.sha256"
            checksum.write_text(f"{sha}  {archive.name}\n", encoding="utf-8")
            tree_digests = {
                "public_release_pack": bootstrap_ai_assets._tree_digest(pack),
                "github_staging": bootstrap_ai_assets._tree_digest(staging),
                "github_handoff": bootstrap_ai_assets._tree_digest(handoff_dir),
            }
            provenance = {
                "provenance_kind": "unsigned-release-provenance-v1",
                "executes_anything": False,
                "subject": {"archive_sha256": sha},
                "tree_digests": tree_digests,
            }
            provenance_path = provenance_dir / "portable-ai-assets-provenance-demo.json"
            provenance_path.write_text(__import__("json").dumps(provenance), encoding="utf-8")
            reports = tmp / "bootstrap" / "reports"
            (reports / "latest-release-provenance.json").write_text(__import__("json").dumps({"provenance_json": str(provenance_path)}), encoding="utf-8")
            (reports / "latest-public-release-archive.json").write_text(__import__("json").dumps({"pack_dir": str(pack), "archive_path": str(archive), "checksum_path": str(checksum), "summary":{"archive_sha256": sha}}), encoding="utf-8")
            (reports / "latest-public-repo-staging-status.json").write_text(__import__("json").dumps({"staging_dir": str(staging), "summary":{"remote_configured": False}}), encoding="utf-8")
            (reports / "latest-github-handoff-pack.json").write_text(__import__("json").dumps({"handoff_dir": str(handoff_dir)}), encoding="utf-8")
            report = bootstrap_ai_assets.build_verify_release_provenance_report(tmp)
            self.assertEqual(report["mode"], "verify-release-provenance")
            self.assertEqual(report["summary"]["status"], "ready")
            self.assertEqual(report["summary"]["fail"], 0)
            self.assertEqual(report["subject"]["computed_archive_sha256"], sha)
            self.assertTrue(report["tree_results"]["github_staging"]["sha256_match"])
            self.assertTrue(report["tree_results"]["github_handoff"]["file_count_match"])

    def test_external_reference_inventory_tracks_required_memory_backend_references(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            docs = tmp / "docs"
            docs.mkdir(parents=True)
            (docs / "external-reference-strategy.md").write_text("# Strategy\n", encoding="utf-8")
            (docs / "reference-memos-local-plugin.md").write_text("# MemOS\nsource/runtime separation adapter skill taxonomy review bridge canonical should not raw\n", encoding="utf-8")
            (docs / "reference-mempalace.md").write_text("# MemPalace\nruntime memory bridge canonical corpus preview review runtime cache not copy avoid raw\n", encoding="utf-8")
            (docs / "reference-letta-memgpt.md").write_text("# Letta / MemGPT\ncore memory archival memory recall memory adapter canonical runtime boundary avoid raw auto preview review\n", encoding="utf-8")
            (docs / "reference-openmemory.md").write_text("# OpenMemory\nshared memory service app client scope MCP adapter canonical preview review runtime boundary should not become raw auto\n", encoding="utf-8")
            (docs / "reference-mcp-memory-servers.md").write_text("# MCP Memory Servers\nprotocol runtime memory tools adapter canonical preview review runtime boundary should not mutate raw auto\n", encoding="utf-8")
            (docs / "reference-supermemory.md").write_text("# Supermemory\nmanaged memory profile projection container tags MCP plugin adapter canonical preview review runtime boundary should not become raw auto\n", encoding="utf-8")
            (docs / "reference-langgraph-memory.md").write_text("# LangGraph Memory\nthread workflow memory checkpoint namespace semantic episodic procedural adapter canonical preview review runtime boundary should not mirror raw auto\n", encoding="utf-8")
            (docs / "reference-open-webui-memory.md").write_text("# Open WebUI Memory\nlocal assistant memory knowledge RAG storage vector adapter canonical preview review runtime boundary should not mirror raw auto\n", encoding="utf-8")
            (docs / "reference-workflow-builders.md").write_text("# Workflow Builders\nDify Flowise Langflow workflow graph prompt RAG tool adapter canonical preview review runtime boundary should not execute raw auto\n", encoding="utf-8")
            (docs / "reference-ide-project-memory.md").write_text("# IDE Project Memory\nCursor Zed IDE project rules instruction files adapter canonical preview review runtime boundary should not index raw auto\n", encoding="utf-8")
            (docs / "reference-assistant-projects.md").write_text("# Assistant Projects\nClaude Projects Custom GPTs hosted project assistant instructions knowledge memory actions sharing adapter canonical preview review runtime boundary should not execute raw auto\n", encoding="utf-8")
            (docs / "reference-hosted-agent-workspace-governance.md").write_text("# Hosted Agent Workspace Governance\nhosted agent workspace governance admin audit retention RBAC permissions policy capability adapter canonical preview review runtime boundary should not execute raw auto\n", encoding="utf-8")
            (docs / "reference-capability-risk-policy-gates.md").write_text("# Capability Risk Policy Gates\nMCP actions hooks custom agents cloud execution capability risk policy gates adapter canonical preview review runtime boundary should not execute raw auto credentials admin-control\n", encoding="utf-8")
            (docs / "reference-project-pack-preview.md").write_text("# Project Pack Preview\nproject pack instructions knowledge actions capability adapter canonical preview review runtime boundary should not execute raw auto credentials\n", encoding="utf-8")
            (docs / "reference-capability-policy-preview.md").write_text("# Capability Policy Preview\ncapability policy preview delta baseline project pack team pack canonical review runtime boundary should not execute raw auto credentials\n", encoding="utf-8")
            (docs / "reference-capability-policy-baseline-apply.md").write_text("# Capability Policy Baseline Apply\nreviewed baseline apply capability policy canonical backup review runtime boundary should not execute raw auto credentials provider admin\n", encoding="utf-8")
            (docs / "reference-capability-policy-candidate-status.md").write_text("# Capability Policy Candidate Status\nreviewed baseline candidate status capability policy canonical preview review runtime boundary should not execute raw auto credentials provider admin\n", encoding="utf-8")
            (docs / "reference-completed-work-review.md").write_text("# Completed Work Review\npost-phase review roadmap alignment external learning avoid closed-door building capability policy canonical runtime boundary should not execute raw auto credentials provider admin\n", encoding="utf-8")
            report = bootstrap_ai_assets.build_external_reference_inventory_report(tmp)
            self.assertEqual(report["mode"], "external-reference-inventory")
            self.assertEqual(report["summary"]["status"], "ready")
            self.assertIn("mempalace", report["summary"]["systems"])
            self.assertIn("memos-local-plugin", report["summary"]["systems"])
            self.assertIn("letta-memgpt", report["summary"]["systems"])
            self.assertIn("openmemory", report["summary"]["systems"])
            self.assertIn("mcp-memory-servers", report["summary"]["systems"])
            self.assertIn("supermemory", report["summary"]["systems"])
            self.assertIn("langgraph-memory", report["summary"]["systems"])
            self.assertIn("open-webui-memory", report["summary"]["systems"])
            self.assertIn("workflow-builders", report["summary"]["systems"])
            self.assertIn("ide-project-memory", report["summary"]["systems"])
            self.assertIn("assistant-projects", report["summary"]["systems"])
            self.assertIn("hosted-agent-workspace-governance", report["summary"]["systems"])
            self.assertIn("capability-risk-policy-gates", report["summary"]["systems"])
            self.assertIn("project-pack-preview", report["summary"]["systems"])
            self.assertIn("capability-policy-preview", report["summary"]["systems"])
            self.assertIn("capability-policy-baseline-apply", report["summary"]["systems"])
            self.assertIn("capability-policy-candidate-status", report["summary"]["systems"])
            self.assertIn("completed-work-review", report["summary"]["systems"])
            self.assertEqual(report["summary"]["reference_docs"], 18)
            check_names = {check["name"] for check in report["checks"]}
            self.assertIn("letta-memgpt-reference", check_names)
            self.assertIn("openmemory-reference", check_names)
            self.assertIn("mcp-memory-servers-reference", check_names)
            self.assertIn("supermemory-reference", check_names)
            self.assertIn("langgraph-memory-reference", check_names)
            self.assertIn("open-webui-memory-reference", check_names)
            self.assertIn("workflow-builders-reference", check_names)
            self.assertIn("ide-project-memory-reference", check_names)
            self.assertIn("assistant-projects-reference", check_names)
            self.assertIn("hosted-agent-workspace-governance-reference", check_names)
            self.assertIn("capability-risk-policy-gates-reference", check_names)
            self.assertIn("project-pack-preview-reference", check_names)
            self.assertIn("capability-policy-preview-reference", check_names)
            self.assertIn("capability-policy-baseline-apply-reference", check_names)
            self.assertIn("capability-policy-candidate-status-reference", check_names)
            self.assertIn("completed-work-review-reference", check_names)
            self.assertTrue(any(ref["mentions_bridge"] for ref in report["references"]))

    def test_build_team_pack_preview_reports_public_safe_sample_pack(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            (tmp / "docs").mkdir(parents=True)
            (tmp / "sample-assets" / "team-pack" / "policies").mkdir(parents=True)
            (tmp / "sample-assets" / "team-pack" / "playbooks").mkdir(parents=True)
            (tmp / "sample-assets" / "team-pack" / "adapters").mkdir(parents=True)
            (tmp / "sample-assets" / "team-pack" / "roles").mkdir(parents=True)
            (tmp / "examples" / "redacted").mkdir(parents=True)
            (tmp / "docs" / "team-grade-packaging.md").write_text("# Team\n", encoding="utf-8")
            (tmp / "sample-assets" / "team-pack" / "README.md").write_text("# Team Pack\n", encoding="utf-8")
            (tmp / "examples" / "redacted" / "team-pack.example.md").write_text("# Example\n", encoding="utf-8")
            (tmp / "sample-assets" / "team-pack" / "team-pack.yaml").write_text(
                "name: example-team-pack\npack_version: v1\nasset_class: public\nshareability: public-safe\nlayers:\n  - team-baseline\nroles:\n  - engineer\npolicies:\n  - policies/engineering-review.md\nplaybooks:\n  - playbooks/release-readiness.md\nadapters:\n  - adapters/shared-instructions.md\napply_policy: human-review-required\n",
                encoding="utf-8",
            )
            (tmp / "sample-assets" / "team-pack" / "policies" / "engineering-review.md").write_text("# Policy\n", encoding="utf-8")
            (tmp / "sample-assets" / "team-pack" / "playbooks" / "release-readiness.md").write_text("# Playbook\n", encoding="utf-8")
            (tmp / "sample-assets" / "team-pack" / "adapters" / "shared-instructions.md").write_text("# Adapter\n", encoding="utf-8")
            (tmp / "sample-assets" / "team-pack" / "roles" / "engineer.md").write_text("# Engineer\n", encoding="utf-8")
            report = bootstrap_ai_assets.build_team_pack_preview_report(tmp)
            self.assertEqual(report["mode"], "team-pack-preview")
            self.assertEqual(report["summary"]["status"], "ready")
            self.assertEqual(report["summary"]["manifests"], 1)
            self.assertEqual(report["summary"]["public_safe_manifests"], 1)
            self.assertEqual(report["summary"]["roles"], 1)
            self.assertEqual(report["manifests"][0]["missing_references"], 0)

    def test_external_reference_backlog_tracks_candidates_and_reviewed_docs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            docs = tmp / "docs"
            docs.mkdir(parents=True)
            (docs / "external-reference-strategy.md").write_text("# Strategy\n", encoding="utf-8")
            (docs / "reference-memos-local-plugin.md").write_text("# MemOS\n", encoding="utf-8")
            (docs / "reference-mempalace.md").write_text("# MemPalace\n", encoding="utf-8")
            (docs / "reference-letta-memgpt.md").write_text("# Letta / MemGPT\n", encoding="utf-8")
            (docs / "reference-openmemory.md").write_text("# OpenMemory\n", encoding="utf-8")
            (docs / "reference-coding-agent-workspace-portability.md").write_text("# Coding agents\n", encoding="utf-8")
            (docs / "reference-agent-workflow-skill-registries.md").write_text("# Agent workflow skills\n", encoding="utf-8")
            (docs / "reference-reproducible-environment-portability.md").write_text("# Reproducible environments\n", encoding="utf-8")
            (docs / "reference-supply-chain-provenance.md").write_text("# Supply-chain provenance\n", encoding="utf-8")
            (docs / "reference-declarative-desired-state.md").write_text("# Declarative desired state\n", encoding="utf-8")
            (docs / "external-reference-backlog.md").write_text(
                "# Backlog\n\n| id | system | category | state | priority | why review | expected output |\n"
                "|---|---|---|---|---|---|---|\n"
                "| memos-local-plugin | MemOS local plugin | memory | reviewed | high | baseline | `docs/reference-memos-local-plugin.md` |\n"
                "| mempalace | MemPalace | bridge | reviewed | high | baseline | `docs/reference-mempalace.md` |\n"
                "| letta-memgpt | Letta / MemGPT | memory | reviewed | high | tiers | `docs/reference-letta-memgpt.md` |\n"
                "| openmemory | OpenMemory | memory service | reviewed | high | boundary | `docs/reference-openmemory.md` |\n"
                "| coding-agent-workspace-portability | Continue.dev / Cline / Roo Code / Aider / OpenHands | coding-agent workspace | reviewed | high | workspace | `docs/reference-coding-agent-workspace-portability.md` |\n"
                "| agent-workflow-skill-registries | CrewAI / AutoGen / Semantic Kernel / Anthropic Agent Skills / LangGraph | agent workflow registries | reviewed | high | skills | `docs/reference-agent-workflow-skill-registries.md` |\n"
                "| reproducible-environment-portability | Nix flakes / Dev Containers / Home Manager / chezmoi / yadm | environment portability | reviewed | high | environments | `docs/reference-reproducible-environment-portability.md` |\n"
                "| supply-chain-provenance | Sigstore / SLSA / in-toto / CycloneDX / SPDX | release provenance | reviewed | high | release evidence | `docs/reference-supply-chain-provenance.md` |\n"
                "| declarative-desired-state | Kubernetes CRD / GitOps / Argo CD / Flux | desired-state reconciliation | reviewed | high | desired state | `docs/reference-declarative-desired-state.md` |\n",
                encoding="utf-8",
            )
            report = bootstrap_ai_assets.build_external_reference_backlog_report(tmp)
            self.assertEqual(report["mode"], "external-reference-backlog")
            self.assertEqual(report["summary"]["status"], "ready")
            self.assertEqual(report["summary"]["items"], 9)
            self.assertEqual(report["summary"]["state_counts"]["reviewed"], 9)
            self.assertEqual(report["summary"].get("high_priority_candidates", 0), 0)
            self.assertEqual(report["missing_expected_docs"], [])
            radar = report["reference_intake_radar"]
            self.assertEqual(radar["status"], "empty")
            self.assertFalse(radar["executes_anything"])
            self.assertFalse(radar["calls_external_services"])
            self.assertFalse(radar["writes_runtime_state"])
            self.assertEqual(radar["adoption_workflow"], ["candidate", "queued", "reviewed", "adopted", "rejected"])
            self.assertEqual(radar["recommended_lanes"], [])
            self.assertFalse(any(lane["lane"] == "coding-agent workspace portability" for lane in radar["recommended_lanes"]))
            self.assertFalse(any(lane["lane"] == "agent workflow and skill registries" for lane in radar["recommended_lanes"]))
            self.assertFalse(any(lane["lane"] == "reproducible environment portability" for lane in radar["recommended_lanes"]))
            self.assertFalse(any(lane["lane"] == "supply-chain provenance and release evidence" for lane in radar["recommended_lanes"]))
            self.assertFalse(any(lane["lane"] == "declarative desired-state reconciliation" for lane in radar["recommended_lanes"]))
            self.assertIn("public conceptual notes", radar["public_safe_boundary"])
            self.assertIn("no network", radar["non_execution_boundary"])
            markdown = bootstrap_ai_assets.markdown_for_external_reference_backlog(report)
            self.assertIn("## Reference intake radar", markdown)
            self.assertIn("Status: empty", markdown)
            self.assertIn("executes_anything: False", markdown)

    def test_capability_risk_inventory_classifies_connectors_and_team_pack_assets(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            (tmp / "adapters" / "registry").mkdir(parents=True)
            (tmp / "sample-assets" / "team-pack" / "policies").mkdir(parents=True)
            (tmp / "sample-assets" / "team-pack" / "playbooks").mkdir(parents=True)
            (tmp / "sample-assets" / "team-pack" / "adapters").mkdir(parents=True)
            (tmp / "sample-assets" / "team-pack" / "roles").mkdir(parents=True)
            (tmp / "docs").mkdir(parents=True)
            (tmp / "examples" / "redacted").mkdir(parents=True)
            (tmp / "docs" / "team-grade-packaging.md").write_text("# Team\n", encoding="utf-8")
            (tmp / "sample-assets" / "team-pack" / "README.md").write_text("# Team Pack\n", encoding="utf-8")
            (tmp / "examples" / "redacted" / "team-pack.example.md").write_text("# Example\n", encoding="utf-8")
            (tmp / "sample-assets" / "team-pack" / "team-pack.yaml").write_text(
                "name: example-team-pack\npack_version: v1\nasset_class: public\nshareability: public-safe\nlayers:\n  - team-baseline\nroles:\n  - engineer\npolicies:\n  - policies/engineering-review.md\nplaybooks:\n  - playbooks/release-readiness.md\nadapters:\n  - adapters/shared-instructions.md\napply_policy: human-review-required\n",
                encoding="utf-8",
            )
            (tmp / "sample-assets" / "team-pack" / "policies" / "engineering-review.md").write_text("# Policy\n", encoding="utf-8")
            (tmp / "sample-assets" / "team-pack" / "playbooks" / "release-readiness.md").write_text("# Playbook\n", encoding="utf-8")
            (tmp / "sample-assets" / "team-pack" / "adapters" / "shared-instructions.md").write_text("# Adapter\n", encoding="utf-8")
            (tmp / "sample-assets" / "team-pack" / "roles" / "engineer.md").write_text("# Engineer\n", encoding="utf-8")
            (tmp / "adapters" / "registry" / "runtime.yaml").write_text(
                "name: runtime-adapter\nadapter_version: 1\nruntime: demo\ncanonical_sources:\n  - adapters/demo/source.md\nlive_targets:\n  - ~/.demo/config.yaml\nconnector:\n  import: read-file\n  export: write-file\n  notes:\n    - Uses credential reference names only.\napply_policy: human-review-required\n",
                encoding="utf-8",
            )

            report = bootstrap_ai_assets.build_capability_risk_inventory_report(tmp)

            self.assertEqual(report["mode"], "capability-risk-inventory")
            self.assertEqual(report["summary"]["status"], "ready")
            self.assertFalse(report["summary"]["executes_anything"])
            self.assertGreaterEqual(report["summary"]["capabilities"], 3)
            self.assertIn("text-only", report["summary"]["risk_class_counts"])
            self.assertIn("read-only-data", report["summary"]["risk_class_counts"])
            self.assertIn("write-files", report["summary"]["risk_class_counts"])
            self.assertIn("review-required", report["summary"]["policy_outcome_counts"])
            names = {item["name"] for item in report["capabilities"]}
            self.assertIn("runtime-adapter:import:read-file", names)
            self.assertIn("runtime-adapter:export:write-file", names)
            self.assertTrue(any(item["kind"] == "team-pack" for item in report["capabilities"]))

    def test_capability_policy_preview_reports_added_removed_and_risk_upgrades(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            root = tmp / "sample-assets" / "project-pack"
            (root / "instructions").mkdir(parents=True)
            (tmp / "sample-assets" / "capability-policy").mkdir(parents=True)
            (root / "project-pack.yaml").write_text(
                "name: example-project-pack\npack_version: v1\nasset_class: public\nshareability: public-safe\nproject_scope: sample-product\nvisibility: project\ninstructions:\n  - instructions/project.md\ncapabilities:\n  - name: project-guidance\n    risk_class: text-only\n    policy_outcome: allow-preview\n  - name: read-context\n    risk_class: read-only-data\n    policy_outcome: allow-preview\n  - name: deploy-hook\n    risk_class: code-execution\n    policy_outcome: review-required\napply_policy: human-review-required\n",
                encoding="utf-8",
            )
            (root / "instructions" / "project.md").write_text("# Instructions\n", encoding="utf-8")
            (tmp / "sample-assets" / "capability-policy" / "baseline.yaml").write_text(
                "capabilities:\n  - name: example-project-pack:project-guidance\n    risk_class: text-only\n    policy_outcome: allow-preview\n  - name: example-project-pack:deploy-hook\n    risk_class: read-only-data\n    policy_outcome: allow-preview\n  - name: example-project-pack:legacy-action\n    risk_class: read-only-data\n    policy_outcome: allow-preview\n",
                encoding="utf-8",
            )

            report = bootstrap_ai_assets.build_capability_policy_preview_report(tmp)

            self.assertEqual(report["mode"], "capability-policy-preview")
            self.assertEqual(report["summary"]["status"], "needs-review")
            self.assertFalse(report["summary"]["executes_anything"])
            self.assertEqual(report["summary"]["added"], 1)
            self.assertEqual(report["summary"]["removed"], 1)
            self.assertEqual(report["summary"]["risk_upgrades"], 1)
            self.assertIn("review-required", report["summary"]["policy_outcome_counts"])
            self.assertEqual(report["deltas"]["added"][0]["name"], "example-project-pack:read-context")
            self.assertEqual(report["deltas"]["removed"][0]["name"], "example-project-pack:legacy-action")
            self.assertEqual(report["deltas"]["risk_upgrades"][0]["name"], "example-project-pack:deploy-hook")

    def test_capability_policy_candidate_generation_writes_template_not_reviewed_baseline(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            root = tmp / "sample-assets" / "project-pack"
            (root / "instructions").mkdir(parents=True)
            (tmp / "sample-assets" / "capability-policy").mkdir(parents=True)
            (root / "project-pack.yaml").write_text(
                "name: example-project-pack\npack_version: v1\nasset_class: public\nshareability: public-safe\nproject_scope: sample-product\nvisibility: project\ninstructions:\n  - instructions/project.md\ncapabilities:\n  - name: project-guidance\n    risk_class: code-execution\n    policy_outcome: review-required\n  - name: deploy-hook\n    risk_class: code-execution\n    policy_outcome: review-required\napply_policy: human-review-required\n",
                encoding="utf-8",
            )
            (root / "instructions" / "project.md").write_text("# Instructions\n", encoding="utf-8")
            (tmp / "sample-assets" / "capability-policy" / "baseline.yaml").write_text(
                "capabilities:\n  - name: example-project-pack:project-guidance\n    risk_class: text-only\n    policy_outcome: allow-preview\n  - name: example-project-pack:legacy-action\n    risk_class: read-only-data\n    policy_outcome: allow-preview\n",
                encoding="utf-8",
            )

            report = bootstrap_ai_assets.build_capability_policy_candidate_generation_report(tmp)

            template = tmp / "bootstrap" / "candidates" / "capability-policy" / "reviewed-baseline.yaml.template"
            reviewed = tmp / "bootstrap" / "candidates" / "capability-policy" / "reviewed-baseline.yaml"
            template_text = template.read_text(encoding="utf-8")
            self.assertEqual(report["mode"], "capability-policy-candidate-generation")
            self.assertEqual(report["summary"]["status"], "generated")
            self.assertFalse(report["summary"]["executes_anything"])
            self.assertEqual(report["summary"]["templates_written"], 1)
            self.assertEqual(report["summary"]["reviewed_baselines_written"], 0)
            self.assertEqual(report["summary"]["added"], 1)
            self.assertEqual(report["summary"]["removed"], 1)
            self.assertEqual(report["summary"]["risk_upgrades"], 1)
            self.assertTrue(template.is_file())
            self.assertFalse(reviewed.exists())
            self.assertIn("Copy this file to reviewed-baseline.yaml only after human review", template_text)
            self.assertIn("example-project-pack:deploy-hook", template_text)
            self.assertIn("risk_class: code-execution", template_text)
            self.assertIn("policy_outcome: review-required", template_text)
            self.assertNotIn("example-project-pack:legacy-action", template_text)
            markdown = bootstrap_ai_assets.markdown_for_capability_policy_candidate_generation(report)
            self.assertIn("reviewed-baseline.yaml.template", markdown)
            self.assertIn("human review", markdown)
            self.assertIn("Executes anything: False", markdown)

    def test_capability_policy_candidate_status_reports_review_readiness_without_writing_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            root = tmp / "sample-assets" / "project-pack"
            candidate_dir = tmp / "bootstrap" / "candidates" / "capability-policy"
            (root / "instructions").mkdir(parents=True)
            (tmp / "sample-assets" / "capability-policy").mkdir(parents=True)
            candidate_dir.mkdir(parents=True)
            (root / "project-pack.yaml").write_text(
                "name: example-project-pack\npack_version: v1\nasset_class: public\nshareability: public-safe\nproject_scope: sample-product\nvisibility: project\ninstructions:\n  - instructions/project.md\ncapabilities:\n  - name: project-guidance\n    risk_class: text-only\n    policy_outcome: allow-preview\n  - name: deploy-hook\n    risk_class: code-execution\n    policy_outcome: review-required\n  - name: read-context\n    risk_class: read-only-data\n    policy_outcome: allow-preview\napply_policy: human-review-required\n",
                encoding="utf-8",
            )
            (root / "instructions" / "project.md").write_text("# Instructions\n", encoding="utf-8")
            (tmp / "sample-assets" / "capability-policy" / "baseline.yaml").write_text(
                "capabilities:\n  - name: example-project-pack:project-guidance\n    risk_class: text-only\n    policy_outcome: allow-preview\n  - name: example-project-pack:deploy-hook\n    risk_class: read-only-data\n    policy_outcome: allow-preview\n  - name: example-project-pack:legacy-action\n    risk_class: read-only-data\n    policy_outcome: allow-preview\n",
                encoding="utf-8",
            )
            template = candidate_dir / "reviewed-baseline.yaml.template"
            reviewed = candidate_dir / "reviewed-baseline.yaml"
            template.write_text(
                "# Candidate capability policy baseline. Copy this file to reviewed-baseline.yaml only after human review.\ncapabilities:\n  - name: example-project-pack:project-guidance\n    risk_class: text-only\n    policy_outcome: allow-preview\n  - name: example-project-pack:deploy-hook\n    risk_class: code-execution\n    policy_outcome: review-required\n  - name: example-project-pack:read-context\n    risk_class: read-only-data\n    policy_outcome: allow-preview\n",
                encoding="utf-8",
            )
            template_before = template.read_text(encoding="utf-8")

            report = bootstrap_ai_assets.build_capability_policy_candidate_status_report(tmp)

            self.assertEqual(report["mode"], "capability-policy-candidate-status")
            self.assertEqual(report["summary"]["status"], "needs-human-review")
            self.assertFalse(report["summary"]["executes_anything"])
            self.assertTrue(report["summary"]["template_exists"])
            self.assertFalse(report["summary"]["reviewed_baseline_exists"])
            self.assertFalse(report["summary"]["ready_for_apply"])
            self.assertEqual(report["summary"]["apply_readiness"], "needs-human-review")
            self.assertEqual(report["summary"]["templates_written"], 0)
            self.assertEqual(report["summary"]["reviewed_baselines_written"], 0)
            self.assertEqual(report["summary"]["added"], 1)
            self.assertEqual(report["summary"]["removed"], 1)
            self.assertEqual(report["summary"]["risk_upgrades"], 1)
            self.assertIn("review-required", report["summary"]["policy_outcome_counts"])
            self.assertIn("code-execution", report["summary"]["risk_class_counts"])
            guidance = report["reviewer_guidance"]
            self.assertEqual(guidance["status"], "needs-human-review")
            self.assertEqual(guidance["next_action"], "human-review-template")
            self.assertFalse(guidance["commands"]["copy_template_to_reviewed"]["executes"])
            self.assertFalse(guidance["commands"]["status_after_review"]["executes"])
            self.assertFalse(guidance["commands"]["apply_when_ready"]["executes"])
            self.assertIn("cp bootstrap/candidates/capability-policy/reviewed-baseline.yaml.template bootstrap/candidates/capability-policy/reviewed-baseline.yaml", guidance["commands"]["copy_template_to_reviewed"]["command"])
            checklist_text = "\n".join(guidance["checklist"])
            self.assertIn("added/removed/changed", checklist_text)
            self.assertIn("risk upgrades", checklist_text)
            self.assertIn("credential values", checklist_text)
            self.assertIn("do not execute", checklist_text)
            audit = report["review_handoff_audit"]
            self.assertEqual(audit["status"], "needs-human-review")
            self.assertFalse(audit["executes_anything"])
            self.assertFalse(audit["writes_anything"])
            self.assertEqual(audit["evidence"]["template_sha256"], bootstrap_ai_assets.sha256_text(template))
            self.assertIsNone(audit["evidence"]["reviewed_baseline_sha256"])
            self.assertFalse(audit["preflight"]["ready_for_apply"])
            self.assertIn("human-reviewed-baseline-present", [item["name"] for item in audit["preflight"]["checklist"]])
            self.assertIn("candidate status report", "\n".join(audit["handoff_steps"]))
            self.assertTrue(template.is_file())
            self.assertEqual(template.read_text(encoding="utf-8"), template_before)
            self.assertFalse(reviewed.exists())
            markdown = bootstrap_ai_assets.markdown_for_capability_policy_candidate_status(report)
            self.assertIn("reviewed-baseline.yaml.template", markdown)
            self.assertIn("reviewed-baseline.yaml", markdown)
            self.assertIn("needs human review", markdown)
            self.assertIn("does not apply", markdown)
            self.assertIn("## Reviewer guidance", markdown)
            self.assertIn("Next action: human-review-template", markdown)
            self.assertIn("Command drafts are non-executing", markdown)
            self.assertIn("## Review handoff audit", markdown)
            self.assertIn("Template SHA256", markdown)
            self.assertIn("human-reviewed-baseline-present", markdown)
            self.assertIn("Writes anything: False", markdown)
            self.assertIn("Executes anything: False", markdown)

    def test_capability_policy_baseline_apply_writes_only_reviewed_baseline(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            baseline = tmp / "sample-assets" / "capability-policy" / "baseline.yaml"
            reviewed = tmp / "bootstrap" / "candidates" / "capability-policy" / "reviewed-baseline.yaml"
            baseline.parent.mkdir(parents=True)
            reviewed.parent.mkdir(parents=True)
            baseline.write_text(
                "capabilities:\n  - name: old-capability\n    risk_class: text-only\n    policy_outcome: allow-preview\n",
                encoding="utf-8",
            )
            reviewed.write_text(
                "capabilities:\n  - name: reviewed-capability\n    risk_class: read-only-data\n    policy_outcome: allow-preview\n",
                encoding="utf-8",
            )

            report = bootstrap_ai_assets.execute_capability_policy_baseline_apply(tmp)

            self.assertEqual(report["mode"], "capability-policy-baseline-apply")
            self.assertEqual(report["summary"]["status"], "applied")
            self.assertFalse(report["summary"]["executes_anything"])
            self.assertEqual(report["summary"]["applied"], 1)
            self.assertEqual(report["summary"]["skipped"], 0)
            self.assertIn("reviewed-capability", baseline.read_text(encoding="utf-8"))
            self.assertTrue(Path(report["backup_path"]).is_file())

    def test_completed_work_review_checks_alignment_safety_and_external_learning(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            docs = tmp / "docs"
            reports = tmp / "bootstrap" / "reports"
            docs.mkdir(parents=True)
            reports.mkdir(parents=True)
            (docs / "public-roadmap.md").write_text(
                "# Roadmap\n\n## Vision\nportable AI assets layer across agents models clients machines\n\n## Product Thesis\nnot another agent runtime canonical memory adapter projections safe migration reviewable reconciliation\n\n## Non-Goals\nnot a workflow builder not a memory backend\n\n### Phase 62 — Reviewed capability policy baseline apply ✅\nreviewed apply baseline only\n\n### Phase 63 — Completed work review gate ✅\npost-phase review alignment safety external learning\n",
                encoding="utf-8",
            )
            (docs / "external-reference-backlog.md").write_text(
                "# Backlog\n\n| id | system | category | state | priority | why review | expected output |\n"
                "|---|---|---|---|---|---|---|\n"
                "| memos-local-plugin | MemOS | memory | reviewed | high | learn | `docs/reference-memos-local-plugin.md` |\n"
                "| capability-policy-candidate-generation | Candidate generation | governance | candidate | high | template | `docs/reference-capability-policy-candidate-generation.md` |\n",
                encoding="utf-8",
            )
            (docs / "reference-memos-local-plugin.md").write_text("# MemOS\nadopt avoid boundary raw runtime\n", encoding="utf-8")
            (reports / "latest-release-readiness.json").write_text(__import__("json").dumps({"summary": {"readiness": "ready", "fail": 0, "warn": 0}}), encoding="utf-8")
            (reports / "latest-public-safety-scan.json").write_text(__import__("json").dumps({"summary": {"status": "pass", "blockers": 0, "warnings": 0}}), encoding="utf-8")
            (reports / "latest-external-reference-inventory.json").write_text(__import__("json").dumps({"summary": {"status": "ready", "reference_docs": 1, "systems": ["memos-local-plugin"]}}), encoding="utf-8")
            (reports / "latest-capability-policy-preview.json").write_text(__import__("json").dumps({"summary": {"status": "ready", "executes_anything": False, "risk_upgrades": 0}}), encoding="utf-8")
            (reports / "latest-capability-policy-candidate-generation.json").write_text(__import__("json").dumps({"summary": {"status": "generated", "executes_anything": False, "templates_written": 1, "reviewed_baselines_written": 0}}), encoding="utf-8")
            (reports / "latest-capability-policy-candidate-status.json").write_text(__import__("json").dumps({"summary": {"status": "needs-human-review", "apply_readiness": "needs-human-review", "executes_anything": False, "templates_written": 0, "reviewed_baselines_written": 0}}), encoding="utf-8")
            (reports / "latest-capability-policy-baseline-apply.json").write_text(__import__("json").dumps({"summary": {"status": "skipped", "executes_anything": False, "fail": 0}}), encoding="utf-8")

            report = bootstrap_ai_assets.build_completed_work_review_report(tmp)

            self.assertEqual(report["mode"], "completed-work-review")
            self.assertEqual(report["summary"]["status"], "aligned")
            self.assertFalse(report["summary"]["executes_anything"])
            self.assertEqual(report["summary"]["fail"], 0)
            self.assertEqual(report["review_axes"]["safety"]["status"], "pass")
            self.assertEqual(report["review_axes"]["vision_alignment"]["status"], "pass")
            self.assertEqual(report["review_axes"]["external_learning"]["status"], "pass")
            self.assertIn("capability-policy-candidate-generation", report["next_recommended_candidates"])
            self.assertIn("latest_completed_phase=Phase 63", report["review_axes"]["vision_alignment"]["evidence"])
            self.assertIn("capability-policy-candidate-generation", report["latest_report_summaries"])
            self.assertFalse(report["latest_report_summaries"]["capability-policy-candidate-generation"]["executes_anything"])
            self.assertIn("capability-policy-candidate-generation: executes_anything=False", report["review_axes"]["safety"]["evidence"])

    def test_completed_work_review_blocks_phase103_without_valid_phase102_report_evidence(self):
        valid_phase102_summary = {
            "status": "syntax-invalid-failclosed",
            "syntax_invalid_evidence_blocks_completion": True,
            "agent_side_complete": False,
            "machine_side_complete": False,
            "requires_user_code_review": False,
            "external_owner_decision_required": True,
            "human_feedback_pending": True,
            "shares_anything": False,
            "sends_invitations": False,
            "writes_anything": False,
            "writes": 0,
            "executes_anything": False,
            "remote_mutation_allowed": False,
            "credential_validation_allowed": False,
            "auto_approves_release": False,
            "remote_issues_created": 0,
            "issue_backlog_mutation_allowed": False,
            "checks": 5,
            "pass": 5,
            "fail": 0,
            "warn": 0,
        }
        invalid_phase102_summary_with_bool_warn = dict(valid_phase102_summary)
        invalid_phase102_summary_with_bool_warn["warn"] = False
        for phase102_payload in [
            None,
            {"mode": "wrong-mode", "summary": valid_phase102_summary},
            {"mode": "agent-complete-syntax-invalid-evidence-failclosed-review", "summary": invalid_phase102_summary_with_bool_warn},
        ]:
            with self.subTest(phase102_payload=phase102_payload):
                with tempfile.TemporaryDirectory() as tmpdir:
                    tmp = Path(tmpdir)
                    docs = tmp / "docs"
                    reports = tmp / "bootstrap" / "reports"
                    docs.mkdir(parents=True)
                    reports.mkdir(parents=True)
                    (docs / "public-roadmap.md").write_text(
                        "# Roadmap\n\n## Vision\nportable AI assets layer across agents models clients machines\n\n## Product Thesis\nnot another agent runtime canonical memory adapter projections safe migration reviewable reconciliation\n\n"
                        "### Phase 103 — Agent-complete Phase102 rollup evidence fail-closed review ✅\n"
                        "Confirms downstream completed-work and agent-complete rollups require valid Phase102 report evidence before continuing.\n",
                        encoding="utf-8",
                    )
                    (docs / "external-reference-backlog.md").write_text(
                        "# Backlog\n\n| id | system | category | state | priority | why review | expected output |\n"
                        "|---|---|---|---|---|---|---|\n"
                        "| memos-local-plugin | MemOS | memory | reviewed | high | learn | `docs/reference-memos-local-plugin.md` |\n",
                        encoding="utf-8",
                    )
                    (docs / "reference-memos-local-plugin.md").write_text("# MemOS\nadopt avoid boundary raw runtime\n", encoding="utf-8")
                    (reports / "latest-release-readiness.json").write_text(__import__("json").dumps({"summary": {"readiness": "ready", "fail": 0, "warn": 0}}), encoding="utf-8")
                    (reports / "latest-public-safety-scan.json").write_text(__import__("json").dumps({"summary": {"status": "pass", "blockers": 0, "warnings": 0}}), encoding="utf-8")
                    (reports / "latest-external-reference-inventory.json").write_text(__import__("json").dumps({"summary": {"status": "ready", "reference_docs": 1, "systems": ["memos-local-plugin"]}}), encoding="utf-8")
                    (reports / "latest-capability-policy-preview.json").write_text(__import__("json").dumps({"summary": {"status": "ready", "executes_anything": False, "risk_upgrades": 0}}), encoding="utf-8")
                    (reports / "latest-capability-policy-candidate-generation.json").write_text(__import__("json").dumps({"summary": {"status": "generated", "executes_anything": False, "templates_written": 1, "reviewed_baselines_written": 0}}), encoding="utf-8")
                    (reports / "latest-capability-policy-candidate-status.json").write_text(__import__("json").dumps({"summary": {"status": "needs-human-review", "apply_readiness": "needs-human-review", "executes_anything": False, "templates_written": 0, "reviewed_baselines_written": 0}}), encoding="utf-8")
                    (reports / "latest-capability-policy-baseline-apply.json").write_text(__import__("json").dumps({"summary": {"status": "skipped", "executes_anything": False, "fail": 0}}), encoding="utf-8")
                    if phase102_payload is not None:
                        (reports / "latest-agent-complete-syntax-invalid-evidence-failclosed-review.json").write_text(__import__("json").dumps(phase102_payload), encoding="utf-8")

                    report = bootstrap_ai_assets.build_completed_work_review_report(tmp)

                    self.assertEqual(report["summary"]["status"], "blocked")
                    self.assertEqual(report["review_axes"]["agent_completion_evidence"]["status"], "fail")
                    self.assertIn("phase102_report_evidence_valid=False", report["review_axes"]["agent_completion_evidence"]["evidence"])
                    self.assertEqual(report["summary"]["fail"], 1)

    def test_project_pack_preview_reports_capability_deltas_and_public_safe_sample(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            root = tmp / "sample-assets" / "project-pack"
            for rel in ["instructions", "knowledge", "actions", "adapters"]:
                (root / rel).mkdir(parents=True)
            (tmp / "docs").mkdir(parents=True)
            (tmp / "examples" / "redacted").mkdir(parents=True)
            (tmp / "docs" / "project-pack-preview.md").write_text("# Project Pack Preview\n", encoding="utf-8")
            (tmp / "sample-assets" / "project-pack" / "README.md").write_text("# Project Pack\n", encoding="utf-8")
            (tmp / "examples" / "redacted" / "project-pack.example.md").write_text("# Project Example\n", encoding="utf-8")
            (root / "project-pack.yaml").write_text(
                "name: example-project-pack\npack_version: v1\nasset_class: public\nshareability: public-safe\nproject_scope: sample-product\nvisibility: project\ninstructions:\n  - instructions/project.md\nknowledge_sources:\n  - knowledge/architecture.md\nactions:\n  - actions/read-context.yaml\nadapters:\n  - adapters/project-instructions.md\ncapabilities:\n  - name: project-guidance\n    risk_class: text-only\n    policy_outcome: allow-preview\n  - name: read-context\n    risk_class: read-only-data\n    policy_outcome: allow-preview\napply_policy: human-review-required\n",
                encoding="utf-8",
            )
            (root / "instructions" / "project.md").write_text("# Instructions\n", encoding="utf-8")
            (root / "knowledge" / "architecture.md").write_text("# Architecture\n", encoding="utf-8")
            (root / "actions" / "read-context.yaml").write_text("name: read-context\n", encoding="utf-8")
            (root / "adapters" / "project-instructions.md").write_text("# Adapter\n", encoding="utf-8")

            report = bootstrap_ai_assets.build_project_pack_preview_report(tmp)

            self.assertEqual(report["mode"], "project-pack-preview")
            self.assertEqual(report["summary"]["status"], "ready")
            self.assertEqual(report["summary"]["manifests"], 1)
            self.assertEqual(report["summary"]["public_safe_manifests"], 1)
            self.assertEqual(report["summary"]["capabilities"], 2)
            self.assertIn("text-only", report["summary"]["risk_class_counts"])
            self.assertIn("read-only-data", report["summary"]["risk_class_counts"])
            self.assertEqual(report["manifests"][0]["missing_references"], 0)
            self.assertFalse(report["summary"]["executes_anything"])

    def test_build_public_safety_scan_flags_secret_like_content_and_private_paths(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            (tmp / "docs").mkdir(parents=True)
            (tmp / "README.md").write_text("# Demo\n", encoding="utf-8")
            (tmp / "docs" / "safe.md").write_text("Use /Users/example/.demo only.\n", encoding="utf-8")
            private_home = "/Users/" + "alice" + "/.demo"
            (tmp / "docs" / "unsafe.md").write_text(
                f"private path {private_home}\napi_key: abcdefghijklmnop\n",
                encoding="utf-8",
            )
            (tmp / "docs" / "redacted.md").write_text("api_key: [REDACTED]", encoding="utf-8")
            (tmp / "bin").mkdir(parents=True)
            (tmp / "bin" / "paa").write_text("#!/usr/bin/env bash\ntoken: abcdefghijklmnop\n", encoding="utf-8")
            report = bootstrap_ai_assets.build_public_safety_scan_report(tmp)
            self.assertEqual(report["mode"], "public-safety-scan")
            self.assertEqual(report["summary"]["blockers"], 2)
            self.assertEqual(report["summary"]["warnings"], 1)
            finding_paths = {finding["path"] for finding in report["findings"]}
            self.assertIn("bin/paa", finding_paths)
            finding_types = {finding["type"] for finding in report["findings"]}
            self.assertIn("api-key-assignment", finding_types)
            self.assertIn("private-macos-home", finding_types)

    def test_build_release_readiness_reports_missing_required_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            (tmp / "README.md").write_text("# Demo\n", encoding="utf-8")
            report = bootstrap_ai_assets.build_release_readiness_report(tmp)
            self.assertEqual(report["mode"], "release-readiness")
            self.assertEqual(report["summary"]["readiness"], "blocked")
            self.assertGreater(report["summary"]["fail"], 0)
            self.assertTrue(any(check["name"] == "required:CONTRIBUTING.md" and check["status"] == "fail" for check in report["checks"]))

    def test_markdown_for_public_safety_scan_includes_findings(self):
        report = {
            "generated_at": "2026-04-24T00:00:00",
            "engine_root": "/engine",
            "root": "/assets",
            "summary": {"status": "blocked", "scanned_files": 1, "findings": 1, "blockers": 1, "warnings": 0},
            "findings": [{"severity": "blocker", "path": "docs/x.md", "line": 1, "type": "api-key-assignment", "excerpt": "api_key: demo"}],
            "recommendations": ["Fix blockers"],
        }
        text = bootstrap_ai_assets.markdown_for_public_safety_scan(report)
        self.assertIn("Public Safety Scan", text)
        self.assertIn("docs/x.md:1", text)

    def test_build_refresh_canonical_assets_report_runs_export_and_refresh_scripts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            setup_dir = tmp / "bootstrap" / "setup"
            setup_dir.mkdir(parents=True)
            export_script = setup_dir / "export-canonical-profile.sh"
            refresh_script = setup_dir / "refresh-canonical-memory.sh"
            export_script.write_text("#!/usr/bin/env bash\necho export-ok\n", encoding="utf-8")
            refresh_script.write_text("#!/usr/bin/env bash\necho refresh-ok\n", encoding="utf-8")
            export_script.chmod(0o755)
            refresh_script.chmod(0o755)
            report = bootstrap_ai_assets.build_refresh_canonical_assets_report(tmp)
            self.assertEqual(report["summary"]["successful_steps"], 2)
            self.assertEqual(report["steps"][0]["name"], "export-canonical-profile")
            self.assertEqual(report["steps"][0]["status"], "ok")
            self.assertIn("export-ok", report["steps"][0]["output"])
            self.assertEqual(report["steps"][1]["name"], "refresh-canonical-memory")
            self.assertEqual(report["steps"][1]["status"], "ok")
            self.assertIn("refresh-ok", report["steps"][1]["output"])

    def test_resolve_runtime_paths_uses_config_file_for_private_asset_root(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            config_path = tmp / 'config.yaml'
            config_path.write_text(
                "engine_root: ~/portable-ai-assets-engine\n"
                "asset_root: ~/AI-Assets-private\n"
                "asset_repo_remote: git@example.com:private/ai-assets.git\n"
                "default_sync_mode: review-before-commit\n"
                "allow_auto_commit: false\n",
                encoding='utf-8',
            )
            runtime_paths = bootstrap_ai_assets.resolve_runtime_paths(config_path=str(config_path), script_path=MODULE_PATH)
            self.assertEqual(runtime_paths['asset_root'], str(Path('~/AI-Assets-private').expanduser().resolve()))
            self.assertEqual(runtime_paths['engine_root'], str(Path('~/portable-ai-assets-engine').expanduser().resolve()))
            self.assertEqual(runtime_paths['asset_repo_remote'], 'git@example.com:private/ai-assets.git')
            self.assertEqual(runtime_paths['default_sync_mode'], 'review-before-commit')
            self.assertFalse(runtime_paths['allow_auto_commit'])

    def test_resolve_runtime_paths_defaults_asset_root_to_engine_root_without_config(self):
        runtime_paths = bootstrap_ai_assets.resolve_runtime_paths(config_path='/tmp/does-not-exist.yaml', engine_root_override='/tmp/demo-engine', script_path=MODULE_PATH)
        self.assertEqual(runtime_paths['engine_root'], str(Path('/tmp/demo-engine').resolve()))
        self.assertEqual(runtime_paths['asset_root'], str(Path('/tmp/demo-engine').resolve()))

    def test_initialize_private_assets_repo_creates_scaffold_and_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            asset_root = tmp / 'private-assets'
            config_path = tmp / 'config' / 'config.yaml'
            report = bootstrap_ai_assets.initialize_private_assets_repo(
                asset_root,
                config_path=config_path,
                asset_repo_remote='git@example.com:private/ai-assets.git',
                initialize_git=False,
            )
            self.assertEqual(report['mode'], 'init-private-assets')
            self.assertTrue((asset_root / 'README.md').is_file())
            self.assertTrue((asset_root / 'GIT-POLICY.md').is_file())
            self.assertTrue((asset_root / '.gitignore').is_file())
            self.assertTrue((asset_root / 'memory' / 'profile').is_dir())
            self.assertTrue((asset_root / 'memory' / 'projects').is_dir())
            self.assertTrue((asset_root / 'adapters' / 'claude').is_dir())
            self.assertTrue((asset_root / 'bootstrap' / 'reports').is_dir())
            config_text = config_path.read_text(encoding='utf-8')
            self.assertIn(f'asset_root: {asset_root.resolve()}', config_text)
            self.assertIn('asset_repo_remote: git@example.com:private/ai-assets.git', config_text)
            self.assertEqual(report['summary']['git_status'], 'skipped')
            self.assertIn(report['summary']['config_status'], {'created', 'unchanged'})

    def test_parse_git_status_short_categorizes_private_asset_changes(self):
        entries = bootstrap_ai_assets.parse_git_status_short(
            ' M memory/profile/user.md\n?? memory/projects/demo.md\nA  adapters/claude/instructions.md\n M stack/tools/hermes.yaml\n'
        )
        self.assertEqual([entry['category'] for entry in entries], ['memory_profile', 'memory_projects', 'adapters', 'stack'])
        self.assertEqual(entries[1]['status'], '??')

    def test_build_private_assets_status_report_handles_non_git_root(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            report = bootstrap_ai_assets.build_private_assets_status_report(Path(tmpdir))
            self.assertEqual(report['mode'], 'private-assets-status')
            self.assertTrue(report['git']['root_exists'])
            self.assertFalse(report['git']['is_git_repo'])
            self.assertIn('Initialize Git', ' '.join(report['recommendations']))

    def test_build_memos_health_report_is_report_only(self):
        def fake_probe(args, timeout=8):
            return {'available': True, 'path': f'/bin/{args[0]}', 'ok': True, 'timed_out': False, 'returncode': 0, 'output': 'ok'}
        with tempfile.TemporaryDirectory() as tmpdir, patch.object(bootstrap_ai_assets, 'run_probe_command', side_effect=fake_probe):
            report = bootstrap_ai_assets.build_memos_health_report(Path(tmpdir))
            self.assertEqual(report['mode'], 'memos-health')
            self.assertIn('node_version', report['commands'])
            self.assertIn('hermes_runtime_root', report['paths'])
            self.assertIn('ready_for_test_profile_install', report['summary'])
            self.assertTrue(report['recommendations'])

    def test_build_memos_import_preview_handles_missing_db(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            report = bootstrap_ai_assets.build_memos_import_preview_report(Path(tmpdir))
            self.assertEqual(report['mode'], 'memos-import-preview')
            self.assertFalse(report['memos']['db_exists'])
            self.assertEqual(report['summary']['candidate_outputs'], 0)
            self.assertTrue(report['errors'])
            self.assertIn('read-only', ' '.join(report['recommendations']))

    def test_memos_candidate_outputs_maps_known_tables(self):
        candidates = bootstrap_ai_assets._memos_candidate_outputs({'traces': 1, 'episodes': 1, 'policies': 1, 'world_model': 1, 'skills': 1, 'decision_repairs': 1})
        paths = [item['candidate_path'] for item in candidates]
        self.assertIn('memory/projects/<reviewed-from-memos>.md', paths)
        self.assertIn('memory/policies/<reviewed-policy>.md', paths)
        self.assertIn('memory/world-models/<reviewed-world-model>.md', paths)
        self.assertIn('skills/<portable-skill>.yaml', paths)

    def test_detect_manifest_schema_identifies_portable_skill_manifest(self):
        self.assertEqual(
            bootstrap_ai_assets.detect_manifest_schema(Path('/Users/example/AI-Assets/sample-assets/skills/example.yaml')),
            'portable-skill-manifest-v1',
        )
        self.assertEqual(
            bootstrap_ai_assets.detect_manifest_schema(Path('/Users/example/AI-Assets/skills/review-before-sync.yaml')),
            'portable-skill-manifest-v1',
        )

    def test_build_skills_inventory_report_summarizes_lifecycle(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            schema_dir = tmp / 'schemas'
            skill_dir = tmp / 'sample-assets' / 'skills'
            schema_dir.mkdir(parents=True)
            skill_dir.mkdir(parents=True)
            (schema_dir / 'portable-skill-manifest-v1.json').write_text(
                __import__('json').dumps(bootstrap_ai_assets.DEFAULT_SCHEMA_DEFINITIONS['portable-skill-manifest-v1']),
                encoding='utf-8',
            )
            (skill_dir / 'example.yaml').write_text(
                'name: example-skill\n'
                'skill_version: v1\n'
                'status: probationary\n'
                'confidence: medium\n'
                'description: Example portable skill.\n'
                'trigger: When an example is needed.\n'
                'procedure:\n'
                '  - Do the safe thing.\n'
                'verification:\n'
                '  - Check the report.\n'
                'boundaries:\n'
                '  - Do not write runtime files.\n'
                'source_evidence:\n'
                '  - type: human-authored\n'
                '    reference: docs/example.md\n'
                'adapter_projection:\n'
                '  hermes: adapters/hermes/USER.md\n',
                encoding='utf-8',
            )
            report = bootstrap_ai_assets.build_skills_inventory_report(tmp, schema_dir=schema_dir)
            self.assertEqual(report['mode'], 'skills-inventory')
            self.assertEqual(report['summary']['total_skills'], 1)
            self.assertEqual(report['summary']['valid_skills'], 1)
            self.assertEqual(report['summary']['statuses']['probationary'], 1)
            self.assertIn('hermes', report['summary']['projection_targets'])
            self.assertEqual(report['skills'][0]['name'], 'example-skill')

    def test_build_memos_skill_candidates_handles_missing_db_without_writing_candidates(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            memos_root = tmp / 'missing-memos'
            report = bootstrap_ai_assets.build_memos_skill_candidates_report(tmp, memos_root=memos_root)
            self.assertEqual(report['mode'], 'memos-skill-candidates')
            self.assertEqual(report['summary']['generated_candidates'], 0)
            self.assertTrue(report['errors'])
            self.assertFalse((tmp / 'bootstrap' / 'candidates').exists())

    def test_build_memos_skill_candidates_generates_review_bundle_from_sqlite_skills(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            memos_root = tmp / 'memos-plugin'
            db_path = memos_root / 'data' / 'memos.db'
            db_path.parent.mkdir(parents=True)
            sqlite3 = __import__('sqlite3')
            conn = sqlite3.connect(db_path)
            try:
                conn.execute('CREATE TABLE skills (id TEXT, name TEXT, description TEXT, trigger TEXT, procedure TEXT, verification TEXT, boundaries TEXT, status TEXT, confidence TEXT, updated_at TEXT)')
                conn.execute(
                    'INSERT INTO skills VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    ('skill-1', 'Runtime Sync Skill', 'Keep sync safe.', 'After runtime import.', 'Inspect reports\nReview diffs', 'Tests pass', 'No auto-push', 'active', 'high', '2026-04-24T12:00:00'),
                )
                conn.commit()
            finally:
                conn.close()
            report = bootstrap_ai_assets.build_memos_skill_candidates_report(tmp, memos_root=memos_root)
            self.assertEqual(report['summary']['source_rows'], 1)
            self.assertEqual(report['summary']['generated_candidates'], 1)
            bundle = Path(report['bundle_dir'])
            self.assertTrue((bundle / 'REVIEW-INSTRUCTIONS.md').is_file())
            self.assertTrue((bundle / 'SUMMARY.md').is_file())
            candidate_path = Path(report['candidates'][0]['candidate_path'])
            self.assertTrue(candidate_path.is_file())
            candidate_text = candidate_path.read_text(encoding='utf-8')
            self.assertIn('name: runtime-sync-skill', candidate_text)
            self.assertIn('status: probationary', candidate_text)
            self.assertIn('type: runtime-import', candidate_text)
            self.assertIn('reference: MemOS skills table row skill-1', candidate_text)

    def test_build_skill_candidates_status_reports_review_ready_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            bundle = tmp / 'bootstrap' / 'candidates' / 'memos-skills-20260424-120000'
            bundle.mkdir(parents=True)
            (bundle / '001-demo.candidate.yaml').write_text('name: demo\n', encoding='utf-8')
            (bundle / '001-demo.reviewed.yaml').write_text(
                'name: demo\n'
                'skill_version: v1\n'
                'status: active\n'
                'confidence: high\n'
                'description: Demo skill.\n'
                'trigger: When demo is needed.\n'
                'procedure:\n'
                '  - Do it.\n'
                'verification:\n'
                '  - Check it.\n'
                'boundaries:\n'
                '  - Stay safe.\n'
                'source_evidence:\n'
                '  - type: human-authored\n'
                '    reference: REVIEW.md\n'
                'adapter_projection:\n'
                '  hermes: adapters/hermes/USER.md\n',
                encoding='utf-8',
            )
            report = bootstrap_ai_assets.build_skill_candidates_status_report(tmp)
            self.assertEqual(report['mode'], 'skill-candidates-status')
            self.assertEqual(report['summary']['bundles'], 1)
            self.assertEqual(report['summary']['candidate_files'], 1)
            self.assertEqual(report['summary']['reviewed_files'], 1)
            self.assertEqual(report['summary']['ready_to_apply'], 1)

    def test_execute_skill_review_apply_copies_only_reviewed_skill_manifests(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            bundle = tmp / 'bootstrap' / 'candidates' / 'memos-skills-20260424-120000'
            bundle.mkdir(parents=True)
            (bundle / '001-skip.candidate.yaml').write_text('name: skip\n', encoding='utf-8')
            reviewed = bundle / '001-reviewed-sync.reviewed.yaml'
            reviewed.write_text(
                'name: reviewed-sync\n'
                'skill_version: v1\n'
                'status: active\n'
                'confidence: high\n'
                'description: Reviewed sync skill.\n'
                'trigger: After review.\n'
                'procedure:\n'
                '  - Review candidate.\n'
                'verification:\n'
                '  - Run tests.\n'
                'boundaries:\n'
                '  - Do not auto-push.\n'
                'source_evidence:\n'
                '  - type: human-authored\n'
                '    reference: REVIEW.md\n'
                'adapter_projection:\n'
                '  hermes: adapters/hermes/USER.md\n',
                encoding='utf-8',
            )
            report = bootstrap_ai_assets.execute_skill_review_apply(tmp)
            self.assertEqual(report['mode'], 'skill-review-apply')
            self.assertEqual(report['summary']['applied'], 1)
            self.assertEqual(report['summary']['failed'], 0)
            target = tmp / 'skills' / 'reviewed-sync.yaml'
            self.assertTrue(target.is_file())
            self.assertIn('name: reviewed-sync', target.read_text(encoding='utf-8'))
            self.assertFalse((tmp / 'skills' / 'skip.yaml').exists())

    def test_build_skill_projection_preview_reports_active_skill_adapter_targets_without_writing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            schema_dir = tmp / 'schemas'
            skill_dir = tmp / 'skills'
            adapter_dir = tmp / 'adapters' / 'hermes'
            schema_dir.mkdir(parents=True)
            skill_dir.mkdir(parents=True)
            adapter_dir.mkdir(parents=True)
            (schema_dir / 'portable-skill-manifest-v1.json').write_text(
                __import__('json').dumps(bootstrap_ai_assets.DEFAULT_SCHEMA_DEFINITIONS['portable-skill-manifest-v1']),
                encoding='utf-8',
            )
            (adapter_dir / 'USER.md').write_text('# Hermes User\n', encoding='utf-8')
            (skill_dir / 'reviewed-sync.yaml').write_text(
                'name: reviewed-sync\n'
                'skill_version: v1\n'
                'status: active\n'
                'confidence: high\n'
                'description: Reviewed sync skill.\n'
                'trigger: After review.\n'
                'procedure:\n'
                '  - Review candidate.\n'
                'verification:\n'
                '  - Run tests.\n'
                'boundaries:\n'
                '  - Do not auto-push.\n'
                'source_evidence:\n'
                '  - type: human-authored\n'
                '    reference: REVIEW.md\n'
                'adapter_projection:\n'
                '  hermes: adapters/hermes/USER.md\n'
                '  codex: adapters/codex/instructions.md\n',
                encoding='utf-8',
            )
            (skill_dir / 'retired.yaml').write_text(
                'name: retired-skill\n'
                'skill_version: v1\n'
                'status: retired\n'
                'description: Retired.\n'
                'trigger: Never.\n'
                'procedure:\n'
                '  - Do not use.\n'
                'verification:\n'
                '  - None.\n'
                'boundaries:\n'
                '  - None.\n'
                'source_evidence:\n'
                '  - type: human-authored\n'
                '    reference: old.md\n'
                'adapter_projection:\n'
                '  hermes: adapters/hermes/USER.md\n',
                encoding='utf-8',
            )
            report = bootstrap_ai_assets.build_skill_projection_preview_report(tmp, schema_dir=schema_dir)
            self.assertEqual(report['mode'], 'skill-projection-preview')
            self.assertEqual(report['summary']['projectable_skills'], 1)
            self.assertEqual(report['summary']['actions'], 2)
            self.assertIn('hermes', report['summary']['projection_targets'])
            self.assertTrue(any(action['target_exists'] for action in report['actions']))
            self.assertIn('Reviewed sync skill.', report['actions'][0]['preview_text'])
            self.assertEqual((adapter_dir / 'USER.md').read_text(encoding='utf-8'), '# Hermes User\n')

    def test_generate_skill_projection_candidates_writes_review_bundle_without_touching_adapters(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            schema_dir = tmp / 'schemas'
            skill_dir = tmp / 'skills'
            adapter_dir = tmp / 'adapters' / 'hermes'
            schema_dir.mkdir(parents=True)
            skill_dir.mkdir(parents=True)
            adapter_dir.mkdir(parents=True)
            (schema_dir / 'portable-skill-manifest-v1.json').write_text(
                __import__('json').dumps(bootstrap_ai_assets.DEFAULT_SCHEMA_DEFINITIONS['portable-skill-manifest-v1']),
                encoding='utf-8',
            )
            adapter_path = adapter_dir / 'USER.md'
            adapter_path.write_text('# Hermes User\n', encoding='utf-8')
            (skill_dir / 'reviewed-sync.yaml').write_text(
                'name: reviewed-sync\n'
                'skill_version: v1\n'
                'status: active\n'
                'confidence: high\n'
                'description: Reviewed sync skill.\n'
                'trigger: After review.\n'
                'procedure:\n'
                '  - Review candidate.\n'
                'verification:\n'
                '  - Run tests.\n'
                'boundaries:\n'
                '  - Do not auto-push.\n'
                'source_evidence:\n'
                '  - type: human-authored\n'
                '    reference: REVIEW.md\n'
                'adapter_projection:\n'
                '  hermes: adapters/hermes/USER.md\n',
                encoding='utf-8',
            )
            report = bootstrap_ai_assets.generate_skill_projection_candidates(tmp, schema_dir=schema_dir)
            self.assertEqual(report['mode'], 'skill-projection-candidates')
            self.assertEqual(report['summary']['candidate_files'], 1)
            bundle = Path(report['bundle_dir'])
            self.assertTrue((bundle / 'REVIEW-INSTRUCTIONS.md').is_file())
            self.assertTrue((bundle / 'SUMMARY.md').is_file())
            candidate_path = Path(report['candidates'][0]['candidate_path'])
            self.assertTrue(candidate_path.is_file())
            candidate_text = candidate_path.read_text(encoding='utf-8')
            self.assertIn('reviewed-sync', candidate_text)
            self.assertIn('Target adapter', candidate_text)
            self.assertIn('Reviewed sync skill.', candidate_text)
            self.assertEqual(adapter_path.read_text(encoding='utf-8'), '# Hermes User\n')

    def test_build_skill_projection_status_reports_reviewed_projection_ready_to_apply(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            adapter = tmp / 'adapters' / 'hermes' / 'USER.md'
            adapter.parent.mkdir(parents=True)
            adapter.write_text('# Hermes User\n', encoding='utf-8')
            bundle = tmp / 'bootstrap' / 'candidates' / 'skill-projections-20260424-130000'
            bundle.mkdir(parents=True)
            candidate = bundle / 'hermes.USER.skill-projection.md'
            candidate.write_text(
                '# Candidate\n\n- Target adapter: `' + str(adapter) + '`\n',
                encoding='utf-8',
            )
            reviewed = bundle / 'hermes.USER.reviewed.md'
            reviewed.write_text(
                '# Reviewed Projection\n\n'
                '- Target adapter: `' + str(adapter) + '`\n\n'
                '## Reviewed projection block\n\n'
                '### reviewed-sync\n\nUse reviewed sync safely.\n',
                encoding='utf-8',
            )
            report = bootstrap_ai_assets.build_skill_projection_status_report(tmp)
            self.assertEqual(report['mode'], 'skill-projection-status')
            self.assertEqual(report['summary']['bundles'], 1)
            self.assertEqual(report['summary']['candidate_files'], 1)
            self.assertEqual(report['summary']['reviewed_files'], 1)
            self.assertEqual(report['summary']['ready_to_apply'], 1)
            self.assertEqual(report['bundles'][0]['reviewed_files'][0]['target'], str(adapter))

    def test_execute_skill_projection_review_apply_appends_only_reviewed_projection(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            adapter = tmp / 'adapters' / 'hermes' / 'USER.md'
            adapter.parent.mkdir(parents=True)
            adapter.write_text('# Hermes User\n', encoding='utf-8')
            bundle = tmp / 'bootstrap' / 'candidates' / 'skill-projections-20260424-130000'
            bundle.mkdir(parents=True)
            (bundle / 'hermes.USER.skill-projection.md').write_text(
                '# Candidate\n\n- Target adapter: `' + str(adapter) + '`\n\nSHOULD NOT APPLY\n',
                encoding='utf-8',
            )
            (bundle / 'hermes.USER.reviewed.md').write_text(
                '# Reviewed Projection\n\n'
                '- Target adapter: `' + str(adapter) + '`\n\n'
                '## Reviewed projection block\n\n'
                '### reviewed-sync\n\nUse reviewed sync safely.\n',
                encoding='utf-8',
            )
            report = bootstrap_ai_assets.execute_skill_projection_review_apply(tmp)
            self.assertEqual(report['mode'], 'skill-projection-review-apply')
            self.assertEqual(report['summary']['applied'], 1)
            self.assertEqual(report['summary']['failed'], 0)
            text = adapter.read_text(encoding='utf-8')
            self.assertIn('# Hermes User', text)
            self.assertIn('Use reviewed sync safely.', text)
            self.assertNotIn('SHOULD NOT APPLY', text)

    def test_short_paa_command_wrapper_supports_codex_style_subcommands(self):
        repo_root = Path(__file__).resolve().parents[1]
        wrapper = repo_root / 'bin' / 'paa'
        self.assertTrue(wrapper.is_file())
        text = wrapper.read_text(encoding='utf-8')
        self.assertIn('bootstrap/setup/bootstrap-ai-assets.sh', text)
        self.assertIn('project-pack-preview', text)
        self.assertIn('--project-pack-preview', text)
        self.assertIn('ppack', text)
        self.assertIn('paa project-pack-preview --both', text)
        self.assertIn('paa setup', text)
        self.assertIn('AI-Assets-private', text)
        self.assertIn('--init-private-assets', text)
        self.assertIn('PAA_DEFAULT_ASSET_ROOT', text)
        self.assertIn('paa install', text)
        self.assertIn('paa uninstall', text)
        self.assertIn('paa doctor', text)
        self.assertIn('paa list', text)
        self.assertIn('paa version', text)
        self.assertIn('PAA_INSTALL_BIN_DIR', text)
        self.assertIn('ln -sfn', text)
        self.assertIn('rm -f', text)
        self.assertIn('exec "${BOOTSTRAP}"', text)
        self.assertTrue(os.access(wrapper, os.X_OK))

    def test_paa_install_creates_global_command_symlink_in_target_bin_dir(self):
        repo_root = Path(__file__).resolve().parents[1]
        wrapper = repo_root / 'bin' / 'paa'
        with tempfile.TemporaryDirectory() as tmpdir:
            install_dir = Path(tmpdir) / 'bin'
            command = f'PAA_INSTALL_BIN_DIR="{install_dir}" "{wrapper}" install >/tmp/paa-install-test-{os.getpid()}.out 2>&1'
            self.assertEqual(os.system(command), 0)
            installed = install_dir / 'paa'
            self.assertTrue(installed.exists())
            self.assertTrue(installed.is_symlink())
            self.assertEqual(installed.resolve(), wrapper.resolve())
            command = f'PATH="{install_dir}:$PATH" paa --help >/tmp/paa-installed-help-test-{os.getpid()}.out 2>&1'
            self.assertEqual(os.system(command), 0)
            command = f'PATH="{install_dir}:$PATH" paa list >/tmp/paa-installed-list-test-{os.getpid()}.out 2>&1'
            self.assertEqual(os.system(command), 0)
            list_text = Path(f'/tmp/paa-installed-list-test-{os.getpid()}.out').read_text(encoding='utf-8')
            self.assertIn('ppack', list_text)
            self.assertIn('project-pack-preview', list_text)
            command = f'PATH="{install_dir}:$PATH" paa doctor >/tmp/paa-installed-doctor-test-{os.getpid()}.out 2>&1'
            self.assertEqual(os.system(command), 0)
            doctor_text = Path(f'/tmp/paa-installed-doctor-test-{os.getpid()}.out').read_text(encoding='utf-8')
            self.assertIn('PAA doctor', doctor_text)
            self.assertIn('bootstrap wrapper: ok', doctor_text)
            command = f'PATH="{install_dir}:$PATH" paa version >/tmp/paa-installed-version-test-{os.getpid()}.out 2>&1'
            self.assertEqual(os.system(command), 0)
            version_text = Path(f'/tmp/paa-installed-version-test-{os.getpid()}.out').read_text(encoding='utf-8')
            self.assertIn('Portable AI Assets CLI', version_text)
            self.assertIn('repo root:', version_text)
            command = f'PATH="{install_dir}:$PATH" paa uninstall >/tmp/paa-installed-uninstall-test-{os.getpid()}.out 2>&1'
            self.assertEqual(os.system(command), 0)
            uninstall_text = Path(f'/tmp/paa-installed-uninstall-test-{os.getpid()}.out').read_text(encoding='utf-8')
            self.assertIn('Uninstalled paa', uninstall_text)
            self.assertFalse(installed.exists())

    def test_paa_uninstall_refuses_non_matching_or_regular_file_targets(self):
        repo_root = Path(__file__).resolve().parents[1]
        wrapper = repo_root / 'bin' / 'paa'
        with tempfile.TemporaryDirectory() as tmpdir:
            install_dir = Path(tmpdir) / 'bin'
            install_dir.mkdir(parents=True)
            regular = install_dir / 'paa'
            regular.write_text('#!/usr/bin/env bash\necho not-paa\n', encoding='utf-8')
            command = f'PAA_INSTALL_BIN_DIR="{install_dir}" "{wrapper}" uninstall >/tmp/paa-uninstall-regular-test-{os.getpid()}.out 2>&1'
            self.assertNotEqual(os.system(command), 0)
            self.assertTrue(regular.exists())
            regular_text = regular.read_text(encoding='utf-8')
            self.assertIn('not-paa', regular_text)
            output = Path(f'/tmp/paa-uninstall-regular-test-{os.getpid()}.out').read_text(encoding='utf-8')
            self.assertIn('Refusing to remove', output)

        with tempfile.TemporaryDirectory() as tmpdir:
            install_dir = Path(tmpdir) / 'bin'
            install_dir.mkdir(parents=True)
            other_target = Path(tmpdir) / 'other-paa'
            other_target.write_text('#!/usr/bin/env bash\necho other-paa\n', encoding='utf-8')
            installed = install_dir / 'paa'
            installed.symlink_to(other_target)
            command = f'PAA_INSTALL_BIN_DIR="{install_dir}" "{wrapper}" uninstall >/tmp/paa-uninstall-other-symlink-test-{os.getpid()}.out 2>&1'
            self.assertNotEqual(os.system(command), 0)
            self.assertTrue(installed.exists())
            self.assertEqual(installed.resolve(), other_target.resolve())
            output = Path(f'/tmp/paa-uninstall-other-symlink-test-{os.getpid()}.out').read_text(encoding='utf-8')
            self.assertIn('Refusing to remove', output)


if __name__ == "__main__":
    unittest.main()
