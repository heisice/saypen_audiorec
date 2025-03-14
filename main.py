import os
import sys
import time
import json
import requests
import re
from urllib import parse
from datetime import datetime
import zipfile
import io
import threading
import socket
from flask import Flask, request, jsonify, send_file, Response
from waitress import serve
import logging

# PyQt5 임포트
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel, QStatusBar
from PyQt5.QtCore import QUrl, Qt, QSize
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtGui import QIcon, QFont

# 상수 정의
UPLOAD_FOLDER = os.path.join(os.path.expanduser('~'), 'Documents', '세이펜_오디오')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Flask 앱 설정
app = Flask(__name__)
app.logger.disabled = True
log = logging.getLogger('werkzeug')
log.disabled = True

# 정규식 패턴 목록
PATTERNS = {
    'redirect': re.compile('<meta http-equiv="Refresh" content="0; URL=/word/view\\.do\\?wordid=([^&]+)&q='),
    'audio_link': re.compile('<a href="(http://t1\\.daumcdn\\.net/language/[^"]+)"')
}

DAUM_SEARCH_URL = 'https://dic.daum.net/search.do?q={}&dic=eng'
DAUM_WORD_URL = 'https://dic.daum.net/word/view.do?wordid={}&q={}'

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
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>세이펜 오디오랙 영어단어 파일 생성기</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 10px;
                background-color: #f5f5f5;
            }
            .container {
                max-width: 100%;
                margin: 0 auto;
                background-color: white;
                padding: 15px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            h1 {
                color: #333;
                margin-top: 0;
                font-size: 1.5em;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                margin-top: 15px;
            }
            th, td {
                padding: 8px;
                border: 1px solid #ddd;
                text-align: left;
            }
            th {
                background-color: #f2f2f2;
            }
            input[type="text"] {
                width: 100%;
                padding: 6px;
                box-sizing: border-box;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
            button {
                background-color: #4CAF50;
                color: white;
                padding: 8px 12px;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                margin-top: 10px;
                margin-right: 5px;
            }
            button:hover {
                background-color: #45a049;
            }
            .delete-link {
                color: #f44336;
                text-decoration: none;
                cursor: pointer;
                font-size: 0.9em;
            }
            .delete-link:hover {
                text-decoration: underline;
                color: #d32f2f;
            }
            .progress {
                margin-top: 15px;
                display: none;
            }
            .progress-bar {
                width: 100%;
                background-color: #f3f3f3;
                border-radius: 4px;
                padding: 2px;
            }
            .progress-bar-fill {
                height: 16px;
                background-color: #4CAF50;
                border-radius: 4px;
                width: 0%;
                transition: width 0.3s;
            }
            .status-text {
                margin: 5px 0;
                font-size: 0.9em;
                color: #666;
            }
        </style>
    </head>
    <body oncontextmenu="return false;">
        <div class="container">
            <h1>세이펜 오디오랙 영어단어 파일 생성기</h1>
            
            <p style="margin: 8px 0;">스티커 번호와 단어를 입력하세요. 단어 입력 후 엔터를 누르면 새 행이 추가됩니다.</p>
            
            <table id="wordTable">
                <thead>
                    <tr>
                        <th style="width: 30%">스티커 번호</th>
                        <th style="width: 60%">단어</th>
                        <th style="width: 10%">삭제</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td><input type="text" class="sticker-no" placeholder="스티커 번호" value="1"></td>
                        <td><input type="text" class="word" placeholder="단어"></td>
                        <td style="text-align: center;"><a href="javascript:void(0);" class="delete-link" onclick="deleteRow(this)">삭제</a></td>
                    </tr>
                </tbody>
            </table>
            
            <div style="margin-top: 10px;">
                <button onclick="processAllData()">단어 일괄 다운로드</button>
                <button onclick="openFolder()">저장 폴더 열기</button>
            </div>
            
            <div class="progress" id="progressContainer">
                <p class="status-text" id="statusText">다운로드 준비 중...</p>
                <div class="progress-bar">
                    <div class="progress-bar-fill" id="progressBar"></div>
                </div>
                <p class="status-text" id="progressText">0%</p>
            </div>
        </div>
        
        <script>
            // 마우스 오른쪽 버튼 비활성화
            document.addEventListener('contextmenu', function(e) {
                e.preventDefault();
                return false;
            }, false);
            
            // 키보드 단축키 비활성화 (선택적)
            document.addEventListener('keydown', function(e) {
                // Ctrl+S, Ctrl+P, Ctrl+U, F12 등 비활성화
                if ((e.ctrlKey && (e.key === 's' || e.key === 'p' || e.key === 'u')) || 
                    e.key === 'F12') {
                    e.preventDefault();
                    return false;
                }
            }, false);
            
            // 페이지 로드 시 첫 번째 단어 입력 필드에 이벤트 리스너 추가
            document.addEventListener('DOMContentLoaded', function() {
                setupWordInputListeners();
            });
            
            // 단어 입력 필드에 이벤트 리스너 추가하는 함수
            function setupWordInputListeners() {
                const wordInputs = document.querySelectorAll('.word');
                wordInputs.forEach(input => {
                    if (!input.hasAttribute('data-has-listener')) {
                        input.setAttribute('data-has-listener', 'true');
                        input.addEventListener('keypress', function(e) {
                            if (e.key === 'Enter') {
                                e.preventDefault();
                                addRowWithIncrement(this);
                            }
                        });
                    }
                });
            }
            
            // 0 패딩을 유지하면서 숫자 증가시키는 함수
            function incrementWithPadding(stickerNo) {
                // 숫자가 아닌 경우 기본값 1 반환
                if (!stickerNo || isNaN(parseInt(stickerNo))) {
                    return "1";
                }
                
                // 앞의 0 개수 확인
                const leadingZeros = stickerNo.match(/^0*/)[0].length;
                
                // 숫자 부분만 추출하여 증가
                const numericPart = parseInt(stickerNo);
                const incremented = numericPart + 1;
                
                // 증가된 숫자를 문자열로 변환
                let result = incremented.toString();
                
                // 원래 숫자의 길이보다 증가된 숫자의 길이가 길어진 경우 (예: 999 -> 1000)
                // 0 패딩을 하나 줄임
                const originalNumericLength = numericPart.toString().length;
                const newNumericLength = result.length;
                const paddingLength = Math.max(0, leadingZeros - (newNumericLength - originalNumericLength));
                
                // 필요한 만큼 0 패딩 추가
                result = '0'.repeat(paddingLength) + result;
                
                return result;
            }
            
            // 엔터 키로 행 추가 및 스티커 번호 증가 함수
            function addRowWithIncrement(wordInput) {
                const currentRow = wordInput.closest('tr');
                const tbody = document.querySelector('#wordTable tbody');
                const currentStickerNo = currentRow.querySelector('.sticker-no').value;
                
                // 새 스티커 번호 계산 (0 패딩 유지)
                const newStickerNo = incrementWithPadding(currentStickerNo);
                
                const newRow = document.createElement('tr');
                newRow.innerHTML = `
                    <td><input type="text" class="sticker-no" placeholder="스티커 번호" value="${newStickerNo}"></td>
                    <td><input type="text" class="word" placeholder="단어"></td>
                    <td style="text-align: center;"><a href="javascript:void(0);" class="delete-link" onclick="deleteRow(this)">삭제</a></td>
                `;
                tbody.appendChild(newRow);
                
                // 새 행의 단어 입력 필드에 이벤트 리스너 추가
                setupWordInputListeners();
                
                // 새 행의 단어 입력 필드에 포커스
                const newWordInput = newRow.querySelector('.word');
                newWordInput.focus();
            }
            
            // 행 삭제 함수
            function deleteRow(link) {
                const row = link.closest('tr');
                const tbody = document.querySelector('#wordTable tbody');
                
                // 테이블에 최소 1개의 행은 유지
                if (tbody.rows.length > 1) {
                    row.remove();
                } else {
                    // 마지막 행은 삭제하지 않고 내용만 비움
                    row.querySelector('.sticker-no').value = "1";
                    row.querySelector('.word').value = "";
                }
            }
            
            function processAllData() {
                const rows = document.querySelectorAll('#wordTable tbody tr');
                const data = [];
                
                rows.forEach(row => {
                    const stickerNo = row.querySelector('.sticker-no').value;
                    const word = row.querySelector('.word').value;
                    
                    if (stickerNo && word) {
                        data.push({
                            sticker_no: stickerNo,
                            word: word
                        });
                    }
                });
                
                if (data.length === 0) {
                    alert('데이터를 입력해주세요.');
                    return;
                }
                
                // 진행 표시줄 표시
                document.getElementById('progressContainer').style.display = 'block';
                document.getElementById('statusText').textContent = '단어 다운로드 중...';
                
                // 진행 상황 이벤트 소스 설정
                const eventSource = new EventSource('/progress');
                eventSource.onmessage = function(event) {
                    const data = JSON.parse(event.data);
                    document.getElementById('progressBar').style.width = data.progress + '%';
                    document.getElementById('progressText').textContent = data.progress + '%';
                    
                    if (data.progress >= 100) {
                        document.getElementById('statusText').textContent = '다운로드 완료!';
                        eventSource.close();
                    }
                };
                
                // 데이터 전송
                fetch('/process', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(data)
                })
                .then(response => {
                    if (!response.ok) {
                        throw new Error('서버 오류');
                    }
                    return response.blob();
                })
                .then(blob => {
                    // 다운로드 링크 생성
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.style.display = 'none';
                    a.href = url;
                    a.download = 'audio_files.zip';
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    
                    // 진행 표시줄 상태 업데이트
                    setTimeout(() => {
                        document.getElementById('progressContainer').style.display = 'none';
                    }, 2000);
                })
                .catch(error => {
                    alert('오류가 발생했습니다: ' + error.message);
                    document.getElementById('progressContainer').style.display = 'none';
                });
            }
            
            function openFolder() {
                fetch('/open-folder', {
                    method: 'GET'
                })
                .catch(error => {
                    alert('폴더를 열 수 없습니다.');
                });
            }
        </script>
    </body>
    </html>
    """

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
                print(f"Error processing {word}: {str(e)}")
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

@app.route('/open-folder', methods=['GET'])
def open_folder():
    try:
        if sys.platform == 'win32':
            os.startfile(UPLOAD_FOLDER)
        elif sys.platform == 'darwin':  # macOS
            os.system(f'open "{UPLOAD_FOLDER}"')
        else:  # Linux
            os.system(f'xdg-open "{UPLOAD_FOLDER}"')
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 사용 가능한 포트 찾기
def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port

# Flask 서버 실행 함수 (Waitress WSGI 서버 사용)
def run_flask(port):
    serve(app, host='127.0.0.1', port=port, threads=4)

# PyQt5 메인 윈도우 클래스
class MainWindow(QMainWindow):
    def __init__(self, port):
        super().__init__()
        self.port = port
        self.init_ui()
        
    def init_ui(self):
        # 윈도우 설정
        self.setWindowTitle('세이펜 오디오랙 영어단어 파일 생성기')
        self.setGeometry(100, 100, 900, 700)
        
        # 중앙 위젯 설정
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 레이아웃 설정 - 마진 최소화
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)  # 좌, 상, 우, 하 마진을 0으로 설정
        layout.setSpacing(0)  # 위젯 간 간격도 0으로 설정
        
        # 웹뷰 생성
        self.web_view = QWebEngineView()
        self.web_view.load(QUrl(f'http://127.0.0.1:{self.port}'))
        layout.addWidget(self.web_view)
        
        self.show()
    
    def open_folder(self):
        if sys.platform == 'win32':
            os.startfile(UPLOAD_FOLDER)
        elif sys.platform == 'darwin':  # macOS
            os.system(f'open "{UPLOAD_FOLDER}"')
        else:  # Linux
            os.system(f'xdg-open "{UPLOAD_FOLDER}"')
    
    def closeEvent(self, event):
        # 애플리케이션 종료 시 처리
        event.accept()
        sys.exit(0)

def main():
    # 포트 찾기
    port = find_free_port()
    
    # Flask 서버 스레드 시작
    server_thread = threading.Thread(target=run_flask, args=(port,), daemon=True)
    server_thread.start()
    
    # 서버가 시작될 때까지 잠시 대기
    time.sleep(1)
    
    # PyQt5 애플리케이션 시작
    app = QApplication(sys.argv)
    window = MainWindow(port)
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main() 