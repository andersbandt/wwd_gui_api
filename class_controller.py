

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

        # Try to parse the existing XML file
        try:
            tree = ET.parse("config/ports_used.xml")
            root = tree.getroot()
        except FileNotFoundError:
            # If the file does not exist, create a new root element
            root = ET.Element("PortsUsed")
            tree = ET.ElementTree(root)

        # Create a mapping from port numbers to their elements
        port_elements = {child.text: child for child in root}

        # Update or create elements based on self.ports_used
        for port, usage in self.ports_used.items():
            if str(port) in port_elements:
                # Update existing element
                port_element = port_elements[str(port)]
                port_element.tag = usage
            else:
                # Create a new element if not found
                port_element = ET.SubElement(root, usage)
                port_element.text = str(port)

        # Write back to the XML file
        with open("config/ports_used.xml", "wb") as xml_file:
            tree.write(xml_file)

        print("Ports used have been saved to ports_used.xml")

