from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

urlpatterns = [
    path("", views.vagas, name="vagas"),
    path("inscrever/", views.inscrever, name="inscrever"),
    path("presenca/", views.presenca, name="presenca"),
    path("entrar/", views.LoginComBloqueio.as_view(), name="login"),
    path("sair/", LogoutView.as_view(), name="logout"),
]
