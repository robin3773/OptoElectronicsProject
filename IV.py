import time
import serial
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import warnings
import numpy as np
import random
from func_utils import connect_serial
from multiprocessing import Process


class AnimationPlot:
    def __init__(self, serial_connection):
        self.led_current = []
        self.led_voltage = []
        self.luminous_intensity = []
        self.fig = plt.figure(num=1, figsize=(10, 10), tight_layout=True)
        self.ax1 = self.fig.add_subplot(211)
        self.ax2 = self.fig.add_subplot(212)
        self.serial_connection = serial_connection

    def extract_serial_data(self):
        value = bytes([v for v in self.serial_connection.readline() if v in range(1, 127)])
        value = value.decode().strip()
        value = value.split()

        try:
            if len(value) == 3:
                received_data = [float(V) / 1000000 for V in value]
                V1, V2, I = received_data
                self.led_current.append(I)
                self.led_voltage.append(V2)
                self.luminous_intensity.append(intensity)
                #print(received_data)
        except:
            warnings.warn("Corrupted Data Received")
            pass

        self.led_current = self.led_current[-50:]
        self.led_voltage = self.led_voltage[-50:]

    def animate(self, i):
        self.extract_serial_data()
        self.get_plot_format()
        self.ax1.plot(self.led_voltage, self.led_current, color='m', linewidth=2)
        # self.ax2.plot(self.led_current, self.luminous_intensity, color = 'c')

    def get_plot_format(self):
        self.ax1.clear()
        self.ax2.clear()
        self.ax1.set_ylim([-0.5, 1])
        self.ax1.set_xlim([0.5, 3.5])
        self.ax1.set_title("IV Curve")
        self.ax1.set_ylabel("I (mA)")
        self.ax1.set_xlabel("Voltage (V)")
        self.ax1.grid(color='g', linestyle='--', linewidth=0.5)

        self.ax2.set_ylim([0, 1])
        self.ax2.set_xlim([-0.5, 1])
        self.ax2.set_title("LI Curve")
        self.ax2.set_xlabel("I (mA)")
        self.ax2.set_ylabel("Power")
        self.ax2.grid(color='g', linestyle='--', linewidth=0.5)

    def print_value(self):
        print("V = ", self.led_voltage)
        print("I = ", self.led_current)

    def run(self):
        ani = animation.FuncAnimation(self.fig, self.animate, frames=10000, interval=10, blit=True)
        plt.show(block = False)


def main_program():
    ser = connect_serial()
    r = AnimationPlot(ser)
    r.run()


if __name__ == "__main__":
    intensity = 1
    serialConnection = connect_serial()
    realTimePlot = AnimationPlot(serialConnection)

    p = Process(target=realTimePlot.run())
    p.start()
    main_program()
    p.join()
