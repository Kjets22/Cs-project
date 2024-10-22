import socket
import signal
import sys
import random
import urllib.parse
import threading

# Initialize shutdown event
shutdown_event = threading.Event()

# Dictionary to store active sessions: token -> username
sessions = {}

### Contents of pages we will serve.
# Login form with relative action
login_form = """
    <form action="/" method="post">
    Name: <input type="text" name="username"> <br/>
    Password: <input type="password" name="password" /> <br/>
    <input type="submit" value="Submit" />
    </form>
"""

# Default: Login page.
login_page = "<h1>Please login</h1>" + login_form

# Error page for bad credentials
bad_creds_page = "<h1>Bad user/pass! Try again</h1>" + login_form

# Successful logout
logout_page = "<h1>Logged out successfully</h1>" + login_form

# Success page with secret and logout option
success_page = """
    <h1>Welcome!</h1>
    <form action="/" method="post">
    <input type="hidden" name="action" value="logout" />
    <input type="submit" value="Click here to logout" />
    </form>
    <br/><br/>
    <h1>Your secret data is here:</h1>
    {secret}
"""

#### Helper functions
def print_value(tag, value):
    print(f"Here is the {tag}")
    print('"""')
    print(value)
    print('"""')
    print()

def parse_headers(header_text):
    headers = {}
    lines = header_text.split('\r\n')
    for line in lines[1:]:  # Skip the request line
        if ': ' in line:
            key, value = line.split(': ', 1)
            headers[key.strip()] = value.strip()
    return headers

def parse_cookies(cookie_header):
    cookies = {}
    cookie_pairs = cookie_header.split('; ')
    for pair in cookie_pairs:
        if '=' in pair:
            key, value = pair.split('=', 1)
            cookies[key] = value
    return cookies

def parse_body(body_text):
    params = urllib.parse.parse_qs(body_text)
    # Convert list values to single values
    return {k: v[0] for k, v in params.items()}


def load_user_data(filename, data_type):
    user_data = {}
    with open(filename, 'r') as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) >= 2:
                username, value = parts[0], parts[1]
                user_data[username] = value
    return user_data

def server_thread(port, credentials, secrets):
    hostname = "localhost"  # Use 'localhost' explicitly for consistency
    # Start a listening server socket on the port
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(('', port))
    sock.listen(5)
    print(f"Server is running on port {port}...")

    while not shutdown_event.is_set():
        try:
            sock.settimeout(1.0)  # Timeout to periodically check shutdown_event
            client, addr = sock.accept()
        except socket.timeout:
            continue
        except Exception as e:
            if shutdown_event.is_set():
                break
            print(f"Error accepting connections: {e}")
            continue

        # Handle client in a separate thread
        threading.Thread(target=handle_client, args=(client, hostname, port, credentials, secrets)).start()

    sock.close()
    print("Server socket closed.")

def handle_client(client, hostname, port, credentials, secrets):
        req = client.recv(4096).decode()

        # Split headers and body
        header_body = req.split('\r\n\r\n', 1)
        headers = header_body[0]
        body = header_body[1] if len(header_body) > 1 else ''
        print_value('headers', headers)
        print_value('entity body', body)

        # Parse headers into a dictionary
        header_dict = parse_headers(headers)

        # Extract cookies if present
        cookies = {}
        if 'Cookie' in header_dict:
            cookies = parse_cookies(header_dict['Cookie'])
            print(f"Received cookies: {cookies}")  # Debugging

        # Parse body parameters
        post_data = parse_body(body)
        print(f"Parsed POST data: {post_data}")  # Debugging

        # Initialize variables for response
        html_content_to_send = login_page
        headers_to_send = ''

        # Determine the action based on the request
        # Priority: Logout > Cookie Validation > Login Attempt > Show Login Page

        # 1. Case E: Logout
        if post_data.get('action') == 'logout':
            token = cookies.get('token')
            if token and token in sessions:
                username = sessions.pop(token)
                print(f"User '{username}' logged out.")
            else:
                print("Logout requested with invalid or missing token.")
            # Set expired cookie to clear it on the client
            headers_to_send += 'Set-Cookie: token=; expires=Thu, 01 Jan 1970 00:00:00 GMT\r\n'
            html_content_to_send = logout_page

        # 2. Case C: Valid Cookie
        elif 'token' in cookies and cookies['token'] in sessions:
            username = sessions[cookies['token']]
            secret = secrets.get(username, '')
            print(f"Valid session for user '{username}'.")
            html_content_to_send = success_page.format(secret=secret)

        # 3. Case D: Invalid Cookie
        elif 'token' in cookies:
            print(f"Invalid session token: {cookies['token']}")
            html_content_to_send = bad_creds_page

        # 4. Cases A and B: Handle POST data for login
        elif 'username' in post_data or 'password' in post_data:
            username = post_data.get('username', '')
            password = post_data.get('password', '')
            print(f"Login attempt with username: '{username}' and password: '{password}'")

            if username and password and username in credentials and credentials[username] == password:
                # Case A: Successful authentication
                secret = secrets.get(username, '')
                html_content_to_send = success_page.format(secret=secret)
                # Generate and set a new cookie
                rand_val = random.getrandbits(64)
                token = str(rand_val)
                headers_to_send += f'Set-Cookie: token={token}; HttpOnly\r\n'
                sessions[token] = username
                print(f"User '{username}' authenticated successfully. Token: {token}")
            else:
                # Case B: Failed authentication
                html_content_to_send = bad_creds_page
                print(f"Authentication failed for username: '{username}'")

        # 5. Basic Case: Show login page (already set)

        # Construct and send the final response
        response  = 'HTTP/1.1 200 OK\r\n'
        response += headers_to_send
        response += 'Content-Type: text/html\r\n\r\n'
        response += html_content_to_send

        print_value('response', response)
        client.sendall(response.encode())
        client.close()
        print("Served one request/connection!\n")

def main():
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print("Invalid port number. Using default port 8080.")
            port = 8080
    else:
        port = 8080
        print("Using default port 8080")

    # Load credentials and secrets

    credentials = load_user_data('passwords.txt', 'password')
    secrets = load_user_data('secrets.txt', 'secret')
    # Start server in a separate thread
    server = threading.Thread(target=server_thread, args=(port, credentials, secrets), daemon=True)
    server.start()

    # Wait for shutdown event (triggered by Ctrl+C)
    try:
        while not shutdown_event.is_set():
            shutdown_event.wait(1)
    except KeyboardInterrupt:
        print("\nKeyboardInterrupt received.")

    # Initiate shutdown
    shutdown_event.set()
    server.join()
    print("Server has been shut down gracefully.")

if __name__ == "__main__":
    main()
