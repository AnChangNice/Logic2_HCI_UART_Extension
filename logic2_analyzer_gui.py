import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import re

from logic2_analyzer import Logic2_Analyzer

class GUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Logic Analyzer")
        self.digital_channels = []
        self.digital_sample_rate = tk.StringVar(value='16000000')
        # self.analog_channels = []
        # self.analog_sample_rate = tk.StringVar(value='16000000')
        self.save_folder = tk.StringVar(value=os.path.abspath('.'))
        
        self.analyzer = Logic2_Analyzer()
        self.capturing = False

        self.__ui_capture_config(root)
        self.__ui_analyzer_config(root)
        self.__ui_save_config(root)
        self.__ui_capture_control(root)


    def __ui_capture_config(self, root):
        # Capture Config
        frame_capture = ttk.LabelFrame(root, text="Capture Configuration")
        frame_capture.pack(fill=tk.X, padx=5, pady=5)

        ## digital channel selector
        frame_digital = ttk.LabelFrame(frame_capture, text="Digital Channels")
        frame_digital.pack(fill=tk.X, padx=5, pady=5)

        ### digital channel checkboxes
        frame_digital_selector = ttk.Frame(frame_digital)
        frame_digital_selector.pack(fill=tk.X, padx=5, pady=5)
        
        for i in range(16):  # Assuming 16 digital channels
            var = tk.BooleanVar(value=True if i < 2 else False)
            self.digital_channels.append(var)
            cb = ttk.Checkbutton(frame_digital_selector, text=f"D{i}",variable=var)
            cb.grid(row=i//8, column=i%8, sticky=tk.W, padx=5, pady=2)

        ### digital sample rate
        frame_digital_sample_rate = ttk.Frame(frame_digital)
        frame_digital_sample_rate.pack(fill=tk.X, padx=5, pady=5)
        
        label_digital_sample_rate = ttk.Label(frame_digital_sample_rate, text="Sample Rate (Hz):")
        label_digital_sample_rate.pack(side='left', padx=5)
        
        entry_digital_sample_rate = ttk.Entry(frame_digital_sample_rate, width=10, textvariable=self.digital_sample_rate)
        entry_digital_sample_rate.pack(side='left', padx=5)

        # ## analog channel selector
        # frame_analog = ttk.LabelFrame(frame_capture, text="Analog Channels")
        # frame_analog.pack(fill=tk.X, padx=5, pady=5)

        # ### analog channel checkboxes
        # frame_analog_selector = ttk.Frame(frame_analog)
        # frame_analog_selector.pack(fill=tk.X, padx=5, pady=5)
        
        # for i in range(16):  # Assuming 16 analog channels
        #     var = tk.BooleanVar()
        #     self.analog_channels.append(var)
        #     cb = ttk.Checkbutton(frame_analog_selector, text=f"A{i}",variable=var)
        #     cb.grid(row=i//8, column=i%8, sticky=tk.W, padx=5, pady=2)

        # ### analog sample rate
        # frame_analog_sample_rate = ttk.Frame(frame_analog)
        # frame_analog_sample_rate.pack(fill=tk.X, padx=5, pady=5)
        
        # label_analog_sample_rate = ttk.Label(frame_analog_sample_rate, text="Sample Rate (Hz):")
        # label_analog_sample_rate.pack(side='left', padx=5)
        
        # entry_analog_sample_rate = ttk.Entry(frame_analog_sample_rate, width=10, textvariable=self.analog_sample_rate)
        # entry_analog_sample_rate.pack(side='left', padx=5)


    def __ui_analyzer_config(self, root):
        notebook = ttk.Notebook(root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        frame_hci_uart = ttk.Frame(notebook)
        frame_i2s = ttk.Frame(notebook)
        
        notebook.add(frame_hci_uart, text="HCI UART")

        self.__ui_analyzer_hci_uart(frame_hci_uart)


    def __ui_analyzer_hci_uart(self, root):
        # HCI UART Configuration
        frame_hci_uart_add = ttk.LabelFrame(root, text="New Config")
        frame_hci_uart_add.pack(padx=5, pady=5, expand=True, fill='x')

        ## HCI UART Port Selection
        frame_row_1 = ttk.Frame(frame_hci_uart_add)
        frame_row_1.pack(fill=tk.X, pady=5)

        frame_row_2 = ttk.Frame(frame_hci_uart_add)
        frame_row_2.pack(fill=tk.X, pady=5)

        frame_row_3 = ttk.Frame(frame_hci_uart_add)
        frame_row_3.pack(fill=tk.X, pady=5)

        frame_row_4 = ttk.Frame(frame_hci_uart_add)
        frame_row_4.pack(fill=tk.X, pady=5)

        frame_row_5 = ttk.Frame(frame_hci_uart_add)
        frame_row_5.pack(fill=tk.X, pady=5)

        frame_row_6 = ttk.Frame(frame_hci_uart_add)
        frame_row_6.pack(fill=tk.X, pady=5)

        label_hci_uart_port_name = ttk.Label(frame_row_1, text="            Name:")
        label_hci_uart_port_name.pack(side='left')
        
        self.entry_hci_uart_port_name = ttk.Entry(frame_row_1, width=20)
        self.entry_hci_uart_port_name.pack(side='left')
        
        label_hci_uart_port_tx = ttk.Label(frame_row_2, text="                   TX:")
        label_hci_uart_port_tx.pack(side='left')
        
        self.combo_hci_uart_port_selector_tx = ttk.Combobox(frame_row_2, width=3, values=[i for i in range(16)])
        self.combo_hci_uart_port_selector_tx.pack(side='left')
        
        label_hci_uart_port_rx = ttk.Label(frame_row_2, text="        RX:")
        label_hci_uart_port_rx.pack(side='left')
        
        self.combo_hci_uart_port_selector_rx = ttk.Combobox(frame_row_2, width=3, values=[i for i in range(16)])
        self.combo_hci_uart_port_selector_rx.pack(side='left')

        label_hci_uart_port_baudrate = ttk.Label(frame_row_3, text="       Baudrate:")
        label_hci_uart_port_baudrate.pack(side='left')

        self.entry_hci_uart_port_baudrate = ttk.Entry(frame_row_3, width=20)
        self.entry_hci_uart_port_baudrate.pack(side='left')

        self.tx_trigger = tk.BooleanVar(value=False)
        check_button_tx_trigger = ttk.Checkbutton(frame_row_4, text=f"TX Trigger", variable=self.tx_trigger)
        check_button_tx_trigger.pack(side='left')

        tx_trigger_vlidate_cmd = (root.register(self.tx_trigger_validate), '%P')
        self.tx_trigger_frame_var = tk.StringVar(value="01 03 0C 00") # HCI RESET CMD: 01 03 0C 00
        entry_tx_trigger = ttk.Entry(frame_row_4, width=40, textvariable=self.tx_trigger_frame_var, validate='key', validatecommand=tx_trigger_vlidate_cmd)
        entry_tx_trigger.pack(side='left')

        self.rx_trigger = tk.BooleanVar(value=False)
        check_button_rx_trigger = ttk.Checkbutton(frame_row_5, text=f"RX Trigger", variable=self.rx_trigger)
        check_button_rx_trigger.pack(side='left')

        rx_trigger_vlidate_cmd = (root.register(self.rx_trigger_validate), '%P')
        self.rx_trigger_frame_var = tk.StringVar(value="04 0E 04 01 03 0C 00") # HCI RESET RES: 04 0E 04 01 03 0C 00
        entry_rx_trigger = ttk.Entry(frame_row_5, width=40, textvariable=self.rx_trigger_frame_var, validate='key', validatecommand=rx_trigger_vlidate_cmd)
        entry_rx_trigger.pack(side='left')

        ## HCI UART Port Add
        btn_uart_port_add = ttk.Button(frame_row_6, text="Add", command=self.hci_uart_port_add)
        btn_uart_port_add.pack(side='left', padx=75, ipadx=30)

        ## Listbox
        frame_hci_uart_list = ttk.LabelFrame(root, text="Config List")
        frame_hci_uart_list.pack(padx=5, pady=5, expand=True, fill='x')

        self.hci_uart_listbox = tk.Listbox(frame_hci_uart_list, height=4)
        self.hci_uart_listbox.pack(padx=5, fill='both')
        self.hci_uart_listbox.insert(1, "hci_uart: tx 0, rx 1, rate 3000000, tx_trigger None, rx_trigger None")

        btn_uart_port_remove = ttk.Button(frame_hci_uart_list, text="Remove", command=self.hci_uart_port_remove)
        btn_uart_port_remove.pack(side='left', padx=5, pady=5)
        
        btn_uart_port_clear = ttk.Button(frame_hci_uart_list, text="Clear", command=self.hci_uart_port_remove_all)
        btn_uart_port_clear.pack(side='left', padx=5, pady=5)

    def tx_trigger_validate(self, value):
        value_str = value

        if value_str == '':
            return True

        try:
            value_str = [x for x in value_str.split(' ')]
            if value_str[-1] == '':
                value_str.pop()
            values = [int(x, 16) for x in value_str]

            if len(values) > 0 and all(0 <= x <= 255 for x in values):
                return True
        except:
            return False
    
        return False

    def rx_trigger_validate(self, value):
        value_str = value

        if value_str == '':
            return True

        try:
            value_str = [x for x in value_str.split(' ')]
            if value_str[-1] == '':
                value_str.pop()
            values = [int(x, 16) for x in value_str]
            if len(values) > 0 and all(0 <= x <= 255 for x in values):
                return True
        except:
            return False
    
        return False

    def __ui_save_config(self, root):
        # Save Options
        frame_save_options = ttk.LabelFrame(root, text="Save Options")
        frame_save_options.pack(fill=tk.X, padx=5, pady=5)
        
        ## Save Path Selection
        frame_save_path = ttk.Frame(frame_save_options)
        frame_save_path.pack(fill=tk.X, padx=5, pady=5)
        
        label_save_path = ttk.Label(frame_save_path, text="Save Folder:")
        label_save_path.pack(side='left', padx=5)
        
        self.entry_save_path = ttk.Entry(frame_save_path, textvariable=self.save_folder)
        self.entry_save_path.pack(side='left', padx=5, fill=tk.X, expand=True)
        
        button_select_folder = ttk.Button(frame_save_path, text="Select Folder", command=self.select_folder)
        button_select_folder.pack(side='left', padx=5)


    def __ui_capture_control(self, root):
        # Capture Control
        frame_capture_control = ttk.LabelFrame(root, text="Capture Control")
        frame_capture_control.pack(fill=tk.X, padx=5, pady=5)

        ## Start / Stop
        frame_capture_start_stop = ttk.Frame(frame_capture_control)
        frame_capture_start_stop.pack(fill=tk.X, padx=5, pady=5)

        style = ttk.Style()
        style.configure("MyButton.TButton", padding=(30, 15))

        button_capture_start = ttk.Button(frame_capture_start_stop, text="Start", style="MyButton.TButton", command=self.start_capture)
        button_capture_start.pack(side='left', padx=5)

        button_capture_stop = ttk.Button(frame_capture_start_stop, text="Stop", style="MyButton.TButton", command=self.stop_capture)
        button_capture_stop.pack(side='left', padx=30)


    def hci_uart_port_add(self):
        name = self.entry_hci_uart_port_name.get()
        tx   = int(self.combo_hci_uart_port_selector_tx.get())
        rx   = int(self.combo_hci_uart_port_selector_rx.get())
        baudrate = int(self.entry_hci_uart_port_baudrate.get())
        tx_trigger = self.tx_trigger_frame_var.get() if self.tx_trigger.get() else None
        rx_trigger = self.rx_trigger_frame_var.get() if self.rx_trigger.get() else None

        new_config = f"{name}: tx {tx}, rx {rx}, rate {baudrate}, tx_trigger {tx_trigger}, rx_trigger {rx_trigger}"

        # skip if duplicate
        for i in range(self.hci_uart_listbox.size()):
            config = self.hci_uart_listbox.get(i)

            if new_config == config:
                return

        index = self.hci_uart_listbox.size() + 1
        self.hci_uart_listbox.insert(index, new_config)

    def hci_uart_port_remove(self):
        
        select = self.hci_uart_listbox.curselection()

        if select == ():
            return
        
        index = select[0]

        self.hci_uart_listbox.delete(index)

    def hci_uart_port_remove_all(self):
        for _ in range(self.hci_uart_listbox.size()):
            self.hci_uart_listbox.delete(0)

    def select_folder(self):
        new_fodler = filedialog.askdirectory(initialdir=self.save_folder.get())
        
        if len(new_fodler) == 0:
            return

        self.save_folder.set(new_fodler)

    def start_capture(self):
        if self.capturing:
            return

        # config
        self.analyzer.set_save_folder(self.save_folder.get())

        # capture
        self.analyzer.capture_config(digital_channels=self.get_digital_channels(),
                                     digital_sample_rate=self.get_digital_sample_rate())
        
        self.analyzer.capture_start()

        self.capturing = True


    def stop_capture(self):
        if not self.capturing:
            return

        self.analyzer.capture_stop()
        self.capturing = False

        info = ''

        for index in range(self.hci_uart_listbox.size()):
            config_str = self.hci_uart_listbox.get(index)

            # f"{name}: tx {tx}, rx {rx}, rate {baudrate}, tx_trigger {tx_trigger}, rx_trigger {rx_trigger}"
            res = re.findall(r"(\w+): tx (\d+), rx (\d+), rate (\d+), tx_trigger (.*?), rx_trigger (.*+)", config_str)
            if res == []:
                continue

            res = res[0]

            name = res[0]
            tx   = int(res[1])
            rx   = int(res[2])
            rate = int(res[3])
            tx_trigger = res[4] if res[4] != 'None' else ''
            rx_trigger = res[5] if res[5] != 'None' else ''

            self.analyzer.export_btsnoop(name, tx_channel=tx, rx_channel=rx, bit_rate=rate, trigger_frame_tx=tx_trigger, trigger_frame_rx=rx_trigger)
        
            info += f"{name} btsnoop generated!\n"

        self.analyzer.capture_save()

        messagebox.showinfo(self.root, message=f"Capture Saved!\n{info}")

    def get_digital_channels(self):
        """Returns a list of selected digital channels"""
        return [i for i, var in enumerate(self.digital_channels) if var.get()]

    def get_digital_sample_rate(self):
        return int(self.digital_sample_rate.get())

    # def get_analog_channels(self):
    #     """Returns a list of selected analog channels"""
    #     return [i for i, var in enumerate(self.analog_channels) if var.get()]

    # def get_analog_sample_rate(self):
    #     return int(self.analog_sample_rate.get())

    def on_closing(self):
        """Handle application closing, perform cleanup if necessary"""
        # Close the main window
        self.root.destroy()
        # Close Analyzer
        self.analyzer.close()


if __name__ == "__main__":
    root = tk.Tk()
    myapp = GUI(root)
    root.protocol("WM_DELETE_WINDOW", myapp.on_closing)
    root.mainloop()
