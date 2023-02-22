import cv2 
import argparse
import time
import numpy as np

def rotate(image, angle):
	image_center = tuple(np.array(image.shape[1::-1]) / 2)
	rot_mat = cv2.getRotationMatrix2D(image_center, angle, 1.0)
	result = cv2.warpAffine(image, rot_mat, image.shape[1::-1], flags=cv2.INTER_LINEAR)
	return result



def command_line_argument():
	parser = argparse.ArgumentParser()
	parser.add_argument("--device", type=int, default=0, help="Video Device number e.g. 0, use v4l2-ctl --list-devices")
	parser.add_argument("--fps", type=int, default=30, help="Frame Rate e.g. 30")
	group = parser.add_mutually_exclusive_group()
	group.add_argument("--fullscreen", help="Fullscreen (Native 800*480)",action="store_true")
	args = parser.parse_args()
	dispFullscreen = False
	dispWaterfall = False
	if args.fullscreen:
		print("Fullscreen Spectrometer enabled")
		dispFullscreen = True
	if args.device:
		dev = args.device
	else:
		dev = 0
		
	if args.fps:
		fps = args.fps
	else:
		fps = 30

	return dispFullscreen, dev, fps

def init_video(dev, dispFullscreen, video_window_title, frameWidth, frameHeight, fps):
	cap = cv2.VideoCapture('/dev/video'+str(dev), cv2.CAP_V4L)
	print(cap.isOpened())
	print("[info] W, H, FPS")
	cap.set(cv2.CAP_PROP_FRAME_WIDTH,frameWidth)
	cap.set(cv2.CAP_PROP_FRAME_HEIGHT,frameHeight)
	cap.set(cv2.CAP_PROP_FPS,fps)

	print(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
	print(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
	print(cap.get(cv2.CAP_PROP_FPS))
	cfps = (cap.get(cv2.CAP_PROP_FPS))


	title1 = video_window_title
	stackHeight = 320+80+80 #height of the displayed CV window (graph+preview+messages)


	if dispFullscreen == True:
		cv2.namedWindow(title1,cv2.WND_PROP_FULLSCREEN)
		cv2.setWindowProperty(title1,cv2.WND_PROP_FULLSCREEN,cv2.WINDOW_FULLSCREEN)
	else:
		cv2.namedWindow(title1,cv2.WINDOW_GUI_NORMAL)
		cv2.resizeWindow(title1,frameWidth,stackHeight)
		cv2.moveWindow(title1,0,0)
	
	return cap, cfps

def snapshot(savedata):
	now = time.strftime("%Y%m%d--%H%M%S")
	timenow = time.strftime("%H:%M:%S")
	imdata1 = savedata[0]
	graphdata = savedata[1]
	cv2.imwrite("spectrum-" + now + ".png",imdata1)
	#print(graphdata[0]) #wavelengths
	#print(graphdata[1]) #intensities
	f = open("Spectrum-"+now+'.csv','w')
	f.write('Wavelength,Intensity\r\n')
	for x in zip(graphdata[0],graphdata[1]):
		f.write(str(x[0])+','+str(x[1])+'\r\n')
	f.close()
	message = "Last Save: "+timenow
	return(message)


