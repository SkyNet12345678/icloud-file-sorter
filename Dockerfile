FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /workspace

COPY pyproject.toml README.md requirements.txt ./
COPY app ./app
COPY tests ./tests

RUN pip install --upgrade pip \
    && pip install -r requirements.txt \
    && pip install -e .

CMD ["bash"]
