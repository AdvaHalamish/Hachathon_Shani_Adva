import socket
import struct
import threading
import time
from typing import Optional, Tuple


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

        print("Client started, listening for offer requests...")

    def start(self):
        while self.active:
            try:
                # Get user input
                size = int(input("Enter size (bytes): "))
                tcp_conns = int(input("Enter TCP connections: "))
                udp_conns = int(input("Enter UDP connections: "))

                # Find server
                self._find_server()
                if not self.server:
                    continue

                # Start all transfers in parallel
                threads = []
                for i in range(tcp_conns):
                    t = threading.Thread(target=self._tcp_test, args=(i + 1, size))
                    threads.append(t)
                    t.start()

                for i in range(udp_conns):
                    t = threading.Thread(target=self._udp_test,
                                         args=(tcp_conns + i + 1, size))
                    threads.append(t)
                    t.start()

                # Wait for all transfers to complete
                for t in threads:
                    t.join()

                print("All transfers complete, listening to offer requests")

            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(1)

    def _find_server(self):
        try:
            data, addr = self.sock.recvfrom(1024)
            if len(data) >= 9:
                magic, msg_type, udp_port, tcp_port = struct.unpack('!IbHH', data[:9])
                if magic == self.MAGIC_COOKIE and msg_type == self.MSG_TYPE_OFFER:
                    self.server = (addr[0], udp_port, tcp_port)
                    print(f"Received offer from {addr[0]}")
        except:
            pass

    def _tcp_test(self, test_id, size):
        start_time = time.time()
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self.server[0], self.server[2]))
            sock.send(f"{size}\n".encode())

            received = 0
            while received < size:
                data = sock.recv(8192)
                if not data:
                    break
                received += len(data)

            duration = time.time() - start_time
            speed = (received * 8) / duration
            print(f"TCP transfer #{test_id} finished, total time: {duration:.2f} seconds, "
                  f"total speed: {speed:.1f} bits/second\n")

        except Exception as e:
            print(f"TCP test error: {e}")
        finally:
            sock.close()

    def _udp_test(self, test_id, size):
        start_time = time.time()
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(1.0)

            request = struct.pack('!IbQ', self.MAGIC_COOKIE, self.MSG_TYPE_REQUEST, size)
            sock.sendto(request, (self.server[0], self.server[1]))

            segments = set()
            last_recv = time.time()
            bytes_received = 0
            total_packets = 0

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
                            bytes_received += len(payload)
                            total_packets = total

                except socket.timeout:
                    if time.time() - last_recv > 1.0:  # No data for 1 second
                        break
                    continue

            duration = time.time() - start_time
            speed = (bytes_received * 8) / duration
            success_rate = (len(segments) / total_packets * 100) if total_packets else 0

            print(f"UDP transfer #{test_id} finished, total time: {duration:.2f} seconds, "
                  f"total speed: {speed:.1f} bits/second,\n "
                  f"percentage of packets received successfully: {success_rate:.1f}%")

        except Exception as e:
            print(f"UDP test error: {e}")
        finally:
            sock.close()


if __name__ == "__main__":
    client = SpeedTestClient()
    client.start()
