"""Testes unitários do formulário de inscrição (RF01, RNF02, RNF04)."""

from django.test import TestCase

from gestao.forms import InscricaoForm


def dados(**extra):
    base = {
        "nome_completo": "Marina Souza",
        "data_nascimento": "10/03/2012",
        "telefone": "(00) 90000-0000",
        "nome_responsavel": "Paula Souza",
    }
    base.update(extra)
    return base


class InscricaoFormTests(TestCase):
    def test_dados_validos(self):
        self.assertTrue(InscricaoForm(dados()).is_valid())

    def test_telefone_vazio_mostra_orientacao(self):
        f = InscricaoForm(dados(telefone=""))
        self.assertFalse(f.is_valid())
        self.assertIn("Exemplo: (00) 90000-0000", f.errors["telefone"][0])

    def test_telefone_sem_ddd_invalido(self):
        self.assertIn("telefone", InscricaoForm(dados(telefone="90000-0000")).errors)

    def test_menor_exige_responsavel(self):
        f = InscricaoForm(dados(nome_responsavel=""))
        self.assertIn("nome_responsavel", f.errors)

    def test_adulto_nao_exige_responsavel(self):
        f = InscricaoForm(dados(data_nascimento="10/03/1990", nome_responsavel=""))
        self.assertTrue(f.is_valid(), f.errors)

    def test_nascimento_no_futuro_recusado(self):
        self.assertIn("data_nascimento", InscricaoForm(dados(data_nascimento="10/03/2999")).errors)

    def test_nome_obrigatorio(self):
        self.assertIn("nome_completo", InscricaoForm(dados(nome_completo="")).errors)
