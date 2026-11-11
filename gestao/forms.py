import re
from datetime import date

from django import forms

from .models import Participante


class InscricaoForm(forms.Form):
    """Formulário da Tela 2 — Inscrever participante (RF01, RF04, RF05)."""

    participante_existente = forms.ModelChoiceField(
        queryset=Participante.objects.filter(ativo=True),
        required=False,
        label="Participante já cadastrado",
        empty_label="Novo participante",
    )
    nome_completo = forms.CharField(label="Nome completo", max_length=150, required=False)
    data_nascimento = forms.DateField(
        label="Data de nascimento", required=False, input_formats=["%d/%m/%Y", "%Y-%m-%d"]
    )
    telefone = forms.CharField(label="Telefone (com DDD)", max_length=20, required=False)
    nome_responsavel = forms.CharField(label="Nome do responsável", max_length=150, required=False)

    def clean_telefone(self):
        tel = self.cleaned_data.get("telefone", "").strip()
        if tel and len(re.sub(r"\D", "", tel)) not in (10, 11):
            raise forms.ValidationError("Informe o telefone com DDD. Exemplo: (00) 90000-0000")
        return tel

    def clean(self):
        dados = super().clean()
        if dados.get("participante_existente"):
            return dados
        if not dados.get("nome_completo"):
            self.add_error("nome_completo", "Informe o nome completo.")
        nasc = dados.get("data_nascimento")
        if not nasc and not self.has_error("data_nascimento"):
            self.add_error("data_nascimento", "Informe a data de nascimento. Exemplo: 10/03/2012")
        elif nasc and nasc > date.today():
            self.add_error("data_nascimento", "A data de nascimento não pode ser no futuro.")
        if not dados.get("telefone") and not self.has_error("telefone"):
            self.add_error("telefone", "Informe o telefone com DDD. Exemplo: (00) 90000-0000")
        if nasc and nasc <= date.today():
            idade = (
                date.today().year
                - nasc.year
                - ((date.today().month, date.today().day) < (nasc.month, nasc.day))
            )
            if idade < 18 and not dados.get("nome_responsavel"):
                self.add_error("nome_responsavel", "Menor de 18 anos: informe o nome do responsável.")
        return dados

    def has_error(self, campo):
        return campo in self.errors
