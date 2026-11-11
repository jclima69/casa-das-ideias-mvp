"""Teste do comando que carrega os dados fictícios de demonstração."""

from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from gestao.models import Inscricao, Oficina


class PopularDemoTests(TestCase):
    def test_carrega_dados_e_usuario(self):
        call_command("popular_demo", "--senha", "senha-de-demo-123", stdout=StringIO())
        teatro = Oficina.objects.get(nome="Teatro")
        self.assertTrue(teatro.lotada)
        self.assertEqual(teatro.em_espera, 2)
        self.assertEqual(Oficina.objects.get(nome="Violão iniciante").vagas_livres, 7)
        self.assertEqual(Inscricao.objects.get(participante__nome_completo="Bruno Alves").faltas, 2)
        usuario = get_user_model().objects.get(username="coordenacao")
        self.assertTrue(usuario.check_password("senha-de-demo-123"))

    def test_senha_curta_recusada(self):
        with self.assertRaises(CommandError):
            call_command("popular_demo", "--senha", "curta")
