FROM python:3.11-slim

WORKDIR /app

# 先复制依赖清单，利用 Docker 层缓存（requirements 不变时跳过重装）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目（.dockerignore 排除 .git / .env / records.db / chroma 等）
COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501"]
