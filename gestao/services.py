"""Regras de negócio (RF03 a RF08), separadas das views para facilitar os testes."""

from django.db import transaction

from .models import Inscricao, Oficina, Presenca


class InscricaoDuplicada(Exception):
    """RF05 — o participante já está inscrito (ou em espera) nesta oficina."""


class InscricaoInvalida(Exception):
    """A inscrição não pode ser feita (por exemplo, oficina inativa)."""


@transaction.atomic
def inscrever(participante, oficina):
    """RF04: confirma se houver vaga; caso contrário, entra na lista de espera."""
    oficina = Oficina.objects.select_for_update().get(pk=oficina.pk)
    if not oficina.ativa:
        raise InscricaoInvalida("Esta oficina não está ativa.")
    existente = Inscricao.objects.filter(participante=participante, oficina=oficina).first()
    if existente and existente.situacao != Inscricao.CANCELADA:
        raise InscricaoDuplicada("Esta pessoa já está inscrita nesta oficina.")
    situacao = Inscricao.CONFIRMADA if oficina.vagas_livres > 0 else Inscricao.EM_ESPERA
    if existente:  # reinscrição após cancelamento
        existente.situacao = situacao
        existente.save(update_fields=["situacao"])
        return existente
    return Inscricao.objects.create(participante=participante, oficina=oficina, situacao=situacao)


@transaction.atomic
def cancelar_inscricao(inscricao):
    """Cancela e, se havia vaga confirmada, promove o primeiro da fila (RF08)."""
    estava_confirmada = inscricao.situacao == Inscricao.CONFIRMADA
    inscricao.situacao = Inscricao.CANCELADA
    inscricao.save(update_fields=["situacao"])
    if estava_confirmada:
        return promover_fila(inscricao.oficina)
    return None


def promover_fila(oficina):
    """Promove o inscrito em espera mais antigo, se houver vaga livre."""
    if oficina.vagas_livres <= 0:
        return None
    proximo = (
        Inscricao.objects.filter(oficina=oficina, situacao=Inscricao.EM_ESPERA)
        .order_by("data_hora_inscricao")
        .first()
    )
    if proximo:
        proximo.situacao = Inscricao.CONFIRMADA
        proximo.save(update_fields=["situacao"])
    return proximo


def registrar_presenca(inscricao, data_encontro, presente):
    """RF06: cria ou atualiza a presença do encontro (uma por inscrição e data)."""
    if inscricao.situacao != Inscricao.CONFIRMADA:
        raise InscricaoInvalida("Só é possível registrar presença de inscrição confirmada.")
    obj, _ = Presenca.objects.update_or_create(
        inscricao=inscricao, data_encontro=data_encontro, defaults={"presente": presente}
    )
    return obj
