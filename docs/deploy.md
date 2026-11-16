# Publicação na nuvem (Render)

Guia de implantação do MVP **Casa das Ideias** em ambiente de produção.

## Serviços

1. **PostgreSQL** (Render → New → PostgreSQL). Copie a *Internal Database URL*.
2. **Web Service** (Render → New → Web Service), ligado ao repositório GitHub.

## Web Service

| Campo | Valor |
|---|---|
| Runtime | Python 3 |
| Build Command | `./build.sh` |
| Start Command | `gunicorn config.wsgi:application --workers 1 --bind 0.0.0.0:$PORT` |
| Health Check Path | `/saude/` |

Use **1 worker**: o bloqueio de login (5 falhas em 15 min) usa cache em memória do processo.

## Variáveis de ambiente

| Variável | Valor |
|---|---|
| `DATABASE_URL` | Internal Database URL do PostgreSQL |
| `DJANGO_SECRET_KEY` | texto longo e aleatório (Render pode gerar) |
| `DJANGO_DEBUG` | `0` |
| `PYTHON_VERSION` | `3.12.7` |
| `DEMO_SENHA` | (opcional) senha com 10+ caracteres; se definida, o build cria o usuário `coordenacao` e os dados fictícios de demonstração |

O Render define `RENDER_EXTERNAL_HOSTNAME` automaticamente; o sistema o usa em `ALLOWED_HOSTS` e `CSRF_TRUSTED_ORIGINS`.

## Monitoramento

`GET /saude/` responde `{"status": "ok"}` (200) quando a aplicação e o banco funcionam, e 503 caso contrário.
Aponte um monitor externo de disponibilidade para essa URL.

## Avisos

- No plano gratuito o serviço "adormece" após inatividade e a primeira requisição pode levar cerca de 1 minuto.
- O banco gratuito pode expirar; confira as condições vigentes na documentação oficial do Render.
- Os dados de demonstração são **fictícios**. Não cadastre dados pessoais reais.
