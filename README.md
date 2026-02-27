# 🎬 Video Converter - 로컬 WebUI

동영상 URL을 입력하면 자동으로 720p 다운로드 → 1080p 업스케일 → HandBrake 코덱 변환까지 처리하는 웹앱입니다.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Flask](https://img.shields.io/badge/Flask-3.1-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

## ⚙️ 파이프라인

동영상 URL → yt-dlp(720p 다운로드) → FFmpeg(1080p 업스케일) → HandBrakeCLI(코덱 변환) → 완성!


## 🚀 설치 방법

### 1단계: 이 저장소 다운로드

초록색 **Code** 버튼 → **Download ZIP** 클릭 → 압축 풀기

또는:
```bash
git clone https://github.com/lunaeun/VideoConverter.git
cd VideoConverter
2단계: 필수 프로그램 다운로드
프로그램	다운로드 링크	비고
Python 3.10+	python.org	⚠️ 설치 시 Add to PATH 반드시 체크!
FFmpeg	다운로드	압축 풀고 bin 폴더 안의 exe 복사
HandBrakeCLI	다운로드	압축 풀고 exe 복사
3단계: exe 파일 배치
다운로드한 ffmpeg.exe, ffprobe.exe, HandBrakeCLI.exe를 프로젝트 폴더에 넣으세요:

📁 VideoConverter/
├── app.py
├── requirements.txt
├── install_and_run.bat
├── ffmpeg.exe          ← 여기에 넣기
├── ffprobe.exe         ← 여기에 넣기
├── HandBrakeCLI.exe    ← 여기에 넣기
└── templates/
    └── index.html
4단계: 실행
폴더 열기 → 주소창에 cmd 입력 → Enter

Copypython -m pip install flask yt-dlp
python app.py
브라우저에서 http://localhost:5000 접속하면 끝!

🎞️ 지원 코덱
코덱	설명
H.265 (HEVC)	높은 압축률, 작은 파일
H.264 (AVC)	최고 호환성
AV1 (SVT)	최신 표준
VP9	WebM 형식
💡 사용 팁
최대 10분 이하 영상만 처리 가능합니다
잘 모르면 코덱은 H.265, 품질은 22 그대로 두세요
서버 실행 중에는 검은 창(명령 프롬프트)을 닫지 마세요
변환된 파일은 final 폴더에 저장됩니다
⚠️ 주의사항
개인 용도로만 사용하세요
FFmpeg, HandBrakeCLI는 용량 문제로 저장소에 포함되어 있지 않습니다
직접 다운로드하여 프로젝트 폴더에 넣어주세요
📄 라이선스
MIT License
