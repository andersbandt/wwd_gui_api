
import xml.etree.ElementTree as ET
import xml.dom.minidom

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

    # TODO: figure out how I can automatically remove duplicates here
    def set_used_port(self, port, usage):
        self.ports_used[port] = usage

        try:
            tree = ET.parse("config/ports_used.xml")
            root = tree.getroot()
        except (FileNotFoundError, ET.ParseError):
            root = ET.Element("PortsUsed")
            tree = ET.ElementTree(root)

        # check for already existing port
        port_elements = {child.text: child for child in root}
        if port in port_elements:
            print("Can't save XML element, port already in config file")
            return False

        # Update or create the appropriate element
        usage_elements = {child.tag: child for child in root}
        if usage in usage_elements:
            # If an element with the same usage already exists, update its value
            port_element = usage_elements[usage]
            port_element.text = str(port)
        else:
            # Create a new element if the usage does not exist
            port_element = ET.SubElement(root, usage)
            port_element.text = str(port)

        # Write back to the XML file
        with open("config/ports_used.xml", "wb") as xml_file:
            tree.write(xml_file)

        print(f"Ports saved to XML: {usage}, {port}")



