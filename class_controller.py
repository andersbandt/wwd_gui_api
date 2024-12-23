
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
    # TODO: should I add a check for if the ports are matching with anything else too?
    def set_used_port(self, port, usage):
        self.ports_used[port] = usage

        try:
            tree = ET.parse("config/ports_used.xml")
            root = tree.getroot()
        except (FileNotFoundError, ET.ParseError):
            root = ET.Element("PortsUsed")
            tree = ET.ElementTree(root)

        # Create a mapping of usage (tags) to elements
        usage_elements = {child.tag: child for child in root}
        print(f"class_controller.py (set_used_port) is dealing with usage elements: {usage_elements}")

        # Update or create the appropriate element
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



