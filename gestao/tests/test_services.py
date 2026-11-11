"""Testes unitários das regras de negócio (RF03 a RF08)."""

import datetime as dt

from django.db import IntegrityError, transaction
from django.test import TestCase

from gestao import services
from gestao.models import Inscricao, Oficina, Participante, Presenca


def criar_oficina(vagas=2, nome="Violão iniciante"):
    return Oficina.objects.create(
        nome=nome,
        area="Música",
        instrutor="Fictício",
        dia_semana=5,
        horario_inicio=dt.time(9),
        horario_fim=dt.time(10, 30),
        vagas=vagas,
    )


def criar_pessoa(nome="Ana Lima", ano=1990):
    return Participante.objects.create(
        nome_completo=nome, data_nascimento=dt.date(ano, 1, 1), telefone="(00) 90000-0000"
    )


class VagasTests(TestCase):
    def test_vagas_livres_diminuem_com_confirmadas(self):
        of = criar_oficina(vagas=2)
        services.inscrever(criar_pessoa("A"), of)
        self.assertEqual(of.vagas_livres, 1)
        self.assertFalse(of.lotada)

    def test_oficina_lotada_quando_vagas_acabam(self):
        of = criar_oficina(vagas=1)
        services.inscrever(criar_pessoa("A"), of)
        self.assertTrue(of.lotada)
        self.assertEqual(of.vagas_livres, 0)

    def test_vagas_nao_pode_ser_zero(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            criar_oficina(vagas=0)

    def test_horario_texto(self):
        self.assertEqual(criar_oficina().horario_texto, "Sábado, 9h às 10h30")


class InscricaoTests(TestCase):
    def test_inscricao_confirmada_com_vaga(self):
        insc = services.inscrever(criar_pessoa(), criar_oficina())
        self.assertEqual(insc.situacao, Inscricao.CONFIRMADA)

    def test_lista_de_espera_quando_lotada(self):
        of = criar_oficina(vagas=1)
        services.inscrever(criar_pessoa("A"), of)
        espera = services.inscrever(criar_pessoa("B"), of)
        self.assertEqual(espera.situacao, Inscricao.EM_ESPERA)
        self.assertEqual(of.em_espera, 1)

    def test_bloqueia_duplicidade(self):
        of, p = criar_oficina(), criar_pessoa()
        services.inscrever(p, of)
        with self.assertRaises(services.InscricaoDuplicada):
            services.inscrever(p, of)
        self.assertEqual(Inscricao.objects.count(), 1)

    def test_bloqueia_duplicidade_na_espera(self):
        of = criar_oficina(vagas=1)
        services.inscrever(criar_pessoa("A"), of)
        b = criar_pessoa("B")
        services.inscrever(b, of)
        with self.assertRaises(services.InscricaoDuplicada):
            services.inscrever(b, of)

    def test_oficina_inativa_recusa_inscricao(self):
        of = criar_oficina()
        of.ativa = False
        of.save()
        with self.assertRaises(services.InscricaoInvalida):
            services.inscrever(criar_pessoa(), of)

    def test_reinscricao_apos_cancelamento(self):
        of, p = criar_oficina(), criar_pessoa()
        insc = services.inscrever(p, of)
        services.cancelar_inscricao(insc)
        nova = services.inscrever(p, of)
        self.assertEqual(nova.pk, insc.pk)
        self.assertEqual(nova.situacao, Inscricao.CONFIRMADA)


class FilaTests(TestCase):
    def test_cancelar_promove_primeiro_da_fila(self):
        of = criar_oficina(vagas=1)
        a = services.inscrever(criar_pessoa("A"), of)
        b = services.inscrever(criar_pessoa("B"), of)
        c = services.inscrever(criar_pessoa("C"), of)
        promovido = services.cancelar_inscricao(a)
        b.refresh_from_db()
        c.refresh_from_db()
        self.assertEqual(promovido.pk, b.pk)
        self.assertEqual(b.situacao, Inscricao.CONFIRMADA)
        self.assertEqual(c.situacao, Inscricao.EM_ESPERA)

    def test_cancelar_espera_nao_promove_ninguem(self):
        of = criar_oficina(vagas=1)
        services.inscrever(criar_pessoa("A"), of)
        b = services.inscrever(criar_pessoa("B"), of)
        self.assertIsNone(services.cancelar_inscricao(b))


class PresencaTests(TestCase):
    def setUp(self):
        self.of = criar_oficina()
        self.insc = services.inscrever(criar_pessoa(), self.of)

    def test_registra_presenca(self):
        p = services.registrar_presenca(self.insc, dt.date(2026, 11, 14), True)
        self.assertTrue(p.presente)

    def test_atualiza_em_vez_de_duplicar(self):
        d = dt.date(2026, 11, 14)
        services.registrar_presenca(self.insc, d, True)
        services.registrar_presenca(self.insc, d, False)
        self.assertEqual(Presenca.objects.count(), 1)
        self.assertFalse(Presenca.objects.get().presente)

    def test_conta_faltas(self):
        services.registrar_presenca(self.insc, dt.date(2026, 11, 7), False)
        services.registrar_presenca(self.insc, dt.date(2026, 11, 14), False)
        services.registrar_presenca(self.insc, dt.date(2026, 11, 21), True)
        self.assertEqual(self.insc.faltas, 2)

    def test_recusa_presenca_de_inscricao_em_espera(self):
        of = criar_oficina(vagas=1, nome="Teatro")
        services.inscrever(criar_pessoa("X"), of)
        espera = services.inscrever(criar_pessoa("Y"), of)
        with self.assertRaises(services.InscricaoInvalida):
            services.registrar_presenca(espera, dt.date(2026, 11, 14), True)


class ParticipanteTests(TestCase):
    def test_nome_e_nascimento_unicos(self):
        criar_pessoa("Ana", 1990)
        with self.assertRaises(IntegrityError), transaction.atomic():
            criar_pessoa("Ana", 1990)

    def test_idade_em(self):
        p = Participante(nome_completo="M", data_nascimento=dt.date(2012, 3, 10))
        self.assertEqual(p.idade_em(dt.date(2026, 3, 9)), 13)
        self.assertEqual(p.idade_em(dt.date(2026, 3, 10)), 14)
