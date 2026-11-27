import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATE_FILE = ROOT / "ESTADO_ATUAL.md"


class CanonicalStateMemoryTests(unittest.TestCase):
    def test_canonical_state_memory_contains_required_governance(self):
        text = STATE_FILE.read_text(encoding="utf-8")
        for heading in (
            "## Estado canônico",
            "## Arquitetura vigente",
            "## Evidências verificadas",
            "## Pendências reais",
            "## Próxima ação prioritária",
        ):
            self.assertIn(heading, text)
        self.assertIn("Produção automática: **DESATIVADA**", text)
        self.assertIn("Execução paralela: **PROIBIDA**", text)
        self.assertIn("Commit verificado:", text)

    def test_state_memory_does_not_contain_credentials(self):
        text = STATE_FILE.read_text(encoding="utf-8").lower()
        for marker in ("api_key", "access_token", "client_secret", "password="):
            self.assertNotIn(marker, text)


if __name__ == "__main__":
    unittest.main()
