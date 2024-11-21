import socket
import select
import time
import argparse

# Settings
RTO = 0.500  # Retransmission timeout
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
        return ser_repr.encode("utf-8")

    def __str__(self):
        return f"Seq: {self.seq}   ACK: {self.ack}   Len: {self.len}   Msg: {self.msg.strip()}"

    @staticmethod
    def deserialize(ser_bytes_msg):
        ser_msg = ser_bytes_msg.decode("utf-8")
        parts = ser_msg.split("|")
        if len(parts) >= 4:
            return Msg(int(parts[0].strip()), int(parts[1].strip()), "|".join(parts[3:]).strip())
        else:
            print("Error in deserializing into Msg object.")
            exit(-1)


# Helper functions
def init_socket():
    try:
        cs = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        print("[S]: Sender socket created")
        return cs
    except socket.error as err:
        print(f"Socket open error: {err}")
        exit()


def get_filedata(filename):
    print(f"[S] Transmitting file {filename}")
    with open(filename, "r") as f:
        filedata = f.read()
    return filedata


def chunk_data(filedata):
    messages = [filedata[i : i + CHUNK_SIZE] for i in range(0, len(filedata), CHUNK_SIZE)]
    messages = [str(len(filedata))] + messages
    content_len = sum(len(m) for m in messages)
    seq_to_msgindex = {}
    accumulated = INIT_SEQNO
    for i, msg in enumerate(messages):
        seq_to_msgindex[accumulated] = i
        accumulated += len(msg)
    return messages, content_len, seq_to_msgindex


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--port", type=int, help="Receiver port to connect to (default 50007)", default=50007
    )
    parser.add_argument(
        "--infile",
        type=str,
        help="Name of input file (default test-input.txt)",
        default="test-input.txt",
    )
    parser.add_argument("--winsize", type=int, help="Window size (default 4)", default=4)
    return parser.parse_args()


############################################
# Main reliable sending function
def send_reliable(cs, filedata, receiver_binding, win_size):
    messages, content_len, seq_to_msgindex = chunk_data(filedata)

    # Initialize variables
    window_list = []  # Tracks sequence numbers and data for current window
    unacked_packets = {}  # Tracks unacknowledged packets and their send times
    next_seq = INIT_SEQNO  # Next sequence number to send
    last_ack = INIT_SEQNO  # Tracks the cumulative ACK received
    final_ack = INIT_SEQNO + content_len  # Final sequence number expected

    # Helper function to send packets in the window
    def send_window():
        for seq, msg in window_list:
            if seq not in unacked_packets:
                m = Msg(seq, __ACK_UNUSED, msg)
                cs.sendto(m.serialize(), receiver_binding)
                print(f"Transmitted {m}")
                unacked_packets[seq] = time.time()

    # Helper function to retransmit unACKed packets
    def retransmit_window():
        current_time = time.time()
        for seq, msg in window_list:
            if current_time - unacked_packets[seq] >= RTO:
                m = Msg(seq, __ACK_UNUSED, msg)
                cs.sendto(m.serialize(), receiver_binding)
                print(f"Retransmitted {m}")
                unacked_packets[seq] = current_time

    # Populate initial window
    while len(window_list) < win_size and next_seq < final_ack:
        index = seq_to_msgindex[next_seq]
        msg = messages[index]
        window_list.append((next_seq, msg))
        next_seq += len(msg)

    send_window()  # Send initial window

    # Main loop
    while last_ack < final_ack:
        ready = select.select([cs], [], [], RTO)
        if ready[0]:  # ACK received
            data_from_receiver, _ = cs.recvfrom(1024)
            ack_msg = Msg.deserialize(data_from_receiver)
            ack_num = ack_msg.ack
            print(f"Received ACK: {ack_num}")

            # Identify the sequence corresponding to the ACK
            seq_acked = ack_num - CHUNK_SIZE

            # Remove acknowledged packets from window_list
            window_list = [(seq, msg) for seq, msg in window_list if seq != seq_acked]

            # Remove from unacked_packets
            if seq_acked in unacked_packets:
                del unacked_packets[seq_acked]

            # Slide the window forward
            last_ack = max(last_ack, ack_num)
            while len(window_list) < win_size and next_seq < final_ack:
                index = seq_to_msgindex[next_seq]
                msg = messages[index]
                window_list.append((next_seq, msg))
                next_seq += len(msg)

            send_window()  # Transmit new packets in the window
        else:
            # Timeout occurred, retransmit unacknowledged packets
            retransmit_window()

    print("[S] Sender finished all transmissions.")


if __name__ == "__main__":
    args = parse_args()
    filedata = get_filedata(args.infile)
    receiver_binding = ("localhost", args.port)
    cs = init_socket()
    send_reliable(cs, filedata, receiver_binding, args.winsize)
    cs.close()
