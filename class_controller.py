

import xml.etree.ElementTree as ET


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
        # Create the root element
        root = ET.Element("PortsUsed")

        # Add each port and its usage as a child element
        for port, usage in self.ports_used.items():
            port_element = ET.SubElement(root, usage)
            # port_element = ET.SubElement(root, usage, name=str(port))
            port_element.text = str(port)

        # Write to an XML file
        tree = ET.ElementTree(root)
        with open("config/ports_used.xml", "wb") as xml_file:
            tree.write(xml_file)

        print("Ports used have been saved to ports_used.xml")

