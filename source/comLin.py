import tkinter as tk
from tkinter import ttk, filedialog, messagebox, Toplevel
import can
import json
import os
import threading
import time

class LINControlGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("LIN Control GUI")

        # CAN bus setup (simulating LIN)
        self.can_bus = None
        self.ldf = None
        self.config_file_name = "N/A"

        # Configuration state variables
        self.saved_ldf_file_path = ""

        # Control Window
        control_frame = ttk.LabelFrame(self.root, text="Control")
        control_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.messages_frame = ttk.LabelFrame(self.root, text="LIN Messages")
        self.messages_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.message_labels = {}  # Dictionary to store labels for each message ID

        self.config_name_label = ttk.Label(control_frame, text=f"Configuration: {self.config_file_name}")
        self.config_name_label.grid(row=0, column=0, columnspan=2, padx=5, pady=5)

        self.lin_status = tk.Label(control_frame, text="LIN Disconnected", bg="red", width=20)
        self.lin_status.grid(row=1, column=0, padx=5, pady=5)

        self.connect_button = ttk.Button(control_frame, text="Connect", command=self.connect_or_disconnect_lin)
        self.connect_button.grid(row=1, column=1, padx=5, pady=5)

        ttk.Button(control_frame, text="Configure", command=self.open_configure_window).grid(row=2, column=0, columnspan=2, pady=10)

        # Start CAN message listener (simulating LIN)
        self.listener_thread = threading.Thread(target=self.lin_message_listener)
        self.listener_thread.daemon = True
        self.listener_thread.start()

        # Start periodic message sender
        self.periodic_thread = threading.Thread(target=self.send_periodic_messages)
        self.periodic_thread.daemon = True
        self.periodic_thread.start()

    def open_configure_window(self):
        config_window = Toplevel(self.root)
        config_window.title("Configuration")

        ttk.Label(config_window, text="Select LDF File:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.ldf_file_path = tk.StringVar(value=self.saved_ldf_file_path)
        ttk.Entry(config_window, textvariable=self.ldf_file_path, width=50).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(config_window, text="Browse", command=self.browse_file).grid(row=0, column=2, padx=5, pady=5)

        ttk.Button(config_window, text="Save Configuration", command=self.save_configuration).grid(row=1, column=0, padx=5, pady=5)
        ttk.Button(config_window, text="Load Configuration", command=self.load_configuration).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(config_window, text="Close", command=lambda: self.close_config_window(config_window)).grid(row=2, column=0, columnspan=3, pady=10)

        if self.ldf:
            self.config_name_label.config(text=f"Configuration: {self.config_file_name}")

    def close_config_window(self, window):
        # Save the current configuration to the main GUI
        self.saved_ldf_file_path = self.ldf_file_path.get()
        
        if self.config_file_name == "N/A":
            self.config_file_name = "Spontaneous Configuration"
        self.config_name_label.config(text=f"Configuration: {self.config_file_name}")

        window.destroy()

    def browse_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("LDF Files", "*.ldf")])
        if file_path:
            self.ldf_file_path.set(file_path)
            self.load_ldf(file_path)

    def load_ldf(self, file_path):
        try:
            with open(file_path, 'r') as file:
                self.ldf = file.read()
            messagebox.showinfo("Success", "LDF file loaded successfully")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load LDF file: {e}")

    def save_configuration(self):
        config = {
            'ldf_file': self.ldf_file_path.get()
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
                self.ldf_file_path.set(config['ldf_file'])
                self.load_ldf(config['ldf_file'])

            self.config_file_name = os.path.basename(load_path)
            self.config_name_label.config(text=f"Configuration: {self.config_file_name}")
            messagebox.showinfo("Success", "Configuration loaded successfully")

    def connect_or_disconnect_lin(self):
        if self.can_bus:
            self.disconnect_lin()
        else:
            self.connect_lin()

    def connect_lin(self):
        try:
            self.can_bus = can.interface.Bus(bustype='socketcan', channel='can0', bitrate=19200)
            self.lin_status.config(text="LIN Connected", bg="green")
            self.connect_button.config(text="Disconnect")
        except Exception as e:
            print(f"LIN connection error: {e}")
            messagebox.showerror("Error", "Failed to connect to LIN bus")
            self.lin_status.config(text="LIN Disconnected", bg="red")

    def disconnect_lin(self):
        try:
            if self.can_bus:
                self.can_bus.shutdown()
                self.can_bus = None
            self.lin_status.config(text="LIN Disconnected", bg="red")
            self.connect_button.config(text="Connect")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to disconnect from LIN: {e}")

    def lin_message_listener(self):
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
                # Implement periodic message sending logic based on the loaded LDF
                pass
            time.sleep(1)


if __name__ == "__main__":
    root = tk.Tk()
    app = LINControlGUI(root)
    root.mainloop()
