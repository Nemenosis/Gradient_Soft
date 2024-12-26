import time
from src.messenger.packet_id_counter import PacketId


class PacketPreparer:
    def __init__(self, info, packet_id: PacketId, version):
        self.local_id = info["clientid"]
        self.node_id = info["node"]
        self.password = info.get("nodePassword")
        self.packet_id = packet_id or PacketId()
        self.version = version

    @staticmethod
    def get_time_hex():
        current_timestamp = int(time.time() * 1000)
        timestamp_str = str(current_timestamp)
        timestamp_hex = timestamp_str.encode('ascii').hex()
        return timestamp_hex

    @staticmethod
    def get_hex_format(message):
        try:
            return message.encode('ascii').hex()
        except UnicodeEncodeError:
            raise ValueError("Message contains non-ascii characters")

    @staticmethod
    def build_packet(fixed_header, variable_header, payload):
        return bytes.fromhex(fixed_header + variable_header + payload)

    def encoder(self, string_to_encode):
        hex_string = self.get_hex_format(string_to_encode)
        msb = "00"
        lsb = format(len(string_to_encode), "02x")
        result = msb + lsb + hex_string
        return result

    def prepare_connect_packet(self):
        fixed_header = "107D"
        variable_header = "00044D51545405C2003C00"
        payload = self.encoder(self.node_id) + self.encoder(self.local_id) + self.encoder(self.password)
        return self.build_packet(fixed_header, variable_header, payload)

    @staticmethod
    def prepare_pingreq_packet():
        return bytes.fromhex("c000")

    def prepare_150b_packet(self):
        fixed_header = "3093"
        variable_header = "01001E636C69656E742F6F6E6C696E652F"
        node_id_hex = self.get_hex_format(self.node_id)
        dot_space = "007B2274797065223A226F6E6C696E65222C22636C69656E746964223A22"
        comma_space = "222C226163636F756E74223A22"
        local_id_hex = self.get_hex_format(self.local_id)
        timestamp_space = "222C2274696D657374616D70223A"
        timestamp_hex = self.get_time_hex()
        end_message = "7D"
        payload = node_id_hex + dot_space + node_id_hex + comma_space + local_id_hex + timestamp_space + timestamp_hex + end_message
        return self.build_packet(fixed_header, variable_header, payload)

    def prepare_subscribe_packet(self):
        fixed_header = "8222"
        packet_id = self.packet_id.get_hex()
        self.packet_id += 1
        variable_header = packet_id + "00"
        topic = "client/task/" + self.node_id
        payload = self.encoder(topic) + "00"
        return self.build_packet(fixed_header, variable_header, payload)

    def prepare_unsubscribe_packet(self):
        fixed_header = "A221"
        packet_id = self.packet_id.get_hex()
        self.packet_id += 1
        variable_header = packet_id + "00"
        topic = "client/task/" + self.node_id
        payload = self.encoder(topic)
        return self.build_packet(fixed_header, variable_header, payload)

    @staticmethod
    def prepare_disconnect_packet():
        return bytes.fromhex("E000")

    def prepare_version_packet(self):
        fixed_header = "3065"
        variable_header = "001F636C69656E742F76657273696F6E2F" + self.get_hex_format(self.node_id)
        payload = "007B2274797065223A2276657273696F6E222C22636C69656E746964223A22" + self.get_hex_format(
            self.node_id) + "222C2276657273696F6E223A22" + self.get_hex_format(self.version) + "227D"
        return self.build_packet(fixed_header, variable_header, payload)

    def prepare_type_key_packet(self):
        fixed_header = "303D"
        variable_header = "001B636C69656E742F6B65792F" + self.get_hex_format(self.node_id) + "00"
        payload = "7B22636C69656E746964223A22" + self.get_hex_format(self.node_id) + "227d"
        return self.build_packet(fixed_header, variable_header, payload)

