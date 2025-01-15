import socket
import struct
import threading
import time
import random


class SpeedTestServer:
    MAGIC_COOKIE = 0xabcddcba
    MSG_OFFER = 0x2
    MSG_REQUEST = 0x3
    MSG_DATA = 0x3
    MSG_TYPE_PAYLOAD = 0x4

    def __init__(self):
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.udp_socket.bind(('', 0))
        self.tcp_socket.bind(('', 0))
        self.tcp_socket.listen(5)

        self.udp_port = self.udp_socket.getsockname()[1]
        self.tcp_port = self.tcp_socket.getsockname()[1]
        self.active = True

        print(f"Server started on UDP port {self.udp_port}, TCP port {self.tcp_port}")

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

        while sent < size and self.active:
            try:
                remaining = size - sent
                chunk_size = min(1024, remaining)
                chunk = random.randbytes(chunk_size)

                time.sleep(0.0001)

                header = struct.pack('!IbQQ',
                                     self.MAGIC_COOKIE,
                                     self.MSG_TYPE_PAYLOAD,
                                     total,
                                     segment
                                     )

                packet = header + chunk
                bytes_sent = self.udp_socket.sendto(packet, addr)

                if bytes_sent > 0:
                    sent += chunk_size
                    segment += 1

            except Exception as e:
                print(f"UDP transfer error: {e}")
                break


if __name__ == "__main__":
    server = SpeedTestServer()
    server.start()
