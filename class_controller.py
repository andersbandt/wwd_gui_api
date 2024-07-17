



class ClassController():
    def __init__(self):
        self.dmm = None
        self.ps = None
        self.relay = None

        # TODO: finish implementing some cc array to store used ports and their usage
        self.ports_used = {}


    def set_dmm(self, dmm):
        self.dmm = dmm

    def set_ps(self, ps):
        self.ps = ps

    def set_relay(self, relay):
        self.relay = relay

    def set_used_port(self, port, usage):
        self.ports_used[port] = usage

