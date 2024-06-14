import serial
import serial.tools.list_ports
import csv
import os
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

class SerialData:
    def __init__(self, port, baud_rate, timeout=1):
        self.ser = serial.Serial(port, baud_rate, timeout=timeout)
        self.data = []

    def read_data(self):
        try:
            line = self.ser.readline().decode('utf-8', errors='ignore').strip()
        except UnicodeDecodeError:
            return None
        if line:
            try:
                parts = line.split(', ')
                if len(parts) == 7:
                    timestamp, _, a0, _, co2, _, perc_o = parts
                    return {
                        'timestamp': int(timestamp) / 1000,  # Convert to seconds
                        'A0': int(a0),
                        'CO2': int(co2),
                        '%O': float(perc_o)
                    }
            except ValueError:
                pass
        return None

    def close(self):
        if self.ser.is_open:
            self.ser.close()

class RealTimePlot:
    def __init__(self, root, serial_data):
        self.serial_data = serial_data
        self.fig, self.ax = plt.subplots(3, 1, figsize=(10, 8))
        self.ani = animation.FuncAnimation(self.fig, self.update_plot, interval=1000, save_count=100)
        self.data = []
        self.stop_flag = False  # Flag to stop the animation loop

        self.csv_file = self.get_unique_csv_file('sensor_data.csv')
        self.csv_writer = csv.writer(self.csv_file)
        self.csv_writer.writerow(['Timestamp', 'A0', 'CO2', '%O'])  # Write header only once

        self.setup_ui(root)

    def get_unique_csv_file(self, base_filename):
        filename, file_extension = os.path.splitext(base_filename)
        counter = 1
        unique_filename = base_filename
        while os.path.exists(unique_filename):
            unique_filename = f"{filename}_{counter}{file_extension}"
            counter += 1
        return open(unique_filename, mode='a', newline='')

    def setup_ui(self, root):
        self.canvas = FigureCanvasTkAgg(self.fig, master=root)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)
        self.toolbar = NavigationToolbar2Tk(self.canvas, root)
        self.toolbar.update()
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

    def update_plot(self, frame):
        if self.stop_flag:
            return
        new_data = self.serial_data.read_data()
        if new_data:
            self.data.append(new_data)
            self.save_to_csv(new_data)

            timestamps = [d['timestamp'] for d in self.data]
            a0_values = [d['A0'] for d in self.data]
            co2_values = [d['CO2'] for d in self.data]
            perc_o_values = [d['%O'] for d in self.data]

            self.ax[0].clear()
            self.ax[1].clear()
            self.ax[2].clear()

            self.ax[0].plot(timestamps, a0_values, label='A0')
            self.ax[1].plot(timestamps, co2_values, label='CO2')
            self.ax[2].plot(timestamps, perc_o_values, label='%O')

            self.ax[0].set_ylabel('A0')
            self.ax[1].set_ylabel('CO2')
            self.ax[2].set_ylabel('%O')

            self.ax[2].set_xlabel('Time (s)')

            self.ax[0].legend()
            self.ax[1].legend()
            self.ax[2].legend()

            self.canvas.draw()

    def save_to_csv(self, data):
        self.csv_writer.writerow([datetime.now().isoformat(), data['A0'], data['CO2'], data['%O']])

    def stop(self):
        self.stop_flag = True  # Set flag to stop the animation loop
        self.ani.event_source.stop()

    def close(self):
        self.csv_file.close()
        self.serial_data.close()

def list_serial_ports():
    ports = serial.tools.list_ports.comports()
    return [port.device for port in ports]

def start_plot(root, com_port, baud_rate):
    try:
        serial_data = SerialData(com_port, baud_rate)
        plot = RealTimePlot(root, serial_data)
        return plot
    except serial.SerialException as e:
        messagebox.showerror("Error", f"Could not open serial port {com_port}: {e}")
        return None

def main():
    root = tk.Tk()
    root.title("Real-Time Sensor Data")

    ports = list_serial_ports()
    selected_port = tk.StringVar()
    if ports:
        selected_port.set(ports[0])

    controls_frame = ttk.Frame(root)
    controls_frame.pack(side=tk.TOP, fill=tk.X, pady=5)

    port_label = ttk.Label(controls_frame, text="Select COM Port:")
    port_label.pack(side=tk.LEFT, padx=5)

    port_menu = ttk.Combobox(controls_frame, textvariable=selected_port, values=ports)
    port_menu.pack(side=tk.LEFT, padx=5)

    plot = None

    def on_start():
        nonlocal plot
        if plot:
            messagebox.showwarning("Warning", "Plot is already running.")
            return
        com_port = selected_port.get()
        if com_port:
            plot = start_plot(root, com_port, 115200)
        else:
            messagebox.showwarning("Warning", "Please select a COM port.")

    def on_stop():
        nonlocal plot
        if plot:
            if messagebox.askyesno("Confirm Exit", "Do you really want to stop the program?"):
                plot.stop()
                plot.close()
                plot = None
                root.quit()

    start_button = ttk.Button(controls_frame, text="Start", command=on_start)
    start_button.pack(side=tk.LEFT, padx=5)

    stop_button = ttk.Button(controls_frame, text="Stop", command=on_stop)
    stop_button.pack(side=tk.LEFT, padx=5)

    def on_closing():
        if plot:
            plot.stop()
            plot.close()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()
