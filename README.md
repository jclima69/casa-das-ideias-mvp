# Casa das Ideias — MVP de gestão de oficinas

MVP de um sistema web para a **Casa das Ideias** (centro comunitário de cultura, educação e criatividade),
que hoje controla inscrições, vagas e presença por WhatsApp, cadernos e planilhas. O sistema reúne esses
controles em três telas pensadas para uso no celular: **Vagas**, **Inscrição** e **Presença**.

Projeto da disciplina de Projeto de Software (ADS). Alinhado ao **ODS 4** (Educação de Qualidade, metas 4.4 e 4.7).

## Nota sobre os dados e a pesquisa de campo

A investigação com o parceiro e as rodadas de validação foram feitas por **modelo fictício, com dados gerados
por inteligência artificial (IA)**. O motivo é que a autoria **não pôde realizar pesquisa de campo por problemas
de saúde**, e o modelo foi **autorizado pelo tutor**. Nomes, participantes, falas, tempos e notas
são ilustrativos e **não representam pessoas reais**. Os dados de demonstração também são fictícios.

## Funcionalidades

| Requisito | O que faz |
|---|---|
| RF01 | Cadastro de participante (menores informam o responsável) |
| RF03 | Vagas livres, ocupadas e em espera por oficina |
| RF04 | Inscrição com confirmação ou lista de espera quando a oficina está lotada |
| RF05 | Bloqueio de inscrição duplicada |
| RF06 | Registro de presença por encontro |
| RF07 | Histórico de faltas com alerta (⚠) a partir de 2 faltas |
| RF08 | Promoção automática do primeiro da fila ao cancelar uma vaga (serviço testado; sem tela ainda) |
| RNF01 | Login em todas as telas, hash Argon2, senha com 10+ caracteres, sessão de 30 min, bloqueio por 15 min após 5 falhas |
| RNF02 | CSRF, escape de HTML, cookies seguros em produção (HTTPS, HSTS) |
| RNF04 | Estado por texto + símbolo + cor, áreas de toque de 48 px, rótulos associados, foco visível |

O cadastro de oficinas (RF02) é feito pelo painel `/admin/`, fora do escopo das três telas.

## Tecnologias

Python 3.12+, Django 5.2 LTS (MVT em camadas), CSS próprio responsivo, argon2-cffi, WhiteNoise, Gunicorn.
SQLite em desenvolvimento e PostgreSQL em produção (variáveis `POSTGRES_*`).

## Como executar

```bash
python -m venv venv
source venv/bin/activate            # Windows: venv\Scripts\activate
pip install -r requirements-dev.txt
python manage.py migrate
python manage.py popular_demo --senha "uma-senha-com-10+-caracteres"
python manage.py runserver
```

Abra http://127.0.0.1:8000/ e entre com o usuário `coordenacao` e a senha que você definiu.

## Testes e qualidade

```bash
python manage.py test                  # 52 testes unitários e de integração
ruff check . && ruff format --check .  # lint e formatação
coverage run manage.py test && coverage report
```

A Integração Contínua (`.github/workflows/ci.yml`) roda lint, verificação de migrações, testes e
cobertura mínima de 85% a cada *push* na `main` e a cada *Pull Request*.

## Fluxo de trabalho (Git)

- Branches curtas por funcionalidade: `feature/...`, `fix/...`, `docs/...`.
- *Commits* semânticos (`feat:`, `fix:`, `test:`, `docs:`, `ci:`, `chore:`).
- Integração à `main` somente por **Pull Request**, com auto-revisão e CI verde.

## Estrutura

```
config/            configurações do Django
gestao/            app: models, services (regras), forms, views, templates, testes
docs/validacao/    fichas das rodadas de validação (dados fictícios gerados por IA)
.github/workflows/ CI
```

## Produção

Defina `DJANGO_DEBUG=0`, `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS` e as variáveis `POSTGRES_*`;
execute `python manage.py collectstatic --noinput` e sirva com `gunicorn config.wsgi`.
