# mytftp — 파이썬 TFTP 클라이언트

네트워크프로그래밍 기말과제 — 소켓 API를 이용하여 파이썬으로 작성한 TFTP 클라이언트 (RFC 1350 구현)

## 개요

`mytftp.py`는 TFTP 서버로부터 파일을 **다운로드(get)**하거나, TFTP 서버로 파일을 **업로드(put)**할 수 있는 커맨드라인 클라이언트이다. `genie.pcu.ac.kr` (`203.250.133.88`)에서 동작 중인 `tftpd-hpa` 서버를 대상으로 테스트하였다.

## 구현기능

- **GET (다운로드)** — RRQ 전송 → DATA 블록 수신 → ACK 전송 → 파일을 디스크에 저장.
- **PUT (업로드)** — WRQ 전송 → ACK(0) 수신 대기 → 로컬 파일을 512바이트 단위로 읽어서 DATA 블록 전송 → 각 블록마다 ACK 수신 대기.
- 호스트 주소는 **IP 주소** 또는 **도메인네임** 모두 입력 가능.
- **`-p` 포트 옵션** 지원 (기본값: 69번 포트).
- **타임아웃/재전송 처리** — 서버가 RRQ/WRQ 또는 ACK에 응답하지 않을 경우, 최대 5회까지 재전송 후 오류 처리.
- TFTP ERROR 패킷에 대한 **오류 처리**:
  - `File not found` (오류코드 1) — 서버에 존재하지 않는 파일을 다운로드하려 할 때.
  - `File already exists` (오류코드 6) — 서버에 이미 존재하는 파일을 업로드하려 할 때 (서버 설정에 따라 다름, 아래 테스트 결과 참고).

## 사용법

```
$ python3 mytftp.py host [-p port] [get|put] filename
```

### 예

```
$ python3 mytftp.py 203.250.133.88 get tftp.conf
$ python3 mytftp.py 203.250.133.88 put tftp.txt
$ python3 mytftp.py genie.pcu.ac.kr -p 9988 put tftp.txt
```

## 테스트 결과

실제 `genie.pcu.ac.kr` TFTP 서버를 대상으로 테스트함:

- `get tftp.rfc` → 다운로드 성공, 원본 파일과 byte 단위로 동일함을 확인.
- `put myfile.txt` → 업로드 성공; 업로드한 파일을 다시 다운로드하여 `diff`로 비교한 결과 차이 없음을 확인 (round-trip 검증).
- `get <존재하지 않는 파일>` → `Error: File not found` 메시지를 정상적으로 출력하고 종료.
- `File already exists` (오류코드 6) 처리 로직은 로컬 샌드박스 TFTP 서버(WRQ 시 파일이 이미 존재하면 명시적으로 거부하도록 구현)를 대상으로 검증함. 실제 `genie` 서버의 `tftpd-hpa` 설정은 기존 파일을 덮어쓰기(overwrite) 허용하도록 되어 있어, 실제 데모에서는 이 오류가 발생하지 않았으나, 클라이언트는 서버가 보내는 모든 ERROR 패킷을 정상적으로 파싱하고 출력한다.

## 소스코드

[`mytftp.py`](./mytftp.py) 참고 — 강의에서 제공된 `tftp2026.py` pseudocode 템플릿의 함수 구조를 기반으로 작성함.
