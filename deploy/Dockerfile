# Web 展示服务镜像（在飞牛 NAS 上以容器运行）
FROM python:3.10-slim

ENV TZ=Asia/Shanghai \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["python", "run_web.py", "--host", "0.0.0.0", "--port", "5000"]
