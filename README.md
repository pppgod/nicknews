# 뉴스 봇

매일 특정 키워드에 관한 정보들을 텔레그램에 보내주는 봇 서버

## 스택

- Python 3.12
- APScheduler — 스케줄 관리
- yfinance — 주가 조회
- feedparser — RSS 뉴스 파싱

## 설치 및 실행

### 1. 가상환경 생성

```bash
python -m venv venv
source venv/bin/activate
```

### 2. 환경 변수 설정

프로젝트 루트에 `.env` 파일을 생성하고 아래 값을 채운다:

```env
TELEGRAM_TOKEN=<YOUR_TELEGRAM_TOKEN>
TELEGRAM_CHAT_ID=<YOUR_CHAT_ID>
```

### 3. 패키지 설치

```bash
pip install -e .
```

의존성이 자동으로 설치되고, `nicknews` 명령어가 등록된다.

### 4. 실행

```bash
nicknews
```

## 스케줄

| 작업 | 시간 (KST) |
|------|-----------|
| 데일리 뉴스 | 09:00 |
| 코스피 마감 | 15:35 |
| 나스닥 마감 | 05:05 |

## 텔레그램 명령어

| 명령어 | 설명 |
|--------|------|
| `/add <종목명 또는 티커>` | 주식 추가 (한국/미국 자동 구분) |
| `/remove <티커>` | 주식 제거 |
| `/watch <키워드>` | 관심 키워드 추가 |
| `/unwatch <키워드>` | 관심 키워드 제거 |
| `/list` | 전체 구독 목록 확인 |
| `/help` | 명령어 안내 |

**예시**
```
/add 삼성전자
/add AAPL
/watch 엔비디아
/unwatch 인공지능
/remove AAPL
```

## 서버 배포 (gh CLI)

GitHub Actions가 빌드한 wheel 파일을 서버에 직접 받아 설치하는 방법이다.

### 1. gh CLI 설치 (처음 한 번)

```bash
(type -p wget >/dev/null || (sudo apt update && sudo apt install wget -y)) \
&& sudo mkdir -p -m 755 /etc/apt/keyrings \
&& wget -qO- https://cli.github.com/packages/githubcli-archive-keyring.gpg \
   | sudo tee /etc/apt/keyrings/githubcli-archive-keyring.gpg > /dev/null \
&& sudo chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg \
&& echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
   | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
&& sudo apt update && sudo apt install gh -y
```

### 2. GitHub 로그인

```bash
gh auth login
```

### 3. 배포 디렉토리 및 가상환경 생성 (처음 한 번)

```bash
sudo apt install python3-venv -y
mkdir -p ~/nicknews
cd ~/nicknews
python3 -m venv venv
```

### 4. 환경 변수 설정 (처음 한 번)

```bash
cat > ~/nicknews/.env << 'EOF'
TELEGRAM_TOKEN=<YOUR_TELEGRAM_TOKEN>
TELEGRAM_CHAT_ID=<YOUR_CHAT_ID>
EOF
```

### 5. 배포

```bash
cd ~/nicknews
source venv/bin/activate
gh run download --repo <YOUR_GITHUB_USERNAME>/nicknews --name dist --dir dist
pip install dist/nicknews-*.whl
```

### 6. 업데이트

새 버전이 빌드된 후 동일하게 재실행하면 된다:

```bash
cd ~/nicknews
source venv/bin/activate
gh run download --repo <YOUR_GITHUB_USERNAME>/nicknews --name dist --dir dist
pip install --upgrade dist/nicknews-*.whl
```

## systemd로 실행하기

서버에서 백그라운드 상시 실행이 필요할 때 사용한다.

### 1. 서비스 파일 생성

```bash
sudo nano /etc/systemd/system/nicknews.service
```

아래 내용 붙여넣기:

```ini
[Unit]
Description=NickNews Telegram Bot
After=network.target

[Service]
User=$USER
WorkingDirectory=/home/$USER/nicknews
ExecStart=/home/$USER/nicknews/venv/bin/nicknews
EnvironmentFile=/home/$USER/nicknews/.env
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 2. 서비스 등록 및 시작

```bash
sudo systemctl daemon-reload
sudo systemctl enable nicknews   # 부팅 시 자동 시작
sudo systemctl start nicknews    # 지금 바로 시작
```

### 3. 상태 확인 / 로그

```bash
sudo systemctl status nicknews
sudo journalctl -u nicknews -f   # 실시간 로그
```

### 4. 중지 / 재시작

```bash
sudo systemctl stop nicknews
sudo systemctl restart nicknews
```
