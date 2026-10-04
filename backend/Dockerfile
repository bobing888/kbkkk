FROM python:3.11-slim

WORKDIR /app

# 系统依赖（ta-lib 需要）
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    wget \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# ta-lib C 库
RUN wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz && \
    tar -xzf ta-lib-0.4.0-src.tar.gz && \
    cd ta-lib/ && \
    ./configure --prefix=/usr && \
    make && \
    make install && \
    cd .. && \
    rm -rf ta-lib ta-lib-0.4.0-src.tar.gz

# Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 应用代码
COPY . .

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
