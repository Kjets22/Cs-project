import socket
import select
import argparse
import time

# Settings
RTO = 0.500  # Retransmission timeout in seconds
CHUNK_SIZE = 8  # Number of application bytes in one packet
INIT_SEQNO = 5  # Initial sequence number for sender transmissions
__ACK_UNUSED = 2345367  # Dummy ACK number for sender's packets

# Message class
class Msg:
    def __init__(self, seq, ack, msg):
        self.seq = int(seq)  # Sequence number
        self.ack = int(ack)  # Acknowledgment number
        self.msg = str(msg)  # Message content
        self.len = len(self.msg)  # Length of the message

    def serialize(self):
        ser_repr = f"{self.seq} | {self.ack} | {self.len} | {self.msg}"
        return ser_repr.encode('utf-8')

    def __str__(self):
        return f"Seq: {self.seq}   ACK: {self.ack}   Len: {self.len}   Msg: {self.msg.strip()}"

    @staticmethod
    def deserialize(ser_bytes_msg):
        ser_msg = ser_bytes_msg.decode('utf-8')
        parts = ser_msg.split('|')
        if len(parts) >= 4:
            return Msg(int(parts[0].strip()),
                       int(parts[1].strip()),
                       '|'.join(parts[3:]).strip())
        else:
            print("Error in deserializing into Msg object.")
            exit(-1)

# Helper methods
def init_socket(receiver_binding):
    try:
        cs = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        print("[S]: Sender socket created")
    except socket.error as err:
        print(f"Socket open error: {err} \n")
        exit()
    return cs

def get_filedata(filename):
    print(f"[S] Transmitting file {filename}")
    with open(filename, 'r') as f:
        filedata = f.read()
    return filedata

def chunk_data(filedata):
    messages = [filedata[i:i + CHUNK_SIZE] for i in range(0, len(filedata), CHUNK_SIZE)]
    messages = [str(len(filedata))] + messages  # First message contains total length
    content_len = sum(len(m) for m in messages)
    seq_to_msgindex = {}
    accumulated = INIT_SEQNO
    for i, msg in enumerate(messages):
        seq_to_msgindex[accumulated] = i
        accumulated += len(msg)
    return messages, content_len, seq_to_msgindex

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, help="Receiver port to connect to (default 50007)", default=50007)
    parser.add_argument('--infile', type=str, help="Name of input file (default test-input.txt)", default="test-input.txt")
    parser.add_argument('--winsize', type=int, help="Window size to use in pipelined reliability", default=20)
    args = parser.parse_args()
    return vars(args)

############################################
# Main reliable sending loop
def send_reliable(cs, filedata, receiver_binding, win_size):
    messages, content_len, seq_to_msgindex = chunk_data(filedata)

    # Initialize variables
    base = INIT_SEQNO  # Left edge of the window
    next_seqnum = INIT_SEQNO  # Next sequence number to send
    final_seqnum = INIT_SEQNO + content_len  # Sequence number after the last byte
    unacked_packets = {}  # seq_num: (Msg, send_time)
    timer = None  # Timer for the earliest unACKed packet

    # Helper function to send a packet
    def send_packet(seqnum):
        index = seq_to_msgindex[seqnum]
        msg = messages[index]
        m = Msg(seqnum, __ACK_UNUSED, msg)
        cs.sendto(m.serialize(), receiver_binding)
        print(f"Transmitted {m}")
        unacked_packets[seqnum] = (m, time.time())
        return m

    # Send initial window of packets
    while next_seqnum < base + win_size and next_seqnum < final_seqnum:
        send_packet(next_seqnum)
        if base == next_seqnum:
            timer = time.time()  # Start timer for the earliest unACKed packet
        next_seqnum += len(messages[seq_to_msgindex[next_seqnum]])

    while base < final_seqnum:
        # Calculate remaining time for timeout
        if timer:
            elapsed = time.time() - timer
            timeout = max(RTO - elapsed, 0)
        else:
            timeout = None  # No unACKed packets

        # Wait for ACK or timeout
        ready = select.select([cs], [], [], timeout)
        if ready[0]:
            # Receive ACK
            data_from_receiver, _ = cs.recvfrom(1024)
            ack_msg = Msg.deserialize(data_from_receiver)
            ack_num = ack_msg.ack
            print(f"Received ACK for sequence number: {ack_num}")

            if ack_num >= base:
                # Mark packets as acknowledged
                seq_nums_to_remove = []
                for seq in unacked_packets:
                    if seq < ack_num:
                        seq_nums_to_remove.append(seq)
                for seq in seq_nums_to_remove:
                    del unacked_packets[seq]
                # Slide window forward
                while base not in unacked_packets and base < final_seqnum:
                    index = seq_to_msgindex[base]
                    base += len(messages[index])
                # Transmit new packets if window allows
                while next_seqnum < base + win_size and next_seqnum < final_seqnum:
                    send_packet(next_seqnum)
                    next_seqnum += len(messages[seq_to_msgindex[next_seqnum]])
                # Restart timer if there are unACKed packets
                if base in unacked_packets:
                    timer = time.time()
                else:
                    timer = None
            else:
                # Duplicate or old ACK, ignore
                print("[S] Duplicate or old ACK received.")
        else:
            # Timeout occurred
            print("[S] Timeout occurred. Retransmitting the earliest unACKed packet.")
            if base in unacked_packets:
                m, _ = unacked_packets[base]
                cs.sendto(m.serialize(), receiver_binding)
                print(f"Retransmitted {m}")
                unacked_packets[base] = (m, time.time())  # Update send time
                timer = time.time()  # Restart timer
            else:
                # No unACKed packets, timer not needed
                timer = None

    print("[S] Sender finished all transmissions.")

if __name__ == "__main__":
    args = parse_args()
    filedata = get_filedata(args['infile'])
    receiver_binding = ('localhost', args['port'])
    cs = init_socket(receiver_binding)
    send_reliable(cs, filedata, receiver_binding, args['winsize'])
    cs.close()
