# High Level Analyzer
# For more information and documentation, please go to https://support.saleae.com/extensions/high-level-analyzer-extensions

from saleae.analyzers import HighLevelAnalyzer, AnalyzerFrame, StringSetting, NumberSetting, ChoicesSetting


# High level analyzers must subclass the HighLevelAnalyzer class.
class Hla(HighLevelAnalyzer):

    s1_role_choice = ChoicesSetting(label="Role Choice", choices=["Host->Controller", "Controller->Host"])
    s2_decode_mode = ChoicesSetting(label="Decode Mode", choices=["Always", "Trigger"])
    s3_decode_trigger_frame = StringSetting(label="Decode Trigger Frame") # HCI RESET: 01 03 0C 00, RES: 04 0E 04 01 03 0C 00

    # An optional list of types this analyzer produces, providing a way to customize the way frames are displayed in Logic 2.
    result_types = {
        'hci_pack': {
            'format': '{{data.data}}'
        }
    }

    # HCI pack receive state
    HCI_PACK_IDEL     = 0
    HCI_PACK_HDR      = 1
    HCI_PACK_PAYLOAD  = 2
    HCI_PACK_COMPLETE = 3

    # HCI pack type
    HCI_ID_CMD = 0x01
    HCI_ID_ACL = 0x02
    HCI_ID_SCO = 0x03
    HCI_ID_EVT = 0x04
    HCI_ID_ISO = 0x05

    HCI_HEADERS = [HCI_ID_CMD, HCI_ID_ACL, HCI_ID_SCO, HCI_ID_EVT, HCI_ID_ISO]

    HCI_HEARDER_LEN = {
        0x01: 3,
        0x02: 4,
        0x03: 3,
        0x04: 2,
        0x05: 4,
    }

    def __init__(self):
        # receive state
        self.state = self.HCI_PACK_IDEL

        # remain bytes to receive
        self.remain = 0

        # uart stream
        self.uart_frames = []

        # trigger stream
        self.decode_trigger_frame = []
        self.triggered = True
        self.trigger_stream = []
        if self.s2_decode_mode == "Trigger" and len(self.s3_decode_trigger_frame) > 0:
            self.triggered = False
            self.__decode_trigger_set()

    def __decode_trigger_set(self):
        frame_str = self.s3_decode_trigger_frame.split(' ')
        frame = [int(x, 16) for x in frame_str]
        for f in frame:
            if f in range(0x00, 0xFF+1):
                self.decode_trigger_frame.append(f)
            else:
                print(f"Invalid trigger frame byte: {f}")
                self.decode_trigger_frame = []
                break

    def __payload_len(self, hci_header):
        hci_id = hci_header[0]

        total_len = 0

        if hci_id == self.HCI_ID_CMD:
            total_len = hci_header[3]
        elif hci_id == self.HCI_ID_ACL:
            total_len = hci_header[3] | (hci_header[4] << 8) # little endian
        elif hci_id == self.HCI_ID_SCO:
            total_len = hci_header[3]
        elif hci_id == self.HCI_ID_EVT:
            total_len = hci_header[2]
        elif hci_id == self.HCI_ID_ISO:
            total_len = hci_header[3] | ((hci_header[4] & 0x3f) << 8) # little endian

        return total_len

    def __get_frame_data(self, frame):
        return int.from_bytes(frame.data['data'], 'little')

    def __uart_datas(self):
        data = []
        for frame in self.uart_frames:
            data.append(self.__get_frame_data(frame))

        return data

    def __get_hci_pack(self, new_frame):
        # get frame data
        val = self.__get_frame_data(new_frame)

        # read state machine
        if self.state == self.HCI_PACK_IDEL:
            if val in self.HCI_HEADERS:
                self.state = self.HCI_PACK_HDR
                self.uart_frames = [new_frame]
                self.remain = self.HCI_HEARDER_LEN[val]
        
        elif self.state == self.HCI_PACK_HDR:
            if self.remain > 0:
                self.uart_frames.append(new_frame)
                self.remain -= 1
            
            if self.remain == 0:
                self.remain = self.__payload_len(self.__uart_datas())
                if self.remain != 0:
                    self.state = self.HCI_PACK_PAYLOAD
                else:
                    self.state = self.HCI_PACK_COMPLETE

        elif self.state == self.HCI_PACK_PAYLOAD:
            if self.remain > 0:
                self.uart_frames.append(new_frame)
                self.remain -= 1
            
            if self.remain == 0:
                self.state = self.HCI_PACK_COMPLETE

        start_time = 0
        end_time = 0
        pack_data = None
        if self.state == self.HCI_PACK_COMPLETE:
            # set the output data
            start_time = self.uart_frames[0].start_time
            end_time = self.uart_frames[-1].end_time
            pack_data = " ".join(["%02X" % (x) for x in self.__uart_datas()])
            # reset receive state machine
            self.state = self.HCI_PACK_IDEL
            self.uart_frames = []

        # return result
        return start_time, end_time, pack_data

    def decode(self, frame: AnalyzerFrame):
        # Check if decode mode is set to "Always" or if trigger frame matches
        if self.s2_decode_mode == "Trigger" and not self.triggered:
            # append the buffer
            self.trigger_stream.append(frame)
            
            # skip if the length not enough
            if len(self.trigger_stream) < len(self.decode_trigger_frame):
                return
            
            # remove the first one if length is bigger than the length
            if len(self.trigger_stream) > len(self.decode_trigger_frame):
                self.trigger_stream = self.trigger_stream[1:]
            
            # check if it match with the trigger frame
            frame_data = [self.__get_frame_data(x) for x in self.trigger_stream]
            if frame_data != self.decode_trigger_frame:
                return

            self.triggered = True
        
        # try get one full pack
        if len(self.trigger_stream) > 0:
            # add to the tail of the stream
            self.trigger_stream.append(frame)
            while len(self.trigger_stream) > 0:
                # get the first frame then remove it from stream
                trigger_frame = self.trigger_stream[0]
                self.trigger_stream = self.trigger_stream[1:]
                # feed first frame into packet processing
                start_time, end_time, pack_data = self.__get_hci_pack(trigger_frame)
                # if find one packet, then break the loop
                if pack_data != None:
                    break
                # if not find, then continue processing next frame
        else:
            start_time, end_time, pack_data = self.__get_hci_pack(frame)

        # Return the data frame itself
        if pack_data != None:
            if self.s1_role_choice == "Host->Controller":
                pack_data = "H->C:" + pack_data
            else:
                pack_data = "C->H:" + pack_data
            return AnalyzerFrame('hci_pack', start_time, end_time, {
                'data': pack_data
            })
