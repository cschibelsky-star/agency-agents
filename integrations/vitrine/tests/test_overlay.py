"""Testes offline: integridade e nao ativacao do overlay; sem acesso de rede."""
import json
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import install_agents  # noqa: E402


class OverlayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))

    def test_three_roles_only(self):
        self.assertEqual(len(self.manifest["agents"]), 3)
        self.assertEqual({a["role"] for a in self.manifest["agents"]},
                         {"architecture", "quality_evidence", "independent_review"})
        self.assertEqual(len({a["id"] for a in self.manifest["agents"]}), 3)

    def test_supervisor_is_observer_and_fail_closed(self):
        g = self.manifest["governance"]
        self.assertEqual(self.manifest["integration_mode"], "offline_advisory")
        self.assertEqual(self.manifest["supervisor_mode"], "OBSERVER")
        self.assertIs(self.manifest["execution_enabled"], False)
        for field in ("can_advance", "dispatch_allowed", "production_allowed", "api_calls_allowed"):
            self.assertIs(g[field], False)
        self.assertEqual(g["max_retries"], 3)
        self.assertEqual(g["gates"], [f"G{i}" for i in range(7)])

    def test_agent_files_and_upstream_paths_exist(self):
        for agent in self.manifest["agents"]:
            self.assertFalse(agent["may_approve_own_work"])
            self.assertTrue((ROOT / agent["file"]).is_file())
            self.assertTrue((ROOT.parent.parent / agent["upstream"]).is_file())
            contents = (ROOT / agent["file"]).read_text(encoding="utf-8")
            header, body = install_agents.profile(contents)
            self.assertEqual(header["name"], agent["name"])
            self.assertIn("VIA", body)

    def test_codex_toml_is_parseable(self):
        for agent in self.manifest["agents"]:
            md = (ROOT / agent["file"]).read_text(encoding="utf-8")
            data = tomllib.loads(install_agents.render(md, "codex"))
            self.assertEqual(data["name"], agent["name"])
            self.assertIn("developer_instructions", data)

    def test_dry_run_has_no_side_effects(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "new"
            self.assertEqual(install_agents.main(["--tool", "codex", "--dest", str(target)]), 0)
            self.assertFalse(target.exists())

    def test_explicit_install_claude_and_refuse_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "claude"
            opts = ["--tool", "claude-code", "--dest", str(target), "--apply"]
            self.assertEqual(install_agents.main(opts), 0)
            self.assertEqual(len(list(target.glob("*.md"))), 3)
            self.assertEqual(install_agents.main(opts), 2)

    def test_explicit_install_codex(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "codex"
            self.assertEqual(install_agents.main(
                ["--tool", "codex", "--dest", str(target), "--apply"]), 0)
            self.assertEqual(len(list(target.glob("*.toml"))), 3)

    def test_governance_refers_to_factory_not_shadow_gate(self):
        g = self.manifest["governance"]
        self.assertEqual(g["canonical_repository"], "cschibelsky-star/VitrineAI-Factory")
        self.assertEqual(g["handoff_verifier"], "tools/verify-agent-handoff.php")
        self.assertFalse((ROOT / "tools" / "verify-agent-handoff.php").exists())


if __name__ == "__main__":
    unittest.main()
