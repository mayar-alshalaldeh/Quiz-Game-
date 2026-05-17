Task 2 - Quiz Game
Student ID: 1231643
Name: Mayar AL-Shalaldeh
Student ID: 1221806
Name: Manar Zitawi


How to Run the Task ... :

1:- Run the server first:
   > python server.py

   The server will start listening on:
   - TCP port = 3643
   - UDP port = 7231

2:- Run at least two clients (in separate terminals):
   > python client.py

   Each client will be asked to enter a unique username.

3:- The game starts automatically when the minimum number of players (2) is connected.

4:- Each question is broadcasted via TCP.
   Players must type their answer (a/b/c/d) in their client.
   Feedback (Correct/Wrong/Too_Late/Duplicate) is sent immediately via UDP.

5:- After all questions are done, the server sends the final results and announces the winner.


** Notes : 

- If a username is already taken, the client will be rejected.
- The server accepts between 2 and 4 players.
- Each round has a time limit of 10 seconds.
- Libraries used: socket, threading, time, random (only standard Python libraries).
