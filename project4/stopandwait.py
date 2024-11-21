
import threading
import time
import random
import socket
import select
import argparse
from functools import reduce

# Settings
# Retransmission timeout
RTO = 0.500
# Number of application bytes in one packet
CHUNK_SIZE = 8
# Initial sequence number for sender transmissions
INIT_SEQNO = 5
# dummy ACK number for sender's packets
__ACK_UNUSED = 2345367

# Message class: we use this class to structure our protocol
# message. The fields in our protocol are:
# seq no: the starting sequence number of application bytes
# on this packet
# ack no: the cumulative ACK number of application bytes
# being acknowledged in this ACK
# len: the number of application bytes being transmitted on
# this packet
# msg: the actual application payload on this packet
# The methods `serialize` and `deserialize` allow the
# conversion of a protocol object to bytes transmissible
# through a sendto() system call and the bytes from a
# recvfrom() system call into a protocol structure.
class Msg:
    def __init__(self, seq, ack, msg):
        self.seq = int(seq)
        self.ack = int(ack)
        self.msg = str(msg)
        self.len = len(self.msg)

    def serialize(self):
        ser_repr = (str(self.seq) + ' | ' + str(self.ack) + ' | ' +
                    str(self.len) + ' | ' + self.msg)
        return ser_repr.encode('utf-8')

    def __str__(self):
        repr  = "Seq: " + str(self.seq) + '   '
        repr += "ACK: " + str(self.ack) + '   '
        repr += "Len: " + str(self.len) + '   '
        repr += "Msg: " + self.msg.strip()
        return repr

    @staticmethod
    def deserialize(ser_bytes_msg):
        ser_msg = ser_bytes_msg.decode('utf-8')
        parts = ser_msg.split('|')
        if len(parts) >= 4:
            return Msg(int(parts[0]),
                       int(parts[1]),
                       '|'.join(parts[3:])[1:])
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
        print('socket open error: {} \n'.format(err))
        exit()
    return cs

#### Slurp a file into a single string.
#### Warning: do not use on very large files
def get_filedata(filename):
    print ("[S] Transmitting file {}".format(filename))
    f = open(filename, 'r')
    filedata = f.read()
    f.close()
    return filedata

#### Chunk a large string into fixed size chunks.
#### The first chunk is a string with the number of
#### following chunks.
#### `seq_to_msgindex` tracks the index of the packet
#### that will contain a given sequence number as its
#### starting sequence number.
def chunk_data(filedata):
    global CHUNK_SIZE
    global INIT_SEQNO
    messages = [filedata[i:i + CHUNK_SIZE]
                for i in range(0, len(filedata),
                               CHUNK_SIZE)]
    messages = [str(len(filedata))] + messages
    content_len = reduce(lambda x, y: x + len(y),
                         messages, 0)
    seq_to_msgindex = {}
    accumulated = INIT_SEQNO
    for i in range(0, len(messages)):
        seq_to_msgindex[accumulated] = i
        accumulated += len(messages[i])
    return messages, content_len, seq_to_msgindex

#### Parse command line arguments
def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port',
                        type = int,
                        help = "receiver port to connect to (default 50007)",
                        default = 50007)
    parser.add_argument('--infile',
                        type = str,
                        help = "name of input file (default test-input.txt)",
                        default = "test-input.txt")
    parser.add_argument('--winsize',
                        type = int,
                        help = "Window size to use in pipelined reliability",
                        default = 20)
    args = parser.parse_args()
    return vars(args)

############################################
# Main reliable sending loop
def send_reliable(cs, filedata, receiver_binding, win_size):
    global RTO
    global INIT_SEQNO
    global __ACK_UNUSED
    messages, content_len, seq_to_msgindex = chunk_data(filedata)

    win_left_edge = INIT_SEQNO
    final_seqno = INIT_SEQNO + content_len

    # TODO: This is where you will make your changes. You
    # will not need to change any other parts of this file.

    # Implement Stop-and-Wait reliability
    while win_left_edge < final_seqno:
        # Transmit one packet
        index = seq_to_msgindex[win_left_edge]
        msg = messages[index]
        m = Msg(win_left_edge, __ACK_UNUSED, msg)
        cs.sendto(m.serialize(), receiver_binding)
        print("Transmitted {}".format(str(m)))

        # Wait for ACK with timeout
        ready = select.select([cs], [], [], RTO)
        if ready[0]:
            try:
                data_from_receiver, _ = cs.recvfrom(1024)
                ack_msg = Msg.deserialize(data_from_receiver)
                print("Received {}".format(str(ack_msg)))
                ack_num = ack_msg.ack
                if ack_num == win_left_edge + len(msg):
                    # Correct ACK received, move to next packet
                    win_left_edge = ack_num
                else:
                    # Incorrect ACK, retransmit
                    print("[S] Incorrect ACK received. Retransmitting.")
            except Exception as e:
                print("[S] Error receiving ACK: {}".format(e))
        else:
            # Timeout occurred, retransmit
            print("[S] Timeout occurred. Retransmitting.")
    print("[S] Sender finished all transmissions.")

if __name__ == "__main__":
    args = parse_args()
    filedata = get_filedata(args['infile'])
    receiver_binding = ('localhost', args['port'])
    cs = init_socket(receiver_binding)
    send_reliable(cs, filedata, receiver_binding,
                  args['winsize'])
    cs.close()
