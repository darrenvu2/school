from socket import *

msg = "\r\n I love computer networks!"
endmsg = "\r\n.\r\n"

mailserver = 'smtp.sjsu.edu'
port = 25

# Create socket
clientSocket = socket(AF_INET, SOCK_STREAM)
clientSocket.connect((mailserver, port))

recv = clientSocket.recv(1024).decode()
print(recv)

# HELO
clientSocket.send("HELO Darren\r\n".encode())
print(clientSocket.recv(1024).decode())

# MAIL FROM
clientSocket.send("MAIL FROM:<darren.vu@sjsu.edu>\r\n".encode())
print(clientSocket.recv(1024).decode())

# RCPT TO
clientSocket.send("RCPT TO:<darren.vu@sjsu.edu>\r\n".encode())
print(clientSocket.recv(1024).decode())

# DATA
clientSocket.send("DATA\r\n".encode())
print(clientSocket.recv(1024).decode())

# Message
clientSocket.send(msg.encode())

# End message
clientSocket.send(endmsg.encode())
print(clientSocket.recv(1024).decode())

# QUIT
clientSocket.send("QUIT\r\n".encode())
print(clientSocket.recv(1024).decode())

clientSocket.close()