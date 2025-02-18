FROM python:3.10

# 更换 apt 源为阿里云 Debian 镜像源
RUN echo "deb https://mirrors.aliyun.com/debian/ bookworm main non-free non-free-firmware contrib" > /etc/apt/sources.list
RUN echo "deb https://mirrors.aliyun.com/debian-security/ bookworm-security main" >> /etc/apt/sources.list
RUN echo "deb https://mirors.aliyun.com/debian/ bookworm-updates main non-free non-free-firmware contrib" >> /etc/apt/sources.list
RUN echo "deb https://mirrors.aliyun.com/debian/ bookworm-backports main non-free non-free-firmware contrib" >> /etc/apt/sources.list

RUN apt-get update && apt-get install -y ffmpeg

# 设置工作目录
WORKDIR /app

# 将当前目录的内容复制到容器的工作目录中
COPY . /app

RUN pip3 config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple/

# 安装任何必需的 Python 包
RUN python -m pip install --upgrade pip wheel
RUN pip install -r requirements.txt

# 创建上传目录
RUN mkdir -p uploads

# 暴露端口
EXPOSE 5000

# 启动应用
CMD ["python", "app.py"]