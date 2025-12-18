
import xml.etree.ElementTree as ET

class ClassController:
    def __init__(self):
        self.ser = None
        self.dmm = None
        self.ps = None
        self.relay = None

        self.ports_used = {}

    def set_ser(self, ser):
        self.ser = ser

    def set_dmm(self, dmm):
        self.dmm = dmm

    def set_ps(self, ps):
        self.ps = ps

    def set_relay(self, relay):
        self.relay = relay


    def get_ser_status(self):
        if self.ser is None:
            return False
        else:
            return self.ser.status

    def get_dmm_status(self):
        if self.dmm is None:
            return False
        else:
            return self.dmm.status

    def get_ps_status(self):
        if self.ps is None:
            return False
        else:
            return self.ps.status

    def get_relay_status(self):
        if self.relay is None:
            return False
        else:
            return self.relay.status


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
            print(f"Can't save XML element {usage}@{port}, port already in config file (not an issue).")
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
            return True



