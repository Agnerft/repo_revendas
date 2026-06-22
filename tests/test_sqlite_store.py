import os
import tempfile
import unittest

import pandas as pd

from sqlite_store import init_database, search_clients, sync_excel_snapshot


class SqliteStoreTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = os.path.join(self.temp_dir.name, "revendas.db")
        self.dataframe = pd.DataFrame(
            [
                {
                    "Revenda": "Alpha",
                    "DT_RowId": "row-1",
                    "Id_client": "72",
                    "nome": "Cliente Um",
                    "telefone": "+5551999991111",
                    "plano": "Mensal",
                    "data_expiracao": "21/06/2026",
                },
                {
                    "Revenda": "Beta",
                    "DT_RowId": "row-2",
                    "Id_client": "1720",
                    "nome": "556592437451",
                    "telefone": "+5565999992222",
                    "plano": "Anual",
                    "data_expiracao": "22/06/2026",
                },
                {
                    "Revenda": "Alpha",
                    "DT_RowId": "row-3",
                    "Id_client": "7200",
                    "nome": "Cliente Tres",
                    "telefone": "+5551999993333",
                    "plano": "Mensal",
                    "data_expiracao": "21/06/2026",
                },
            ]
        )
        init_database(self.database_path)
        sync_excel_snapshot(self.database_path, self.dataframe)

    def tearDown(self):
        self.temp_dir.cleanup()

    def expected_records(self, term):
        source = self.dataframe.astype(str).agg(" ".join, axis=1).str.lower()
        return self.dataframe[source.str.contains(term.lower(), regex=False)].to_dict(
            orient="records"
        )

    def test_partial_search_matches_excel_semantics(self):
        for term in ["72", "cliente", "21/06/2026", "556592437451", "+5551999991111"]:
            with self.subTest(term=term):
                self.assertEqual(
                    search_clients(self.database_path, term),
                    self.expected_records(term),
                )

    def test_search_accepts_phone_without_plus(self):
        self.assertEqual(
            search_clients(self.database_path, "5551999991111"),
            self.expected_records("5551999991111"),
        )

    def test_sync_replaces_previous_snapshot(self):
        replacement = self.dataframe.iloc[:1]
        sync_excel_snapshot(self.database_path, replacement)

        self.assertEqual(len(search_clients(self.database_path, "cliente")), 1)
        self.assertEqual(search_clients(self.database_path, "cliente tres"), [])


if __name__ == "__main__":
    unittest.main()
