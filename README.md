**SpeedTest System**

General Description
The system consists of a Server and a Client that allow network speed tests using the TCP and UDP protocols.
The client connects to the server, sends requests for speed tests, and measures the data transfer rate.
The server responds to client requests, performs the transfers, and shares information about the transfer.

System Structure
SpeedTestClient
This is a class representing the client that connects to the server to perform speed tests.

Key Attributes:

MAGIC_COOKIE: A unique identifier for communication between the client and server.
MSG_TYPE_OFFER, MSG_TYPE_REQUEST, MSG_TYPE_PAYLOAD: Identifiers for message types exchanged between the client and server.
Functions:

__init__():
Initializes the client, prepares the sockets, and listens for connection offers.

start():
The main loop allows the client to configure test details and search for a suitable server.

_get_positive_int(prompt: str):
Prompts the user to enter a positive integer and handles input errors.

_find_server():
Searches for a valid server offering test services using a "Offer" message (MSG_TYPE_OFFER).

_tcp_test(test_id, size):
Performs a TCP speed test and reports the achieved rate.

_udp_test(test_id, size):
Performs a UDP speed test, counts successful packets, and reports the rate and success percentage.

SpeedTestServer
This is a class representing the server that provides speed testing services to clients.

Key Attributes:

MAGIC_COOKIE: A unique identifier for communication between the client and server.
MSG_OFFER, MSG_REQUEST, MSG_TYPE_PAYLOAD: Identifiers for message types.
Functions:

__init__():
Initializes the server, opens TCP and UDP sockets, and waits for connections.

start():
Launches three processes:

Broadcasting messages (_broadcast) to notify clients of server availability.
Handling TCP connections (_handle_tcp) to send requested data to clients.
Handling UDP requests (_handle_udp) to send data packets to clients.
_broadcast():
Sends broadcast messages to notify clients of server availability.

_handle_tcp():
Listens for TCP requests from clients and transfers the requested amount of data.

_handle_udp():
Listens for UDP requests, processes them, and sends data in small packets.

_udp_transfer(addr, size):
Performs data transfer over UDP, including sending data packets with unique identifiers.
