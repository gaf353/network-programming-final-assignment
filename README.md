# mytftp — Python TFTP Client

Network Programming 기말과제 (Final Term Project) — a TFTP client written in Python using the Socket API, implementing RFC 1350.

## 개요 (Overview)

`mytftp.py` is a command-line TFTP client that can **download (get)** a file from a TFTP server or **upload (put)** a file to a TFTP server. It was tested against the `tftpd-hpa` server running on `genie.pcu.ac.kr` (`203.250.133.88`).

## 구현기능 (Implemented Features)

- **GET (download)** — sends an RRQ, receives DATA blocks, sends ACKs, writes the file to disk.
- **PUT (upload)** — sends a WRQ, waits for ACK(0), reads the local file in 512-byte blocks, sends DATA blocks, waits for each ACK.
- Host address accepted as either an **IP address** or a **domain name**.
- **`-p` port option** (defaults to port 69).
- **Timeout / retry handling** — if the server does not respond to RRQ/WRQ (or an ACK), the request is retransmitted up to 5 times before giving up.
- **Error handling** for TFTP ERROR packets, including:
  - `File not found` (error code 1) — when downloading a file that does not exist on the server.
  - `File already exists` (error code 6) — when uploading a file that already exists on the server (server-dependent; see Testing notes below).

## 사용법 (Usage)

```
$ python3 mytftp.py host [-p port] [get|put] filename
```

### 예 (Examples)

```
$ python3 mytftp.py 203.250.133.88 get tftp.conf
$ python3 mytftp.py 203.250.133.88 put tftp.txt
$ python3 mytftp.py genie.pcu.ac.kr -p 9988 put tftp.txt
```

## 테스트 결과 (Testing notes)

Tested against the real `genie.pcu.ac.kr` TFTP server:

- `get tftp.rfc` → downloaded successfully, byte-identical to the source file.
- `put myfile.txt` → uploaded successfully; verified by downloading it back and comparing with `diff` (no differences).
- `get <nonexistent file>` → correctly prints `Error: File not found` and exits.
- The client's error-handling code for `File already exists` (ERROR code 6) was verified against a local sandbox TFTP server, which explicitly rejects a WRQ when the target file already exists. The live `genie` server's `tftpd-hpa` configuration allows overwriting existing files, so that specific error was not observed in a live demo, but the client correctly parses and reports any ERROR packet the server sends.

## 소스코드 (Source)

See [`mytftp.py`](./mytftp.py) — built on the function structure given in the course's `tftp2026.py` pseudocode template.
