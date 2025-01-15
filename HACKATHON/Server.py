import socket
import struct
import threading
import time
import random


class SpeedTestServer:
    MAGIC_COOKIE = 0xabcddcba
    MSG_OFFER = 0x2
    MSG_REQUEST = 0x3
    MSG_TYPE_PAYLOAD = 0x4

    def __init__(self):
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Enable socket reuse
        for sock in (self.udp_socket, self.tcp_socket):
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Get IP address
        hostname = socket.gethostname()
        self.ip_address = socket.gethostbyname(hostname)

        self.udp_socket.bind(('', 0))
        self.tcp_socket.bind(('', 0))
        self.tcp_socket.listen(5)

        self.udp_port = self.udp_socket.getsockname()[1]
        self.tcp_port = self.tcp_socket.getsockname()[1]
        self.active = True

        print(f"Server started, listening on IP address {self.ip_address}")

    def start(self):
        threads = [
            threading.Thread(target=self._broadcast),
            threading.Thread(target=self._handle_tcp),
            threading.Thread(target=self._handle_udp)
        ]

        for t in threads:
            t.daemon = True
            t.start()

        try:
            while self.active:
                time.sleep(1)
        except KeyboardInterrupt:
            self.active = False

    def _broadcast(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        while self.active:
            try:
                message = struct.pack('!IbHH', self.MAGIC_COOKIE, self.MSG_OFFER,
                                      self.udp_port, self.tcp_port)
                sock.sendto(message, ('<broadcast>', 13117))
                time.sleep(1)
            except:
                pass

    def _handle_tcp(self):
        while self.active:
            try:
                client, _ = self.tcp_socket.accept()
                threading.Thread(target=self._tcp_client, args=(client,)).start()
            except:
                pass

    def _tcp_client(self, client):
        try:
            size = int(client.recv(1024).decode().strip())
            sent = 0
            while sent < size:
                chunk = random.randbytes(min(8192, size - sent))
                client.send(chunk)
                sent += len(chunk)
        finally:
            client.close()

    def _handle_udp(self):
        while self.active:
            try:
                data, addr = self.udp_socket.recvfrom(1024)
                if len(data) >= 13:
                    magic, msg_type, size = struct.unpack('!IbQ', data[:13])
                    if magic == self.MAGIC_COOKIE and msg_type == self.MSG_REQUEST:
                        threading.Thread(target=self._udp_transfer,
                                         args=(addr, size)).start()
            except:
                pass

    def _udp_transfer(self, addr, size):
        sent = 0
        segment = 0
        total = (size + 1023) // 1024
        transfer_start = time.time()
        max_transfer_time = 10  # Timeout כולל של 10 שניות להעברה

        while sent < size and self.active:
            try:
                if time.time() - transfer_start > max_transfer_time:
                    print(f"UDP transfer timed out for {addr}")
                    break

                remaining = size - sent
                chunk_size = min(1024, remaining)
                chunk = random.randbytes(chunk_size)

                header = struct.pack('!IbQQ',
                                     self.MAGIC_COOKIE,
                                     self.MSG_TYPE_PAYLOAD,
                                     total,
                                     segment)

                packet = header + chunk
                self.udp_socket.sendto(packet, addr)

                sent += chunk_size
                segment += 1
                time.sleep(0.0001)  # Small delay to prevent overwhelming the network

            except Exception as e:
                print(f"UDP transfer error: {e}")
                break


if __name__ == "__main__":
    server = SpeedTestServer()
    server.start()
