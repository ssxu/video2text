# 音视频转文字应用

一个基于Flask的Web应用，可以将音频和视频文件转换为文字。支持多种音视频格式，并提供简单直观的用户界面。

## 功能特点

- 支持多种音视频格式（mp4, wav, mp3, aac, m4a）
- 自动音频分段处理，支持长音频文件
- 智能音频转写，使用先进的语音识别模型
- 简洁的Web界面，操作便捷
- 支持转写结果下载
- 自动清理临时文件
- 内置重试机制，提高转写稳定性

## 环境要求

- Python 3.9+
- FFmpeg
- Docker（可选，用于容器化部署）

## API Token 申请

在使用本应用之前，您需要：
1. 访问 [硅基云平台](https://cloud.siliconflow.cn/) 注册账号
2. 在平台中申请 API Token
3. 将获取到的 Token 配置到应用中

## 安装部署

### 方法一：直接部署

1. 克隆项目并安装依赖：
```bash
pip install -r requirements.txt
```

2. 配置环境变量：
创建 `.env` 文件并设置API Token：
```
API_TOKEN=your_api_token_here
```

3. 运行应用：
```bash
python app.py
```
应用将在 http://localhost:5000 启动

### 方法二：Docker部署

1. 构建Docker镜像：
```bash
docker build -t video2text .
```

2. 运行容器：
```bash
docker run -p 5000:5000 -e API_TOKEN=your_api_token_here video2text
```

## 使用方法

1. 打开浏览器访问 http://localhost:5000
2. 点击选择文件，上传音频或视频文件
3. 点击"开始转换