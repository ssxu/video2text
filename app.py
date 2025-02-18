import os
from flask import Flask, request, jsonify, send_file, render_template
from werkzeug.utils import secure_filename
from pydub import AudioSegment
import webrtcvad
import numpy as np
import soundfile as sf
import requests
import time
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# 配置上传文件存储路径
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 允许的文件类型
ALLOWED_EXTENSIONS = {'mp4', 'wav', 'mp3', 'aac', 'm4a'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def process_audio(audio_path):
    # 获取音频文件信息
    audio = AudioSegment.from_file(audio_path)
    audio = audio.set_channels(1)  # 转换为单声道
    audio = audio.set_frame_rate(16000)  # 设置采样率为16kHz
    
    # 每5分钟切割一段
    segment_duration = 5 * 60 * 1000  # 5分钟，转换为毫秒
    segments = []
    
    # 分段处理音频
    for start_time in range(0, len(audio), segment_duration):
        end_time = min(start_time + segment_duration, len(audio))
        segment = audio[start_time:end_time]
        
        # 只添加长度超过1秒的片段
        if len(segment) > 1000:
            segments.append(segment)
    
    return segments

def transcribe_segment(segment, api_token, max_retries=5):
    # 使用绝对路径
    temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), app.config['UPLOAD_FOLDER'])
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
    
    # 使用唯一的临时文件名
    temp_filename = f'temp_{int(time.time())}_{os.getpid()}.wav'
    temp_path = os.path.join(temp_dir, temp_filename)
    
    try:
        # 保存临时音频文件
        segment.export(temp_path, format='wav')
        url = "https://api.siliconflow.cn/v1/audio/transcriptions"
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Connection": "keep-alive",
            "User-Agent": "Mozilla/5.0"
        }
        
        retry_count = 0
        while retry_count < max_retries:
            try:
                # 添加1秒延迟
                time.sleep(1)
                
                session = requests.Session()
                adapter = requests.adapters.HTTPAdapter(
                    max_retries=3,
                    pool_connections=10,
                    pool_maxsize=10,
                    pool_block=False
                )
                session.mount('https://', adapter)
                
                with open(temp_path, 'rb') as audio_file:
                    files = {
                        'file': ('audio.wav', audio_file, 'audio/wav'),
                        'model': (None, 'FunAudioLLM/SenseVoiceSmall')
                    }
                    response = session.post(
                        url, 
                        headers=headers, 
                        files=files, 
                        timeout=(30, 300),  # (连接超时, 读取超时)
                        verify=True
                    )
                    
                    if response.status_code == 200:
                        return response.json().get('text', '')
                    elif response.status_code == 429:  # Rate limit
                        retry_after = int(response.headers.get('Retry-After', 30))
                        time.sleep(retry_after)
                    else:
                        print(f"API调用失败: {response.status_code} - {response.text}")
                        time.sleep(5 * (retry_count + 1))  # 递增等待时间
                        
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                print(f"网络错误 (尝试 {retry_count + 1}/{max_retries}): {str(e)}")
                if retry_count < max_retries - 1:
                    wait_time = min(2 ** retry_count * 5, 60)  # 最大等待60秒
                    time.sleep(wait_time)
                    retry_count += 1
                    continue
                raise Exception(f"网络连接错误: {str(e)}")
            
            finally:
                session.close()
                
            retry_count += 1
            
    except Exception as e:
        print(f"转写错误: {str(e)}")
        raise Exception(f"转写过程发生错误: {str(e)}")
        
    finally:
        # 确保清理临时文件
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception as e:
            print(f"清理临时文件失败: {str(e)}")
    
    return ''

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': '没有文件上传'}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '没有选择文件'}), 400
        
    if not allowed_file(file.filename):
        return jsonify({'error': '不支持的文件类型'}), 400

    api_token = os.getenv('API_TOKEN')
    if not api_token:
        return jsonify({'error': 'API token未配置'}), 500

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    try:
        # 处理音频并进行VAD分段
        segments = process_audio(filepath)
        
        # 转写每个分段并拼接结果
        transcription = []
        for segment in segments:
            text = transcribe_segment(segment, api_token)
            if text:
                transcription.append(text)
        
        # 保存转写结果
        result_filename = f"{os.path.splitext(filename)[0]}_transcription.txt"
        result_path = os.path.join(app.config['UPLOAD_FOLDER'], result_filename)
        with open(result_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(transcription))
        
        return jsonify({
            'success': True,
            'text': '\n'.join(transcription),
            'filename': result_filename
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        # 清理上传的原始文件
        if os.path.exists(filepath):
            os.remove(filepath)

@app.route('/download/<filename>')
def download_file(filename):
    try:
        return send_file(
            os.path.join(app.config['UPLOAD_FOLDER'], filename),
            as_attachment=True
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)