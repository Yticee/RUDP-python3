import sys
import getopt
import time

import Checksum
import BasicSender

'''
This is a skeleton sender class. Create a fantastic transport protocol here.
'''
class Sender(BasicSender.BasicSender):
    def __init__(self, dest, port, filename, debug=False, sackMode=False):
        super(Sender, self).__init__(dest, port, filename, debug)
        self.sackMode = sackMode
        self.timeout = 0.5   
        self.base = 0
        self.szWin = 5
        self.ack = 0
        self.seqno = 0
        self.packets = []
        self.sacks = []   

    def make_all_packets(self):
        seqno = 0
        msg = self.infile.read(500)
        msg_type = None
        while not msg_type == 'end':
            next_msg = self.infile.read(500)

            msg_type = 'data'
            if seqno == 0: 
                msg_type = 'start'
            elif next_msg == "": 
                msg_type = 'end'

            packet = self.make_packet(msg_type,seqno,msg)
            self.packets.append(packet)

            msg = next_msg
            seqno += 1

        self.infile.close()
        self.timers = [0 for i in range(len(self.packets))]
        
        
        
    # Main sending loop.
    def start(self):
        self.make_all_packets()
        
        while self.ack < len(self.packets):
            cnt = 0
            while self.seqno < self.base + self.szWin and self.seqno < len(self.packets):
            # while cnt < self.szWin and self.seqno < len(self.packets):    
                if not self.sackMode or (self.sackMode and self.seqno not in self.sacks):
                    self.timers[self.seqno] = time.time()
                    self.send(self.packets[self.seqno])
                    cnt += 1
                    if self.debug:
                        print("sent: %s, timers: %s" % self.packets[self.seqno], self.timers[self.seqno])
                self.seqno += 1
            
            for seqno in range(self.base, self.seqno):
                now = time.time()
                if now - self.timers[seqno] >= self.timeout:
                    self.handle_timeout(seqno)
                    break
            
            # for i in range(0, cnt):    
                resp = self.receive(self.timeout)
                if resp != None:
                    resp = resp.decode()
                    msg_type, ack_seqno, data, checksum = self.split_packet(resp)
                    if not Checksum.validate_checksum(resp):
                        continue
                    if msg_type == 'ack':
                        if int(ack_seqno) > self.base:
                            self.handle_new_ack(int(ack_seqno))
                        else:
                            self.handle_dup_ack(int(ack_seqno))
                    elif msg_type == 'sack':
                        ack_seqno = ack_seqno.split(';')
                        sacks = [ack_seqno[i] for i in range(1, len(ack_seqno))]
                        ack_seqno = ack_seqno[0] # cum_ack
                        if len(sacks) > 0:
                            if int(ack_seqno) > self.base:
                                self.handle_new_ack(int(ack_seqno))
                            else:
                                self.handle_dup_ack(int(ack_seqno))
                            for i in sacks:
                                if i not in self.sacks:
                                    self.sacks.append(i)
  
    

    def handle_timeout(self, seqno):
        self.seqno = seqno

    def handle_new_ack(self, ack):
        self.ack = max(self.ack, ack)
        if self.debug:
            print("update base from {} to {}".format(self.base, self.ack))
        self.base = self.ack

    def handle_dup_ack(self, ack):
        pass

    def log(self, msg):
        if self.debug:
            print(msg)


'''
This will be run if you run this script from the command line. You should not
change any of this; the grader may rely on the behavior here to test your
submission.
'''
if __name__ == "__main__":
    def usage():
        print("RUDP Sender")
        print("-f FILE | --file=FILE The file to transfer; if empty reads from STDIN")
        print("-p PORT | --port=PORT The destination port, defaults to 33122")
        print("-a ADDRESS | --address=ADDRESS The receiver address or hostname, defaults to localhost")
        print("-d | --debug Print debug messages")
        print("-h | --help Print this usage message")
        print("-k | --sack Enable selective acknowledgement mode")

    try:
        opts, args = getopt.getopt(sys.argv[1:],
                               "f:p:a:dk", ["file=", "port=", "address=", "debug=", "sack="])
    except:
        usage()
        exit()

    port = 33122
    dest = "localhost"
    filename = None
    debug = False
    sackMode = False

    for o,a in opts:
        if o in ("-f", "--file="):
            filename = a
        elif o in ("-p", "--port="):
            port = int(a)
        elif o in ("-a", "--address="):
            dest = a
        elif o in ("-d", "--debug="):
            debug = True
        elif o in ("-k", "--sack="):
            sackMode = True

    s = Sender(dest, port, filename, debug, sackMode)
    try:
        s.start()
    except (KeyboardInterrupt, SystemExit):
        exit()
