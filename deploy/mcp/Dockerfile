FROM python:3.12-slim@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY q_speace ./q_speace
RUN python -m pip install --no-cache-dir '.[http]' && useradd --create-home --uid 1000 app
COPY deploy/mcp/entrypoint.py /app/entrypoint.py
USER app
ENV PORT=7860
EXPOSE 7860
CMD ["python", "/app/entrypoint.py"]

