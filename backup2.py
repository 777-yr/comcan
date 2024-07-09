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
        self.crc_enabled = tk.BooleanVar()
        self.activate_motor = tk.BooleanVar()
        self.crc_enabled.trace_add('write', self.crc_checkbox_changed)
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

        # Control Window
        control_frame = ttk.LabelFrame(self.root, text="Control")
        control_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.config_name_label = ttk.Label(control_frame, text=f"Configuration: {self.config_file_name}")
        self.config_name_label.grid(row=0, column=0, columnspan=2, padx=5, pady=5)
        
        self.can_status = tk.Label(control_frame, text="CAN Disconnected", bg="red", width=20)
        self.can_status.grid(row=1, column=0, padx=5, pady=5)
        
        self.connect_button = ttk.Button(control_frame, text="Connect", command=self.connect_or_disconnect_can)
        self.connect_button.grid(row=1, column=1, padx=5, pady=5)
        
        ttk.Label(control_frame, text="Target Speed:").grid(row=2, column=0, padx=5, pady=5, sticky="e")
        self.target_speed = ttk.Entry(control_frame)
        self.target_speed.grid(row=2, column=1, padx=5, pady=5)
        
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
        
        # CRC Checkbox
        self.crc_checkbox = ttk.Checkbutton(control_frame, text="CRC", variable=self.crc_enabled)
        self.crc_checkbox.grid(row=7, column=0, columnspan=2, pady=5)
        
        # Wakeup Signal Dropdown
        ttk.Label(control_frame, text="Wakeup Signal:").grid(row=8, column=0, padx=5, pady=5, sticky="e")
        self.wakeup_signal_value = ttk.Combobox(control_frame, width=20)
        self.wakeup_signal_value.grid(row=8, column=1, padx=5, pady=5)
        
        ttk.Button(control_frame, text="Configure", command=self.open_configure_window).grid(row=9, column=0, columnspan=2, pady=10)

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
        
        ttk.Label(config_window, text="Actual Speed Signal:").grid(row=2, column=0, padx=5, pady=5, sticky="e")
        self.actual_speed_signal = ttk.Combobox(config_window, width=47)
        self.actual_speed_signal.grid(row=2, column=1, padx=5, pady=5)

        ttk.Label(config_window, text="Message Counter 1 Signal:").grid(row=3, column=0, padx=5, pady=5, sticky="e")
        self.msg_counter1_signal = ttk.Combobox(config_window, width=47)
        self.msg_counter1_signal.grid(row=3, column=1, padx=5, pady=5)

        ttk.Label(config_window, text="Message Counter 2 Signal:").grid(row=4, column=0, padx=5, pady=5, sticky="e")
        self.msg_counter2_signal = ttk.Combobox(config_window, width=47)
        self.msg_counter2_signal.grid(row=4, column=1, padx=5, pady=5)

        ttk.Label(config_window, text="Activate Motor Signal:").grid(row=5, column=0, padx=5, pady=5, sticky="e")
        self.activate_motor_signal = ttk.Combobox(config_window, width=47)
        self.activate_motor_signal.grid(row=5, column=1, padx=5, pady=5)

        ttk.Label(config_window, text="Wakeup Signal:").grid(row=6, column=0, padx=5, pady=5, sticky="e")
        self.wakeup_signal = ttk.Combobox(config_window, width=47)
        self.wakeup_signal.grid(row=6, column=1, padx=5, pady=5)

        ttk.Label(config_window, text="MsgCRC1 Signal:").grid(row=7, column=0, padx=5, pady=5, sticky="e")
        self.msg_crc1_signal = ttk.Combobox(config_window, width=47)
        self.msg_crc1_signal.grid(row=7, column=1, padx=5, pady=5)

        ttk.Label(config_window, text="MsgCRC2 Signal:").grid(row=8, column=0, padx=5, pady=5, sticky="e")
        self.msg_crc2_signal = ttk.Combobox(config_window, width=47)
        self.msg_crc2_signal.grid(row=8, column=1, padx=5, pady=5)

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

        # Update wakeup signal values in the control window
        wakeup_signal_values = self.get_signal_values(self.saved_wakeup_signal)
        self.wakeup_signal_value['values'] = wakeup_signal_values

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
            messagebox.showinfo("Success", "DBC file loaded successfully")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load DBC file: {e}")

    def get_signal_values(self, signal_name):
        values = []
        if self.db:
            for message in self.db.messages:
                for signal in message.signals:
                    if signal.name == signal_name:
                        if hasattr(signal, 'choices'):
                            values = [f"{key}: {value}" for key, value in signal.choices.items()]
                        break
        return values

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
            'gen_sig_data_id_2': self.saved_gen_sig_data_id_2
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

                # Initialize counters if not already set
                if self.saved_msg_counter1_signal not in self.signal_counters:
                    self.signal_counters[self.saved_msg_counter1_signal] = 0
                if self.saved_msg_counter2_signal not in self.signal_counters:
                    self.signal_counters[self.saved_msg_counter2_signal] = 0

            self.config_file_name = os.path.basename(load_path)
            self.config_name_label.config(text=f"Configuration: {self.config_file_name}")
            messagebox.showinfo("Success", "Configuration loaded successfully")

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
        except Exception:
            pass

        # Try to connect using Vector VN1611 if PEAK CAN connection failed
        if not connected:
            for channel in range(4):  # Try channels 0, 1, 2, 3
                try:
                    self.can_bus = can.interface.Bus(bustype='vector', app_name='CANoe', channel=channel, bitrate=500000)
                    self.can_status.config(text=f"CAN Connected (Vector VN1611, Channel {channel})", bg="green")
                    self.connect_button.config(text="Disconnect")
                    connected = True
                    break
                except Exception as e:
                    self.can_status.config(text="CAN Disconnected", bg="red")

        if not connected:
            messagebox.showerror("Error", "Failed to connect to CAN using both PEAK and Vector VN1611 interfaces")

    def disconnect_can(self):
        try:
            if self.can_bus:
                self.can_bus.shutdown()
                self.can_bus = None
            self.can_status.config(text="CAN Disconnected", bg="red")
            self.connect_button.config(text="Connect")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to disconnect from CAN: {e}")

    def crc_checkbox_changed(self, *args):
        if self.crc_enabled.get():
            self.start_crc_sending()
        else:
            self.stop_crc_sending()

    def activate_motor_changed(self, *args):
        if self.can_bus and self.db and self.saved_activate_motor_signal:
            self.send_message(self.saved_activate_motor_signal, self.activate_motor.get())

    def start_crc_sending(self):
        self.stop_crc_event = threading.Event()
        self.crc_thread = threading.Thread(target=self.send_crc_messages)
        self.crc_thread.start()

    def stop_crc_sending(self):
        if hasattr(self, 'stop_crc_event'):
            self.stop_crc_event.set()
            self.crc_thread.join()

    def send_crc_messages(self):
        while not self.stop_crc_event.is_set():
            self.send_message(self.saved_msg_counter1_signal, self.saved_msg_crc1_signal, self.saved_gen_sig_data_id_1)
            self.send_message(self.saved_msg_counter2_signal, self.saved_msg_crc2_signal, self.saved_gen_sig_data_id_2)
            time.sleep(1)  # Adjust the sending interval as needed

    def send_message(self, counter_signal, crc_signal, gen_sig_data_id):
        if not self.db:
            return

        message_name = self.get_message_name_by_signal(crc_signal)
        if not message_name:
            return

        message = self.db.get_message_by_name(message_name)
        if not message:
            return

        data = [0] * 8
        counter_value = self.get_signal_counter_value(counter_signal)
        newCnt = (counter_value + 1) % 16
        data[0] = (data[0] & 0xf0) | newCnt
        data[1:] = [0] * 6  # Update with actual data bytes as needed
        data[7] = gen_sig_data_id[newCnt]
        crc = self.calculate_crc8h2f(data)
        data[7] = crc
        self.set_signal_counter_value(counter_signal, newCnt)
        msg = can.Message(arbitration_id=message.frame_id, data=data)
        self.can_bus.send(msg)

    def get_message_name_by_signal(self, signal_name):
        for message in self.db.messages:
            for signal in message.signals:
                if signal.name == signal_name:
                    return message.name
        return None

    def get_signal_counter_value(self, signal_name):
        return self.signal_counters.get(signal_name, 0)

    def set_signal_counter_value(self, signal_name, value):
        self.signal_counters[signal_name] = value

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

if __name__ == "__main__":
    root = tk.Tk()
    app = CANControlGUI(root)
    root.mainloop()
