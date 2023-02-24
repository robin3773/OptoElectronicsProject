import time
import serial
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import warnings
import numpy as np



dataList1, dataList2 = [], []                                         
                                                        
fig = plt.figure()                                     
ax = fig.add_subplot(111)   

class AnimationPlot:
    def animate(self, i, dataList1, dataList2, ser):  
        value = bytes([v for v in serialConnection.readline() if v in range(1,127)])
        value = value.decode().strip()
        value = value.split()

        try:
            if len(value) == 3:
                received_data = [float(V)/1000000 for V in value]
                V1, V2, I = received_data   
                dataList1.append(I)
                dataList2.append(V2)
                print(received_data)  

        except:                                          
            warnings.warn("Corrupted Data Received")                 
            pass   

        dataList1 = dataList1[-500:]    
        dataList2 = dataList2[-500:]                       
        
        ax.clear()                                         
        
        self.getPlotFormat()
        ax.plot(dataList2, dataList1, color = 'm')                       
        

    def getPlotFormat(self):
        ax.set_ylim([-0.5, 4])    
        ax.set_xlim([0.5, 2])                          
        ax.set_title("IV Curve")                        
        ax.set_ylabel("I (mA)")   
        ax.set_xlabel("Voltage (V)")
        ax.grid(color = 'g', linestyle = '--', linewidth= 0.5)

           


realTimePlot = AnimationPlot()
serialBaud = 9600
serialPort = '/dev/ttyACM0'
print('Trying to connect to: ' + str(serialPort) + ' at ' + str(serialBaud) + ' BAUD.')
try:
    serialConnection = serial.Serial(serialPort, serialBaud, timeout=6)
    print('Connected to ' + str(serialPort) + ' at ' + str(serialBaud) + ' BAUD.')
except:
    print("Failed to connect with " + str(serialPort) + ' at ' + str(serialBaud) + ' BAUD.')

time.sleep(2)                                       

                                                       
ani = animation.FuncAnimation(fig, realTimePlot.animate, frames=10000, fargs=(dataList1, dataList2, serialConnection), interval=10, blit = True) 
plt.show()                                   