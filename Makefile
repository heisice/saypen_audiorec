all:
	@echo "세이펜 오디오 생성기"


clean:
	@rm -rf files/*.mp3

run:
	.venv/bin/python app.py	
