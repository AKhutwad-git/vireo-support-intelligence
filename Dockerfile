FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    HOME=/home/vireo \
    VIREO_INTERIM_DIR=/app/runtime-data

WORKDIR /app

COPY requirements.lock /tmp/requirements.lock
RUN python -m pip install --no-cache-dir --require-hashes -r /tmp/requirements.lock \
    && groupadd --system vireo \
    && useradd --system --gid vireo --create-home vireo \
    && mkdir -p /app/runtime-data /home/vireo/.streamlit \
    && chown -R vireo:vireo /app/runtime-data /home/vireo

COPY --chown=vireo:vireo app /app/app
COPY --chown=vireo:vireo src /app/src
COPY --chown=vireo:vireo .streamlit/config.toml /app/.streamlit/config.toml

USER vireo
EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s --start-period=45s --retries=3 CMD ["python", "-m", "app.healthcheck"]
ENTRYPOINT ["python", "-m", "streamlit", "run", "app/streamlit_app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]
