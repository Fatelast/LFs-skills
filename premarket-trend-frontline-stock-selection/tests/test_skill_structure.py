import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SkillStructureTests(unittest.TestCase):
    def test_required_files_exist(self):
        for relative in (
            "SKILL.md",
            "README.md",
            "requirements.txt",
            "references/akshare-data-contract.md",
            "scripts/market_snapshot.py",
        ):
            self.assertTrue((ROOT / relative).is_file(), relative)

    def test_frontmatter_and_direct_references_are_valid(self):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        frontmatter = text.split("---", 2)[1]
        keys = [line.split(":", 1)[0].strip() for line in frontmatter.splitlines() if ":" in line]
        self.assertEqual(keys, ["name", "description"])
        self.assertIn("[AKShare 数据契约](references/akshare-data-contract.md)", text)
        self.assertIn("scripts/market_snapshot.py --mode post_close", text)
        self.assertIn("scripts/market_snapshot.py --mode auction", text)
        self.assertIn("scripts/market_snapshot.py --mode health", text)
        self.assertIn('risk.status = "not_checked"', text)
        self.assertIn("17:10", text)
        self.assertIn("9:25", text)

    def test_dependency_is_pinned(self):
        requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8").strip()
        self.assertEqual(requirements, "akshare==1.18.64")

    def test_docs_prohibit_storing_tokens(self):
        combined = "\n".join(
            (ROOT / relative).read_text(encoding="utf-8")
            for relative in ("SKILL.md", "README.md", "references/akshare-data-contract.md")
        )
        self.assertIn("ZHITU_API_TOKEN", combined)
        self.assertIn("不得", combined)
        self.assertNotIn("ZHITU_TOKEN_LIMIT_TEST", combined)


if __name__ == "__main__":
    unittest.main()