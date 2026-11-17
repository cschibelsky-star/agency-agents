import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from prepare_task import prepare

class PacketTests(unittest.TestCase):
    def sample(self):
        return {"task_id":"T1","repository":"cschibelsky-star/agency-agents","branch":"feature/pilot","objective":"Audit","scope":"offline","criteria":["No dispatch"]}
    def test_three_roles_are_blocked(self):
        for role in ("architect","evidence","review"):
            packet, h = prepare(self.sample(), role)
            self.assertIn("NAO EXECUTADO",packet)
            self.assertEqual(h["state"],"blocked")
            self.assertFalse(h["authorization"]["approved_for_branch_write"])
            self.assertEqual(h["review"]["status"],"pending")
            self.assertEqual(h["checks"],[])
    def test_main_blocked(self):
        d=self.sample();d["branch"]="main"
        with self.assertRaises(ValueError):prepare(d,"architect")
    def test_unknown_field_blocked(self):
        d=self.sample();d["token"]="secret"
        with self.assertRaises(ValueError):prepare(d,"architect")
    def test_schema_required_fields(self):
        _,h=prepare(self.sample(),"architect")
        self.assertEqual(h["schema_version"],"1.0")
        self.assertEqual(len(h),16)
if __name__ == "__main__":
    unittest.main()
