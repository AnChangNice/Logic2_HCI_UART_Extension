
import os
from datetime import datetime

from saleae.automation import *

class Logic2_Analyzer:

    manager = None
    capture = None

    digital_channels = []
    digital_sample_rate = 12500000

    analog_channels = []
    analog_sample_rate = 1562500

    # List[GlitchFilterEntry]
    """
        class GlitchFilterEntry:
            "Represents the glitch filter specifications for a single digital channel"

            #: Digital channel index
            channel_index: int
            #: Minimum pulse width in seconds. The software will round this to the nearest number of samples.
            pulse_width_seconds: float
    """
    glitch_filters = []

    hci_analyzer_list = []

    capture_save_path = None

    capture_timestamp = ''


    def __init__(self):

        try:
            print("Analyzer launch Logic2 ...")
            self.manager = Manager.launch()
            print("Logic2 running!")
        except saleae.automation.errors.Logic2AlreadyRunningError:
            print("Logic2AlreadyRunning!")
            print("Analyzer connect Logic2 ...")
            self.manager = Manager.connect()
            print("Logic2 running!")

        self.save_folder = os.path.abspath('.')


    def capture_config(self, digital_channels=None, digital_sample_rate=12500000, 
                    analog_channels=None, analog_sample_rate=None, glitch_filter=[]):
        if digital_channels is None:
            digital_channels = [0, 1]
        self.digital_channels = digital_channels
        self.digital_sample_rate = digital_sample_rate
        
        if analog_channels is None:
            analog_channels = []
        self.analog_channels = analog_channels
        self.analog_sample_rate = analog_sample_rate

        self.glitch_filter = glitch_filter


    def set_save_folder(self, folder):
        folder = os.path.abspath(folder)
        if not os.path.exists(folder):
            os.makedirs(folder)

        self.save_folder = folder


    def capture_start(self):
        if self.analog_channels is None:
            self.capture = self.manager.start_capture(
                device_id=self.manager.get_devices()[0].device_id,
                device_configuration=LogicDeviceConfiguration(
                    enabled_digital_channels=self.digital_channels,
                    digital_sample_rate=self.digital_sample_rate,
                    glitch_filters=self.glitch_filters
                )
            )
        else:
            self.capture = self.manager.start_capture(
                device_id=self.manager.get_devices()[0].device_id,
                device_configuration=LogicDeviceConfiguration(
                    enabled_digital_channels=self.digital_channels,
                    enabled_analog_channels=self.analog_channels,
                    digital_sample_rate=self.digital_sample_rate,
                    analog_sample_rate=self.analog_sample_rate,
                    glitch_filters=self.glitch_filters
                )
            )
        
        self.capture_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        print("Session:", self.capture.capture_id)


    def capture_save(self, name=None):

        if name:
            name = f"{name}.sal"
        else:
            name = 'capture.sal'

        prefix = self.capture_timestamp

        path = self.save_folder + '/' + f"{prefix}_{name}"

        self.capture.save_capture(path)


    def capture_stop(self):
        self.capture.stop()


    def close(self):
        self.manager.close()


    def export_btsnoop(self, name, tx_channel, rx_channel, bit_rate, trigger_frame_tx="", trigger_frame_rx=""):
        uart_tx = self.capture.add_analyzer(
            "Async Serial",
            label=f"{name}_UART_TX",
            settings={
                "Input Channel": tx_channel,
                "Bit Rate (Bits/s)": bit_rate
            }
        )
        
        uart_rx = self.capture.add_analyzer(
            "Async Serial",
            label=f"{name}_UART_RX",
            settings={
                "Input Channel": rx_channel,
                "Bit Rate (Bits/s)": bit_rate
            }
        )

        hci_tx = self.capture.add_high_level_analyzer(
            extension_directory=os.path.abspath("./HCI_UART"),
            name="UART HCI",
            input_analyzer=uart_tx,
            settings={
                "input analyzer": f"{name}_UART_TX",
                "s1_role_choice": "Host->Controller",
                "s2_decode_mode": "Always" if trigger_frame_tx == "" else "Trigger",
                "s3_decode_trigger_frame": trigger_frame_tx,
                "show in protocol results table": True
            },
            label=f"{name}_HCI_TX"
        )

        hci_rx = self.capture.add_high_level_analyzer(
            extension_directory=os.path.abspath("./HCI_UART"),
            name="UART HCI",
            input_analyzer=uart_rx,
            settings={
                "input analyzer": f"{name}_UART_RX",
                "s1_role_choice": "Controller->Host",
                "s2_decode_mode": "Always" if trigger_frame_rx == "" else "Trigger",
                "s3_decode_trigger_frame": trigger_frame_rx,
                "show in protocol results table": True
            },
            label=f"{name}_HCI_RX"
        )

        prefix = self.capture_timestamp

        csv_file_path = self.save_folder + '/' + f"{prefix}_{name}.csv"
        
        self.capture.export_data_table(
            filepath=csv_file_path,
            analyzers=[hci_tx, hci_rx],
            iso8601_timestamp=True
        )
        
        generate_btsnoop_script = os.path.abspath("./csv2btsnoop.py")
        output_btsnoop_path = self.save_folder + '/' + f"{prefix}_{name}_btsnoop.log"
        
        generate_btsnoop_cmd = f"python {generate_btsnoop_script} {csv_file_path} {output_btsnoop_path}"
        os.system(generate_btsnoop_cmd)


if __name__ == "__main__":

    analyzer = Logic2_Analyzer()

    analyzer.set_save_folder('./log')

    analyzer.capture_config(digital_channels=[0, 1, 2, 3, 4, 5], 
                           digital_sample_rate=12500000)


    analyzer.capture_start()
    time.sleep(3)
    analyzer.capture_stop()

    analyzer.export_btsnoop('ums', tx_channel=0, rx_channel=1, bit_rate=3000000)
    analyzer.export_btsnoop('umr', tx_channel=2, rx_channel=3, bit_rate=3000000)
    
    analyzer.capture_save()

    analyzer.close()

