# client.py

import socket
import sys

def main():
    rs_host = sys.argv[1]
    port = int(sys.argv[2])
    identification = 1

    with open('hostnames.txt', 'r') as f:
        queries = [line.strip().split() for line in f]

    with open('resolved.txt', 'w') as resolved_log:
        for domain, flag in queries:
            domain = domain.lower()
            s = socket.socket()
            s.connect((rs_host, port))
            message = f'0 {domain} {identification} {flag}'
            s.send(message.encode())
            response = s.recv(1024).decode()
            resolved_log.write(response + '\n')
            s.close()
            resp_tokens = response.strip().split()
            resp_flag = resp_tokens[4]
            if flag == 'it' and resp_flag == 'ns': 
                print(resp_tokens[2])
                resp_host , resp_port = resp_tokens[2].split(':')
                resp_port=int(resp_port)
                identification += 1
                ts_sock = socket.socket()
                ts_sock.connect((resp_host,port))
                ts_message = f'0 {domain} {identification} {flag}'
                ts_sock.send(ts_message.encode())
                ts_response = ts_sock.recv(1024).decode()
                resolved_log.write(ts_response + '\n')
                ts_sock.close()
            identification += 1
            print("done")

if __name__ == "__main__":
    main()
