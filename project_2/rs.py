# rs.py

import socket
import sys

def main():
    port = int(sys.argv[1])
    ts_servers = {}
    rs_db = {}

    with open('rsdatabase.txt', 'r') as f:
        lines = [line.strip() for line in f]
        ts1_info = lines[0].split()
        ts2_info = lines[1].split()
        # Include port numbers for TS servers
        ts_servers[ts1_info[0]] = (ts1_info[1], 5001)  # TS1 port hardcoded
        ts_servers[ts2_info[0]] = (ts2_info[1], 5002)  # TS2 port hardcoded
        for line in lines[2:]:
            domain, ip = line.lower().split()
            rs_db[domain] = ip

    s = socket.socket()
    s.bind(('', port))
    s.listen()

    with open('rsresponses.txt', 'w') as resolved_log:
        while True:  
            conn, _ = s.accept()
            data = conn.recv(1024).decode()
            tokens = data.strip().split()
            if len(tokens) != 4:
                conn.close()
                continue
            _, domain, ident, flag = tokens
            domain = domain.lower()
            tld = domain.split('.')[-1]
    
            if tld in ts_servers:
                if flag == 'it':
                    ts_host, ts_port = ts_servers[tld]
                    # Include port number in the response
                    ts_info = f'{ts_host}:{ts_port}'# do this instead of ts_host line below
                    response = f'1 {domain} {ts_host} {ident} ns'
                    # resolved_log.write(response + '\n')
                    # resolved_log.flush()                       
                    conn.send(response.encode())
                else:
                    ts_host, ts_port = ts_servers[tld]
                    ts_sock = socket.socket()
                    ts_sock.connect((ts_host, port))
                    ts_sock.send(data.encode())
                    ts_response = ts_sock.recv(1024).decode()
                    ts_sock.close()
                    resp_tokens = ts_response.strip().split()
                    if resp_tokens[4] == 'aa':
                        resp_tokens[4] = 'ra'
                    response = ' '.join(resp_tokens)
                    # resolved_log.write(response + '\n')
                    # resolved_log.flush()                    
                    conn.send(response.encode())
            else:
                if domain in rs_db:
                    response = f'1 {domain} {rs_db[domain]} {ident} aa'
                else:
                    response = f'1 {domain} 0.0.0.0 {ident} nx'
                conn.send(response.encode())
            resolved_log.write(response + '\n')
            resolved_log.flush()              
            conn.close()
       

if __name__ == "__main__":
    main()
