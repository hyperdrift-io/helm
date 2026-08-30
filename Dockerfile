FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv && uv export --frozen --no-dev -o req.txt && \
    pip install --no-cache-dir -r req.txt
COPY helm ./helm
COPY assets ./assets
ENV GOOGLE_GENAI_USE_VERTEXAI=TRUE GOOGLE_CLOUD_LOCATION=global
CMD ["python", "-m", "helm"]
