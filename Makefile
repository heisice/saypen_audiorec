# Makefile for building single executable with Nuitka
# Automatically detects OS and builds accordingly

# 기본 변수 설정
PYTHON := python3
PIP := pip3
MAIN_FILE := main.py
APP_NAME := audio_rec
APP_TITLE := "세이펜 단어 사운드 생성기"
ICON_FILE := icon.png

# 운영체제 감지
ifeq ($(OS),Windows_NT)
	DETECTED_OS := Windows
	EXE_EXT := .exe
	RM_CMD := del /Q
	MKDIR_CMD := mkdir
	ICON_OPTION := --windows-icon-from-ico=$(ICON_FILE)
else
	UNAME_S := $(shell uname -s)
	ifeq ($(UNAME_S),Darwin)
		DETECTED_OS := macOS
		EXE_EXT :=
		RM_CMD := rm -rf
		MKDIR_CMD := mkdir -p
		ICON_OPTION := --macos-app-icon=$(ICON_FILE)
	else
		DETECTED_OS := Linux
		EXE_EXT :=
		RM_CMD := rm -rf
		MKDIR_CMD := mkdir -p
		ICON_OPTION :=
	endif
endif

# 기본 타겟
.PHONY: all
all: check-deps
	@echo "사용 가능한 명령:"
	@echo "  make mac     - macOS용 앱 번들(.app) 빌드"
	@echo "  make windows - Windows용 실행 파일 빌드"
	@echo "  make clean   - 빌드 파일 정리"
	@echo "감지된 운영체제: $(DETECTED_OS)"

# 종속성 확인
.PHONY: check-deps
check-deps:
	@echo "종속성 확인 중..."
	@$(PIP) list | grep -q nuitka || (echo "Nuitka가 설치되어 있지 않습니다. 설치 중..." && $(PIP) install nuitka)
	@$(PIP) list | grep -q ordered-set || (echo "ordered-set이 설치되어 있지 않습니다. 설치 중..." && $(PIP) install ordered-set)
	@$(PIP) list | grep -q imageio || (echo "imageio가 설치되어 있지 않습니다. 설치 중..." && $(PIP) install imageio)
	@echo "종속성 확인 완료"

# macOS 빌드
.PHONY: mac
mac: check-deps
	@echo "macOS용 앱 번들(.app) 빌드 중..."
	$(RM_CMD) dist
	$(MKDIR_CMD) dist
	$(PYTHON) -m nuitka \
		--standalone \
		--macos-create-app-bundle \
		$(ICON_OPTION) \
		--macos-app-name=$(APP_TITLE) \
		--macos-app-mode=gui \
		--include-package=imageio \
		--include-package=PIL \
		--include-package=numpy \
		--include-package=flask \
		--include-package=waitress \
		--include-package=PyQt5 \
		--include-package=requests \
		--remove-output \
		--assume-yes-for-downloads \
		--disable-console \
		--output-dir=dist \
		--plugin-enable=pyqt5 \
		--nofollow-import-to=PyQt5.QtWebEngineWidgets,PyQt5.QtWebEngine,PyQt5.QtWebEngineCore \
		$(MAIN_FILE)
	@echo "macOS 앱 번들 빌드 완료"
	@echo "앱 번들 구조:"
	@ls -la dist/

# Windows 빌드
.PHONY: windows
windows: check-deps
	@echo "Windows용 실행 파일 빌드 중..."
	$(RM_CMD) dist
	$(MKDIR_CMD) dist
	$(PYTHON) -m nuitka \
		--standalone \
		--onefile \
		$(ICON_OPTION) \
		--windows-product-name=$(APP_TITLE) \
		--windows-company-name="세이펜" \
		--windows-file-description=$(APP_TITLE) \
		--include-package=imageio \
		--include-package=PIL \
		--include-package=numpy \
		--include-package=flask \
		--include-package=waitress \
		--include-package=PyQt5 \
		--include-package=requests \
		--remove-output \
		--assume-yes-for-downloads \
		--disable-console \
		--output-dir=dist \
		--output-filename=$(APP_NAME)$(EXE_EXT) \
		--plugin-enable=pyqt5 \
		--nofollow-import-to=PyQt5.QtWebEngineWidgets,PyQt5.QtWebEngine,PyQt5.QtWebEngineCore \
		$(MAIN_FILE)
	@echo "Windows 빌드 완료: dist/$(APP_NAME)$(EXE_EXT)"
	@echo "파일 구조:"
	@ls -la dist/

# 자동 OS 감지 빌드
.PHONY: build
build: check-deps
ifeq ($(DETECTED_OS),macOS)
	@$(MAKE) mac
else ifeq ($(DETECTED_OS),Windows)
	@$(MAKE) windows
else
	@echo "지원되지 않는 운영체제입니다: $(DETECTED_OS)"
	@echo "수동으로 'make mac' 또는 'make windows'를 실행하세요."
endif

# 정리
.PHONY: clean
clean:
	@echo "빌드 파일 정리 중..."
	$(RM_CMD) dist
	$(RM_CMD) build
	$(RM_CMD) *.build
	$(RM_CMD) *.dist
	$(RM_CMD) *.bin
	$(RM_CMD) *.exe
	$(RM_CMD) *.app
	$(RM_CMD) *.spec
	@echo "정리 완료"
