import socket
import struct
import threading
import time
from typing import Optional, Tuple
from colorama import Fore, Style, init

init(autoreset=True)


class SpeedTestClient:
    """
    A client class for performing network speed tests using TCP and UDP protocols.
    """

    MAGIC_COOKIE = 0xabcddcba
    MSG_TYPE_OFFER = 0x2
    MSG_TYPE_REQUEST = 0x3
    MSG_TYPE_PAYLOAD = 0x4

    def __init__(self):
        """
        Initializes the client, sets up sockets for communication, and prepares to listen for server offers.
        """

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(('', 13117))
        self.server = None
        self.active = True

        print(f"{Fore.CYAN}Client started, listening for offer requests...{Style.RESET_ALL}")

    def start(self):
        """
        Starts the main client loop, allowing the user to configure tests and execute them.
        """
        while self.active:
            try:
                size = self._get_positive_int(f"{Fore.GREEN}Enter size (bytes): {Style.RESET_ALL}")
                tcp_conns = self._get_positive_int(f"{Fore.GREEN}Enter TCP connections: {Style.RESET_ALL}")
                udp_conns = self._get_positive_int(f"{Fore.GREEN}Enter UDP connections: {Style.RESET_ALL}")

                self._find_server()
                if not self.server:
                    print(f"{Fore.RED}No valid server found. Retrying...{Style.RESET_ALL}")
                    continue

                threads = []
                for i in range(tcp_conns):
                    t = threading.Thread(target=self._tcp_test, args=(i + 1, size))
                    threads.append(t)
                    t.start()

                for i in range(udp_conns):
                    t = threading.Thread(target=self._udp_test, args=(tcp_conns + i + 1, size))
                    threads.append(t)
                    t.start()

                for t in threads:
                    t.join()

                print(f"{Fore.CYAN}All transfers complete, listening to offer requests{Style.RESET_ALL}")

            except KeyboardInterrupt:
                self.active = False
                print(f"{Fore.YELLOW}Client shutting down...{Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.RED}Unexpected error: {e}{Style.RESET_ALL}")
                time.sleep(1)

    def _get_positive_int(self, prompt: str) -> int:
        """
               Prompts the user to enter a positive integer.

               Args:
                   prompt (str): The prompt message to display to the user.

               Returns:
                   int: The positive integer entered by the user.
        """

        while True:
            try:
                value = int(input(prompt))
                if value <= 0:
                    raise ValueError("Value must be positive.")
                return value
            except ValueError as e:
                print(f"{Fore.RED}Invalid input: {e}{Style.RESET_ALL}")

    def _find_server(self):
        """
                Searches for a server broadcasting a valid offer.
        """
        try:
            data, addr = self.sock.recvfrom(1024)
            if len(data) >= 9:
                magic, msg_type, udp_port, tcp_port = struct.unpack('!IbHH', data[:9])
                if magic == self.MAGIC_COOKIE and msg_type == self.MSG_TYPE_OFFER:
                    self.server = (addr[0], udp_port, tcp_port)
                    print(f"{Fore.GREEN}Received valid offer from {addr[0]}{Style.RESET_ALL}")
                else:
                    print(f"{Fore.RED}Invalid offer packet received.{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}Error while receiving server offer: {e}{Style.RESET_ALL}")

    def _tcp_test(self, test_id, size):
        """
        Performs a TCP speed test with the server.

        Args:
            test_id (int): The ID of the test for logging purposes.
            size (int): The size of data to transfer in bytes.
        """
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
            print(f"{Fore.BLUE}TCP transfer #{test_id} finished: {received} bytes in {duration:.2f} seconds, "
                  f"speed: {speed:.1f} bits/second{Style.RESET_ALL}\n")

        except Exception as e:
            print(f"{Fore.RED}TCP test error (test #{test_id}): {e}{Style.RESET_ALL}")
        finally:
            sock.close()

    def _udp_test(self, test_id, size):
        """
               Performs a UDP speed test with the server.

               Args:
                   test_id (int): The ID of the test for logging purposes.
                   size (int): The size of data to transfer in bytes.
        """
        start_time = time.time()
        max_test_duration = 10.0
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(1)

            request = struct.pack('!IbQ', self.MAGIC_COOKIE, self.MSG_TYPE_REQUEST, size)
            sock.sendto(request, (self.server[0], self.server[1]))

            segments = set()
            bytes_received = 0
            total_packets = 0

            while time.time() - start_time < max_test_duration:
                try:
                    data, _ = sock.recvfrom(2048)
                    if len(data) >= 21:
                        magic, msg_type, total, seg = struct.unpack('!IbQQ', data[:21])
                        if (magic == self.MAGIC_COOKIE and msg_type == self.MSG_TYPE_PAYLOAD and seg not in segments):
                            payload = data[21:]
                            segments.add(seg)
                            bytes_received += len(payload)
                            total_packets = total
                except socket.timeout:
                    continue

            duration = time.time() - start_time
            speed = (bytes_received * 8) / duration if duration > 0 else 0
            success_rate = (len(segments) / total_packets * 100) if total_packets else 0

            print(f"{Fore.MAGENTA}UDP transfer #{test_id} finished: {bytes_received} bytes in {duration:.2f} seconds, "
                  f"speed: {speed:.1f} bits/second, success rate: {success_rate:.1f}%{Style.RESET_ALL}\n")

        except Exception as e:
            print(f"{Fore.RED}UDP test error (test #{test_id}): {e}{Style.RESET_ALL}")
        finally:
            sock.close()


if __name__ == "__main__":
    """
    Main entry point for the client. Initializes and starts the SpeedTestClient.
    """
    client = SpeedTestClient()
    client.start()
