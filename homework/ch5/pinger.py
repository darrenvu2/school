from socket import *
import os
import sys
import struct
import time
import select
import binascii

ICMP_ECHO_REQUEST = 8

# ICMP error type/code descriptions
ICMP_ERRORS = {
    (3, 0): "Destination Network Unreachable",
    (3, 1): "Destination Host Unreachable",
    (3, 2): "Destination Protocol Unreachable",
    (3, 3): "Destination Port Unreachable",
    (3, 4): "Fragmentation Required but DF Bit Set",
    (3, 5): "Source Route Failed",
    (3, 6): "Destination Network Unknown",
    (3, 7): "Destination Host Unknown",
    (3, 9): "Communication with Destination Network Administratively Prohibited",
    (3, 10): "Communication with Destination Host Administratively Prohibited",
    (3, 11): "Destination Network Unreachable for ToS",
    (3, 12): "Destination Host Unreachable for ToS",
    (3, 13): "Communication Administratively Prohibited",
    (11, 0): "TTL Expired in Transit",
    (11, 1): "Fragment Reassembly Time Exceeded",
}


def checksum(string):
    csum = 0
    countTo = (len(string) // 2) * 2
    count = 0
    while count < countTo:
        thisVal = ord(string[count + 1]) * 256 + ord(string[count])
        csum = csum + thisVal
        csum = csum & 0xffffffff
        count = count + 2
    if countTo < len(string):
        csum = csum + ord(string[len(string) - 1])
        csum = csum & 0xffffffff
    csum = (csum >> 16) + (csum & 0xffff)
    csum = csum + (csum >> 16)
    answer = ~csum
    answer = answer & 0xffff
    answer = answer >> 8 | (answer << 8 & 0xff00)
    return answer


def receiveOnePing(mySocket, ID, timeout, destAddr):
    timeLeft = timeout
    while 1:
        startedSelect = time.time()
        whatReady = select.select([mySocket], [], [], timeLeft)
        howLongInSelect = (time.time() - startedSelect)
        if whatReady[0] == []:  # Timeout
            return None, "Request timed out."

        timeReceived = time.time()
        recPacket, addr = mySocket.recvfrom(1024)

        # Fill in start
        # Fetch the ICMP header from the IP packet
        # IP header is 20 bytes; ICMP header starts at byte 20
        icmpHeader = recPacket[20:28]

        # Unpack the ICMP header: type (B), code (B), checksum (H), packetID (H), sequence (H)
        icmpType, icmpCode, icmpChecksum, packetID, sequence = struct.unpack("bbHHh", icmpHeader)

        # Check for ICMP error messages (type != 0 means it's not an echo reply)
        if icmpType != 0:
            error_key = (icmpType, icmpCode)
            error_msg = ICMP_ERRORS.get(error_key, f"ICMP Error (type={icmpType}, code={icmpCode})")
            return None, error_msg

        # Verify this reply is for our ping (match process ID)
        if packetID == ID:
            # Extract the time from the data payload (after 8-byte ICMP header)
            dataField = recPacket[28:]
            timeSent = struct.unpack("d", dataField[:8])[0]
            rtt = (timeReceived - timeSent) * 1000  # Convert to milliseconds

            # Extract TTL from IP header (byte 8 of the IP header)
            ttl = struct.unpack("B", recPacket[8:9])[0]

            return rtt, f"Reply from {addr[0]}: TTL={ttl} time={rtt:.2f} ms"
        # Fill in end

        timeLeft = timeLeft - howLongInSelect
        if timeLeft <= 0:
            return None, "Request timed out."


def sendOnePing(mySocket, destAddr, ID):
    # Header is type (8), code (8), checksum (16), id (16), sequence (16)
    myChecksum = 0
    # Make a dummy header with a 0 checksum
    header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, myChecksum, ID, 1)
    data = struct.pack("d", time.time())
    # Calculate the checksum on the data and the dummy header.
    myChecksum = checksum(str(header + data))
    # Get the right checksum, and put in the header
    if sys.platform == 'darwin':
        myChecksum = htons(myChecksum) & 0xffff
    else:
        myChecksum = htons(myChecksum)
    header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, myChecksum, ID, 1)
    packet = header + data
    mySocket.sendto(packet, (destAddr, 1))


def doOnePing(destAddr, timeout):
    icmp = getprotobyname("icmp")
    mySocket = socket(AF_INET, SOCK_RAW, icmp)
    myID = os.getpid() & 0xFFFF
    sendOnePing(mySocket, destAddr, myID)
    rtt, message = receiveOnePing(mySocket, myID, timeout, destAddr)
    mySocket.close()
    return rtt, message


def ping(host, timeout=1, count=10):
    """
    Ping a host and display statistics.
    
    Args:
        host: hostname or IP address to ping
        timeout: seconds to wait for reply (default: 1)
        count: number of ping requests to send (0 = infinite)
    """
    dest = gethostbyname(host)
    print(f"Pinging {dest} ({host}) using Python:")
    print("")

    rtts = []
    sent = 0
    received = 0
    seq = 0

    try:
        while True:
            seq += 1
            sent += 1
            rtt, message = doOnePing(dest, timeout)
            print(f"  {seq}: {message}")

            if rtt is not None:
                received += 1
                rtts.append(rtt)

            time.sleep(1)

            if count > 0 and seq >= count:
                break

    except KeyboardInterrupt:
        print("\n--- Ping interrupted ---")

    # Print statistics
    lost = sent - received
    loss_pct = (lost / sent * 100) if sent > 0 else 0

    print(f"\n--- {host} ping statistics ---")
    print(f"  {sent} packets transmitted, {received} received, {loss_pct:.0f}% packet loss")

    if rtts:
        print(f"  RTT min/avg/max = {min(rtts):.2f}/{sum(rtts)/len(rtts):.2f}/{max(rtts):.2f} ms")
    else:
        print("  No replies received.")


if __name__ == "__main__":
    # Default: ping google.com 10 times
    # Usage: python icmp_pinger.py [host] [count]
    host = sys.argv[1] if len(sys.argv) > 1 else "google.com"
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    ping(host, count=count)