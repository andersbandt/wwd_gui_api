"""Central controller that holds references to all connected equipment."""

import os
import xml.etree.ElementTree as ET

from services import DMMService, PSService, FGService, OscService

_PORTS_XML = os.path.join("config", "ports_used.xml")


def _write_xml(tree, root):
    """Strip compounded whitespace nodes, re-indent, and write ports_used.xml."""
    for elem in root.iter():
        if elem.text and not elem.text.strip():
            elem.text = None
        if elem.tail and not elem.tail.strip():
            elem.tail = None
    ET.indent(root, space="    ", level=0)
    with open(_PORTS_XML, "wb") as f:
        tree.write(f, encoding="utf-8", xml_declaration=True)


class ClassController:
    def __init__(self):
        # Create ports_used.xml on first run if it doesn't exist
        if not os.path.exists(_PORTS_XML):
            root = ET.Element("PortsUsed")
            _write_xml(ET.ElementTree(root), root)
        self.ser = None
        self.dmm = None
        self.ps = None
        self.relay = None
        self.fg = None
        self.osc = None

        # Recording status flag - set by logging tab to prevent gui_refresh during active recording
        self.recording = False

        self.ports_used = {}  # Tracks last used ports (for XML config)
        self.active_connections = {}  # Tracks currently active connections {port: usage_name}

        # Equipment services (tabs set registries during their init)
        self.dmm_service = DMMService(self)
        self.ps_service = PSService(self)
        self.fg_service = FGService(self)
        self.osc_service = OscService(self)

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

    def set_osc(self, osc):
        self.osc = osc

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

    def get_osc_status(self):
        if self.osc is None:
            return False
        else:
            return self.osc.status

    def set_used_port(self, port, usage):
        """
        Save the port used by a specific tab/usage to XML config.
        If the port is already used by a different tab, it will be reassigned.
        If the usage already has a port, it will be updated.
        """
        self.ports_used[port] = usage

        # Load or create XML tree
        try:
            tree = ET.parse(_PORTS_XML)
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
            old_port = usage_element.text
            usage_element.text = str(port)
            if old_port != port:
                print(f"Updated {usage}: {old_port} -> {port}")
        else:
            usage_element = ET.SubElement(root, usage)
            usage_element.text = str(port)
            print(f"Created new port mapping: {usage} -> {port}")

        _write_xml(tree, root)
        return True

    def set_used_model(self, model, usage):
        """
        Save the equipment model used by a specific tab/usage to XML config.
        If the usage already has a model, it will be updated.

        Args:
            model: The equipment model name (e.g., "SPD3303X", "XDM1041")
            usage: The name of the connection (e.g., "DMM_Serial", "PS_PyVISA")
        """
        # Load or create XML tree
        try:
            tree = ET.parse(_PORTS_XML)
            root = tree.getroot()
        except (FileNotFoundError, ET.ParseError):
            root = ET.Element("PortsUsed")
            tree = ET.ElementTree(root)

        # Find or create the usage element
        usage_element = root.find(usage)
        if usage_element is None:
            usage_element = ET.SubElement(root, usage)
            usage_element.text = ""

        old_model = usage_element.get("model")
        usage_element.set("model", str(model))

        if old_model != model:
            if old_model:
                print(f"Updated {usage} model: {old_model} -> {model}")
            else:
                print(f"Set {usage} model: {model}")

        _write_xml(tree, root)
        return True

    def get_used_model(self, usage):
        """
        Retrieve the previously used equipment model for a specific tab/usage.

        Args:
            usage: The name of the connection (e.g., "DMM_Serial", "PS_PyVISA")

        Returns:
            str: The model name if found, None otherwise
        """
        try:
            tree = ET.parse(_PORTS_XML)
            root = tree.getroot()
        except (FileNotFoundError, ET.ParseError):
            return None

        usage_element = root.find(usage)
        if usage_element is not None:
            model = usage_element.get("model")
            return model

        return None

    def set_used_method(self, method, usage):
        """Save the port detection method for a specific tab/usage as an XML attribute."""
        try:
            tree = ET.parse(_PORTS_XML)
            root = tree.getroot()
        except (FileNotFoundError, ET.ParseError):
            root = ET.Element("PortsUsed")
            tree = ET.ElementTree(root)

        usage_element = root.find(usage)
        if usage_element is None:
            usage_element = ET.SubElement(root, usage)
            usage_element.text = ""

        usage_element.set("method", str(method))
        _write_xml(tree, root)

    def get_used_method(self, usage):
        """Retrieve the saved port detection method for a specific tab/usage."""
        try:
            tree = ET.parse(_PORTS_XML)
            root = tree.getroot()
        except (FileNotFoundError, ET.ParseError):
            return None

        usage_element = root.find(usage)
        if usage_element is not None:
            method = usage_element.get("method")
            if method is not None:
                return int(method)
        return None

    def add_active_connection(self, port, usage):
        """
        Register a port as actively connected.

        Args:
            port: The port identifier (e.g., "COM3", "/dev/ttyUSB0", "ASRL3::INSTR")
            usage: The name of the connection (e.g., "DMM", "Serial", "PS")
        """
        self.active_connections[port] = usage
        print(f"Active connection added: {usage} @ {port}")

    def remove_active_connection(self, port):
        """
        Unregister a port from active connections.

        Args:
            port: The port identifier to remove

        Returns:
            True if port was removed, False if it wasn't in active connections
        """
        if port in self.active_connections:
            usage = self.active_connections.pop(port)
            print(f"Active connection removed: {usage} @ {port}")
            return True
        return False

    def is_port_active(self, port):
        """
        Check if a port is currently in active use.

        Args:
            port: The port identifier to check

        Returns:
            tuple: (is_active, usage_name) where is_active is bool and usage_name is str or None
        """
        if port in self.active_connections:
            return (True, self.active_connections[port])
        return (False, None)

    def get_active_connections(self):
        """
        Get all currently active connections.

        Returns:
            dict: Copy of active_connections dictionary
        """
        return self.active_connections.copy()



