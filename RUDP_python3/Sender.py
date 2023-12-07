import sys
import getopt
import time
import base64

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
        self.szwin = 5 # 滑动窗口
        self.szpacket = 500 # 数据包大小
        self.seqno = 0
        self.maxack = 0
        self.timerecord = time.time() # 超时
        self.packets = [] # 所有packets
        self.acks = [] # Sack mode
        
        self.Buf = dict() # 缓冲区
        

    def make_all_packets(self):
        seqno = 0
        msg = self.infile.read(self.szpacket)
        msg = base64.b64encode(msg).decode()
        msg_type = None
        while not msg_type == 'end':
            next_msg = self.infile.read(self.szpacket)
            next_msg = base64.b64encode(next_msg).decode()
            # print(next_msg)
            msg_type = 'data'
            if seqno == 0: # 起始段判断
                msg_type = 'start'
            elif (next_msg == "" or next_msg == ''): # 结束段判断
                msg_type = 'end'

            packet = self.make_packet(msg_type,seqno,msg)
            self.packets.append(packet)

            msg = next_msg
            seqno += 1

        self.infile.close()
        
    def GobackN(self):
        keys = []
        for key in self.Buf.keys():
            if key < self.maxack:
                keys.append(key)
        for key in keys:
                self.Buf.pop(key)
        
        # 填充缓冲区
        while len(self.Buf) < self.szwin and self.seqno < len(self.packets):
            self.Buf.update({self.seqno:self.packets[self.seqno]})
            self.seqno += 1
            
    def SackRepeat(self):
        keys_sr = []
        for key in self.Buf.keys():
            if key < self.maxack:
                keys_sr.append(key)
            if key in self.acks:
                keys_sr.append(key) 
        for key in keys_sr:
            self.Buf.pop(key) 
        self.acks.clear()
        
        # 填充缓冲区
        while len(self.Buf) < self.szwin and self.seqno < len(self.packets):
            self.Buf.update({self.seqno:self.packets[self.seqno]})
            self.seqno += 1
        
                   
    # Main sending loop.
    def start(self):
        self.make_all_packets()
        flag = False
        while 1:
            if(flag == False):
                # 填充缓冲区
                while len(self.Buf) < self.szwin and self.seqno < len(self.packets):
                    self.Buf.update({self.seqno:self.packets[self.seqno]})
                    self.seqno += 1
            else:
                if(self.sackMode == False):
                    self.GobackN()
                else:
                    self.SackRepeat()
            
            for key, value in self.Buf.items():
                if key < self.maxack:
                    continue
                self.send("{}".format(value))
            
            self.timerecord = time.time()
            cnt = 0
            while cnt <= len(self.Buf):
                if time.time() - self.timerecord >= self.timeout:
                    break
                resp = self.receive(self.timeout)
                cnt += 1
                if resp != None:
                    resp = resp.decode()
                    if not Checksum.validate_checksum(resp):
                        continue
                    msg_type, ack_seqno, data, checksum = self.split_packet(resp)
                    # if(self.sackMode == False):
                    if(msg_type == 'ack'):
                        if(int(ack_seqno) > self.maxack):
                            self.maxack = int(ack_seqno)
                    elif(msg_type == 'sack'):
                        ack_seqno = ack_seqno.split(';')
                        if(int(ack_seqno[0]) > self.maxack):
                            self.maxack = int(ack_seqno[0])
                        try:
                            acks = ack_seqno[1].split(',')
                            for ack in acks:
                                self.acks.append(ack)
                        except:
                            continue
                            
            if(self.maxack < self.seqno):
                flag = True
            else:
                flag = False
                self.Buf.clear()
            if(self.seqno >= len(self.packets) and len(self.Buf) == 0):
                break            
                

    def handle_timeout(self):
        pass

    def handle_new_ack(self, ack):
        pass

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
