import unittest

import api


class CoreBehaviorTests(unittest.TestCase):
    def test_unified_query_returns_payment_line_and_maxplayer(self):
        original_buscar = api.buscar_cliente
        original_linha = api.consultar_linha_externa_get
        original_max = api.pesquisar_usuario_maxplayer

        try:
            api.buscar_cliente = lambda request: {
                "Revenda": "Teste",
                "DT_RowId": "abc123",
                "Id_client": "42",
                "nome": "Cliente Teste",
                "telefone": request.termo,
                "plano": "Mensal",
                "data_expiracao": "31/12/2026",
                "Link": "https://pagueaqui.top/abc123",
            }
            api.consultar_linha_externa_get = lambda telefone: {
                "status": "sucesso",
                "linha": {"telefone": telefone, "usuario": "iptv_user", "senha": "iptv_pass"},
            }
            api.pesquisar_usuario_maxplayer = lambda request: {
                "status": "nao_encontrado",
                "usuarios": [],
            }

            result = api.consulta_cliente_unificada(api.SearchRequest(termo="(21) 99999-9999"))

            self.assertEqual(result["status"], "sucesso")
            self.assertTrue(result["resumo"]["revenda_encontrada"])
            self.assertTrue(result["resumo"]["linha_encontrada"])
            self.assertFalse(result["resumo"]["maxplayer_encontrado"])
            self.assertEqual(result["revenda"]["Link"], "https://pagueaqui.top/abc123")
        finally:
            api.buscar_cliente = original_buscar
            api.consultar_linha_externa_get = original_linha
            api.pesquisar_usuario_maxplayer = original_max

    def test_prevalidate_create_masks_password(self):
        original_consulta = api.consulta_cliente_unificada

        try:
            api.consulta_cliente_unificada = lambda request: {
                "telefone_normalizado": "21999999999",
                "resumo": {"maxplayer_encontrado": False},
                "linha": {"linha": {"usuario": "iptv_user", "senha": "supersecret"}},
                "maxplayer": {"status": "nao_encontrado"},
            }

            result = api.prevalidar_criacao_maxplayer(api.SearchRequest(termo="21999999999"))

            self.assertTrue(result["pode_criar"])
            self.assertEqual(result["sugestao"]["iptv_user"], "iptv_user")
            self.assertIn("***", result["sugestao"]["iptv_pass"])
        finally:
            api.consulta_cliente_unificada = original_consulta

    def test_create_user_payload_is_sent_to_panel(self):
        original_post = api.maxplayer_panel_post
        original_decode = api.decode_maxplayer_panel_token
        captured = {}

        try:
            api.decode_maxplayer_panel_token = lambda: {"group": "reseller", "id": "9206"}

            def fake_post(path, payload):
                captured["path"] = path
                captured["payload"] = payload
                return {"user_id": "123"}

            api.maxplayer_panel_post = fake_post
            result = api.criar_usuario_maxplayer(
                api.MaxplayerCreateRequest(
                    domain_id="domain1",
                    iptv_user="iptv_user",
                    iptv_pass="iptv_pass",
                    username="iptv_user",
                )
            )

            self.assertEqual(result["status"], "sucesso")
            self.assertEqual(captured["path"], "/api/panel/actions/reseller/create-user")
            self.assertEqual(captured["payload"]["domain_id"], "domain1")
            self.assertEqual(captured["payload"]["iptv_user"], "iptv_user")
        finally:
            api.maxplayer_panel_post = original_post
            api.decode_maxplayer_panel_token = original_decode


if __name__ == "__main__":
    unittest.main()
