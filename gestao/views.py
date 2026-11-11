from datetime import date

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.cache import cache
from django.shortcuts import get_object_or_404, redirect, render

from . import services
from .forms import InscricaoForm
from .models import Inscricao, Oficina, Participante


class LoginComBloqueio(LoginView):
    """RNF01: bloqueia o usuário por 15 min após 5 tentativas com falha."""

    template_name = "registration/login.html"

    def _chave(self, usuario):
        return f"login-falhas:{usuario.lower()}"

    def post(self, request, *args, **kwargs):
        usuario = request.POST.get("username", "")
        if cache.get(self._chave(usuario), 0) >= settings.LOGIN_ATTEMPT_LIMIT:
            form = self.get_form()
            form.add_error(None, "Acesso bloqueado temporariamente. Tente novamente em 15 minutos.")
            return self.render_to_response(self.get_context_data(form=form), status=429)
        return super().post(request, *args, **kwargs)

    def form_invalid(self, form):
        chave = self._chave(self.request.POST.get("username", ""))
        cache.set(chave, cache.get(chave, 0) + 1, settings.LOGIN_LOCKOUT_SECONDS)
        return super().form_invalid(form)

    def form_valid(self, form):
        cache.delete(self._chave(form.get_user().get_username()))
        return super().form_valid(form)


@login_required
def vagas(request):
    """Tela 1 — vagas por oficina (RF03)."""
    oficinas = Oficina.objects.filter(ativa=True)
    return render(request, "gestao/vagas.html", {"oficinas": oficinas, "aba": "vagas"})


@login_required
def inscrever(request):
    """Tela 2 — inscrição com controle de vagas, espera e duplicidade (RF01, RF04, RF05)."""
    oficina = None
    oficina_id = request.POST.get("oficina") or request.GET.get("oficina")
    if oficina_id and str(oficina_id).isdigit():
        oficina = Oficina.objects.filter(pk=oficina_id, ativa=True).first()
    if oficina is None:
        messages.error(request, "Escolha uma oficina na tela de Vagas para iniciar a inscrição.")
        return redirect("vagas")

    if request.method == "POST":
        form = InscricaoForm(request.POST)
        if form.is_valid():
            dados = form.cleaned_data
            participante = dados.get("participante_existente")
            if participante is None:
                participante, _ = Participante.objects.get_or_create(
                    nome_completo=dados["nome_completo"].strip(),
                    data_nascimento=dados["data_nascimento"],
                    defaults={
                        "telefone": dados["telefone"],
                        "nome_responsavel": dados.get("nome_responsavel", ""),
                    },
                )
            try:
                inscricao = services.inscrever(participante, oficina)
            except services.InscricaoDuplicada:
                form.add_error(None, f"{participante.nome_completo} já está inscrito(a) em {oficina.nome}.")
            except services.InscricaoInvalida as erro:
                form.add_error(None, str(erro))
            else:
                oficina.refresh_from_db()
                if inscricao.situacao == Inscricao.EM_ESPERA:
                    messages.warning(
                        request,
                        f"Oficina lotada: {participante.nome_completo} entrou na lista de espera "
                        f"de {oficina.nome}.",
                    )
                else:
                    livres = oficina.vagas_livres
                    texto_vagas = "1 vaga livre" if livres == 1 else f"{livres} vagas livres"
                    messages.success(
                        request,
                        f"Inscrição confirmada: {participante.nome_completo}, {oficina.nome}. {texto_vagas}.",
                    )
                return redirect(f"/presenca/?oficina={oficina.pk}")
    else:
        form = InscricaoForm()
    return render(request, "gestao/inscrever.html", {"form": form, "oficina": oficina, "aba": "inscrever"})


@login_required
def presenca(request):
    """Tela 3 — presença e histórico de faltas (RF06, RF07)."""
    oficina_id = request.GET.get("oficina") or request.POST.get("oficina")
    oficina = None
    if oficina_id and str(oficina_id).isdigit():
        oficina = Oficina.objects.filter(pk=oficina_id, ativa=True).first()
    if oficina is None:
        oficina = Oficina.objects.filter(ativa=True).first()
    if oficina is None:
        return redirect("vagas")

    texto_data = request.GET.get("data") or request.POST.get("data")
    try:
        data_encontro = date.fromisoformat(texto_data) if texto_data else date.today()
    except ValueError:
        data_encontro = date.today()

    if request.method == "POST":
        inscricao = get_object_or_404(
            Inscricao, pk=request.POST.get("inscricao"), oficina=oficina, situacao=Inscricao.CONFIRMADA
        )
        presente = request.POST.get("presente") == "1"
        services.registrar_presenca(inscricao, data_encontro, presente)
        return redirect(f"/presenca/?oficina={oficina.pk}&data={data_encontro.isoformat()}")

    linhas = []
    for insc in oficina.inscricoes.filter(situacao=Inscricao.CONFIRMADA).select_related("participante"):
        registro = insc.presencas.filter(data_encontro=data_encontro).first()
        linhas.append(
            {
                "inscricao": insc,
                "faltas": insc.faltas,
                "alerta": insc.faltas >= settings.LIMITE_FALTAS_ALERTA,
                "estado": None if registro is None else registro.presente,
            }
        )
    contexto = {
        "oficina": oficina,
        "oficinas": Oficina.objects.filter(ativa=True),
        "data_encontro": data_encontro,
        "linhas": linhas,
        "aba": "presenca",
    }
    return render(request, "gestao/presenca.html", contexto)
