# 뉴스 봇

매일 특정 키워드에 관한 정보들을 텔레그램에 보내주는 봇 서버

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

## systemd로 실행하기

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
ExecStart=/home/$USER/nicknews/venv/bin/python3 /home/$USER/nicknews/bot.py
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
