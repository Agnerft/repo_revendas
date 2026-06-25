import unittest
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pandas as pd

from api import filter_clients_by_expiration


class ExpirationExportTest(unittest.TestCase):
    def setUp(self):
        timezone = ZoneInfo("America/Sao_Paulo")
        self.now = datetime(2026, 6, 25, 12, 0, tzinfo=timezone)
        self.dataframe = pd.DataFrame(
            [
                {"nome": "Expirado", "data_expiracao": "25/06/2026"},
                {
                    "nome": "Ativo",
                    "data_expiracao": str(
                        int(datetime(2026, 6, 26, 18, 30, tzinfo=timezone).timestamp())
                    ),
                },
                {"nome": "Fora do intervalo", "data_expiracao": "30/06/2026"},
                {"nome": "Sem data", "data_expiracao": ""},
            ]
        )

    def test_filters_range_and_status_at_extraction_time(self):
        start = date(2026, 6, 25)
        end = date(2026, 6, 26)

        all_records = filter_clients_by_expiration(
            self.dataframe, start, end, "todos", self.now
        )
        active_records = filter_clients_by_expiration(
            self.dataframe, start, end, "ativos", self.now
        )
        expired_records = filter_clients_by_expiration(
            self.dataframe, start, end, "expirados", self.now
        )

        self.assertEqual([row["nome"] for row in all_records], ["Expirado", "Ativo"])
        self.assertEqual([row["nome"] for row in active_records], ["Ativo"])
        self.assertEqual([row["nome"] for row in expired_records], ["Expirado"])

    def test_rejects_inverted_range(self):
        with self.assertRaises(ValueError):
            filter_clients_by_expiration(
                self.dataframe,
                date(2026, 6, 27),
                date(2026, 6, 25),
                "todos",
                self.now,
            )


if __name__ == "__main__":
    unittest.main()
