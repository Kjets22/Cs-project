import socket


def client():
    # Create a TCP/IP socket
    cs = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print("[C]: Client socket created")

    # Define the server address and port
    port = 50007        # Must match the server's listening port
    localhost_addr = socket.gethostbyname(socket.gethostname())
    # Connect to the server on the local machine
    server_binding = (localhost_addr, port)
    cs.connect(server_binding)
    print(f"[C]: Connected to server at {server_binding}")
    msg="HellO"
    print(f"[C]: input {msg}")
    cs.send(msg.encode('utf-8'))
    recoved=cs.recv(1024)
    decoded=recoved.decode('utf-8')
    print(f"[C]: output {decoded}")

    # Open the input and output files
    with open('in-proj.txt', 'r') as infile, open('out-proj.txt', 'w') as outfile:
        lines = infile.readlines()
        print(f"[C]: Total lines to send: {len(lines)}")
        for idx, line in enumerate(lines, 1):
            line = line.strip()  # Remove leading/trailing whitespace and newline characters
            print(f"[C]: Sending line {idx}: {line}")
            cs.send(line.encode('utf-8'))

            # Receive the processed message from the server
            data_from_server = cs.recv(1024)
            if data_from_server:
                processed_line = data_from_server.decode('utf-8')
                print(f"[C]: Received from server for line {idx}: {processed_line}")
                outfile.write(processed_line + '\n')
            else:
                print(f"[C]: No data received from server for line {idx}.")
                break

    # Close the client socket
    cs.close()
    print("[C]: Client socket closed")


if __name__ == "__main__":
    client()
