FROM python:3.12-slim AS build
WORKDIR /build
COPY requirements.lock ./
RUN python -m pip install --no-cache-dir --prefix=/install -r requirements.lock
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN python -m pip install --no-cache-dir --no-deps --prefix=/install .

FROM python:3.12-slim
RUN groupadd --gid 10001 connector && useradd --uid 10001 --gid connector --no-create-home connector \
    && mkdir /data && chown connector:connector /data
COPY --from=build /install /usr/local
WORKDIR /app
COPY scripts/setup.py /app/scripts/setup.py
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 DATA_DIR=/data HOST=0.0.0.0
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz',timeout=3)"
CMD ["bitpin-ai-connector", "serve", "--transport", "http"]
