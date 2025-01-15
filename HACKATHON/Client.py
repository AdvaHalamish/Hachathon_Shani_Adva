import socket
import struct
import threading
import time
from dataclasses import dataclass


@dataclass
class Stats:
    id: int
    protocol: str
    start: float
    end: float = 0
    bytes: int = 0
    packets: int = 0
    total_packets: int = 0


class SpeedTestClient:
    MAGIC_COOKIE = 0xabcddcba
    MSG_TYPE_OFFER = 0x2
    MSG_TYPE_REQUEST = 0x3
    MSG_TYPE_PAYLOAD = 0x4

    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.bind(('', 13117))
        self.server = None
        self.active = True

    def start(self):
        print("Client started, waiting for server...")

        while self.active:
            try:
                size = int(input("Enter size (bytes): "))
                tcp = int(input("Enter TCP connections: "))
                udp = int(input("Enter UDP connections: "))

                self._find_server()
                if not self.server:
                    continue

                threads = []
                for i in range(tcp):
                    t = threading.Thread(target=self._tcp_test, args=(i + 1, size))
                    threads.append(t)
                    t.start()

                for i in range(udp):
                    t = threading.Thread(target=self._udp_test, args=(tcp + i + 1, size))
                    threads.append(t)
                    t.start()

                for t in threads:
                    t.join()

            except KeyboardInterrupt:
                break
            except:
                time.sleep(1)

    def _find_server(self):
        print("Looking for server...")
        try:
            data, addr = self.sock.recvfrom(1024)
            if len(data) >= 9:
                magic, msg_type, udp_port, tcp_port = struct.unpack('!IbHH', data[:9])
                if magic == self.MAGIC_COOKIE and msg_type == self.MSG_TYPE_OFFER:
                    self.server = (addr[0], udp_port, tcp_port)
                    print(f"Found server at {addr[0]}")
        except:
            pass

    def _tcp_test(self, test_id, size):
        stats = Stats(test_id, "TCP", time.time())
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self.server[0], self.server[2]))
            sock.send(f"{size}\n".encode())

            while stats.bytes < size:
                data = sock.recv(8192)
                if not data:
                    break
                stats.bytes += len(data)

        finally:
            sock.close()
            stats.end = time.time()
            self._print_stats(stats)

    def _udp_test(self, test_id, size):
        stats = Stats(test_id, "UDP", time.time())
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(1.0)

            request = struct.pack('!IbQ', self.MAGIC_COOKIE, self.MSG_TYPE_REQUEST, size)
            sock.sendto(request, (self.server[0], self.server[1]))

            segments = set()
            last_recv = time.time()

            while True:
                try:
                    data, _ = sock.recvfrom(2048)
                    last_recv = time.time()

                    if len(data) >= 21:
                        magic, msg_type, total, seg = struct.unpack('!IbQQ', data[:21])

                        if (magic == self.MAGIC_COOKIE and
                                msg_type == self.MSG_TYPE_PAYLOAD and
                                seg not in segments):

                            payload = data[21:]
                            segments.add(seg)
                            stats.bytes += len(payload)
                            stats.packets += 1
                            stats.total_packets = total

                            if stats.packets % 100 == 0:
                                print(f"UDP #{stats.id}: received {stats.packets}/{total} packets")

                except socket.timeout:
                    if time.time() - last_recv > 2.0:
                        break
                    continue

        except Exception as e:
            print(f"UDP test error: {e}")
        finally:
            sock.close()
            stats.end = time.time()
            self._print_stats(stats)

    def _print_stats(self, stats):
        duration = stats.end - stats.start
        speed = (stats.bytes * 8) / duration

        if stats.protocol == "TCP":
            print(f"TCP #{stats.id}: {duration:.2f}s, {speed:.1f} bits/s")
        else:
            success = (stats.packets / stats.total_packets * 100) if stats.total_packets else 0
            print(f"UDP #{stats.id}: {duration:.2f}s, {speed:.1f} bits/s, {success:.1f}% packets")


if __name__ == "__main__":
    client = SpeedTestClient()
    client.start()
