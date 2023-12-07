import random
from tests.BasicTest import BasicTest

class RepeatedTest(BasicTest):
    def __init__(self, forwarder, input_file):
        super(RepeatedTest, self).__init__(forwarder, input_file, sackMode = False)
        
    def handle_packet(self):
        for p in self.forwarder.in_queue:
            self.forwarder.out_queue.append(p)
            if random.choice([True, False]):
                self.forwarder.out_queue.append(p)
        # empty out the in_queue
        self.forwarder.in_queue = []