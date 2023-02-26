import cv2
import time
import base64
from scipy import integrate
import argparse
import numpy as np
import matplotlib.pyplot as plt
from specFunctions import wavelength_to_rgb, savitzky_golay, peakIndexes, readcal, writecal, background, \
    generateGraticule
from func_utils import *
from IV import *
import threading
from multiprocessing import Process
from IV import AnimationPlot
import socket 

import socket
import time

def create_socket(server_address = 'localhost', server_port=12345):
    # Create a socket object
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Connect to the server
    client_socket.connect((server_address, server_port))

    return client_socket


class PySpectrometer:
    def __init__(self, device_id, fps, display_fullscreen):
        self.spectrum_vertical = None
        self.fifties = None
        self.graticuleData = None
        self.cal_msg3 = None
        self.cal_msg2 = None
        self.cal_msg1 = None
        self.wavelengthData = None
        self.cal_data = None
        self.c_fps = None
        self.fps = fps
        self.dev = device_id
        self.cap = None
        self.tens = None
        self.display_fullscreen = display_fullscreen
        self.hold_msg = None
        self.data = None
        self.cols = None
        self.rows = None
        self.cropped = None
        self.bw_image = None
        self.frame = None
        self.ret = None
        self.mouseY = None
        self.mouseX = None
        self.cal_complete = None
        self.save_data = None
        self.graph_data = None
        self.keyPress = None
        self.video_window_title = "Spectrograph"
        self.frameWidth = 800
        self.frameHeight = 600
        self.font = cv2.FONT_HERSHEY_SIMPLEX

        self.calibrate = False
        self.hold_peaks = False  # are we holding peaks?
        self.measure = False  # are we measuring?
        self.recPixels = False  # are we measuring pixels and recording clicks?

        # settings for peak detect
        self.sav_poly = 7  # savgol filter polynomial max val 15
        self.min_dist = 50  # minimum distance between peaks max val 100
        self.thresh = 20  # Threshold max val 100

        self.clickArray = []
        self.cursorX = 0
        self.cursorY = 0
        # listen for click on plot window

        self.intensity = [0] * self.frameWidth  # array for intensity data...full of zeroes

        # messages
        self.msg1 = ""
        self.saveMsg = "No data saved"

        # blank image for Graph
        self.graph = np.zeros([320, self.frameWidth, 3], dtype=np.uint8)
        self.graph.fill(255)  # fill white

    def grab_cal_data(self):
        # Go grab the computed calibration data
        self.cal_data = readcal(self.frameWidth)
        self.wavelengthData = self.cal_data[0]
        self.cal_msg1 = self.cal_data[1]
        self.cal_msg2 = self.cal_data[2]
        self.cal_msg3 = self.cal_data[3]

    def setup_graticule(self):
        # generate the graticule data
        self.graticuleData = generateGraticule(self.wavelengthData)
        self.tens = (self.graticuleData[0])
        self.fifties = (self.graticuleData[1])

    def setup(self):
        self.sock_obj = create_socket()
        self.cap, self.c_fps = init_video(self.display_fullscreen, self.video_window_title, self.frameWidth,
                                          self.frameHeight, self.fps, self.dev)
        cv2.setMouseCallback(self.video_window_title, self.handle_mouse)
        self.grab_cal_data()
        self.setup_graticule()

    def handle_keypress(self):
        self.keyPress = cv2.waitKey(1)
        if self.keyPress == ord('q'):
            self.quit_program()
        elif self.keyPress == ord('h'):
            if not self.hold_peaks:
                self.hold_peaks = True
            elif self.hold_peaks:
                self.hold_peaks = False
        elif self.keyPress == ord("s"):
            # package up the data!
            self.graph_data = [self.wavelengthData, self.intensity]
            self.save_data = [self.spectrum_vertical, self.graph_data]
            self.saveMsg = snapshot(self.save_data)
        elif self.keyPress == ord("c"):
            self.cal_complete = writecal(self.clickArray)
            if self.cal_complete:
                # overwrite wavelength data
                # Go grab the computed calibration data
                self.grab_cal_data()
                # overwrite graticule data
                self.setup_graticule()
        elif self.keyPress == ord("x"):
            self.clickArray = []
        elif self.keyPress == ord("m"):
            self.recPixels = False  # turn off rec_pixels!
            if not self.measure:
                self.measure = True
            elif self.measure:
                self.measure = False
        elif self.keyPress == ord("p"):
            self.measure = False  # turn off measure!
            if not self.recPixels:
                self.recPixels = True
            elif self.recPixels:
                self.recPixels = False
        elif self.keyPress == ord("o"):  # sav up
            self.sav_poly += 1
            if self.sav_poly >= 15:
                self.sav_poly = 15
        elif self.keyPress == ord("l"):  # sav down
            self.sav_poly -= 1
            if self.sav_poly <= 0:
                self.sav_poly = 0
        elif self.keyPress == ord("i"):  # Peak width up
            self.min_dist += 1
            if self.min_dist >= 100:
                self.min_dist = 100
        elif self.keyPress == ord("k"):  # Peak Width down
            self.min_dist -= 1
            if self.min_dist <= 0:
                self.min_dist = 0
        elif self.keyPress == ord("u"):  # label thresh up
            self.thresh += 1
            if self.thresh >= 100:
                self.thresh = 100
        elif self.keyPress == ord("j"):  # label thresh down
            self.thresh -= 1
            if self.thresh <= 0:
                self.thresh = 0

    def handle_mouse(self, event, x, y, flags, param):
        mouseYOffset = 160
        if event == cv2.EVENT_MOUSEMOVE:
            self.cursorX = x
            self.cursorY = y
        if event == cv2.EVENT_LBUTTONDOWN:
            self.mouseX = x
            self.mouseY = y - mouseYOffset
            self.clickArray.append([self.mouseX, self.mouseY])

    def display_graticule_line(self):
        # Display a graticule calibrated with cal data
        text_offset = 12
        # vertical lines every whole 10nm
        for position in self.tens:
            cv2.line(self.graph, (position, 15), (position, 320), (200, 200, 200), 1)

        # vertical lines every whole 50nm
        for position_data in self.fifties:
            cv2.line(self.graph, (position_data[0], 15), (position_data[0], 320), (0, 0, 0), 1)
            cv2.putText(self.graph, str(position_data[1]) + 'nm', (position_data[0] - text_offset, 12), self.font, 0.4,
                        (0, 0, 0), 1, cv2.LINE_AA)

        # horizontal lines
        for i in range(320):
            if i >= 64:
                if i % 64 == 0:  # suppress the first line then draw the rest...
                    cv2.line(self.graph, (0, i), (self.frameWidth, i), (100, 100, 100), 1)

    def process_plot_intensity(self, halfway):
        # intensity = []
        for i in range(self.cols):
            # data = bwimage[halfway,i] #pull the pixel data from the halfway mark
            # print(type(data)) #numpy.uint8
            # average the data of 3 rows of pixels:
            data_minus_1 = self.bw_image[halfway - 1, i]
            data_zero = self.bw_image[halfway, i]  # pull the pixel data from the halfway mark
            data_plus_1 = self.bw_image[halfway + 1, i]
            self.data = (int(data_minus_1) + int(data_zero) + int(data_plus_1)) / 3
            self.data = np.uint8(self.data)

            if self.hold_peaks:
                if self.data > self.intensity[i]:
                    self.intensity[i] = self.data
            else:
                self.intensity[i] = self.data

        # Draw the intensity data :-)
        # first filter if not holding peaks!
        if not self.hold_peaks:
            self.intensity = savitzky_golay(self.intensity, 17, self.sav_poly)
            self.intensity = np.array(self.intensity)
            self.intensity = self.intensity.astype(int)
            self.hold_msg = "Hold-peaks OFF"
        else:
            self.hold_msg = "Hold-peaks ON"

        # now draw the intensity data....
        index = 0
        for i in self.intensity:
            # derive the color from the  wavelengthData array
            rgb = wavelength_to_rgb(round(self.wavelengthData[index]))
            r, g, b = rgb[0], rgb[1], rgb[2]
            # or some reason origin is top left.
            cv2.line(self.graph, (index, 320), (index, 320 - i), (b, g, r), 1)
            cv2.line(self.graph, (index, 319 - i), (index, 320 - i), (0, 0, 0), 1, cv2.LINE_AA)
            index += 1

    def find_label_peaks(self):
        text_offset = 12
        self.thresh = int(self.thresh)  # make sure the data is int.
        indexes = peakIndexes(self.intensity, thres=self.thresh / max(self.intensity), min_dist=self.min_dist)
        # print(indexes)
        for i in indexes:
            height = self.intensity[i]
            height = 310 - height
            wavelength = round(self.wavelengthData[i], 1)
            cv2.rectangle(self.graph, ((i - text_offset) - 2, height), ((i - text_offset) + 60, height - 15),
                          (0, 255, 255),
                          -1)
            cv2.rectangle(self.graph, ((i - text_offset) - 2, height), ((i - text_offset) + 60, height - 15),
                          (0, 0, 0), 1)
            cv2.putText(self.graph, str(wavelength) + 'nm', (i - text_offset, height - 3), self.font, 0.4, (0, 0, 0), 1,
                        cv2.LINE_AA)
            # flagpoles
            cv2.line(self.graph, (i, height), (i, height + 10), (0, 0, 0), 1)

    def display(self, messages):
        self.spectrum_vertical = np.vstack((messages, self.cropped, self.graph))
        # dividing lines...
        cv2.line(self.spectrum_vertical, (0, 80), (self.frameWidth, 80), (255, 255, 255), 1)
        cv2.line(self.spectrum_vertical, (0, 160), (self.frameWidth, 160), (255, 255, 255), 1)
        # print the messages
        cv2.putText(self.spectrum_vertical, self.cal_msg1, (490, 15), self.font, 0.4, (0, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(self.spectrum_vertical, self.cal_msg3, (490, 33), self.font, 0.4, (0, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(self.spectrum_vertical, "Framerate: " + str(self.c_fps), (490, 51), self.font, 0.4, (0, 255, 255),
                    1,
                    cv2.LINE_AA)
        cv2.putText(self.spectrum_vertical, self.saveMsg, (490, 69), self.font, 0.4, (0, 255, 255), 1, cv2.LINE_AA)
        # Second column
        cv2.putText(self.spectrum_vertical, self.hold_msg, (640, 15), self.font, 0.4, (0, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(self.spectrum_vertical, "Savgol Filter: " + str(self.sav_poly), (640, 33), self.font, 0.4,
                    (0, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(self.spectrum_vertical, "Label Peak Width: " + str(self.min_dist), (640, 51), self.font, 0.4,
                    (0, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(self.spectrum_vertical, "Label Threshold: " + str(self.thresh), (640, 69), self.font, 0.4,
                    (0, 255, 255), 1, cv2.LINE_AA)
        cv2.imshow(self.video_window_title, self.spectrum_vertical)

        data = str(integrate.simpson(np.array(self.intensity)/256, np.array(self.wavelengthData)))

        try:
            print("Sending L  = ", data)
            self.sock_obj.send(data.encode())
        except: 
            pass
        

    def run(self):
        self.setup()
        while self.cap.isOpened():
            # Capture frame-by-frame
            self.ret, self.frame = self.cap.read()
            # cv2.imshow("Original Image", frame)
            # cv2.line(frame, (0, 300), (800, 300), (0, 255, 0))
            self.frame = rotate(self.frame, -40)
            # cv2.imshow("Rotated Image", frame)
            if self.ret:
                y = int((self.frameHeight / 2) - 40)  # origin of the vertical crop
                y = 50  # origin of the vert crop
                x = 0  # origin of the horiz crop
                h = 100  # height of the crop
                w = self.frameWidth  # width of the crop
                self.cropped = self.frame[y:y + h, x:x + w]
                # cv2.imshow("Cropped_Image", cropped)
                self.bw_image = cv2.cvtColor(self.cropped, cv2.COLOR_BGR2GRAY)
                self.rows, self.cols = self.bw_image.shape
                halfway = int(self.rows / 2)
                # show our line on the original image
                # now a 3px wide region
                cv2.line(self.cropped, (0, halfway - 2), (self.frameWidth, halfway - 2), (255, 255, 255), 1)
                cv2.line(self.cropped, (0, halfway + 2), (self.frameWidth, halfway + 2), (255, 255, 255), 1)

                # banner image
                decoded_data = base64.b64decode(background)
                np_data = np.frombuffer(decoded_data, np.uint8)
                img = cv2.imdecode(np_data, 3)
                messages = img

                # blank image for Graph
                self.graph = np.zeros([320, self.frameWidth, 3], dtype=np.uint8)
                self.graph.fill(255)  # fill white

                # Display a graticule calibrated with cal data
                self.display_graticule_line()

                # Now process the intensity data and display it
                self.process_plot_intensity(halfway=halfway)

                # find peaks and label them
                self.find_label_peaks()

                if self.measure:
                    # show the cursor!
                    cv2.line(self.graph, (self.cursorX, self.cursorY - 140),
                             (self.cursorX, self.cursorY - 180), (0, 0, 0), 1)
                    cv2.line(self.graph, (self.cursorX - 20, self.cursorY - 160),
                             (self.cursorX + 20, self.cursorY - 160), (0, 0, 0), 1)
                    cv2.putText(self.graph, str(round(self.wavelengthData[self.cursorX], 2)) + 'nm', (self.cursorX + 5,
                                                                                                      self.cursorY - 165),
                                self.font, 0.4, (0, 0, 0), 1, cv2.LINE_AA)

                if self.recPixels:
                    # display the points
                    cv2.line(self.graph, (self.cursorX, self.cursorY - 140),
                             (self.cursorX, self.cursorY - 180), (0, 0, 0), 1)
                    cv2.line(self.graph, (self.cursorX - 20, self.cursorY - 160),
                             (self.cursorX + 20, self.cursorY - 160), (0, 0, 0), 1)
                    cv2.putText(self.graph, str(self.cursorX) + 'px', (self.cursorX + 5, self.cursorY - 165), self.font,
                                0.4, (0, 0, 0), 1, cv2.LINE_AA)
                else:
                    # also make sure the click array stays empty
                    self.clickArray = []

                if self.clickArray:
                    for data in self.clickArray:
                        self.mouseX = data[0]
                        self.mouseY = data[1]
                        cv2.circle(self.graph, (self.mouseX, self.mouseY), 5, (0, 0, 0), -1)
                        # we can display text :-) so we can work out wavelength from x-pos and display it ultimately
                        cv2.putText(self.graph, str(self.mouseX), (self.mouseX + 5, self.mouseY),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.4,
                                    (0, 0, 0))

                # stack the images and display the spectrum
                self.display(messages=messages)

                self.handle_keypress()

            else:
                break
        self.quit_program()

        return self.intensity, self.wavelengthData

    def quit_program(self):
        # Everything done, release the vid
        self.cap.release()
        cv2.destroyAllWindows()
        self.sock_obj.close()


if __name__ == '__main__':
    spec = PySpectrometer(device_id=0, fps=30, display_fullscreen=False)
    intensity, wavelength = spec.run()

