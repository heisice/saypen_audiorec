#!/usr/bin/env python3

"""

세이펜 오디오 랙 스티커용 영어 단어 음원파일을 다운로드하는 스크립트.
다음 사전에서 단어를 검색한 후 단어 읽기 링크를 찾아서 다운로드한다.

개인적인 용도로 사용하기 위해 만들었으며, 상업적인 목적으로 사용하는 것은 금지합니다.

2024-03-10
김기수 <heisice@gmail.com>

"""

import re
import os
import requests

from urllib import parse

# 정규식 패턴 목록
csv_pattern = re.compile('([^,]+),"?([^"\n]+)"?\n?')
filename_pattern = re.compile('[^A-Za-z0-9_\\.]')
redirect_pattern = re.compile('<meta http-equiv="Refresh" content="0; URL=/word/view\\.do\\?wordid=([^&]+)&q=')
audio_link_pattern = re.compile('<a href="(http://t1\\.daumcdn\\.net/language/[^"]+)"')

# csv 파일을 열어서 오디오랙 스티커 번호와 단어를 읽어온다.
# 각 라인을 읽어서 스티커 번호와 단어를 파싱한다. (CSV는 엑셀로 차트를 만들어 내보내기 하면 편합니다.)
# 오디오 스티커 번호,단어
# 예: 02001,blue

for line in open('audio_rec.csv', encoding = 'utf-8-sig'):
	
	# 정규식으로 라인을 파싱
	parsed = csv_pattern.findall(line)
	
	# 파싱되지 않으면
	if not parsed:
		# 에러 메시지를 출력하고 종료
		raise Exception('Invalid line: ' + line)
	
	# 정규식으로 파싱된 첫번째 결과를 읽어온다.
	sticker_no, word = parsed[0]

	# 파일명을 만든다.
	filename = "REC1_%s.mp3" % sticker_no.strip()

	# 파일이 이미 있으면 건너띈다.
	if os.path.isfile(filename):
		print('File exists: ' + filename)
		continue

	# 단어를 URL인코딩한다.
	word = parse.quote(word)

	# 단어를 검색하는 URL을 호출한다. (다음 사전의 영어 사전 검색 URL)
	url = 'https://dic.daum.net/search.do?q=' + word + '&dic=eng'
	res = requests.get(url)
	
	# 응답을 정규식으로 파싱한 후 리디렉션 URL이 있는지 확인.
	parsed = redirect_pattern.findall(res.text)

	# 만약 리디렉션 URL이 있다면 거기에서 wordid만 읽어온 다음에
	if parsed:

		# 리디렉션 URL에 wordid를 넘겨 다시 호출한다.
		url = 'https://dic.daum.net/word/view.do?wordid=' + parsed[0] + '&q=' + word
		res = requests.get(url)

	# 페이지에서 바로 단어 읽기 링크를 찾는다.
	parsed = audio_link_pattern.findall(res.text)

	# 단어 읽기 링크가 없으면 뭔가 잘못된 것이다. 에러를 리턴한다.
	if not parsed:
		raise Exception('No audio link: ' + word)

	# 오디오 파일을 다운받는다.
	audio = requests.get(parsed[0])

	# 다운받은 오디오를 저장한다.
	with open(filename, 'wb') as file:
		file.write(audio.content)
		file.close()
