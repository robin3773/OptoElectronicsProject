import time
import serial
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import warnings
import numpy as np
import random
from func_utils import connect_serial
from multiprocessing import Process, Value, Queue
import socket
import threading
import multiprocessing as mp
from itertools import islice



def start_socket_server(server_address, server_port, queue):
    # Create a socket object
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #server_socket.setblocking(0)

    try:
        server_socket.bind((server_address, server_port))
    except OSError:
        server_socket.close()
        exit()

    # Listen for incoming connections
    server_socket.listen()

    # Start the server loop
    while True:
        # Wait for a client connection
        client_socket, client_address = server_socket.accept()

        # Print a message indicating that a client has connected
        print(f'Client connected from {client_address}')

        # Receive and process data from the client
        while True:
            socket_data = client_socket.recv(1024)
            if not socket_data:
                break
            # Process the received data here
            #print(f'Received data: {socket_data.decode()}')
            queue.put(float(socket_data.decode()))

        # Close the client socket when done
        client_socket.close()




class AnimationPlot:
    def __init__(self, serial_connection, queue):
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
                #print("I = ", self.led_current)
               # print(received_data, self.luminous_intensity)
        except:
            warnings.warn("Corrupted Data Received")
            pass

        self.led_current = self.led_current[-50:]
        self.led_voltage = self.led_voltage[-50:]
        
    
        
    def animate(self, i):
        self.extract_serial_data()
        temp = queue.get()
        
        self.luminous_intensity.append(temp)
        self.get_plot_format()
        self.luminous_intensity = list(islice(reversed(self.luminous_intensity), 0, len(self.led_current)))
        self.luminous_intensity.reverse()

        print(self.led_current[-1:], temp)
        self.ax1.plot(self.led_voltage, self.led_current, color='m', linewidth=2)
        self.ax2.plot(self.led_current, self.luminous_intensity, color = 'c')

    def get_plot_format(self):
        self.ax1.clear()
        self.ax2.clear()
        self.ax1.set_ylim([-0.5, 1])
        self.ax1.set_xlim([0.5, 3.5])
        self.ax1.set_title("IV Curve")
        self.ax1.set_ylabel("I (mA)")
        self.ax1.set_xlabel("Voltage (V)")
        self.ax1.grid(color='g', linestyle='--', linewidth=0.5)

        self.ax2.set_xlim([0, 1])
        self.ax2.autoscale_view()
        self.ax2.set_title("LI Curve")
        self.ax2.set_xlabel("I (mA)")
        self.ax2.set_ylabel("Power")
        self.ax2.grid(color='g', linestyle='--', linewidth=0.5)


    def run(self):
        ani = animation.FuncAnimation(self.fig, self.animate, frames=165, interval=1, blit=True)
        plt.show()


if __name__ == "__main__":
    try:
        queue = Queue()
        time.sleep(1)
        t1 = Process(target=start_socket_server, args=('localhost', 12345, queue, ))
        t1.start()

        serialConnection = connect_serial(serialPort='/dev/ttyACM0')
        realTimePlot = AnimationPlot(serialConnection, queue=queue)
        realTimePlot.run()
        t1.terminate()
        t1.join()
    except KeyboardInterrupt: 
        print("Inside Except")
        for child in mp.active_children():
            child.kill()
