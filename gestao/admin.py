from django.contrib import admin

from .models import Inscricao, Oficina, Participante, Presenca

admin.site.register([Participante, Oficina, Inscricao, Presenca])
