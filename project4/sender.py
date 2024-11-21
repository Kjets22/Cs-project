import time
import socket
import select
import argparse
from functools import reduce

# Settings
# Retransmission timeout in seconds
RTO = 0.500
# Number of application bytes in one packet
CHUNK_SIZE = 8
# Initial sequence number for sender transmissions
INIT_SEQNO = 5
# Dummy ACK number for sender's packets
__ACK_UNUSED = 2345367

# Message class
class Msg:
    def __init__(self, seq, ack, msg):
        self.seq = int(seq)
        self.ack = int(ack)
        self.msg = str(msg)
        self.len = len(self.msg)

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

### Helper methods.
#### Initialize a UDP socket
def init_socket(receiver_binding):
    try:
        cs = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        print("[S]: Sender socket created")
    except socket.error as err:
        print(f'socket open error: {err} \n')
        exit()
    return cs

#### Read the entire file data
def get_filedata(filename):
    print(f"[S] Transmitting file {filename}")
    with open(filename, 'r') as f:
        filedata = f.read()
    return filedata

#### Chunk the file data into fixed-size messages
def chunk_data(filedata):
    global CHUNK_SIZE
    global INIT_SEQNO
    messages = [filedata[i:i + CHUNK_SIZE]
                for i in range(0, len(filedata),
                               CHUNK_SIZE)]
    messages = [str(len(filedata))] + messages  # First message contains total length
    content_len = reduce(lambda x, y: x + len(y),
                         messages, 0)
    seq_to_msgindex = {}
    accumulated = INIT_SEQNO
    for i in range(len(messages)):
        seq_to_msgindex[accumulated] = i
        accumulated += len(messages[i])
    return messages, content_len, seq_to_msgindex

#### Parse command line arguments
def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port',
                        type=int,
                        help="Receiver port to connect to (default 50007)",
                        default=50007)
    parser.add_argument('--infile',
                        type=str,
                        help="Name of input file (default test-input.txt)",
                        default="test-input.txt")
    parser.add_argument('--winsize',
                        type=int,
                        help="Window size to use in pipelined reliability",
                        default=20)
    args = parser.parse_args()
    return vars(args)

############################################
# Main reliable sending loop
def send_reliable(cs, filedata, receiver_binding, win_size):
    global RTO
    global INIT_SEQNO
    global __ACK_UNUSED
    messages, content_len, seq_to_msgindex = chunk_data(filedata)

    # Initialize variables as per the instructions
    win_left_edge = INIT_SEQNO
    win_right_edge = min(win_left_edge + win_size,
                         INIT_SEQNO + content_len)
    final_ack = INIT_SEQNO + content_len
    last_acked = INIT_SEQNO
    first_to_tx = win_left_edge

    # Dictionary to keep track of sent but unACKed packets
    sent_packets = {}

    # Helper function to transmit the entire window from a given sequence number
    def transmit_entire_window_from(left_edge):
        latest_tx = left_edge
        while latest_tx < win_right_edge:
            if latest_tx in seq_to_msgindex:
                index = seq_to_msgindex[latest_tx]
                msg = messages[index]
                m = Msg(latest_tx, __ACK_UNUSED, msg)
                cs.sendto(m.serialize(), receiver_binding)
                print(f"Transmitted {m}")
                sent_packets[latest_tx] = m
                latest_tx += len(msg)
            else:
                break
        return latest_tx

    # Helper function to transmit one packet (used for retransmissions)
    def transmit_one():
        # Retransmit the earliest unACKed packet
        seqnum = win_left_edge
        if seqnum in sent_packets:
            m = sent_packets[seqnum]
            cs.sendto(m.serialize(), receiver_binding)
            print(f"Retransmitted {m}")
        else:
            # Should not happen, but in case, send the packet
            if seqnum in seq_to_msgindex:
                index = seq_to_msgindex[seqnum]
                msg = messages[index]
                m = Msg(seqnum, __ACK_UNUSED, msg)
                cs.sendto(m.serialize(), receiver_binding)
                print(f"Retransmitted {m}")
                sent_packets[seqnum] = m

    # Step 4.1: Transmit initial window
    first_to_tx = win_left_edge
    first_to_tx = transmit_entire_window_from(first_to_tx)
    # Start timer for the earliest unACKed packet
    timer_start = time.time()

    while last_acked < final_ack:
        # Calculate remaining time for the timeout
        elapsed = time.time() - timer_start
        timeout = RTO - elapsed
        if timeout <= 0:
            timeout = 0

        # Wait for ACK with timeout
        ready = select.select([cs], [], [], timeout)
        if ready[0]:
            # Receive ACK
            data_from_receiver, _ = cs.recvfrom(1024)
            ack_msg = Msg.deserialize(data_from_receiver)
            print(f"Received {ack_msg}")
            ack_num = ack_msg.ack

            if ack_num > last_acked:
                # Step 4.3: ACK acknowledges fresh data
                # Slide window forward
                last_acked = ack_num
                win_left_edge = last_acked
                win_right_edge = min(win_left_edge + win_size,
                                     INIT_SEQNO + content_len)
                # Remove acknowledged packets from sent_packets
                keys_to_remove = [seq for seq in sent_packets if seq < ack_num]
                for seq in keys_to_remove:
                    del sent_packets[seq]
                # Step 4.4: Transmit new data if any
                if first_to_tx < win_right_edge:
                    first_to_tx = transmit_entire_window_from(first_to_tx)
                # Restart timer for the earliest unACKed packet
                if win_left_edge in sent_packets:
                    timer_start = time.time()
                else:
                    # No unACKed packets, timer not needed
                    timer_start = None
            else:
                # Duplicate or old ACK, ignore
                print("[S] Duplicate or old ACK received.")
        else:
            # Step 4.6: Timeout occurred, retransmit one packet
            print("[S] Timeout occurred. Retransmitting one packet.")
            transmit_one()
            # Restart timer after retransmission
            timer_start = time.time()

    print("[S] Sender finished all transmissions.")

if __name__ == "__main__":
    args = parse_args()
    filedata = get_filedata(args['infile'])
    receiver_binding = ('localhost', args['port'])
    cs = init_socket(receiver_binding)
    send_reliable(cs, filedata, receiver_binding,
                  args['winsize'])
    cs.close()
