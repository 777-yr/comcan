import tkinter as tk
from tkinter import ttk, filedialog, messagebox, Toplevel
import cantools
import can
import json
import os
import threading
import time

class CANControlGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("CAN Control GUI")

        # CAN bus setup
        self.can_bus = None
        self.db = None
        self.signals = []
        self.config_file_name = "N/A"
        self.activate_motor = tk.BooleanVar()
        self.activate_motor.trace_add('write', self.activate_motor_changed)

        # Configuration state variables
        self.saved_dbc_file_path = ""
        self.saved_target_speed_signal = ""
        self.saved_actual_speed_signal = ""
        self.saved_msg_counter1_signal = ""
        self.saved_msg_counter2_signal = ""
        self.saved_activate_motor_signal = ""
        self.saved_wakeup_signal = ""
        self.saved_msg_crc1_signal = ""
        self.saved_msg_crc2_signal = ""
        self.saved_gen_sig_data_id_1 = []
        self.saved_gen_sig_data_id_2 = []

        # Counter values
        self.signal_counters = {}
        self.signal_details = {}
        self.signal_values = {}  # Dictionary to track current signal values

        # Data for each message ID
        self.message_data = {}
        self.cycle_times = {}

        # Control Window
        control_frame = ttk.LabelFrame(self.root, text="Control")
        control_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.messages_frame = ttk.LabelFrame(self.root, text="CAN Messages")
        self.messages_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.message_labels = {}  # Dictionary to store labels for each message ID

        self.config_name_label = ttk.Label(control_frame, text=f"Configuration: {self.config_file_name}")
        self.config_name_label.grid(row=0, column=0, columnspan=2, padx=5, pady=5)

        self.can_status = tk.Label(control_frame, text="CAN Disconnected", bg="red", width=20)
        self.can_status.grid(row=1, column=0, padx=5, pady=5)

        self.connect_button = ttk.Button(control_frame, text="Connect", command=self.connect_or_disconnect_can)
        self.connect_button.grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(control_frame, text="Target Speed:").grid(row=2, column=0, padx=5, pady=5, sticky="e")
        self.target_speed = ttk.Entry(control_frame)
        self.target_speed.grid(row=2, column=1, padx=5, pady=5)
        self.target_speed.bind("<Return>", self.send_target_speed)

        ttk.Label(control_frame, text="Actual Speed:").grid(row=3, column=0, padx=5, pady=5, sticky="e")
        self.actual_speed = ttk.Label(control_frame, text="N/A", width=20)
        self.actual_speed.grid(row=3, column=1, padx=5, pady=5)

        # Message Counters
        ttk.Label(control_frame, text="Message Counter 1:").grid(row=4, column=0, padx=5, pady=5, sticky="e")
        self.msg_counter1 = ttk.Label(control_frame, text="N/A", width=20)
        self.msg_counter1.grid(row=4, column=1, padx=5, pady=5)

        ttk.Label(control_frame, text="Message Counter 2:").grid(row=5, column=0, padx=5, pady=5, sticky="e")
        self.msg_counter2 = ttk.Label(control_frame, text="N/A", width=20)
        self.msg_counter2.grid(row=5, column=1, padx=5, pady=5)

        # Activate Motor Checkbox
        self.activate_motor_checkbox = ttk.Checkbutton(control_frame, text="Activate Motor", variable=self.activate_motor)
        self.activate_motor_checkbox.grid(row=6, column=0, columnspan=2, pady=5)

        # Wakeup Signal Checkbox
        self.wakeup_signal_active = tk.BooleanVar()
        self.wakeup_signal_active.trace_add('write', self.handle_wakeup_signal)

        self.wakeup_signal_checkbox = ttk.Checkbutton(control_frame, text="Send Wakeup Signal", variable=self.wakeup_signal_active, onvalue=True, offvalue=False)
        self.wakeup_signal_checkbox.grid(row=7, column=0, columnspan=2, pady=5)

        ttk.Button(control_frame, text="Configure", command=self.open_configure_window).grid(row=8, column=0, columnspan=2, pady=10)

        # Start CAN message listener
        self.listener_thread = threading.Thread(target=self.can_message_listener)
        self.listener_thread.daemon = True
        self.listener_thread.start()

        # Start periodic message sender
        self.periodic_thread = threading.Thread(target=self.send_periodic_messages)
        self.periodic_thread.daemon = True
        self.periodic_thread.start()

    def open_configure_window(self):
        config_window = Toplevel(self.root)
        config_window.title("Configuration")

        ttk.Label(config_window, text="Select DBC File:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.dbc_file_path = tk.StringVar(value=self.saved_dbc_file_path)
        ttk.Entry(config_window, textvariable=self.dbc_file_path, width=50).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(config_window, text="Browse", command=self.browse_file).grid(row=0, column=2, padx=5, pady=5)

        ttk.Label(config_window, text="Target Speed Signal:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.target_speed_signal = ttk.Combobox(config_window, width=47)
        self.target_speed_signal.grid(row=1, column=1, padx=5, pady=5)
        self.target_speed_signal.bind("<<ComboboxSelected>>", self.signal_selected)

        ttk.Label(config_window, text="Actual Speed Signal:").grid(row=2, column=0, padx=5, pady=5, sticky="e")
        self.actual_speed_signal = ttk.Combobox(config_window, width=47)
        self.actual_speed_signal.grid(row=2, column=1, padx=5, pady=5)
        self.actual_speed_signal.bind("<<ComboboxSelected>>", self.signal_selected)

        ttk.Label(config_window, text="Message Counter 1 Signal:").grid(row=3, column=0, padx=5, pady=5, sticky="e")
        self.msg_counter1_signal = ttk.Combobox(config_window, width=47)
        self.msg_counter1_signal.grid(row=3, column=1, padx=5, pady=5)
        self.msg_counter1_signal.bind("<<ComboboxSelected>>", self.signal_selected)

        ttk.Label(config_window, text="Message Counter 2 Signal:").grid(row=4, column=0, padx=5, pady=5, sticky="e")
        self.msg_counter2_signal = ttk.Combobox(config_window, width=47)
        self.msg_counter2_signal.grid(row=4, column=1, padx=5, pady=5)
        self.msg_counter2_signal.bind("<<ComboboxSelected>>", self.signal_selected)

        ttk.Label(config_window, text="Activate Motor Signal:").grid(row=5, column=0, padx=5, pady=5, sticky="e")
        self.activate_motor_signal = ttk.Combobox(config_window, width=47)
        self.activate_motor_signal.grid(row=5, column=1, padx=5, pady=5)
        self.activate_motor_signal.bind("<<ComboboxSelected>>", self.signal_selected)

        ttk.Label(config_window, text="Wakeup Signal:").grid(row=6, column=0, padx=5, pady=5, sticky="e")
        self.wakeup_signal = ttk.Combobox(config_window, width=47)
        self.wakeup_signal.grid(row=6, column=1, padx=5, pady=5)
        self.wakeup_signal.bind("<<ComboboxSelected>>", self.signal_selected)

        ttk.Label(config_window, text="MsgCRC1 Signal:").grid(row=7, column=0, padx=5, pady=5, sticky="e")
        self.msg_crc1_signal = ttk.Combobox(config_window, width=47)
        self.msg_crc1_signal.grid(row=7, column=1, padx=5, pady=5)
        self.msg_crc1_signal.bind("<<ComboboxSelected>>", self.signal_selected)

        ttk.Label(config_window, text="MsgCRC2 Signal:").grid(row=8, column=0, padx=5, pady=5, sticky="e")
        self.msg_crc2_signal = ttk.Combobox(config_window, width=47)
        self.msg_crc2_signal.grid(row=8, column=1, padx=5, pady=5)
        self.msg_crc2_signal.bind("<<ComboboxSelected>>", self.signal_selected)

        ttk.Label(config_window, text="GenSigDataID 1:").grid(row=9, column=0, padx=5, pady=5, sticky="e")
        self.gen_sig_data_id_1 = tk.Entry(config_window, width=50)
        self.gen_sig_data_id_1.grid(row=9, column=1, padx=5, pady=5)

        ttk.Label(config_window, text="GenSigDataID 2:").grid(row=10, column=0, padx=5, pady=5, sticky="e")
        self.gen_sig_data_id_2 = tk.Entry(config_window, width=50)
        self.gen_sig_data_id_2.grid(row=10, column=1, padx=5, pady=5)

        ttk.Button(config_window, text="Save Configuration", command=self.save_configuration).grid(row=11, column=0, padx=5, pady=5)
        ttk.Button(config_window, text="Load Configuration", command=self.load_configuration).grid(row=11, column=1, padx=5, pady=5)
        ttk.Button(config_window, text="Close", command=lambda: self.close_config_window(config_window)).grid(row=12, column=0, columnspan=3, pady=10)

        # Set current values
        self.target_speed_signal.set(self.saved_target_speed_signal)
        self.actual_speed_signal.set(self.saved_actual_speed_signal)
        self.msg_counter1_signal.set(self.saved_msg_counter1_signal)
        self.msg_counter2_signal.set(self.saved_msg_counter2_signal)
        self.activate_motor_signal.set(self.saved_activate_motor_signal)
        self.wakeup_signal.set(self.saved_wakeup_signal)
        self.msg_crc1_signal.set(self.saved_msg_crc1_signal)
        self.msg_crc2_signal.set(self.saved_msg_crc2_signal)
        self.gen_sig_data_id_1.insert(0, ', '.join(map(str, self.saved_gen_sig_data_id_1)))
        self.gen_sig_data_id_2.insert(0, ', '.join(map(str, self.saved_gen_sig_data_id_2)))

        if self.db:
            self.target_speed_signal['values'] = self.signals
            self.actual_speed_signal['values'] = self.signals
            self.msg_counter1_signal['values'] = self.signals
            self.msg_counter2_signal['values'] = self.signals
            self.activate_motor_signal['values'] = self.signals
            self.wakeup_signal['values'] = self.signals
            self.msg_crc1_signal['values'] = self.signals
            self.msg_crc2_signal['values'] = self.signals

    def close_config_window(self, window):
        # Save the current configuration to the main GUI
        self.saved_dbc_file_path = self.dbc_file_path.get()
        self.saved_target_speed_signal = self.target_speed_signal.get()
        self.saved_actual_speed_signal = self.actual_speed_signal.get()
        self.saved_msg_counter1_signal = self.msg_counter1_signal.get()
        self.saved_msg_counter2_signal = self.msg_counter2_signal.get()
        self.saved_activate_motor_signal = self.activate_motor_signal.get()
        self.saved_wakeup_signal = self.wakeup_signal.get()
        self.saved_msg_crc1_signal = self.msg_crc1_signal.get()
        self.saved_msg_crc2_signal = self.msg_crc2_signal.get()

        # Parse GenSigDataID values from the entry fields
        self.saved_gen_sig_data_id_1 = [int(x.strip()) for x in self.gen_sig_data_id_1.get().split(',') if x.strip().isdigit()]
        self.saved_gen_sig_data_id_2 = [int(x.strip()) for x in self.gen_sig_data_id_2.get().split(',') if x.strip().isdigit()]

        # Initialize counters if not already set
        if self.saved_msg_counter1_signal not in self.signal_counters:
            self.signal_counters[self.saved_msg_counter1_signal] = 0
        if self.saved_msg_counter2_signal not in self.signal_counters:
            self.signal_counters[self.saved_msg_counter2_signal] = 0

        if self.config_file_name == "N/A":
            self.config_file_name = "Spontaneous Configuration"
        self.config_name_label.config(text=f"Configuration: {self.config_file_name}")

        window.destroy()

    def browse_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("DBC Files", "*.dbc")])
        if file_path:
            self.dbc_file_path.set(file_path)
            self.load_dbc(file_path)

    def load_dbc(self, file_path):
        try:
            self.db = cantools.database.load_file(file_path)
            self.signals = [signal.name for message in self.db.messages for signal in message.signals]
            self.target_speed_signal['values'] = self.signals
            self.actual_speed_signal['values'] = self.signals
            self.msg_counter1_signal['values'] = self.signals
            self.msg_counter2_signal['values'] = self.signals
            self.activate_motor_signal['values'] = self.signals
            self.wakeup_signal['values'] = self.signals
            self.msg_crc1_signal['values'] = self.signals
            self.msg_crc2_signal['values'] = self.signals
            self.check_signal_conflicts()
            messagebox.showinfo("Success", "DBC file loaded successfully")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load DBC file: {e}")

    def check_signal_conflicts(self):
        bit_occupancy = {}
        conflicts = []

        for signal in self.signals:
            signal_info = self.get_signal_info(signal)
            message_id = signal_info['message_id']
            start_bit = signal_info['start_bit']
            length = signal_info['length']

            for bit in range(start_bit, start_bit + length):
                if (message_id, bit) in bit_occupancy:
                    conflicts.append((signal, bit_occupancy[(message_id, bit)]))
                else:
                    bit_occupancy[(message_id, bit)] = signal

        if conflicts:
            conflict_message = "Conflicts found between signals:\n"
            for conflict in conflicts:
                conflict_message += f" - {conflict[0]} conflicts with {conflict[1]}\n"
            messagebox.showerror("Signal Conflicts", conflict_message)

    def signal_selected(self, event):
        signal_name = event.widget.get()
        self.get_signal_info(signal_name)

    def get_signal_info(self, signal_name):
        for message in self.db.messages:
            for signal in message.signals:
                if signal.name == signal_name:
                    signal_info = {
                        'name': signal.name,
                        'start_bit': signal.start,
                        'length': signal.length,
                        'byte_order': 'big_endian' if signal.byte_order == 'big_endian' else 'little_endian',
                        'is_signed': signal.is_signed,
                        'message_id': message.frame_id,
                        'message_name': message.name,
                        'message_length': message.length,
                        'cycle_time': message.cycle_time if hasattr(message, 'cycle_time') else 1000
                    }
                    self.signal_details[signal_name] = signal_info
                    self.cycle_times[message.frame_id] = signal_info['cycle_time']
                    return signal_info
        return None

    def save_configuration(self):
        # Parse GenSigDataID values before saving
        self.saved_gen_sig_data_id_1 = [int(x.strip()) for x in self.gen_sig_data_id_1.get().split(',') if x.strip().isdigit()]
        self.saved_gen_sig_data_id_2 = [int(x.strip()) for x in self.gen_sig_data_id_2.get().split(',') if x.strip().isdigit()]

        config = {
            'dbc_file': self.dbc_file_path.get(),
            'target_speed_signal': self.target_speed_signal.get(),
            'actual_speed_signal': self.actual_speed_signal.get(),
            'msg_counter1_signal': self.msg_counter1_signal.get(),
            'msg_counter2_signal': self.msg_counter2_signal.get(),
            'activate_motor_signal': self.activate_motor_signal.get(),
            'wakeup_signal': self.wakeup_signal.get(),
            'msg_crc1_signal': self.msg_crc1_signal.get(),
            'msg_crc2_signal': self.msg_crc2_signal.get(),
            'gen_sig_data_id_1': self.saved_gen_sig_data_id_1,
            'gen_sig_data_id_2': self.saved_gen_sig_data_id_2,
            'signal_details': self.signal_details
        }
        save_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Files", "*.json")])
        if save_path:
            with open(save_path, 'w') as f:
                json.dump(config, f)
            self.config_file_name = os.path.basename(save_path)
            self.config_name_label.config(text=f"Configuration: {self.config_file_name}")
            messagebox.showinfo("Success", "Configuration saved successfully")

    def load_configuration(self):
        load_path = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")])
        if load_path:
            with open(load_path, 'r') as f:
                config = json.load(f)
                self.dbc_file_path.set(config['dbc_file'])
                self.load_dbc(config['dbc_file'])
                self.target_speed_signal.set(config['target_speed_signal'])
                self.actual_speed_signal.set(config['actual_speed_signal'])
                self.msg_counter1_signal.set(config['msg_counter1_signal'])
                self.msg_counter2_signal.set(config['msg_counter2_signal'])
                self.activate_motor_signal.set(config['activate_motor_signal'])
                self.wakeup_signal.set(config['wakeup_signal'])
                self.msg_crc1_signal.set(config['msg_crc1_signal'])
                self.msg_crc2_signal.set(config['msg_crc2_signal'])
                self.saved_gen_sig_data_id_1 = config['gen_sig_data_id_1']
                self.saved_gen_sig_data_id_2 = config['gen_sig_data_id_2']
                self.gen_sig_data_id_1.delete(0, tk.END)
                self.gen_sig_data_id_1.insert(0, ', '.join(map(str, self.saved_gen_sig_data_id_1)))
                self.gen_sig_data_id_2.delete(0, tk.END)
                self.gen_sig_data_id_2.insert(0, ', '.join(map(str, self.saved_gen_sig_data_id_2)))

                self.signal_details = config.get('signal_details', {})

                # Trigger signal_selected for each signal to load its details
                self.trigger_signal_selected(self.target_speed_signal)
                self.trigger_signal_selected(self.actual_speed_signal)
                self.trigger_signal_selected(self.msg_counter1_signal)
                self.trigger_signal_selected(self.msg_counter2_signal)
                self.trigger_signal_selected(self.activate_motor_signal)
                self.trigger_signal_selected(self.wakeup_signal)
                self.trigger_signal_selected(self.msg_crc1_signal)
                self.trigger_signal_selected(self.msg_crc2_signal)

                # Initialize counters if not already set
                if self.saved_msg_counter1_signal not in self.signal_counters:
                    self.signal_counters[self.saved_msg_counter1_signal] = 0
                if self.saved_msg_counter2_signal not in self.signal_counters:
                    self.signal_counters[self.saved_msg_counter2_signal] = 0

            self.config_file_name = os.path.basename(load_path)
            self.config_name_label.config(text=f"Configuration: {self.config_file_name}")
            messagebox.showinfo("Success", "Configuration loaded successfully")

    def trigger_signal_selected(self, combobox):
        signal_name = combobox.get()
        self.get_signal_info(signal_name)

    def connect_or_disconnect_can(self):
        if self.can_bus:
            self.disconnect_can()
        else:
            self.connect_can()

    def connect_can(self):
        connected = False

        # Try to connect using PEAK CAN
        try:
            self.can_bus = can.interface.Bus(bustype='pcan', channel='PCAN_USBBUS1', bitrate=500000)
            self.can_status.config(text="CAN Connected (PEAK)", bg="green")
            self.connect_button.config(text="Disconnect")
            connected = True
        except Exception as e:
            print(f"PEAK CAN connection error: {e}")

        # Try to connect using Vector VN1611 if PEAK CAN connection failed
        if not connected:
            for channel in range(4):  # Try channels 0, 1, 2, 3
                try:
                    self.can_bus = can.interface.Bus(bustype='vector', channel=channel, bitrate=500000)
                    self.can_status.config(text=f"CAN Connected (Vector VN1611, Channel {channel})", bg="green")
                    self.connect_button.config(text="Disconnect")
                    connected = True
                    break
                except Exception as e:
                    print(f"Vector VN1611 connection error (Channel {channel}): {e}")

        if not connected:
            messagebox.showerror("Error", "Failed to connect to CAN using both PEAK and Vector VN1611 interfaces")
            self.can_status.config(text="CAN Disconnected", bg="red")

    def disconnect_can(self):
        try:
            if self.can_bus:
                self.can_bus.shutdown()
                self.can_bus = None
            self.can_status.config(text="CAN Disconnected", bg="red")
            self.connect_button.config(text="Connect")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to disconnect from CAN: {e}")

    def activate_motor_changed(self, *args):
        if self.can_bus and self.saved_activate_motor_signal in self.signal_details:
            signal_info = self.signal_details[self.saved_activate_motor_signal]
            self.signal_values[self.saved_activate_motor_signal] = self.activate_motor.get()
            self.prepare_signal_data(signal_info, self.activate_motor.get())

    def handle_wakeup_signal(self, *args):
        if self.can_bus and self.saved_wakeup_signal in self.signal_details:
            signal_info = self.signal_details[self.saved_wakeup_signal]
            value = 1 if self.wakeup_signal_active.get() else 0
            self.signal_values[self.saved_wakeup_signal] = value
            self.prepare_signal_data(signal_info, value)

    def send_target_speed(self, event):
        if self.can_bus and self.saved_target_speed_signal in self.signal_details:
            signal_info = self.signal_details[self.saved_target_speed_signal]
            target_speed_value = float(self.target_speed.get())
            self.signal_values[self.saved_target_speed_signal] = target_speed_value
            self.prepare_signal_data(signal_info, target_speed_value)

    def prepare_signal_data(self, signal_info, signal_value):
        message_id = signal_info['message_id']
        if message_id not in self.message_data:
            self.message_data[message_id] = [0] * 8

        data = self.message_data[message_id]

        # Ensure signal_value is an integer for bitwise operations
        if isinstance(signal_value, float):
            signal_value = int(signal_value)

        data = self.set_signal_value_in_message(data, signal_info['start_bit'], signal_info['length'], signal_value, signal_info['byte_order'])

        self.message_data[message_id] = data

    def update_message_counter_and_crc(self, message_id):
        if message_id in self.message_data:
            data = self.message_data[message_id]

            if message_id == self.signal_details[self.saved_msg_counter1_signal]['message_id']:
                counter_info = self.signal_details[self.saved_msg_counter1_signal]
                new_cnt = (self.signal_counters[self.saved_msg_counter1_signal] + 1) % 16
                self.signal_counters[self.saved_msg_counter1_signal] = new_cnt
                data = self.set_signal_value_in_message(data, counter_info['start_bit'], counter_info['length'], new_cnt, counter_info['byte_order'])
                data[7] = self.saved_gen_sig_data_id_1[new_cnt]
                crc_info = self.signal_details[self.saved_msg_crc1_signal]
                crc = self.calculate_crc8h2f(data)
                data = self.set_signal_value_in_message(data, crc_info['start_bit'], crc_info['length'], crc, crc_info['byte_order'])

            if message_id == self.signal_details[self.saved_msg_counter2_signal]['message_id']:
                counter_info = self.signal_details[self.saved_msg_counter2_signal]
                new_cnt = (self.signal_counters[self.saved_msg_counter2_signal] + 1) % 16
                self.signal_counters[self.saved_msg_counter2_signal] = new_cnt
                data = self.set_signal_value_in_message(data, counter_info['start_bit'], counter_info['length'], new_cnt, counter_info['byte_order'])
                data[7] = self.saved_gen_sig_data_id_2[new_cnt]
                crc_info = self.signal_details[self.saved_msg_crc2_signal]
                crc = self.calculate_crc8h2f(data)
                data = self.set_signal_value_in_message(data, crc_info['start_bit'], crc_info['length'], crc, crc_info['byte_order'])

            self.message_data[message_id] = data

    def send_message(self, message_id, data):
        self.update_message_counter_and_crc(message_id)
        msg = can.Message(arbitration_id=message_id, data=data, dlc=8, is_extended_id=False)
        try:
            self.can_bus.send(msg)
            print(f"Message sent: Timestamp: {time.time()}    ID: {message_id:03X}    Data: {msg.data.hex()}")
            self.display_sent_message(msg)  # Display sent message in the CAN messages panel
        except Exception as e:
            print(f"Error sending message: {e}")

    def display_sent_message(self, msg):
        message_id_hex = f"0x{msg.arbitration_id:03X}"
        hex_data = ' '.join(f'{byte:02X}' for byte in msg.data)
        message_details = f"ID {message_id_hex}: {hex_data}"

        if message_id_hex not in self.message_labels:
            label = ttk.Label(self.messages_frame, text=message_details)
            label.pack(anchor='w')
            self.message_labels[message_id_hex] = label
        else:
            self.message_labels[message_id_hex].config(text=message_details)

    def calculate_crc8h2f(self, data):
        poly = 0x2F
        crc = 0xFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if (crc & 0x80) != 0:
                    crc = (crc << 1) ^ poly
                else:
                    crc <<= 1
                crc &= 0xFF
        return crc

    def set_signal_value_in_message(self, data, start_bit, length, value, byte_order):
        data_bytes = bytearray(data)

        if byte_order == 'little_endian':
            for i in range(length):
                byte_index = (start_bit + i) // 8
                bit_index = (start_bit + i) % 8
                if value & (1 << i):
                    data_bytes[byte_index] |= (1 << bit_index)
                else:
                    data_bytes[byte_index] &= ~(1 << bit_index)
        else:  # big_endian
            for i in range(length):
                byte_index = (start_bit + length - 1 - i) // 8
                bit_index = (start_bit + length - 1 - i) % 8
                if value & (1 << i):
                    data_bytes[byte_index] |= (1 << bit_index)
                else:
                    data_bytes[byte_index] &= ~(1 << bit_index)

        return list(data_bytes)

    def can_message_listener(self):
        while True:
            if self.can_bus:
                msg = self.can_bus.recv()
                if msg:
                    self.root.after(0, self.update_message_display, msg)
                time.sleep(0.1)

    def update_message_display(self, msg):
        message_id_hex = f"0x{msg.arbitration_id:03X}"
        hex_data = ' '.join(f'{byte:02X}' for byte in msg.data)
        message_details = f"ID {message_id_hex}: {hex_data}"

        if message_id_hex not in self.message_labels:
            label = ttk.Label(self.messages_frame, text=message_details)
            label.pack(anchor='w')
            self.message_labels[message_id_hex] = label
        else:
            self.message_labels[message_id_hex].config(text=message_details)

    def send_periodic_messages(self):
        while True:
            if self.can_bus:
                for message_id in self.message_data:
                    cycle_time = self.cycle_times.get(message_id, 10) / 1000.0
                    self.send_message(message_id, self.message_data[message_id])
                    time.sleep(cycle_time)


if __name__ == "__main__":
    root = tk.Tk()
    app = CANControlGUI(root)
    root.mainloop()
