import os
import sys

from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                            QWidget, QPushButton, QLabel, QTableWidget,
                            QHeaderView, QLineEdit, QProgressBar, QMessageBox)
from PyQt5.QtCore import QTimer, pyqtSignal, QThread

# 상수 정의
UPLOAD_FOLDER = os.path.join(os.path.expanduser('~'), 'Documents', '세이펜_오디오')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# 다운로드 작업을 처리하는 워커 스레드
class DownloadWorker(QThread):
    progress_updated = pyqtSignal(int)
    download_complete = pyqtSignal(list)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, data):
        super().__init__()
        self.data = data
        
    def run(self):
        try:
            # 필요한 모듈을 여기서 임포트 (지연 로딩)
            import requests
            import re
            from urllib import parse
            
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
            
            downloaded_files = []
            total = len(self.data)
            
            for i, row in enumerate(self.data):
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
                                self.progress_updated.emit(int((i + 0.5) / total * 100))  # 다운로드 중간 진행 상태
                        
                        if os.path.exists(filepath):
                            downloaded_files.append(filepath)
                        
                        # 진행 상황 업데이트 (0-100%)
                        progress = int((i + 1) / total * 100)
                        self.progress_updated.emit(progress)
                        
                except Exception as e:
                    self.error_occurred.emit(f"단어 '{word}' 처리 중 오류: {str(e)}")
                    continue
            
            # 다운로드 완료 신호 발생
            self.download_complete.emit(downloaded_files)
            
        except Exception as e:
            self.error_occurred.emit(f"다운로드 중 오류 발생: {str(e)}")

# 메인 윈도우 클래스
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        # 윈도우 설정
        self.setWindowTitle('세이펜 오디오랙 영어단어 파일 생성기')
        self.setGeometry(100, 100, 900, 700)
        
        # 중앙 위젯 설정
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 메인 레이아웃
        main_layout = QVBoxLayout(central_widget)
        
        # 설명
        desc_label = QLabel('스티커 번호와 단어를 입력하세요. 단어 입력 후 엔터를 누르면 새 행이 추가됩니다.')
        desc_label.setStyleSheet('margin-bottom: 15px;')
        main_layout.addWidget(desc_label)
        
        # 테이블 위젯
        self.table = QTableWidget(1, 3)
        self.table.setHorizontalHeaderLabels(['스티커 번호', '단어', '삭제'])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        
        # 첫 번째 행 추가
        self.add_table_row(0, "1")
        
        main_layout.addWidget(self.table)
        
        # 버튼 레이아웃
        button_layout = QHBoxLayout()
        
        # 단어 리스트 클리어 버튼
        self.clear_btn = QPushButton('단어 리스트 초기화')
        self.clear_btn.clicked.connect(self.clear_word_list)
        button_layout.addWidget(self.clear_btn)
        
        # 다운로드 버튼
        self.download_btn = QPushButton('단어 일괄 다운로드')
        self.download_btn.clicked.connect(self.process_all_data)
        button_layout.addWidget(self.download_btn)
        
        # 폴더 열기 버튼
        self.open_folder_btn = QPushButton('저장 폴더 열기')
        self.open_folder_btn.clicked.connect(self.open_folder)
        button_layout.addWidget(self.open_folder_btn)
        
        main_layout.addLayout(button_layout)
        
        # 진행 상황 표시
        progress_layout = QVBoxLayout()
        
        self.status_label = QLabel('다운로드 준비 중...')
        self.status_label.setVisible(False)
        progress_layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)
        
        main_layout.addLayout(progress_layout)
        
    def add_table_row(self, row_index, sticker_no=""):
        # 스티커 번호 입력 필드
        sticker_input = QLineEdit()
        sticker_input.setText(sticker_no)
        sticker_input.setPlaceholderText("스티커 번호")
        
        # 단어 입력 필드
        word_input = QLineEdit()
        word_input.setPlaceholderText("단어")
        word_input.returnPressed.connect(lambda: self.add_row_with_increment(row_index))
        
        # 삭제 버튼
        delete_btn = QPushButton("삭제")
        delete_btn.clicked.connect(lambda: self.delete_row(row_index))
        
        # 테이블에 위젯 추가
        self.table.setCellWidget(row_index, 0, sticker_input)
        self.table.setCellWidget(row_index, 1, word_input)
        self.table.setCellWidget(row_index, 2, delete_btn)
    
    def add_row_with_increment(self, current_row):
        # 현재 스티커 번호 가져오기
        sticker_input = self.table.cellWidget(current_row, 0)
        current_sticker_no = sticker_input.text()
        
        # 새 스티커 번호 계산
        new_sticker_no = self.increment_with_padding(current_sticker_no)
        
        # 새 행 추가
        row_count = self.table.rowCount()
        self.table.setRowCount(row_count + 1)
        self.add_table_row(row_count, new_sticker_no)
        
        # 새 행의 단어 입력 필드에 포커스
        self.table.cellWidget(row_count, 1).setFocus()
    
    def increment_with_padding(self, sticker_no):
        # 숫자가 아닌 경우 기본값 1 반환
        if not sticker_no or not sticker_no.strip() or not sticker_no.strip().isdigit():
            return "1"
        
        sticker_no = sticker_no.strip()
        
        # 앞의 0 개수 확인
        leading_zeros = len(sticker_no) - len(sticker_no.lstrip('0'))
        if leading_zeros == len(sticker_no):  # 모두 0인 경우
            leading_zeros -= 1
        
        # 숫자 부분만 추출하여 증가
        numeric_part = int(sticker_no)
        incremented = numeric_part + 1
        
        # 증가된 숫자를 문자열로 변환
        result = str(incremented)
        
        # 원래 숫자의 길이보다 증가된 숫자의 길이가 길어진 경우 (예: 999 -> 1000)
        # 0 패딩을 하나 줄임
        original_numeric_length = len(str(numeric_part))
        new_numeric_length = len(result)
        padding_length = max(0, leading_zeros - (new_numeric_length - original_numeric_length))
        
        # 필요한 만큼 0 패딩 추가
        result = '0' * padding_length + result
        
        return result
    
    def delete_row(self, row):
        # 테이블에 최소 1개의 행은 유지
        if self.table.rowCount() > 1:
            self.table.removeRow(row)
            # 삭제 버튼 이벤트 재연결 (인덱스 변경됨)
            for i in range(self.table.rowCount()):
                delete_btn = self.table.cellWidget(i, 2)
                delete_btn.clicked.disconnect()
                delete_btn.clicked.connect(lambda checked=False, row=i: self.delete_row(row))
        else:
            # 마지막 행은 삭제하지 않고 내용만 비움
            self.table.cellWidget(0, 0).setText("1")
            self.table.cellWidget(0, 1).setText("")
    
    def clear_word_list(self):
        """단어 리스트를 초기화하는 함수"""
        # 확인 대화상자 표시
        reply = QMessageBox.question(
            self, 
            '단어 리스트 초기화', 
            '정말로 모든 단어를 지우고 리스트를 초기화하시겠습니까?',
            QMessageBox.Yes | QMessageBox.No, 
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # 테이블 초기화
            self.table.setRowCount(0)
            self.table.setRowCount(1)
            # 첫 번째 행 추가
            self.add_table_row(0, "1")
    
    def process_all_data(self):
        # 테이블에서 데이터 수집
        data = []
        for row in range(self.table.rowCount()):
            sticker_no = self.table.cellWidget(row, 0).text()
            word = self.table.cellWidget(row, 1).text()
            
            if sticker_no and word:
                data.append({
                    'sticker_no': sticker_no,
                    'word': word
                })
        
        if not data:
            QMessageBox.warning(self, '경고', '데이터를 입력해주세요.')
            return
        
        # 진행 표시줄 표시
        self.status_label.setText('단어 다운로드 중...')
        self.status_label.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        
        # 다운로드 워커 스레드 시작
        self.download_worker = DownloadWorker(data)
        self.download_worker.progress_updated.connect(self.update_progress)
        self.download_worker.download_complete.connect(self.download_finished)
        self.download_worker.error_occurred.connect(self.show_error)
        self.download_worker.start()
    
    def update_progress(self, value):
        self.progress_bar.setValue(value)
    
    def download_finished(self, downloaded_files):
        if not downloaded_files:
            self.status_label.setVisible(False)
            self.progress_bar.setVisible(False)
            QMessageBox.warning(self, '경고', '다운로드할 파일이 없습니다.')
            return
        
        try:
            self.status_label.setText('다운로드 완료!')
            
            # 2초 후 진행 표시줄 숨기기
            QTimer.singleShot(2000, lambda: self.status_label.setVisible(False))
            QTimer.singleShot(2000, lambda: self.progress_bar.setVisible(False))
            
            # 완료 메시지 표시 (ZIP 압축 없이 개별 파일로 저장됨을 명시)
            QMessageBox.information(self, '완료', f'다운로드가 완료되었습니다.\n총 {len(downloaded_files)}개 파일이 저장되었습니다.\n저장 위치: {UPLOAD_FOLDER}')
            
        except Exception as e:
            self.show_error(f"다운로드 완료 처리 중 오류: {str(e)}")
    
    def show_error(self, message):
        self.status_label.setVisible(False)
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, '오류', message)
    
    def open_folder(self):
        try:
            if sys.platform == 'win32':
                os.startfile(UPLOAD_FOLDER)
            elif sys.platform == 'darwin':  # macOS
                os.system(f'open "{UPLOAD_FOLDER}"')
            else:  # Linux
                os.system(f'xdg-open "{UPLOAD_FOLDER}"')
        except Exception as e:
            QMessageBox.critical(self, '오류', f'폴더를 열 수 없습니다: {str(e)}')

def main():
    # QApplication 생성
    app = QApplication(sys.argv)
    
    # 메인 윈도우 생성 및 표시
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main() 