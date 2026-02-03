
import xml.etree.ElementTree as ET

class ClassController:
    def __init__(self):
        self.ser = None
        self.dmm = None
        self.ps = None
        self.relay = None
        self.fg = None

        # TODO: CLAUDE should somehow set some recording status and DISABLE gui_refresh on all tabs. Otherwise logging will crash when I click into another tab
        self.recording = False

        self.ports_used = {}

    def set_ser(self, ser):
        self.ser = ser

    def set_dmm(self, dmm):
        self.dmm = dmm

    def set_ps(self, ps):
        self.ps = ps

    def set_relay(self, relay):
        self.relay = relay

    def set_fg(self, fg):
        self.fg = fg

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

    def get_fg_status(self):
        if self.fg is None:
            return False
        else:
            return self.fg.status

    def set_used_port(self, port, usage):
        """
        Save the port used by a specific tab/usage to XML config.
        If the port is already used by a different tab, it will be reassigned.
        If the usage already has a port, it will be updated.
        """
        self.ports_used[port] = usage

        # Load or create XML tree
        try:
            tree = ET.parse("config/ports_used.xml")
            root = tree.getroot()
        except (FileNotFoundError, ET.ParseError):
            root = ET.Element("PortsUsed")
            tree = ET.ElementTree(root)

        # Remove any OTHER usage that currently has this port
        # (allows port to be reassigned from one tab to another)
        for child in root:
            if child.text == port and child.tag != usage:
                root.remove(child)
                print(f"Port {port} reassigned from {child.tag} to {usage}")

        # Update or create the element for this usage
        usage_element = root.find(usage)
        if usage_element is not None:
            # Update existing element
            old_port = usage_element.text
            usage_element.text = str(port)
            if old_port != port:
                print(f"Updated {usage}: {old_port} -> {port}")
        else:
            # Create new element for this usage
            usage_element = ET.SubElement(root, usage)
            usage_element.text = str(port)
            print(f"Created new port mapping: {usage} -> {port}")

        # Pretty-print the XML with indentation
        ET.indent(root, space="    ", level=0)

        # Write back to the XML file
        with open("config/ports_used.xml", "wb") as xml_file:
            tree.write(xml_file, encoding="utf-8", xml_declaration=True)

        return True



