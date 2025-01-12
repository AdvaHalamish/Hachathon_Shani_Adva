import socket
import threading
import time
import struct

class Server:
    def __init__(self, udp_port=13117, tcp_port=8080):
        self.udp_port = udp_port
        self.tcp_port = tcp_port

    def broadcast_offers(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
            udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            message = struct.pack('!IBHH', 0xabcddcba, 0x2, self.udp_port, self.tcp_port)
            while True:
                udp_socket.sendto(message, ('<broadcast>', self.udp_port))
                print("Broadcasting offer message")
                time.sleep(1)

    def handle_tcp_client(self, connection, address):
        print(f"Handling TCP client from {address}")
        try:
            data = connection.recv(1024).decode()
            file_size = int(data.strip())

            chunk_size = 1024
            bytes_sent = 0
            while bytes_sent < file_size:
                to_send = min(chunk_size, file_size - bytes_sent)
                connection.sendall(b'X' * to_send)
                bytes_sent += to_send
        except Exception as e:
            print(f"TCP Error: {e}")
        finally:
            connection.close()

    def handle_udp_clients(self, udp_socket):
        try:
            while True:
                try:
                    data, client_address = udp_socket.recvfrom(1024)
                    if len(data) != 13:
                        print(f"Invalid data length from {client_address}: {len(data)} bytes")
                        continue
                    unpacked_data = struct.unpack('!IBQ', data)
                    file_size = unpacked_data[2]

                    # Respond with dummy UDP packets
                    for i in range(file_size // 1024):
                        payload = struct.pack('!IBQQ', 0xabcddcba, 0x4, file_size // 1024, i)
                        udp_socket.sendto(payload, client_address)
                except socket.timeout:
                    continue
        except Exception as e:
            print(f"UDP Error: {e}")

    def start(self):
        threading.Thread(target=self.broadcast_offers, daemon=True).start()

        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
            udp_socket.bind(("0.0.0.0", self.udp_port))
            threading.Thread(target=self.handle_udp_clients, args=(udp_socket,), daemon=True).start()

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp_socket:
            tcp_socket.bind(("0.0.0.0", self.tcp_port))
            tcp_socket.listen()
            print("TCP Server started")

            while True:
                connection, address = tcp_socket.accept()
                threading.Thread(target=self.handle_tcp_client, args=(connection, address), daemon=True).start()

if __name__ == "__main__":
    server = Server()
    server.start()