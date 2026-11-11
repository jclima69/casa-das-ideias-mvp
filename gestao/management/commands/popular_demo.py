"""Carrega dados fictícios (gerados por IA) e cria o usuário de demonstração."""

import datetime as dt

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from gestao.models import Inscricao, Oficina, Participante, Presenca


class Command(BaseCommand):
    help = "Cria oficinas, participantes e presenças fictícias e o usuário de demonstração."

    def add_arguments(self, parser):
        parser.add_argument("--usuario", default="coordenacao")
        parser.add_argument("--senha", required=True, help="mínimo de 10 caracteres")

    def handle(self, *args, **opts):
        if len(opts["senha"]) < 10:
            raise CommandError("A senha precisa ter pelo menos 10 caracteres (RNF01).")
        User = get_user_model()
        user, criado = User.objects.get_or_create(username=opts["usuario"])
        user.set_password(opts["senha"])
        user.save()

        T = dt.time
        violao, _ = Oficina.objects.get_or_create(
            nome="Violão iniciante",
            defaults=dict(
                area="Música",
                instrutor="Instrutor fictício A",
                dia_semana=5,
                horario_inicio=T(9),
                horario_fim=T(10, 30),
                vagas=10,
            ),
        )
        teatro, _ = Oficina.objects.get_or_create(
            nome="Teatro",
            defaults=dict(
                area="Artes cênicas",
                instrutor="Instrutora fictícia B",
                dia_semana=2,
                horario_inicio=T(18),
                horario_fim=T(19, 30),
                vagas=12,
            ),
        )
        audio, _ = Oficina.objects.get_or_create(
            nome="Audiovisual",
            defaults=dict(
                area="Audiovisual",
                instrutor="Instrutor fictício C",
                dia_semana=1,
                horario_inicio=T(14),
                horario_fim=T(16),
                vagas=15,
            ),
        )

        def pessoa(nome, ano):
            p, _ = Participante.objects.get_or_create(
                nome_completo=nome,
                data_nascimento=dt.date(ano, 5, 20),
                defaults={"telefone": "(00) 90000-0000"},
            )
            return p

        base = [
            pessoa(n, 1995 + i)
            for i, n in enumerate(["Ana Lima", "Bruno Alves", "Carla Dias", "Diego Rocha"])
        ]
        for p in base[:3]:
            Inscricao.objects.get_or_create(participante=p, oficina=violao)
        # Teatro lotado, com 2 em espera.
        for i in range(12):
            Inscricao.objects.get_or_create(
                participante=pessoa(f"Participante Teatro {i + 1:02d}", 1990 + i), oficina=teatro
            )
        for i in range(2):
            Inscricao.objects.get_or_create(
                participante=pessoa(f"Espera Teatro {i + 1}", 2000 + i),
                oficina=teatro,
                defaults={"situacao": Inscricao.EM_ESPERA},
            )
        for i in range(9):
            Inscricao.objects.get_or_create(
                participante=pessoa(f"Participante Audio {i + 1:02d}", 1985 + i), oficina=audio
            )

        # Histórico de faltas: Bruno 2, Carla 1.
        faltas = {
            "Bruno Alves": [dt.date(2026, 10, 24), dt.date(2026, 10, 31)],
            "Carla Dias": [dt.date(2026, 10, 31)],
        }
        for nome, datas in faltas.items():
            insc = Inscricao.objects.get(participante__nome_completo=nome, oficina=violao)
            for d in datas:
                Presenca.objects.get_or_create(inscricao=insc, data_encontro=d, defaults={"presente": False})
        self.stdout.write(self.style.SUCCESS("Dados fictícios (gerados por IA) carregados."))
