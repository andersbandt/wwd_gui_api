
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

# TODO: this still won't properly keep onle one unique XML entry per SerialPort
    def set_used_port(self, port, usage):
        self.ports_used[port] = usage

        try:
            tree = ET.parse("config/ports_used.xml")
            root = tree.getroot()
        except (FileNotFoundError, ET.ParseError):
            root = ET.Element("PortsUsed")
            tree = ET.ElementTree(root)

        # Create a mapping from port numbers to their elements
        port_elements = {child.text: child for child in root}
        # print(f"Dealing with port elements: {port_elements}")

        # Remove any existing element with the same usage to prevent duplicates
        # for child in root.findall(usage):
        #     root.remove(child)

        # update instance
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

        print(f"Ports saved to XML: {usage},{port}")


