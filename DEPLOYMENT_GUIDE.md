# 🚀 물레방아하우스 챗봇 배포 가이드 (Ubuntu 리눅스 서버용)

서버(100.95.246.101)가 **Ubuntu 24.04**인 것을 확인했습니다.
리눅스 환경에 맞춰 명령어를 정리해드립니다.

## 📋 전체 로드맵

1.  **서버 접속**: SSH로 접속
2.  **환경 설정**: Python, GitHub CLI 설치
3.  **코드 다운로드**: `git clone` (인증 필요)
4.  **서버 실행**: 패키지 설치 및 실행

---

## 1단계: 필수 프로그램 설치 (서버 터미널에서)

먼저 `sudo` 권한으로 업데이트하고 필요한 도구를 설치합니다.

```bash
sudo apt update
sudo apt install -y python3-pip python3-venv gh
```

-   `python3-venv`: 가상환경을 만들기 위해 필수입니다.
-   `gh`: GitHub 로그인을 쉽게 하기 위한 도구입니다.

---

## 2단계: GitHub 로그인 (가장 중요 ⭐)

비밀번호 입력 방식은 이제 막혔으므로, `gh` 명령어로 로그인합니다.

1.  로그인 시작:
    ```bash
    gh auth login
    ```
2.  화살표 키로 선택:
    -   **GitHub.com** 선택
    -   **HTTPS** 선택
    -   **Yes** (Authenticate Git with your GitHub credentials)
    -   **Login with a web browser** 선택
3.  **인증 코드 복사**: 화면에 8자리 코드가 뜹니다 (예: `ABCD-1234`).
4.  **노트북에서 접속**: 노트북 브라우저에서 `https://github.com/login/device` 에 접속하여 코드를 입력합니다.
5.  승인하면 서버 터미널에서 로그인이 완료됩니다.

---

## 3단계: 코드 내려받기 (Clone)

이제 비밀번호 없이 다운로드됩니다.

```bash
cd ~/guesthouse
git clone https://github.com/ashstring93/guesthouse.git .
```

---

## 4단계: 가상환경 설정 및 패키지 설치

Ubuntu에서는 시스템 Python을 보호하기 위해 **가상환경(Virtual Environment)** 사용이 권장됩니다.

1.  **가상환경 생성 및 활성화**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```
    *(프롬프트 앞에 `(venv)`가 생기면 성공!)*

2.  **라이브러리 설치**:
    ```bash
    pip install fastapi uvicorn google-genai python-dotenv chromadb
    ```

3.  **비밀 파일(.env) 생성**:
    노트북의 `.env` 내용을 복사해서 서버에 만듭니다.
    ```bash
    nano backend/.env
    ```
    (붙여넣기 후 `Ctrl+O`, `Enter`, `Ctrl+X`로 저장/종료)

---

## 5단계: 벡터 DB 생성 및 서버 실행

1.  **지식베이스 업데이트 (필요 시)**:
    - `backend/knowledge_base/*.md` 내용 수정

2.  **DB 생성**:
    ```bash
    cd backend
    python scripts/build_knowledge_base.py
    ```

3.  **서버 실행**:
    ```bash
    uvicorn server:app --host 0.0.0.0 --port 8000
    ```

성공하면 `Application startup complete` 메시지가 뜹니다.
정적 웹 파일은 `frontend/` 디렉토리(`index.html`, `css/`, `js/`, `images/`)에서 서빙됩니다.
이제 노트북이나 모바일에서 `http://100.95.246.101:8000/docs` 로 접속해보세요! (Tailscale망 내부)

### 수동 점검 (테스트 스크립트 대체)

```bash
python quick_test.py

curl http://100.95.246.101:8000/api/health
curl -X POST http://100.95.246.101:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"체크인 시간이 언제인가요?"}'
```
