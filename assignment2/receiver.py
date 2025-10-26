import sys 
from packet import Packet
from socket import * 


def main():
    
    # ------ parse command line arguments --------
    if len(sys.argv) != 6:
        print("Usage: python receiver.py <emulator_host> <emulator_port> <receiver_port> <buffer size> <output_file>")
        sys.exit(1)
    
    emulator_host = sys.argv[1]
    try:
        emulator_port = int(sys.argv[2])
        receiver_port = int(sys.argv[3])
        buffer_size = int(sys.argv[4])
    except ValueError:
        print("Error: <emulator_port>, <receiver_port>, and <buffer size> must be integers.")
        sys.exit(1)

    output_file = sys.argv[5]

    
    # ------ initialize variables ------
    ACKED_packets = []  # indexes of packets that have been ACKed
    written_packets = []  # indexes of packets that have been written to file
    buffer_packets = []  # packets currently in buffer
    recv_base = 0  # base seqnum of the receiver

    # create socket 
    sock = socket(AF_INET, SOCK_DGRAM)
    sock.bind(('', receiver_port))



    # ------ loop to receive packets ------
    while True:
        message, clientAdress = sock.recvfrom(2048)
        received_packet = Packet(message)
        typ = received_packet.typ
        seqnum = received_packet.seqnum
        length = received_packet.length
        data = received_packet.data

        # EOT packet
        if typ == 2:
            eot_ack_packet = Packet(2, seqnum, 0, "")
            sock.sendto(eot_ack_packet.encode(), (emulator_host, emulator_port))
            with open("arrival.log", "a") as log:
                log.write("EOT\n")
            break
        
        # data packet
        if typ == 1:
            # out of window packet, drop packet without sending an ACK
            if seqnum >= recv_base + buffer_size:
                with open("arrival.log", "a") as log:
                    log.write(f"{seqnum} D\n")
                continue

            # already been ACKed
            if seqnum in ACKED_packets:
                ack_packet = Packet(0, seqnum, 0, "")
                sock.sendto(ack_packet.encode(), (emulator_host, emulator_port))
                with open("arrival.log", "a") as log:
                    log.write(f"{seqnum} D\n")
                continue
            
            # within window and not ACKed
            if seqnum >= recv_base and seqnum < recv_base + buffer_size:
                ACKED_packets.append(seqnum)
                ack_packet = Packet(0, seqnum, 0, "")
                sock.sendto(ack_packet.encode(), (emulator_host, emulator_port))
                buffer_packets.append(received_packet)
                buffer_packets.sort(key=lambda pkt: pkt.seqnum)

                with open("arrival.log", "a") as log:
                    log.write(f"{seqnum} B\n")

                # if there's a contiguous in-order sequence from recv_base, write to file
                while buffer_packets and buffer_packets[0].seqnum == recv_base:
                    pkt_to_write = buffer_packets.pop(0)
                    with open(output_file, 'a') as f:
                        f.write(pkt_to_write.data)
                    written_packets.append(recv_base)
                    recv_base += 1
                    
            
            else:
                print("Received unexpected packet: Type={}, Seqnum={}".format(typ, seqnum))

    # close the socket
    sock.close()
    sys.exit(0)


if __name__ == '__main__':
    main()