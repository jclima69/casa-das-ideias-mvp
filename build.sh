#!/usr/bin/env bash
# Comando de build para a hospedagem (Render): instala, coleta estáticos, migra e, se pedido, carrega os dados fictícios.
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate --noinput

if [ -n "$DEMO_SENHA" ]; then
  python manage.py popular_demo --senha "$DEMO_SENHA"
fi
