FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./src/
COPY mcp/ ./mcp/
COPY sql/ ./sql/
ENV PYTHONPATH=/app/src HR_DB=/app/data/dev.db
VOLUME ["/app/data"]
CMD ["python", "-m", "hr_demo_env.generator", "--seed", "42", "--out", "/app/data", "--db", "/app/data/dev.db"]
