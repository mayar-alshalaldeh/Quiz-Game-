import socket
import threading
import time

# Calculate TCP and UDP ports based on student ID
STUDENT_ID = 1231643
TCP_PORT = (STUDENT_ID % 1000) + 3000  # Gets last 3 digits + 3000
UDP_PORT = (STUDENT_ID // 1000) + 6000  # Gets first 3 digits + 6000
SERVER_IP = "127.0.0.1"  # Localhost IP address

# Get player name from user input
player_name = input("Choose a username: ").strip()

# Create TCP and UDP sockets
tcp_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
udp_conn = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Bind UDP socket to any available port
udp_conn.bind(('', 0))

# Function to get user answer and send via UDP
def ask_and_send():
    # Get and validate user input
    answer = input("Enter your choice (a/b/c/d): ").lower().strip()
    while answer not in ("a", "b", "c", "d"):
        answer = input("Invalid! Enter a/b/c/d: ").lower().strip()
    
    # Format and send the answer packet
    packet = f"{player_name}:{answer}"
    udp_conn.sendto(packet.encode(), (SERVER_IP, UDP_PORT))

# Function to handle TCP messages from server
def listen_tcp():
    while True:
        try:
            # Receive data from TCP connection
            raw = tcp_conn.recv(4096)
            if not raw:
                print("[TCP] Server closed the connection.")
                break
            message = raw.decode()

            # Handle different message types from server
            if message.startswith("GAME_START"):
                print("\n>> The quiz is starting!\n")
                print(message)

            elif message.startswith("QUESTION|"):
                # Parse and display question
                _, qnum, qtext = message.split("|", 2)
                print(f"\n### Question {qnum} ###")
                print(qtext)
                # Start a thread to get user answer
                threading.Thread(target=ask_and_send, daemon=True).start()

            elif message.startswith("ROUND_SUMMARY"):
                print("\n--- Round Summary ---")
                print(message)

            elif message.startswith("FINAL_RESULTS"):
                print("\n=== GAME OVER ===")
                print(message)
                break

            else:
                # Handle any other TCP messages
                print("[TCP MSG]", message)

        except Exception as err:
            print("[TCP ERROR]", err)
            break

# Function to handle UDP messages from server
def listen_udp():
    while True:
        try:
            # Receive data from UDP connection
            data, _ = udp_conn.recvfrom(1024)
            print("\n[UDP FEEDBACK]", data.decode())
        except Exception as err:
            print("[UDP ERROR]", err)
            break

try:
    # Connect to server via TCP
    tcp_conn.connect((SERVER_IP, TCP_PORT))
    # Send join request with player name
    tcp_conn.sendall(f"JOIN {player_name}".encode())
    # Wait for registration confirmation
    reply = tcp_conn.recv(1024).decode().strip()

    if reply != "REGISTERED":
        print("(!) Registration failed:", reply)
        tcp_conn.close()
        udp_conn.close()
        exit(1)

    print(f"[INFO] Welcome {player_name}, waiting for the game to begin...")

    # Register UDP connection with server
    udp_conn.sendto(f"UDP_REG {player_name}".encode(), (SERVER_IP, UDP_PORT))

    # Start threads to listen for TCP and UDP messages
    threading.Thread(target=listen_tcp, daemon=True).start()
    threading.Thread(target=listen_udp, daemon=True).start()

    # Main thread just sleeps while worker threads handle communication
    while True:
        time.sleep(1)

except KeyboardInterrupt:
    print("\n[EXIT] Client closed manually.")

finally:
    # Clean up connections
    try:
        tcp_conn.close()
    except:
        pass
    try:
        udp_conn.close()
    except:
        pass