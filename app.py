from flask import Flask, render_template, request, jsonify, send_file, Response
import os
import zipfile
from datetime import datetime
import io
import logging
from urllib import parse
import requests
import re
import json
import time

app = Flask(__name__)

# 상수 정의
UPLOAD_FOLDER = 'files'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

DAUM_SEARCH_URL = 'https://dic.daum.net/search.do?q={}&dic=eng'
DAUM_WORD_URL = 'https://dic.daum.net/word/view.do?wordid={}&q={}'

# 정규식 패턴 목록
PATTERNS = {
    'redirect': re.compile('<meta http-equiv="Refresh" content="0; URL=/word/view\\.do\\?wordid=([^&]+)&q='),
    'audio_link': re.compile('<a href="(http://t1\\.daumcdn\\.net/language/[^"]+)"')
}

def get_audio_url(word: str):
    """단어에 대한 오디오 URL을 검색"""
    encoded_word = parse.quote(word)
    
    # 첫 번째 검색
    res = requests.get(DAUM_SEARCH_URL.format(encoded_word))
    res.raise_for_status()
    
    # 리디렉션 확인
    redirect_match = PATTERNS['redirect'].findall(res.text)
    if redirect_match:
        # 리디렉션된 페이지 검색
        res = requests.get(DAUM_WORD_URL.format(redirect_match[0], encoded_word))
        res.raise_for_status()
    
    # 오디오 링크 찾기
    audio_links = PATTERNS['audio_link'].findall(res.text)
    return audio_links[0] if audio_links else None

def download_audio(url: str, filename: str):
    """오디오 파일 다운로드"""
    response = requests.get(url)
    response.raise_for_status()
    
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    with open(filepath, 'wb') as file:
        file.write(response.content)
    return filepath

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process():
    try:
        data = request.json
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        zip_filename = f'audio_files_{timestamp}.zip'
        
        # 음원 파일 다운로드
        downloaded_files = []
        for row in data:
            try:
                sticker_no = row['sticker_no'].strip()
                word = row['word'].strip()
                
                if sticker_no and word:  # 빈 행 무시
                    filename = f"REC1_{sticker_no}.mp3"
                    filepath = os.path.join(UPLOAD_FOLDER, filename)
                    
                    # 이미 존재하는 파일 확인
                    if not os.path.exists(filepath):
                        audio_url = get_audio_url(word)
                        if audio_url:
                            filepath = download_audio(audio_url, filename)
                    
                    if os.path.exists(filepath):
                        downloaded_files.append(filepath)
                    
            except Exception as e:
                logging.error(f"Error processing {word}: {str(e)}")
                continue
        
        # ZIP 파일 생성
        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file in downloaded_files:
                zf.write(file, os.path.basename(file))
        
        memory_file.seek(0)
        
        return send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name=zip_filename
        )

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/progress', methods=['GET'])
def progress():
    def generate():
        for i in range(0, 101, 10):
            time.sleep(0.1)  # 실제 진행 상황을 시뮬레이션
            yield f"data: {json.dumps({'progress': i})}\n\n"
    return Response(generate(), mimetype='text/event-stream')

@app.route('/download-zip', methods=['POST'])
def download_zip():
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        zip_filename = f'audio_files_{timestamp}.zip'
        
        # ZIP 파일 생성
        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file in os.listdir(UPLOAD_FOLDER):
                if file.endswith('.mp3'):
                    filepath = os.path.join(UPLOAD_FOLDER, file)
                    zf.write(filepath, file)
        
        memory_file.seek(0)
        
        return send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name=zip_filename
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
