# 使用轻量级 Python 镜像
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

# Hugging Face Spaces 默认监听 7860 端口
ENV PORT=7860
EXPOSE 7860

# 运行服务
CMD ["python", "app.py"]
