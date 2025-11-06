import socket
import argparse
import struct
import time

MTU_IN_BYTES = 1500
SOCKET_TIMEOUT_IN_SECONDS = 3
MAX_RETRIES_PER_TTL = 3
ICMP_ECHO_REPLY = 0
ICMP_TIME_EXCEEDED = 11
ICMP_DEST_UNREACH = 3
ICMP_DEST_UNREACH_PORT = 3


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--destination",
        dest="destination",
        default="abhinavbala.com",
        type=str,
        help="The destination you wish to trace.",
    )
    parser.add_argument(
        "--max_ttl",
        dest="max_ttl",
        default=64,
        type=int,
        help="The max ttl before terminating the trace",
    )
    parser.add_argument(
        "--port",
        dest="destination_port",
        default=32456,
        type=int,
        help="Ideally a port that is not used.",
    )

    parser.add_argument(
        "--packet_size",
        dest="packet_size",
        default=40,
        type=int,
        help="The size of the packet in bytes to send to the destination.",
    )

    args = parser.parse_args()

    # parse arguments
    destination = args.destination
    destination_port = args.destination_port
    max_ttl = args.max_ttl
    message = "x" * args.packet_size

    destination_ip = socket.gethostbyname(destination)
    print(
        f"Tracing route to {destination} with ip address {destination_ip} with packet size {args.packet_size}"
    )

    # setup socket
    # AF_INET -> socket will use ipv4
    # SOCK_DGRAM -> socket will send/receive connectionless, unreliable datagrams -> udp
    # SOCK_STREAM -> socket will send/receive connection-based, two-way, sequenced byte-streams -> tcp

    # traceroute sends udp segements. the connection-oriented nature of tcp is an unecessary overhead
    sending_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # configure the socket to reuse the same address
    # reasoning: when a program is done using a socket, the os usually places the port in a TIME_WAIT state
    # this is to let any replies get cleared before the port is ready to be used again
    # the os keeps it in this state typically for 2*MSL (maximum segement lifetime)
    # in our case, if we want to re-run our program, we can just skip this TIME_WAIT state
    # because we're assuming we were the ones who used the program before

    # SOL_SOCKET -> means we want to configure the options of the socket itself, not a specific protocol layer like IP/TCP
    # SO_REUSEADDR -> means we can skip TIME_WAIT state
    # aside: if the port is in use, this option will let you bind to it only if the existing socket is only listening
    # and also set the SO_REUSEADDR option to true
    sending_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # setup socket that will receive the ICMP packets
    # on macOS and linux, we need raw socket to give us ip layer access
    try:
        # SOCK_DGRAM would strip the headers
        receiving_sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
    except (OSError, PermissionError):
        print("Raw sockets require root privileges.")
        print("Please run with: sudo python3 traceroute.py")
        return

    # set timeout so recvfrom doesn't block indefinitely
    receiving_sock.settimeout(SOCKET_TIMEOUT_IN_SECONDS)

    curr_ip = None
    curr_ttl = 1

    while curr_ip != destination_ip:
        if curr_ttl >= max_ttl:
            print("Reached max ttl without reaching the destination.")
            return

        # set the new ttl for the sending socket
        sending_sock.setsockopt(socket.IPPROTO_IP, socket.IP_TTL, curr_ttl)

        # try up to MAX_RETRIES_PER_TTL times to get a response
        # store timings and source_ip for all attempts
        timings = []
        source_ip = None
        destination_reached = False
        response_received = False

        for _ in range(MAX_RETRIES_PER_TTL):
            start_time = time.time()
            try:
                sending_sock.sendto(bytes(message, "utf-8"), (destination_ip, destination_port))

                # recvfrom returns a (data, ) object, we don't care about the data or the port
                packet, _ = receiving_sock.recvfrom(MTU_IN_BYTES)

                # calculate elapsed time in milliseconds
                end_time = time.time()
                elapsed_ms = (end_time - start_time) * 1000
                timings.append(f"{elapsed_ms:.1f} ms")

                # the ip header is the first 20 bytes of the packet
                ip_header = packet[0:20]
                # the source ip is at the 12th byte and is 4 bytes long
                source_ip = socket.inet_ntoa(ip_header[12:16])

                # we need the icmp type and code. This wil be right after the ip_header
                # the first 8 bits are the type and the next 8 bits are the code
                icmp_type = struct.unpack("B", packet[20:21])[0]
                icmp_code = struct.unpack("B", packet[21:22])[0]

                # only process valid ICMP responses (time exceeded or destination unreachable)
                if icmp_type == ICMP_TIME_EXCEEDED or (
                    icmp_type == ICMP_DEST_UNREACH and icmp_code == ICMP_DEST_UNREACH_PORT
                ):
                    # valid response
                    timings.append(f"{elapsed_ms:.1f} ms")
                    curr_ip = source_ip
                    response_received = True

                    # we've reached our destination
                    if icmp_type == ICMP_DEST_UNREACH:
                        destination_reached = True
                    # else: packet timed out en-route
                else:
                    # unexpected ICMP type, just ignore
                    # this could be other ICMP messages on the network
                    continue

            except socket.timeout:
                # timeout - mark with * and continue to next attempt
                timings.append("*")
                # continue to next attempt

        # print results for this TTL
        if response_received:
            timing_str = "  ".join(timings)
            if destination_reached:
                print(f"TTL ({curr_ttl}): {timing_str}  {source_ip} (destination reached!)")
            else:
                print(f"TTL ({curr_ttl}): {timing_str}  {source_ip}")
        else:
            # no responses received for any of the 3 attempts
            timing_str = "  ".join(timings) if timings else "*  *  *"
            print(f"TTL ({curr_ttl}): {timing_str}  (no response)")

        curr_ttl += 1


if __name__ == "__main__":
    main()
