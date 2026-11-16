"""Converte DATABASE_URL (padrão de provedores como o Render) na configuração do Django."""

from urllib.parse import unquote, urlparse

ESQUEMAS_POSTGRES = {"postgres", "postgresql"}


def banco_de_url(url):
    partes = urlparse(url)
    if partes.scheme not in ESQUEMAS_POSTGRES:
        raise ValueError("DATABASE_URL deve começar com postgres:// ou postgresql://")
    nome = partes.path.lstrip("/")
    if not nome or not partes.hostname:
        raise ValueError("DATABASE_URL precisa informar o host e o nome do banco")
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": unquote(nome),
        "USER": unquote(partes.username or ""),
        "PASSWORD": unquote(partes.password or ""),
        "HOST": partes.hostname,
        "PORT": str(partes.port or 5432),
        "CONN_MAX_AGE": 60,
    }
