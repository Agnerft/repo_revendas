FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY api.py update_all_revendas.py update.sh ./
COPY add_revenda.py batch_fetch_v3.py export_vencidos.py json_to_excel.py ./
COPY update_emerson.py update_robson.py comandos.txt ./
COPY static ./static
COPY templates ./templates
COPY revenda*.json ./
COPY revendas_consolidadas.xlsx revendas_logins.json ./
EXPOSE 8080
CMD ["python", "api.py"]
