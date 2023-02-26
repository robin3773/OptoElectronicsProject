import socket



# Define the server address and port
SERVER_ADDRESS = 'localhost'
SERVER_PORT = 12345

# Create a socket object
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Bind the socket to the server address and port
server_socket.bind((SERVER_ADDRESS, SERVER_PORT))

# Listen for incoming connections
server_socket.listen()

# Start the server loop
while True:
    # Wait for a client connection
    client_socket, client_address = server_socket.accept()

    # Print a message indicating that a client has connected
    print(f'Client connected from {client_address}')

    # Receive and process data from the client
    while True:
        data = client_socket.recv(1024)
        if not data:
            break
        # Process the received data here
        print(f'Received data: {data.decode()}')

    # Close the client socket when done
    client_socket.close()

