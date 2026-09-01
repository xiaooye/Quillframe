FROM python:3.14-slim

RUN useradd --create-home --uid 10001 quillframe
WORKDIR /tmp/quillframe-build
COPY pyproject.toml /tmp/quillframe-build/pyproject.toml
COPY quillframe /tmp/quillframe-build/quillframe
COPY studio /tmp/quillframe-build/studio
COPY persistence /tmp/quillframe-build/persistence
COPY production_runtime /tmp/quillframe-build/production_runtime
COPY corpus /tmp/quillframe-build/corpus
COPY surface /tmp/quillframe-build/surface
COPY publication /tmp/quillframe-build/publication
COPY quality /tmp/quillframe-build/quality
COPY learning /tmp/quillframe-build/learning
COPY model_runtime /tmp/quillframe-build/model_runtime
COPY harness /tmp/quillframe-build/harness
COPY agent_runtime /tmp/quillframe-build/agent_runtime
COPY core_operations.py project_resolution.py /tmp/quillframe-build/
RUN python -m pip wheel --no-cache-dir --no-deps . --wheel-dir /tmp/quillframe-wheel \
    && python -m pip install --no-cache-dir --no-deps /tmp/quillframe-wheel/quillframe-*.whl \
    && install -d -o quillframe -g quillframe /srv/quillframe
WORKDIR /srv/quillframe

USER quillframe
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    QUILLFRAME_CLOUD_CORE=1 \
    QUILLFRAME_DATA_DIR=/tmp/quillframe-cloud
EXPOSE 8080
CMD ["python", "-m", "quillframe.cloud_core", "--host", "0.0.0.0", "--port", "8080"]
