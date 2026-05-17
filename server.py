import socket
import threading
import time
import random

# Configuration constants
STUDENT_ID = 1231643
PORT_TCP = (STUDENT_ID % 1000) + 3000  # Calculate TCP port from student ID
PORT_UDP = (STUDENT_ID // 1000) + 6000  # Calculate UDP port from student ID
HOST_IP = "0.0.0.0"  # Listen on all available interfaces

# Game configuration
MIN_PLAYERS = 2  # Minimum players needed to start the game
MAX_PLAYERS = 4  # Maximum players allowed
ROUND_TIME = 10  # Time limit for each question in seconds
TOTAL_QUESTIONS = 5  # Number of questions per game

# Quiz question pool (question, options, correct answer)
quiz_pool = [
    ("Which protocol is connectionless?",
     ["a) TCP", "b) FTP", "c) UDP", "d) HTTP"], "c"),
    ("Which layer does IP operate on?",
     ["a) Transport", "b) Network", "c) Data Link", "d) Physical"], "b"),
    ("What does HTTP stand for?",
     ["a) Hyper Transfer Text Protocol",
      "b) HyperText Transfer Protocol",
      "c) High Text Transmission Protocol",
      "d) None of the above"], "b"),
    ("What port number is typically HTTP?",
     ["a) 20", "b) 22", "c) 80", "d) 443"], "c"),
    ("Which device forwards packets between networks?",
     ["a) Switch", "b) Hub", "c) Router", "d) Modem"], "c"),
]

# Data structures to track clients and game state
clients_tcp = {}  # Maps username to TCP connection
clients_udp = {}  # Maps username to UDP address
points = {}  # Maps username to score

lock = threading.Lock()  # Thread synchronization lock
quiz_started = False  # Flag indicating if game has started
round_open = False  # Flag indicating if answers are being accepted
right_answer = None  # Current correct answer
answered_players = set()  # Set of players who have answered the current question


def register_player(conn, addr):
    global quiz_started
    try:
        # Receive and parse join request
        req = conn.recv(1024).decode().strip()
        if not req.startswith("JOIN "):
            conn.sendall(b"INVALID_FORMAT")
            conn.close()
            return

        uname = req.split(" ", 1)[1].strip()

        with lock:
            # Check various registration conditions
            if quiz_started:
                conn.sendall(b"GAME_IN_PROGRESS")
                conn.close()
                return
            if uname in clients_tcp:
                conn.sendall(b"USERNAME_EXISTS")
                conn.close()
                return
            if len(clients_tcp) >= MAX_PLAYERS:
                conn.sendall(b"SERVER_FULL")
                conn.close()
                return

            # Register the new player
            clients_tcp[uname] = conn
            points[uname] = 0

        conn.sendall(b"REGISTERED")
        print(f"[JOIN] {uname} connected from {addr}, total={len(clients_tcp)}")

    except Exception:
        # Clean up on error
        try:
            conn.close()
        except:
            pass


def tcp_listener():
    # Set up TCP server socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((HOST_IP, PORT_TCP))
    sock.listen(5)
    print(f"[TCP] Listening on {HOST_IP}:{PORT_TCP}")

    # Continuously accept new connections
    while True:
        conn, addr = sock.accept()
        # Handle each connection in a separate thread
        threading.Thread(target=register_player, args=(conn, addr), daemon=True).start()


def udp_handler():
    global round_open, right_answer, answered_players
    # Set up UDP server socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((HOST_IP, PORT_UDP))
    print(f"[UDP] Listening on {HOST_IP}:{PORT_UDP}")

    # Process incoming UDP messages
    while True:
        data, addr = sock.recvfrom(1024)
        text = data.decode().strip()

        # Handle UDP registration requests
        if text.startswith("UDP_REG "):
            uname = text.split(" ", 1)[1].strip()
            with lock:
                clients_udp[uname] = addr
            sock.sendto(b"UDP_OK", addr)
            continue

        # Validate answer format
        if ":" not in text:
            sock.sendto(b"BAD_FORMAT", addr)
            continue

        # Parse username and answer
        uname, ans = text.split(":", 1)
        uname, ans = uname.strip(), ans.strip().lower()

        with lock:
            # Validate the answer submission
            if not round_open:
                sock.sendto(b"TOO_LATE", addr)
                continue
            if uname not in points:
                sock.sendto(b"UNKNOWN_USER", addr)
                continue
            if uname in answered_players:
                sock.sendto(b"DUPLICATE", addr)
                continue

            # Process valid answer
            answered_players.add(uname)
            if ans == right_answer:
                points[uname] += 1
                sock.sendto(b"Correct", addr)
            else:
                sock.sendto(b"Wrong", addr)


def tcp_broadcast(msg: str):
    # Send a message to all connected TCP clients
    to_remove = []
    for uname, conn in list(clients_tcp.items()):
        try:
            conn.sendall(msg.encode())
        except:
            # Mark disconnected clients for cleanup
            to_remove.append(uname)
    # Clean up disconnected clients
    for uname in to_remove:
        with lock:
            print(f"[CLEANUP] {uname} removed.")
            clients_tcp.pop(uname, None)
            clients_udp.pop(uname, None)
            points.pop(uname, None)


def game_flow():
    global quiz_started, round_open, right_answer, answered_players

    # Wait for minimum number of players
    print("[GAME] Waiting for enough players...")
    while True:
        with lock:
            if len(clients_tcp) >= MIN_PLAYERS:
                break
        time.sleep(0.5)

    # Start the game
    with lock:
        quiz_started = True

    print("[GAME] Starting now!")
    tcp_broadcast("GAME_START\nWelcome to the quiz!\n")

    # Select random questions from the pool
    selected = random.sample(quiz_pool, k=min(TOTAL_QUESTIONS, len(quiz_pool)))

    # Process each question
    for qnum, (qtext, options, correct) in enumerate(selected, start=1):
        with lock:
            right_answer = correct
            round_open = True
            answered_players = set()

        # Broadcast question to all players
        qmsg = f"QUESTION|{qnum}|{qtext}\n" + "\n".join(options) + "\n"
        tcp_broadcast(qmsg)
        print(f"[QUESTION {qnum}] {qtext} (ans={correct})")
        print(f"[TIMER] Waiting {ROUND_TIME}s...")

        # Wait for the round time to expire
        start = time.monotonic()
        while time.monotonic() - start < ROUND_TIME:
            time.sleep(0.1)

        # Close the round
        with lock:
            round_open = False
        print("[TIMER] Round closed.")

        # Send round summary to all players
        with lock:
            summary = ["ROUND_SUMMARY"]
            for u in points:
                flag = "Answered" if u in answered_players else "NoAnswer"
                summary.append(f"{u}: {points[u]} pts ({flag})")
        tcp_broadcast("\n".join(summary) + "\n")

        time.sleep(1.5)

    # Send final results
    with lock:
        final = ["FINAL_RESULTS"]
        ranking = sorted(points.items(), key=lambda x: -x[1])
        for u, sc in ranking:
            final.append(f"{u}: {sc} points")
        if ranking:
            final.append(f"Winner: {ranking[0][0]}")
        else:
            final.append("No players.")
    tcp_broadcast("\n".join(summary) + "\n")
    print("[GAME] Final results sent.")


if __name__ == "__main__":
    # Start TCP and UDP listener threads
    threading.Thread(target=tcp_listener, daemon=True).start()
    threading.Thread(target=udp_handler, daemon=True).start()
    time.sleep(0.5)
    # Start the game flow
    game_flow()