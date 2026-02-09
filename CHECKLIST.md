# 설치 전 체크리스트

## ✅ 설치하기 전에 확인하세요

### 1. Python 버전 확인

**명령 프롬프트에서:**
```cmd
py -0
```

**출력 예시:**
```
 -V:3.14          Python 3.14.3
 -V:3.12          Python 3.12.0
 -V:3.10 *        Python 3.10.11  ← 이게 있어야 함!
```

**Python 3.10이 없다면:**
- 다운로드: https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe
- 설치 시 "Add Python 3.10 to PATH" 체크
- 명령 프롬프트 **새로 열기**

---

### 2. Visual C++ 확인

**확인 방법:**
```cmd
dir "C:\Program Files\Microsoft Visual Studio\2022\*" 2>nul
```

**또는:**
- 제어판 → 프로그램 → "Microsoft Visual C++ 2015-2022" 검색

**없다면:**
- 다운로드: https://aka.ms/vs/17/release/vc_redist.x64.exe
- 설치 후 **재부팅**

---

### 3. 인터넷 연결 확인

**테스트:**
```cmd
ping pypi.org
```

**성공 예시:**
```
Reply from 151.101.x.x: bytes=32 time=50ms TTL=54
```

---

### 4. 디스크 공간 확인

**최소 필요:**
- 5GB 여유 공간

**확인:**
- 내 PC → C 드라이브 우클릭 → 속성

---

## 🚀 모두 확인했다면

```cmd
install.bat
```

---

## ⚠️ 자주 하는 실수

### ❌ 실수 1: Python 3.12/3.14 사용
→ **반드시 Python 3.10!**

### ❌ 실수 2: PATH 체크 안 함
→ 설치 시 "Add to PATH" 체크 필수

### ❌ 실수 3: 재부팅 안 함
→ Visual C++ 설치 후 재부팅 필수

### ❌ 실수 4: 이전 venv 삭제 안 함
→ install.bat이 자동으로 삭제함

---

## 📋 설치 시나리오

### ✅ 정상 시나리오
```
1. Python 3.10 설치됨
2. Visual C++ 설치됨
3. install.bat 실행
4. 10분 대기
5. "Installation Complete!" 메시지
6. test.bat 실행
7. "SUCCESS!" 메시지
8. run.bat 실행
9. GUI 열림! ✅
```

### ⚠️ 문제 시나리오
```
1. install.bat 실행
2. "Python 3.10 is required" 오류
3. Python 3.10.11 설치
4. install.bat 다시 실행
5. 성공! ✅
```

---

**준비되셨나요? install.bat을 실행하세요!** 🚀
