#!/usr/bin/python3
# $ mytftp host [-p port] [get|put] filename

import socket
import struct
import sys
import os
import argparse

OPCODE_RRQ = 1
OPCODE_WRQ = 2
OPCODE_DATA = 3
OPCODE_ACK = 4
OPCODE_ERROR = 5

BLOCK_SIZE = 512
TIMEOUT = 2.0
MAX_TRIAL = 5


def send_rrq(sock, server_address, filename, mode='octet'):
    fmt = '!H' + str(len(filename)) + 'sB' + str(len(mode)) + 'sB'
    packet = struct.pack(fmt, OPCODE_RRQ, filename.encode(), 0, mode.encode(), 0)
    sock.sendto(packet, server_address)


def send_wrq(sock, server_address, filename, mode='octet'):
    fmt = '!H' + str(len(filename)) + 'sB' + str(len(mode)) + 'sB'
    packet = struct.pack(fmt, OPCODE_WRQ, filename.encode(), 0, mode.encode(), 0)
    sock.sendto(packet, server_address)


def send_ack(sock, server_address, block_number):
    packet = struct.pack('!HH', OPCODE_ACK, block_number)
    sock.sendto(packet, server_address)


def send_data(sock, server_address, block_number, data):
    packet = struct.pack('!HH', OPCODE_DATA, block_number) + data
    sock.sendto(packet, server_address)


def receive_message(sock):
    data, address = sock.recvfrom(516)
    opcode = struct.unpack('!H', data[:2])[0]

    if opcode == OPCODE_DATA:
        block_number = struct.unpack('!H', data[2:4])[0]
        return {'type': 'DATA', 'block_number': block_number, 'data': data[4:]}, address
    elif opcode == OPCODE_ACK:
        block_number = struct.unpack('!H', data[2:4])[0]
        return {'type': 'ACK', 'block_number': block_number}, address
    elif opcode == OPCODE_ERROR:
        error_code = struct.unpack('!H', data[2:4])[0]
        error_msg = data[4:-1].decode()
        return {'type': 'ERROR', 'error_code': error_code, 'error_msg': error_msg}, address
    else:
        return {'type': 'UNKNOWN'}, address


# GET : 서버 -> 클라이언트로 파일을 받아온다 (download)

def download(host, port, filename):
    server_address = (host, port)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(TIMEOUT)

    send_rrq(sock, server_address, filename)
    f = open(filename, 'wb')

    expected_block_number = 1
    last_ack_number = 0
    trials = 0
    data_server_address = server_address
    connected = False
    success = False

    while True:
        try:
            message, addr = receive_message(sock)
            trials = 0
            data_server_address = addr
        except socket.timeout:
            trials += 1
            if trials <= MAX_TRIAL:
                if not connected:
                    print("timeout, retransmit RRQ")
                    send_rrq(sock, server_address, filename)
                else:
                    print("timeout, retransmit previous ACK")
                    send_ack(sock, data_server_address, last_ack_number)
                continue
            else:
                print(f"Error: no response from server after {MAX_TRIAL} tries")
                break

        if message['type'] == 'DATA':
            connected = True
            if message['block_number'] == expected_block_number:
                send_ack(sock, data_server_address, message['block_number'])
                f.write(message['data'])
                if len(message['data']) < BLOCK_SIZE:
                    print(f"last block {message['block_number']} received, transfer finished")
                    success = True
                    break
                else:
                    last_ack_number = message['block_number']
                    expected_block_number = message['block_number'] + 1
            else:
                send_ack(sock, data_server_address, last_ack_number)

        elif message['type'] == 'ERROR':
            print(f"Error: {message['error_msg']}")
            break
        else:
            print("unexpected message type")
            break

    f.close()
    sock.close()

    if not success:
        if os.path.isfile(filename) and os.path.getsize(filename) == 0:
            os.remove(filename)

    return success


# PUT : 클라이언트 -> 서버로 파일을 올린다 (upload)

def upload(host, port, filename):
    if not os.path.isfile(filename):
        print(f"Error: local file '{filename}' not found")
        return False

    server_address = (host, port)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(TIMEOUT)

    send_wrq(sock, server_address, filename)

    trials = 0
    data_server_address = server_address

    # ---- 1단계: WRQ 에 대한 ACK(0) 대기 ----
    while True:
        try:
            message, addr = receive_message(sock)
            data_server_address = addr
        except socket.timeout:
            trials += 1
            if trials <= MAX_TRIAL:
                print("timeout, retransmit WRQ")
                send_wrq(sock, server_address, filename)
                continue
            else:
                print(f"Error: no response from server after {MAX_TRIAL} tries")
                sock.close()
                return False

        if message['type'] == 'ACK' and message['block_number'] == 0:
            break
        elif message['type'] == 'ERROR':
            print(f"Error: {message['error_msg']}")
            sock.close()
            return False
        else:
            print("unexpected message type while waiting for ACK(0)")
            sock.close()
            return False

    # ---- 2단계: 파일을 512바이트씩 읽어서 DATA 블록 전송 ----
    f = open(filename, 'rb')
    block_number = 1
    success = False

    while True:
        file_block = f.read(BLOCK_SIZE)
        send_data(sock, data_server_address, block_number, file_block)
        trials = 0

        while True:
            try:
                message, addr = receive_message(sock)
            except socket.timeout:
                trials += 1
                if trials <= MAX_TRIAL:
                    print(f"timeout, retransmit DATA block {block_number}")
                    send_data(sock, data_server_address, block_number, file_block)
                    continue
                else:
                    print(f"Error: no response from server after {MAX_TRIAL} tries")
                    f.close()
                    sock.close()
                    return False

            if message['type'] == 'ACK' and message['block_number'] == block_number:
                break
            elif message['type'] == 'ERROR':
                print(f"Error: {message['error_msg']}")
                f.close()
                sock.close()
                return False
            # 잘못된 블록번호의 ACK는 무시하고 계속 기다림

        if len(file_block) < BLOCK_SIZE:
            print(f"last block {block_number} sent, transfer finished")
            success = True
            break
        block_number += 1

    f.close()
    sock.close()
    return success


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="mytftp client")
    parser.add_argument("host", help="server IP address or domain name", type=str)
    parser.add_argument("operation", help="get or put", type=str, choices=['get', 'put'])
    parser.add_argument("filename", help="filename", type=str)
    parser.add_argument("-p", dest="port", type=int, default=69, help="port number (default 69)")
    args = parser.parse_args()

    if args.operation == 'get':
        ok = download(args.host, args.port, args.filename)
    else:  # put
        ok = upload(args.host, args.port, args.filename)

    if ok:
        print(f"'{args.filename}' transfer completed successfully")
    else:
        sys.exit(1)
