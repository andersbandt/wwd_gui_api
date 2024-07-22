



class ClassController:
    def __init__(self):
        self.dmm = None
        self.ps = None
        self.relay = None

        self.ports_used = {}

    def set_dmm(self, dmm):
        self.dmm = dmm

    def set_ps(self, ps):
        self.ps = ps

    def set_relay(self, relay):
        self.relay = relay

    def set_used_port(self, port, usage):
        self.ports_used[port] = usage
        print(f"Debug print of cc ports used: {self.ports_used}")

        # TODO: complete function here to write to some file with ports used (XML?)
        #   or could keep things consistent and use that same config.ini filetype?

