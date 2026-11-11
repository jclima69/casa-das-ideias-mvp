"""Testes de integração dos fluxos das três telas e da autenticação (RNF01)."""

import datetime as dt

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from gestao import services
from gestao.models import Inscricao, Participante, Presenca

from .test_services import criar_oficina, criar_pessoa

SENHA = "senha-de-teste-123"


class BaseLogado(TestCase):
    def setUp(self):
        cache.clear()
        self.user = get_user_model().objects.create_user("coord", password=SENHA)
        self.client.login(username="coord", password=SENHA)
        self.oficina = criar_oficina(vagas=2)


class AutenticacaoTests(TestCase):
    def setUp(self):
        cache.clear()
        get_user_model().objects.create_user("coord", password=SENHA)

    def test_telas_exigem_login(self):
        for nome in ("vagas", "inscrever", "presenca"):
            r = self.client.get(reverse(nome))
            self.assertRedirects(r, f"{reverse('login')}?next={reverse(nome)}")

    def test_login_valido_abre_vagas(self):
        r = self.client.post(reverse("login"), {"username": "coord", "password": SENHA})
        self.assertRedirects(r, reverse("vagas"))

    def test_hash_da_senha_e_argon2(self):
        self.assertTrue(get_user_model().objects.get().password.startswith("argon2"))

    def test_bloqueio_apos_cinco_falhas(self):
        for _ in range(5):
            self.client.post(reverse("login"), {"username": "coord", "password": "errada"})
        r = self.client.post(reverse("login"), {"username": "coord", "password": SENHA})
        self.assertEqual(r.status_code, 429)
        self.assertContains(r, "bloqueado", status_code=429)

    def test_sessao_expira_em_30_minutos(self):
        from django.conf import settings

        self.assertEqual(settings.SESSION_COOKIE_AGE, 1800)

    def test_sair_encerra_sessao(self):
        self.client.login(username="coord", password=SENHA)
        self.client.post(reverse("logout"))
        self.assertEqual(self.client.get(reverse("vagas")).status_code, 302)


class VagasTests(BaseLogado):
    def test_lista_vagas_livres(self):
        r = self.client.get(reverse("vagas"))
        self.assertContains(r, "Violão iniciante")
        self.assertContains(r, "2 vagas livres")
        self.assertContains(r, "Há vagas")

    def test_oficina_lotada_mostra_texto_e_lista_de_espera(self):
        services.inscrever(criar_pessoa("A"), self.oficina)
        services.inscrever(criar_pessoa("B"), self.oficina)
        r = self.client.get(reverse("vagas"))
        self.assertContains(r, "Lotada")
        self.assertContains(r, "Inscrever na lista de espera")


class InscricaoFluxoTests(BaseLogado):
    URL = "/inscrever/"
    DADOS = {
        "nome_completo": "Marina Souza",
        "data_nascimento": "10/03/2012",
        "telefone": "(00) 90000-0000",
        "nome_responsavel": "Paula Souza",
    }

    def post(self, **extra):
        d = dict(self.DADOS, oficina=self.oficina.pk)
        d.update(extra)
        return self.client.post(self.URL, d)

    def test_sem_oficina_volta_para_vagas(self):
        self.assertRedirects(self.client.get(self.URL), reverse("vagas"))

    def test_formulario_mostra_oficina(self):
        r = self.client.get(f"{self.URL}?oficina={self.oficina.pk}")
        self.assertContains(r, "Violão iniciante")
        self.assertContains(r, "2 vagas livres")

    def test_inscricao_confirmada_vai_para_presenca_com_faixa(self):
        r = self.client.post(self.URL, dict(self.DADOS, oficina=self.oficina.pk), follow=True)
        self.assertEqual(r.redirect_chain[-1][0], f"/presenca/?oficina={self.oficina.pk}")
        self.assertContains(r, "Inscrição confirmada: Marina Souza, Violão iniciante. 1 vaga livre.")
        self.assertEqual(Inscricao.objects.get().situacao, Inscricao.CONFIRMADA)

    def test_telefone_ausente_mostra_erro_e_nao_grava(self):
        r = self.post(telefone="")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Informe o telefone com DDD. Exemplo: (00) 90000-0000")
        self.assertEqual(Inscricao.objects.count(), 0)
        self.assertEqual(Participante.objects.count(), 0)

    def test_dados_digitados_sao_mantidos_apos_erro(self):
        r = self.post(telefone="")
        self.assertContains(r, 'value="Marina Souza"')

    def test_duplicidade_fica_na_tela_de_inscricao(self):
        self.post()
        r = self.post()
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "já está inscrito(a)")
        self.assertEqual(Inscricao.objects.count(), 1)

    def test_oficina_lotada_entra_na_lista_de_espera(self):
        services.inscrever(criar_pessoa("A"), self.oficina)
        services.inscrever(criar_pessoa("B"), self.oficina)
        self.post()
        self.assertEqual(
            Inscricao.objects.get(participante__nome_completo="Marina Souza").situacao, Inscricao.EM_ESPERA
        )
        r = self.client.get(f"/presenca/?oficina={self.oficina.pk}")
        self.assertContains(r, "lista de espera")

    def test_participante_existente_pode_ser_escolhido(self):
        p = criar_pessoa("Ana Lima")
        r = self.client.post(self.URL, {"oficina": self.oficina.pk, "participante_existente": p.pk})
        self.assertEqual(r.status_code, 302)
        self.assertTrue(Inscricao.objects.filter(participante=p).exists())

    def test_oficina_inexistente_ou_invalida(self):
        self.assertRedirects(self.client.get(f"{self.URL}?oficina=999"), reverse("vagas"))
        self.assertRedirects(self.client.get(f"{self.URL}?oficina=abc"), reverse("vagas"))


class PresencaFluxoTests(BaseLogado):
    def setUp(self):
        super().setUp()
        self.ana = services.inscrever(criar_pessoa("Ana Lima"), self.oficina)
        self.bruno = services.inscrever(criar_pessoa("Bruno Alves", 1991), self.oficina)
        for d in (dt.date(2026, 10, 24), dt.date(2026, 10, 31)):
            services.registrar_presenca(self.bruno, d, False)

    def marcar(self, insc, valor, data="2026-11-14"):
        return self.client.post(
            "/presenca/", {"oficina": self.oficina.pk, "data": data, "inscricao": insc.pk, "presente": valor}
        )

    def test_lista_turma_com_alerta_por_texto_e_simbolo(self):
        r = self.client.get(f"/presenca/?oficina={self.oficina.pk}&data=2026-11-14")
        self.assertContains(r, "Ana Lima")
        self.assertContains(r, "0 faltas")
        self.assertContains(r, "⚠")
        self.assertContains(r, "2 faltas")

    def test_marca_presente_e_ausente(self):
        self.marcar(self.ana, "1")
        self.marcar(self.bruno, "0")
        self.assertTrue(Presenca.objects.get(inscricao=self.ana, data_encontro="2026-11-14").presente)
        self.assertFalse(Presenca.objects.get(inscricao=self.bruno, data_encontro="2026-11-14").presente)
        self.assertEqual(self.bruno.faltas, 3)

    def test_estado_e_exibido_com_texto(self):
        self.marcar(self.ana, "1")
        r = self.client.get(f"/presenca/?oficina={self.oficina.pk}&data=2026-11-14")
        self.assertContains(r, 'aria-pressed="true"')
        self.assertContains(r, "Presente")

    def test_nao_aceita_inscricao_de_outra_oficina(self):
        outra = criar_oficina(nome="Teatro")
        intrusa = services.inscrever(criar_pessoa("Zé"), outra)
        r = self.marcar(intrusa, "1")
        self.assertEqual(r.status_code, 404)

    def test_data_invalida_usa_hoje(self):
        r = self.client.get(f"/presenca/?oficina={self.oficina.pk}&data=lixo")
        self.assertEqual(r.status_code, 200)

    def test_get_sem_oficina_usa_a_primeira_ativa(self):
        self.assertEqual(self.client.get("/presenca/").status_code, 200)


class SegurancaTests(BaseLogado):
    def test_post_sem_csrf_e_recusado(self):
        from django.test import Client

        c = Client(enforce_csrf_checks=True)
        c.login(username="coord", password=SENHA)
        self.assertEqual(c.post("/presenca/", {}).status_code, 403)

    def test_html_do_nome_e_escapado(self):
        services.inscrever(criar_pessoa("<script>alert(1)</script>"), self.oficina)
        r = self.client.get(f"/presenca/?oficina={self.oficina.pk}")
        self.assertNotContains(r, "<script>alert(1)</script>")
