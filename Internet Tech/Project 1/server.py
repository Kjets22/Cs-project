import threading
import socket


def reverse(string: str) -> str:
    return string[::-1].swapcase()


def handle_client(csockid, addr):
    with csockid:
        while True:
            # Receive data from the client
            data_from_client = csockid.recv(1024)
            if not data_from_client:
                # No more data from client, connection closed
                print(f"[S]: No more data from {addr}. Closing connection.")
                break

            # Decode bytes to string
            decode_data = data_from_client.decode('utf-8')
            print(f"[S]: Received from client: {decode_data}")

            # Process the data
            swapped: str = reverse(decode_data)
            print(f"[S]: Reversed and swapped: {swapped}")

            # Send the processed data back to the client
            csockid.send(swapped.encode('utf-8'))


def server():
    # Create a TCP/IP socket
    ss = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print("[S]: Server socket created")

    # Bind the socket to the port
    server_binding = ('', 50007)  # '' means all available interfaces
    ss.bind(server_binding)
    ss.listen(5)  # Listen for incoming connections with a backlog of 5
    host = socket.gethostname()
    localhost_ip = socket.gethostbyname(host)
    print(f"[S]: Server host name is {host}")
    print(f"[S]: Server IP address is {localhost_ip}")
    print(f"[S]: Listening on port {50007}...")
    
    csockid, addr = ss.accept()
    handle_client(csockid,addr)
    ss.close()
    exit()


if __name__ == "__main__":
    server()
