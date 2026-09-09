# High Level Analyzer
# For more information and documentation, please go to https://support.saleae.com/extensions/high-level-analyzer-extensions

from saleae.analyzers import HighLevelAnalyzer, AnalyzerFrame, StringSetting, NumberSetting, ChoicesSetting


# Some Logic 2 builds accept a list of AnalyzerFrames from decode(), some only a single
# frame. Set this to False if packets go missing; the cost is that up to
# "Sync Packets" packets at the very end of a capture may stay queued.
EMIT_MULTIPLE = True


# High level analyzers must subclass the HighLevelAnalyzer class.
class Hla(HighLevelAnalyzer):

    s1_role_choice = ChoicesSetting(label="Role Choice", choices=["Host->Controller", "Controller->Host"])
    s2_decode_mode = ChoicesSetting(label="Decode Mode", choices=["Always", "Trigger"])
    s3_decode_trigger_frame = StringSetting(label="Decode Trigger Frame") # HCI RESET: 01 03 0C 00, RES: 04 0E 04 01 03 0C 00
    s4_direction_mode = ChoicesSetting(label="Direction Mode", choices=["Auto", "Manual"])
    s5_sync_packets = NumberSetting(label="Sync Packets", min_value=1, max_value=8)
    s6_trigger_rearm = ChoicesSetting(label="Trigger Re-arm", choices=["On Resync", "Once"])

    # An optional list of types this analyzer produces, providing a way to customize the way frames are displayed in Logic 2.
    result_types = {
        'hci_pack': {
            'format': '{{data.data}}'
        }
    }

    # HCI packet type (first byte of every H4 packet)
    HCI_ID_CMD = 0x01
    HCI_ID_ACL = 0x02
    HCI_ID_SCO = 0x03
    HCI_ID_EVT = 0x04
    HCI_ID_ISO = 0x05

    # Bytes of header that follow the packet type byte, per type.
    HCI_HEADER_LEN = {
        HCI_ID_CMD: 3,
        HCI_ID_ACL: 4,
        HCI_ID_SCO: 3,
        HCI_ID_EVT: 2,
        HCI_ID_ISO: 4,
    }

    DIRECTION_H_C = "H->C"
    DIRECTION_C_H = "C->H"

    # Packet types that can legally appear on each wire. ACL/SCO/ISO travel both ways.
    TYPES_H_C = (HCI_ID_CMD, HCI_ID_ACL, HCI_ID_SCO, HCI_ID_ISO)
    TYPES_C_H = (HCI_ID_EVT, HCI_ID_ACL, HCI_ID_SCO, HCI_ID_ISO)
    TYPES_ANY = (HCI_ID_CMD, HCI_ID_ACL, HCI_ID_SCO, HCI_ID_EVT, HCI_ID_ISO)

    # A Command can only be Host->Controller and an Event only Controller->Host, so
    # either one pins down the true direction of the wire it was captured on -- no
    # matter what the role setting says.
    DIRECTION_ANCHOR = {
        HCI_ID_CMD: DIRECTION_H_C,
        HCI_ID_EVT: DIRECTION_C_H,
    }

    # While hunting for the packet alignment, a payload longer than this is treated as
    # a mis-read length field. Host ACL buffers are typically <= 1021 bytes, so 2048 is
    # generous. Once locked the real length field is honoured up to 0xFFFF.
    SEARCH_MAX_PAYLOAD = 2048
    LOCKED_MAX_PAYLOAD = 0xFFFF

    # Hard cap on buffered bytes so a bogus length field cannot grow the buffer forever.
    BUFFER_LIMIT = 16384

    # Consecutive valid packets required to trust an alignment. Measured false lock rate
    # on random bytes: 1.2e-2 at 1, 1.0e-4 at 2, below 1.7e-5 at 3.
    DEFAULT_SYNC_PACKETS = 3

    TRIGGER_WILDCARDS = ("??", "?", "XX", "xx")

    def __init__(self):
        # how many consecutive valid packets are needed to accept an alignment
        self.sync_packets = self.__read_sync_packets()

        # output gating: trigger patterns and whether we are still waiting for one
        self.trigger_patterns = self.__read_trigger_patterns()
        self.trigger_active = bool(self.trigger_patterns)
        self.waiting_for_trigger = self.trigger_active

        # buffered Async Serial frames and their byte values, kept in lockstep
        self.frames = []
        self.bytes = []

        # framer state
        self.locked = False

        # direction proven by a Command/Event packet. Sticky for the whole capture:
        # the wiring does not change halfway through.
        self.direction = None

        # packets waiting to be handed to Logic 2
        self.out_queue = []

    def __read_sync_packets(self):
        try:
            requested = int(self.s5_sync_packets)
        except (TypeError, ValueError):
            return self.DEFAULT_SYNC_PACKETS

        return requested if 1 <= requested <= 8 else self.DEFAULT_SYNC_PACKETS

    def __read_trigger_patterns(self):
        if self.s2_decode_mode != "Trigger":
            return []

        try:
            patterns = self.__trigger_parse(self.s3_decode_trigger_frame)
        except ValueError as err:
            print(f"UART HCI: {err}")
            patterns = []

        if not patterns:
            print("UART HCI: no usable trigger frame, decoding everything instead")

        return patterns

    # ------------------------------------------------------------------ trigger

    def __trigger_parse(self, text):
        """Parse the trigger setting into a list of packet patterns.

        Alternatives are separated by '|' and any one of them may match, which is what
        lets the same setting work no matter which way round TX/RX are wired. A '??'
        token becomes None and matches any byte, useful for fields like the Command
        Complete num_HCI_Command_Packets byte.

            "01 03 0C 00 | 04 0E 04 ?? 03 0C 00"
                -> [[1, 3, 12, 0], [4, 14, 4, None, 3, 12, 0]]
        """
        patterns = []

        for chunk in text.split('|'):
            pattern = [self.__trigger_token(t) for t in chunk.split()]
            if pattern:
                patterns.append(pattern)

        return patterns

    def __trigger_token(self, token):
        """One trigger token to a byte value, or None for a wildcard. Raises on garbage."""
        if token in self.TRIGGER_WILDCARDS:
            return None

        try:
            value = int(token, 16)
        except ValueError:
            value = -1
        if not 0x00 <= value <= 0xFF:
            raise ValueError(f"bad trigger frame byte: {token!r}")

        return value

    def __trigger_match(self, offset, size):
        """True when the complete packet at `offset` matches one of the trigger patterns.

        Matching whole packets rather than raw bytes is what stops a trigger sequence
        that happens to occur inside a payload from starting the decode mid-packet.
        """
        packet = self.bytes[offset:offset + size]

        for pattern in self.trigger_patterns:
            if len(pattern) != len(packet):
                continue
            if all(want is None or want == got for want, got in zip(pattern, packet)):
                return True

        return False

    # ------------------------------------------------------------------ framing

    def __frame_byte(self, frame):
        """Byte carried by an Async Serial frame, or None if the frame is unusable."""
        data = getattr(frame, 'data', None)
        if not isinstance(data, dict) or 'data' not in data:
            return None
        if data.get('error'):
            return None

        try:
            return int.from_bytes(data['data'], 'little')
        except (TypeError, ValueError):
            return None

    def __allowed_types(self):
        """Packet types accepted as a packet start.

        Only a direction actually proven by a Command/Event packet narrows this down.
        The role setting is deliberately never used here: if the probes are swapped it
        would reject every packet on the wire.
        """
        if self.direction == self.DIRECTION_H_C:
            return self.TYPES_H_C
        if self.direction == self.DIRECTION_C_H:
            return self.TYPES_C_H

        return self.TYPES_ANY

    def __payload_len(self, header):
        """Payload length from a complete packet header (bytes after the type byte)."""
        hci_id = header[0]

        if hci_id in (self.HCI_ID_CMD, self.HCI_ID_SCO):
            return header[3]                                    # 8-bit length
        if hci_id == self.HCI_ID_EVT:
            return header[2]                                    # 8-bit length
        if hci_id == self.HCI_ID_ACL:
            return header[3] | (header[4] << 8)                 # 16-bit little endian
        if hci_id == self.HCI_ID_ISO:
            return header[3] | ((header[4] & 0x3f) << 8)        # 14-bit little endian

        return 0

    def __packet_size(self, offset, max_payload):
        """Total bytes of the packet starting at `offset`.

        Returns None if those bytes cannot be a valid packet, and 0 if the packet is
        still incomplete and more data is needed to tell.
        """
        if offset >= len(self.bytes):
            return 0

        hci_id = self.bytes[offset]
        if hci_id not in self.__allowed_types():
            return None

        header_len = 1 + self.HCI_HEADER_LEN[hci_id]
        if offset + header_len > len(self.bytes):
            return 0

        payload_len = self.__payload_len(self.bytes[offset:offset + header_len])
        if payload_len > max_payload:
            return None

        total = header_len + payload_len
        if offset + total > len(self.bytes):
            return 0

        return total

    def __chain_ok(self, offset):
        """Whether `sync_packets` consecutive valid packets parse from `offset`.

        This is the whole idea behind the framer: a wrong alignment almost always trips
        over an impossible type byte or length field within a packet or two, while the
        real alignment keeps parsing cleanly. Returns None while undecidable.
        """
        for _ in range(self.sync_packets):
            size = self.__packet_size(offset, self.SEARCH_MAX_PAYLOAD)
            if size is None:
                return False
            if size == 0:
                return None
            offset += size

        return True

    def __acquire(self):
        """Hunt for the packet alignment, sliding forward through the buffer.

        On success the buffer is trimmed so a packet starts at index 0. Ruled-out bytes
        are dropped, so the search never re-examines them.
        """
        offset = 0

        while offset < len(self.bytes):
            chain = self.__chain_ok(offset)

            if chain is None:
                break   # undecidable for now, keep these bytes and wait for more

            if not chain:
                offset += 1
                continue

            # A clean chain marks a real packet boundary. In Always mode that is enough
            # to lock. In Trigger mode we only lock on the trigger packet, and otherwise
            # skip this whole packet and keep hunting -- so the vendor traffic ahead of
            # Reset is dropped a packet at a time rather than a byte at a time.
            size = self.__packet_size(offset, self.SEARCH_MAX_PAYLOAD)
            if not self.waiting_for_trigger or self.__trigger_match(offset, size):
                self.__discard(offset)
                self.locked = True
                self.waiting_for_trigger = False
                return True

            offset += size

        self.__discard(offset)

        return False

    def __desync(self, clear=False):
        """Give up the current alignment and go back to hunting.

        Losing sync is a normal, repeated event: the board can be reset mid-capture, so
        the stream looks like bad bytes / good frames / bad bytes / good frames. When
        re-arming is enabled each of those good stretches has to present the trigger
        packet again, so every reset gets its pre-Reset traffic filtered too.
        """
        self.locked = False

        if clear:
            self.frames = []
            self.bytes = []

        if self.trigger_active and self.s6_trigger_rearm == "On Resync":
            self.waiting_for_trigger = True

    def __discard(self, count):
        if count <= 0:
            return

        del self.frames[:count]
        del self.bytes[:count]

    # ------------------------------------------------------------------ output

    def __build_packet(self, size):
        """Pop the packet at the head of the buffer and turn it into an AnalyzerFrame."""
        frames = self.frames[:size]
        data = self.bytes[:size]
        self.__discard(size)

        # A Command or an Event settles the direction of this wire for good.
        anchor = self.DIRECTION_ANCHOR.get(data[0])
        if anchor is not None:
            self.direction = anchor

        pack_data = self.__direction_of(data) + ":" + " ".join("%02X" % b for b in data)

        return AnalyzerFrame('hci_pack', frames[0].start_time, frames[-1].end_time, {
            'data': pack_data
        })

    def __direction_of(self, data):
        """Direction label for a packet. Manual mode always trusts the role setting;
        Auto uses the direction proven by a Command/Event, falling back to the role
        until one has been seen."""
        role = self.DIRECTION_H_C if self.s1_role_choice == "Host->Controller" else self.DIRECTION_C_H

        if self.s4_direction_mode == "Manual":
            return role

        return self.direction or role

    def __collect(self):
        """Pull every complete packet currently available out of the buffer."""
        packets = []

        while True:
            if not self.locked and not self.__acquire():
                break

            size = self.__packet_size(0, self.LOCKED_MAX_PAYLOAD)

            if size == 0:
                break           # packet started but not finished yet
            if size is None:
                self.__desync() # stream went bad, hunt for the next good stretch
                continue

            packets.append(self.__build_packet(size))

        return packets

    def decode(self, frame: AnalyzerFrame):
        byte = self.__frame_byte(frame)

        if byte is None:
            # A framing or parity error means the line is not running at the configured
            # bit rate -- typically the board rebooting and reconfiguring its baud rate.
            # Nothing buffered can be trusted.
            self.__desync(clear=True)
            return None

        self.frames.append(frame)
        self.bytes.append(byte)

        if len(self.bytes) > self.BUFFER_LIMIT:
            self.__discard(len(self.bytes) - self.BUFFER_LIMIT)
            self.locked = False

        self.out_queue += self.__collect()

        if not self.out_queue:
            return None

        if EMIT_MULTIPLE:
            packets, self.out_queue = self.out_queue, []
            return packets if len(packets) > 1 else packets[0]

        return self.out_queue.pop(0)
