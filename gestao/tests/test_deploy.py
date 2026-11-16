"""Testes da preparação para a nuvem: verificação de saúde e configuração do banco."""

from unittest import mock

from django.test import TestCase
from django.urls import reverse

from config.dburl import banco_de_url


class SaudeTests(TestCase):
    def test_responde_ok_sem_login(self):
        r = self.client.get(reverse("saude"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"status": "ok"})

    def test_aceita_head_para_monitores(self):
        self.assertEqual(self.client.head(reverse("saude")).status_code, 200)

    def test_recusa_post(self):
        self.assertEqual(self.client.post(reverse("saude")).status_code, 405)

    def test_responde_503_quando_o_banco_falha(self):
        with mock.patch("gestao.views.connection") as conexao:
            conexao.cursor.side_effect = RuntimeError("banco fora do ar")
            r = self.client.get(reverse("saude"))
        self.assertEqual(r.status_code, 503)
        self.assertEqual(r.json(), {"status": "erro"})

    def test_nao_expoe_dados_internos(self):
        corpo = self.client.get(reverse("saude")).content.decode()
        self.assertNotIn("sqlite", corpo.lower())
        self.assertNotIn("password", corpo.lower())


class BancoDeUrlTests(TestCase):
    def test_converte_url_do_postgres(self):
        cfg = banco_de_url("postgresql://usuario:s%40nha@host.exemplo.com:5433/casa")
        self.assertEqual(cfg["ENGINE"], "django.db.backends.postgresql")
        self.assertEqual(cfg["NAME"], "casa")
        self.assertEqual(cfg["USER"], "usuario")
        self.assertEqual(cfg["PASSWORD"], "s@nha")
        self.assertEqual(cfg["HOST"], "host.exemplo.com")
        self.assertEqual(cfg["PORT"], "5433")

    def test_aceita_esquema_postgres_e_porta_padrao(self):
        cfg = banco_de_url("postgres://u:p@h/db")
        self.assertEqual(cfg["PORT"], "5432")

    def test_recusa_esquema_desconhecido(self):
        with self.assertRaises(ValueError):
            banco_de_url("mysql://u:p@h/db")

    def test_recusa_url_sem_nome_de_banco(self):
        with self.assertRaises(ValueError):
            banco_de_url("postgresql://u:p@h/")
