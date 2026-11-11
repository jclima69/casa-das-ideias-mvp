"""Modelos de dados: Participante, Oficina, Inscrição e Presença."""

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class Participante(models.Model):
    nome_completo = models.CharField("Nome completo", max_length=150)
    data_nascimento = models.DateField("Data de nascimento")
    telefone = models.CharField("Telefone", max_length=20)
    nome_responsavel = models.CharField("Nome do responsável", max_length=150, blank=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nome_completo"]
        constraints = [
            models.UniqueConstraint(fields=["nome_completo", "data_nascimento"], name="participante_unico")
        ]

    def __str__(self):
        return self.nome_completo

    def idade_em(self, data):
        anos = data.year - self.data_nascimento.year
        if (data.month, data.day) < (self.data_nascimento.month, self.data_nascimento.day):
            anos -= 1
        return anos


class Oficina(models.Model):
    DIAS = [
        (0, "Segunda"),
        (1, "Terça"),
        (2, "Quarta"),
        (3, "Quinta"),
        (4, "Sexta"),
        (5, "Sábado"),
        (6, "Domingo"),
    ]
    nome = models.CharField(max_length=100)
    area = models.CharField("Área", max_length=60)
    instrutor = models.CharField(max_length=100)
    dia_semana = models.PositiveSmallIntegerField(choices=DIAS)
    horario_inicio = models.TimeField()
    horario_fim = models.TimeField()
    vagas = models.PositiveIntegerField()
    ativa = models.BooleanField(default=True)

    class Meta:
        ordering = ["nome"]
        verbose_name_plural = "oficinas"
        constraints = [models.CheckConstraint(condition=Q(vagas__gt=0), name="oficina_vagas_positivas")]

    def __str__(self):
        return self.nome

    @property
    def vagas_ocupadas(self):
        return self.inscricoes.filter(situacao=Inscricao.CONFIRMADA).count()

    @property
    def vagas_livres(self):
        return max(self.vagas - self.vagas_ocupadas, 0)

    @property
    def em_espera(self):
        return self.inscricoes.filter(situacao=Inscricao.EM_ESPERA).count()

    @property
    def lotada(self):
        return self.vagas_livres == 0

    @property
    def horario_texto(self):
        dia = self.get_dia_semana_display()
        ini, fim = self.horario_inicio, self.horario_fim

        def fmt(t):
            return f"{t.hour}h" if t.minute == 0 else f"{t.hour}h{t.minute:02d}"

        return f"{dia}, {fmt(ini)} às {fmt(fim)}"


class Inscricao(models.Model):
    CONFIRMADA = "confirmada"
    EM_ESPERA = "em_espera"
    CANCELADA = "cancelada"
    SITUACOES = [(CONFIRMADA, "Confirmada"), (EM_ESPERA, "Em espera"), (CANCELADA, "Cancelada")]

    participante = models.ForeignKey(Participante, on_delete=models.CASCADE, related_name="inscricoes")
    oficina = models.ForeignKey(Oficina, on_delete=models.CASCADE, related_name="inscricoes")
    situacao = models.CharField(max_length=12, choices=SITUACOES, default=CONFIRMADA)
    data_hora_inscricao = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["data_hora_inscricao"]
        verbose_name = "inscrição"
        verbose_name_plural = "inscrições"
        constraints = [models.UniqueConstraint(fields=["participante", "oficina"], name="inscricao_unica")]

    def __str__(self):
        return f"{self.participante} em {self.oficina} ({self.situacao})"

    @property
    def faltas(self):
        return self.presencas.filter(presente=False).count()


class Presenca(models.Model):
    inscricao = models.ForeignKey(Inscricao, on_delete=models.CASCADE, related_name="presencas")
    data_encontro = models.DateField()
    presente = models.BooleanField()

    class Meta:
        ordering = ["data_encontro"]
        verbose_name = "presença"
        verbose_name_plural = "presenças"
        constraints = [models.UniqueConstraint(fields=["inscricao", "data_encontro"], name="presenca_unica")]

    def clean(self):
        if self.inscricao_id and self.inscricao.situacao != Inscricao.CONFIRMADA:
            raise ValidationError("Só é possível registrar presença de inscrição confirmada.")

    def __str__(self):
        return f"{self.inscricao} - {self.data_encontro}: {'presente' if self.presente else 'ausente'}"
