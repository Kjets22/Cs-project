# ts2.py

import socket
import sys

def main():
    port = int(sys.argv[1])
    ts_db = {}

    with open('ts2database.txt', 'r') as f:
        for line in f:
            domain, ip = line.strip().lower().split()
            ts_db[domain] = ip

    s = socket.socket()
    s.bind(('', port))
    s.listen()
    with open('ts2responses.txt', 'w') as resolved_log:
        while True:
            conn, _ = s.accept()
            data = conn.recv(1024).decode()
            tokens = data.strip().split()
            if len(tokens) != 4:
                conn.close()
                continue
            _, domain, ident, _ = tokens
            domain = domain.lower()
                
            if domain in ts_db:
                response = f'1 {domain} {ts_db[domain]} {ident} aa'
            else:
                response = f'1 {domain} 0.0.0.0 {ident} nx'
            conn.send(response.encode())
            resolved_log.write(response + '\n')
            resolved_log.flush() 
            conn.close()

if __name__ == "__main__":
    main()
