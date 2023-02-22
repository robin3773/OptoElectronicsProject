import cv2
import time
import base64
import argparse
import numpy as np
import matplotlib.pyplot as plt
from specFunctions import wavelength_to_rgb,savitzky_golay,peakIndexes,readcal,writecal,background,generateGraticule
from func_utils import *


def handle_mouse(event,x,y,flags,param):
	global clickArray
	global cursorX
	global cursorY
	mouseYOffset = 160
	if event == cv2.EVENT_MOUSEMOVE:
		cursorX = x
		cursorY = y	
	if event == cv2.EVENT_LBUTTONDOWN:
		mouseX = x
		mouseY = y-mouseYOffset
		clickArray.append([mouseX,mouseY])

video_window_title = "Spectrograph"
frameWidth = 800
frameHeight = 600
font=cv2.FONT_HERSHEY_SIMPLEX

calibrate = False
holdpeaks = False #are we holding peaks?
measure = False #are we measuring?
recPixels = False #are we measuring pixels and recording clicks?

#settings for peak detect
savpoly = 7 #savgol filter polynomial max val 15
mindist = 50 #minumum distance between peaks max val 100
thresh = 20 #Threshold max val 100

clickArray = [] 
cursorX = 0
cursorY = 0
#listen for click on plot window


intensity = [0] * frameWidth #array for intensity data...full of zeroes



dispFullscreen, dev, fps = command_line_argument()
cap, cfps = init_video(dev, dispFullscreen, video_window_title, frameWidth, frameHeight, fps)
cv2.setMouseCallback(video_window_title,handle_mouse)

#messages
msg1 = ""
saveMsg = "No data saved"

#Go grab the computed calibration data
caldata = readcal(frameWidth)
wavelengthData = caldata[0]
calmsg1 = caldata[1]
calmsg2 = caldata[2]
calmsg3 = caldata[3]

#generate the craticule data
graticuleData = generateGraticule(wavelengthData)
tens = (graticuleData[0])
fifties = (graticuleData[1])


while(cap.isOpened()):
	# Capture frame-by-frame
	ret, frame = cap.read()
	#cv2.imshow("Original Image", frame)
	#cv2.line(frame, (0, 300), (800, 300), (0, 255, 0))
	frame = rotate(frame, -40)
	#cv2.imshow("Rotated Image", frame)
	if ret == True:
		y=int((frameHeight/2)-40) #origin of the vertical crop
		y=180	#origin of the vert crop
		x=0   	#origin of the horiz crop
		h=200 	#height of the crop
		w=frameWidth 	#width of the crop
		cropped = frame[y:y+h, x:x+w]
		#cv2.imshow("Cropped_Image", cropped)
		bwimage = cv2.cvtColor(cropped,cv2.COLOR_BGR2GRAY)
		rows,cols = bwimage.shape
		halfway =int(rows/2)
		#show our line on the original image
		#now a 3px wide region
		cv2.line(cropped,(0,halfway-2),(frameWidth,halfway-2),(255, 255,255),1)
		cv2.line(cropped,(0,halfway+2),(frameWidth,halfway+2),(255,255,255),1)

		#banner image
		decoded_data = base64.b64decode(background)
		np_data = np.frombuffer(decoded_data,np.uint8)
		img = cv2.imdecode(np_data,3)
		messages = img

		#blank image for Graph
		graph = np.zeros([320,frameWidth,3],dtype=np.uint8)
		graph.fill(255) #fill white

		#Display a graticule calibrated with cal data
		textoffset = 12
		#vertial lines every whole 10nm
		for position in tens:
			cv2.line(graph,(position,15),(position,320),(200,200,200),1)

		#vertical lines every whole 50nm
		for positiondata in fifties:
			cv2.line(graph,(positiondata[0],15),(positiondata[0],320),(0,0,0),1)
			cv2.putText(graph,str(positiondata[1])+'nm',(positiondata[0]-textoffset,12),font,0.4,(0,0,0),1, cv2.LINE_AA)

		#horizontal lines
		for i in range (320):
			if i>=64:
				if i%64==0: #suppress the first line then draw the rest...
					cv2.line(graph,(0,i),(frameWidth,i),(100,100,100),1)
		
		#Now process the intensity data and display it
		#intensity = []
		for i in range(cols):
			#data = bwimage[halfway,i] #pull the pixel data from the halfway mark	
			#print(type(data)) #numpy.uint8
			#average the data of 3 rows of pixels:
			dataminus1 = bwimage[halfway-1,i]
			datazero = bwimage[halfway,i] #pull the pixel data from the halfway mark
			dataplus1 = bwimage[halfway+1,i]
			data = (int(dataminus1)+int(datazero)+int(dataplus1))/3
			data = np.uint8(data)
					
			
			if holdpeaks == True:
				if data > intensity[i]:
					intensity[i] = data
			else:
				intensity[i] = data



		#Draw the intensity data :-)
		#first filter if not holding peaks!
		
		if holdpeaks == False:
			intensity = savitzky_golay(intensity,17,savpoly)
			intensity = np.array(intensity)
			intensity = intensity.astype(int)
			holdmsg = "Holdpeaks OFF" 
		else:
			holdmsg = "Holdpeaks ON"
			
		
		#now draw the intensity data....
		index=0
		for i in intensity:
			rgb = wavelength_to_rgb(round(wavelengthData[index]))#derive the color from the wvalenthData array
			r = rgb[0]
			g = rgb[1]
			b = rgb[2]
			#or some reason origin is top left.
			cv2.line(graph, (index,320), (index,320-i), (b,g,r), 1)
			cv2.line(graph, (index,319-i), (index,320-i), (0,0,0), 1,cv2.LINE_AA)
			index+=1


		#find peaks and label them
		textoffset = 12
		thresh = int(thresh) #make sure the data is int.
		indexes = peakIndexes(intensity, thres=thresh/max(intensity), min_dist=mindist)
		#print(indexes)
		for i in indexes:
			height = intensity[i]
			height = 310-height
			wavelength = round(wavelengthData[i],1)
			cv2.rectangle(graph,((i-textoffset)-2,height),((i-textoffset)+60,height-15),(0,255,255),-1)
			cv2.rectangle(graph,((i-textoffset)-2,height),((i-textoffset)+60,height-15),(0,0,0),1)
			cv2.putText(graph,str(wavelength)+'nm',(i-textoffset,height-3),font,0.4,(0,0,0),1, cv2.LINE_AA)
			#flagpoles
			cv2.line(graph,(i,height),(i,height+10),(0,0,0),1)


		if measure == True:
			#show the cursor!
			cv2.line(graph,(cursorX,cursorY-140),(cursorX,cursorY-180),(0,0,0),1)
			cv2.line(graph,(cursorX-20,cursorY-160),(cursorX+20,cursorY-160),(0,0,0),1)
			cv2.putText(graph,str(round(wavelengthData[cursorX],2))+'nm',(cursorX+5,cursorY-165),font,0.4,(0,0,0),1, cv2.LINE_AA)

		if recPixels == True:
			#display the points
			cv2.line(graph,(cursorX,cursorY-140),(cursorX,cursorY-180),(0,0,0),1)
			cv2.line(graph,(cursorX-20,cursorY-160),(cursorX+20,cursorY-160),(0,0,0),1)
			cv2.putText(graph,str(cursorX)+'px',(cursorX+5,cursorY-165),font,0.4,(0,0,0),1, cv2.LINE_AA)
		else:
			#also make sure the click array stays empty
			clickArray = []

		if clickArray:
			for data in clickArray:
				mouseX=data[0]
				mouseY=data[1]
				cv2.circle(graph,(mouseX,mouseY),5,(0,0,0),-1)
				#we can display text :-) so we can work out wavelength from x-pos and display it ultimately
				cv2.putText(graph,str(mouseX),(mouseX+5,mouseY),cv2.FONT_HERSHEY_SIMPLEX,0.4,(0,0,0))
		

	

		#stack the images and display the spectrum	
		spectrum_vertical = np.vstack((messages,cropped, graph))
		#dividing lines...
		cv2.line(spectrum_vertical,(0,80),(frameWidth,80),(255,255,255),1)
		cv2.line(spectrum_vertical,(0,160),(frameWidth,160),(255,255,255),1)
		#print the messages
		cv2.putText(spectrum_vertical,calmsg1,(490,15),font,0.4,(0,255,255),1, cv2.LINE_AA)
		cv2.putText(spectrum_vertical,calmsg3,(490,33),font,0.4,(0,255,255),1, cv2.LINE_AA)
		cv2.putText(spectrum_vertical,"Framerate: "+str(cfps),(490,51),font,0.4,(0,255,255),1, cv2.LINE_AA)
		cv2.putText(spectrum_vertical,saveMsg,(490,69),font,0.4,(0,255,255),1, cv2.LINE_AA)
		#Second column
		cv2.putText(spectrum_vertical,holdmsg,(640,15),font,0.4,(0,255,255),1, cv2.LINE_AA)
		cv2.putText(spectrum_vertical,"Savgol Filter: "+str(savpoly),(640,33),font,0.4,(0,255,255),1, cv2.LINE_AA)
		cv2.putText(spectrum_vertical,"Label Peak Width: "+str(mindist),(640,51),font,0.4,(0,255,255),1, cv2.LINE_AA)
		cv2.putText(spectrum_vertical,"Label Threshold: "+str(thresh),(640,69),font,0.4,(0,255,255),1, cv2.LINE_AA)
		cv2.imshow(video_window_title,spectrum_vertical)


		keyPress = cv2.waitKey(1)
		if keyPress == ord('q'):
			break
		elif keyPress == ord('h'):
			if holdpeaks == False:
				holdpeaks = True
			elif holdpeaks == True:
				holdpeaks = False
		elif keyPress == ord("s"):
			#package up the data!
			graphdata = []
			graphdata.append(wavelengthData)
			graphdata.append(intensity)
			savedata = []
			savedata.append(spectrum_vertical)
			savedata.append(graphdata)
			saveMsg = snapshot(savedata)
		elif keyPress == ord("c"):
			calcomplete = writecal(clickArray)
			if calcomplete:
				#overwrite wavelength data
				#Go grab the computed calibration data
				caldata = readcal(frameWidth)
				wavelengthData = caldata[0]
				calmsg1 = caldata[1]
				calmsg2 = caldata[2]
				calmsg3 = caldata[3]
				#overwrite graticule data
				graticuleData = generateGraticule(wavelengthData)
				tens = (graticuleData[0])
				fifties = (graticuleData[1])
		elif keyPress == ord("x"):
			clickArray = []
		elif keyPress == ord("m"):
			recPixels = False #turn off recpixels!
			if measure == False:
				measure = True
			elif measure == True:
				measure = False
		elif keyPress == ord("p"):
			measure = False #turn off measure!
			if recPixels == False:
				recPixels = True
			elif recPixels == True:
				recPixels = False
		elif keyPress == ord("o"):#sav up
				savpoly+=1
				if savpoly >=15:
					savpoly=15
		elif keyPress == ord("l"):#sav down
				savpoly-=1
				if savpoly <=0:
					savpoly=0
		elif keyPress == ord("i"):#Peak width up
				mindist+=1
				if mindist >=100:
					mindist=100
		elif keyPress == ord("k"):#Peak Width down
				mindist-=1
				if mindist <=0:
					mindist=0
		elif keyPress == ord("u"):#label thresh up
				thresh+=1
				if thresh >=100:
					thresh=100
		elif keyPress == ord("j"):#label thresh down
				thresh-=1
				if thresh <=0:
					thresh=0
	else: 
		break



#Everything done, release the vid
cap.release()

cv2.destroyAllWindows()


