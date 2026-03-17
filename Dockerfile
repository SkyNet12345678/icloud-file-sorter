FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml ./

RUN pip install --upgrade pip && pip install .


# Copy source code
COPY app ./app

CMD ["python", "-m", "app.main"]
