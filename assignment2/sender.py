import sys
import time
from packet import Packet
from socket import *



def main():

    # ----- parse command line arguments --------
    if len(sys.argv) != 7:
        print("Usage: python sender.py <emulator_host> <emulator_port> <sender_port> <timeout(ms)> <N> <input_file>")
        sys.exit(1)
    
    emulator_host = sys.argv[1]
    try:
        emulator_port = int(sys.argv[2])
        sender_port = int(sys.argv[3])
        timeout_period = int(sys.argv[4])
        maximum_windowSize = int(sys.argv[5])
    except ValueError:
        print("Error: <emulator_port>, <sender_port>, <timeout(ms)>, and <N> must be integers.")
        sys.exit(1)
 
    input_file_path = sys.argv[6]

    # sanity checks
    if timeout_period <= 0:
        print("Error: timeout must be a positive integer (milliseconds).")
        sys.exit(1)
    if maximum_windowSize < 5:
        print("Error: maximum_windowSize must be at least 5.")
        sys.exit(1)

    
    # ------ initialize variables ------
    windowSize = 5     # initial window size
    ACKED_packets = []  # indexes of packets that have been ACKed
    UNACKED_packets = []  # indexes of packets that have not been ACKed
    current_window = []
    packages = [] 

    # ------ make packages ------
    # read input files
    try:
        with open(input_file_path, 'rb') as input_file:
            file_data_bytes = input_file.read()
    except FileNotFoundError:
        print(f"Error: Input file '{input_file_path}' not found.")
        sys.exit(1)

    try:
        file_data_bytes.decode('ascii')
    except UnicodeDecodeError as e:
        print(f"Error: Input file must be ASCII text. {e}")
        sys.exit(1)

    # divide into chunks of maximum 500 bytes
    n = len(file_data_bytes)
    seq = 0
    for i in range(0, n, 500):
        chunk_bytes = file_data_bytes[i:i+500]     
        chunk = chunk_bytes.decode('ascii')        
        # create packet here and add to UNACKED_packets
        packet = Packet(1, seq, len(chunk), chunk)  # type=1 for data packet
        packages.append(packet)
        UNACKED_packets.append(seq)
        seq += 1

    # create socket to send packets to emulator
    sock = socket(AF_INET, SOCK_DGRAM)
    sock.bind(('', sender_port))
    sock.settimeout(timeout_period / 1000.0)



    


    # ------ loop to send packets ------
    while len(UNACKED_packets) > 0 or len(current_window) > 0:

        # add packets into current window
        while len(current_window) < windowSize and len(UNACKED_packets) > 0:
            pkt_index = UNACKED_packets.pop(0)
            current_window.append(pkt_index)
        
        # record current time as start time
        start_time  = time.time()

        # send packets in current window
        for pkt_index in current_window:
            packet = packages[pkt_index]
            encoded_packet = packet.encode()
            # send encoded_packet to emulator
            sock.sendto(encoded_packet, (emulator_host, emulator_port))
            #print(f"Sending packet: Seqnum={packet.seqnum}, Length={packet.length}")
        
            
        # wait for ACKs until timeout period
        while True:
            try:
                message, clientAdress = sock.recvfrom(2048)
            except timeout: 
                break  
            received_packet = Packet(message)  

            typ = received_packet.typ 
            seqnum = received_packet.seqnum

            if typ == 0:  # ACK packet
                if seqnum not in ACKED_packets:
                    ACKED_packets.append(seqnum)
                if seqnum in current_window:
                    current_window.remove(seqnum)
                # if it exists in UNACKED_packets, remove it
                if seqnum in UNACKED_packets:
                    UNACKED_packets.remove(seqnum)
                print(f"Received ACK for packet: {seqnum}")

            else:
                print(f"Received unknown packet type: {typ}")
        

        # deal with timeout & cwnd adjustment
        # all packets are ACKed 
        if len(current_window) == 0:
            windowSize = min(windowSize + 1, maximum_windowSize)
        # some packets are not ACKed
        else:
            windowSize = 5 
            while len(current_window) > windowSize:
                # move the ending packets from current window to UNACKED_packets
                pkt_index = current_window.pop()
                UNACKED_packets.insert(0, pkt_index)
    

    # ------ send EOT packet ------
    eot_packet = Packet(2, 0, 0, "")
    encoded_eot_packet = eot_packet.encode()
    sock.sendto(encoded_eot_packet, (emulator_host, emulator_port))

    # ------ wait for EOT ACK ------
    while True:
        message, clientAdress = sock.recvfrom(2048)
        received_packet = Packet(message)
        typ = received_packet.typ
        seqnum = received_packet.seqnum
        

        if typ == 2:  # EOT ACK packet
            #print("Received EOT ACK from receiver. Terminating sender.")
            break
        else:
            print(f"Received unknown packet type while waiting for EOT ACK: {typ}")

    sock.close()
    sys.exit(0)





if __name__ == '__main__':
    main()