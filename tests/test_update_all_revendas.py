import json
import tempfile
import unittest
from pathlib import Path

from update_all_revendas import process_and_save


class ProcessAndSaveTests(unittest.TestCase):
    def test_empty_response_preserves_existing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "revenda.json"
            existing = [{"DT_RowId": "123", "telefone": "5511999999999"}]
            output.write_text(json.dumps(existing), encoding="utf-8")

            saved = process_and_save({"data": []}, output)

            self.assertFalse(saved)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), existing)


if __name__ == "__main__":
    unittest.main()
