import socket
import threading
import time
import struct
class Client:
    def __init__(self, file_size, tcp_connections, udp_connections, udp_port=13117):
        self.file_size = file_size
        self.tcp_connections = tcp_connections
        self.udp_connections = udp_connections
        self.udp_port = udp_port

    def listen_for_offers(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
            udp_socket.bind(('', self.udp_port))
            print("Listening for server offers...")

            while True:
                data, server_address = udp_socket.recvfrom(1024)
                try:
                    unpacked_data = struct.unpack('!IBHH', data)
                    if unpacked_data[0] == 0xabcddcba and unpacked_data[1] == 0x2:
                        print(f"Received offer from {server_address[0]}")
                        return server_address[0], unpacked_data[2], unpacked_data[3]
                except Exception as e:
                    print(f"Offer Error: {e}")

    def tcp_transfer(self, server_ip, server_tcp_port, connection_id):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp_socket:
                tcp_socket.connect((server_ip, server_tcp_port))
                tcp_socket.sendall(f"{self.file_size}\n".encode())

                start_time = time.time()
                received = 0
                while received < self.file_size:
                    chunk = tcp_socket.recv(1024)
                    if not chunk:
                        break
                    received += len(chunk)

                elapsed_time = time.time() - start_time
                speed = received / elapsed_time if elapsed_time > 0 else 0
                print(f"TCP transfer #{connection_id} finished, total time: {elapsed_time:.2f} seconds, speed: {speed:.2f} bytes/second")
        except Exception as e:
            print(f"TCP transfer #{connection_id} error: {e}")

    def udp_transfer(self, server_ip, server_udp_port, connection_id):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
                udp_socket.settimeout(1)

                request = struct.pack('!IBQ', 0xabcddcba, 0x3, self.file_size)
                udp_socket.sendto(request, (server_ip, server_udp_port))

                start_time = time.time()
                received_bytes = 0
                while time.time() - start_time < 1:
                    try:
                        data, _ = udp_socket.recvfrom(1024)
                        received_bytes += len(data)
                    except socket.timeout:
                        break

                elapsed_time = time.time() - start_time
                speed = received_bytes / elapsed_time if elapsed_time > 0 else 0
                print(
                    f"UDP transfer #{connection_id} finished, total time: {elapsed_time:.2f} seconds, "
                    f"speed: {speed:.2f} bytes/second"
                )
        except Exception as e:
            print(f"UDP transfer #{connection_id} error: {e}")

    def start(self):
        server_ip, server_udp_port, server_tcp_port = self.listen_for_offers()

        threads = []

        for i in range(self.tcp_connections):
            t = threading.Thread(target=self.tcp_transfer, args=(server_ip, server_tcp_port, i + 1))
            t.start()
            threads.append(t)

        for i in range(self.udp_connections):
            t = threading.Thread(target=self.udp_transfer, args=(server_ip, server_udp_port, i + 1))
            t.start()
            threads.append(t)

        for t in threads:
            t.join()

if __name__ == "__main__":
    max_file_size = 2**64 - 1
    file_size = int(input("Enter file size (in bytes): ").strip())
    if file_size > max_file_size:
        raise ValueError(f"File size must be at most {max_file_size} bytes (8 bytes).")

    tcp_connections = int(input("Enter number of TCP connections: ").strip())
    udp_connections = int(input("Enter number of UDP connections: ").strip())
    client = Client(file_size, tcp_connections, udp_connections)
    client.start()
