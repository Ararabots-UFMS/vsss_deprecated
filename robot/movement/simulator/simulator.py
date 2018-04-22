from auxiliary import *
import cv2
import numpy as np

# window size 
img = np.zeros((600,800,3), np.uint8)

# arena size 520X600

# top-left
TL = (100,40)
# top-right
TR = (700,40)
# bottom-left
BL = (100,560)
# bottom-right 
BR = (700,560)

# robot 32X32
# robot center
robot = (0,0)
robotSize = 16

# ball center
ball = (0,0)
ballRadius = 2.1

def drawArena():
    # horizontal lines
    cv2.line(img,TL,TR,(255,255,255),1)
    cv2.line(img,BL,BR,(255,255,255),1)
    # vertical lines
    cv2.line(img,TL,BL,(255,255,255),1)
    cv2.line(img,TR,BR,(255,255,255),1)
    # left side goal
    cv2.line(img,(TL[0]-40, TL[1]+180),(TL[0]-40, TL[1]+340),(255,255,255),1)
    cv2.line(img,(TL[0]-40, TL[1]+180),(TL[0], TL[1]+180),(255,255,255),1)
    cv2.line(img,(TL[0]-40, TL[1]+340),(TL[0], TL[1]+340),(255,255,255),1)
    # right side goal
    cv2.line(img,(TR[0]+40, TR[1]+180),(TR[0]+40, TR[1]+340),(255,255,255),1)
    cv2.line(img,(TR[0]+40, TR[1]+180),(TR[0], TR[1]+180),(255,255,255),1)
    cv2.line(img,(TR[0]+40, TR[1]+340),(TR[0], TR[1]+340),(255,255,255),1)

def drawMarks():
    cv2.line(img,(400,40),(400,560),(255,255,255),1)
    cv2.circle(img,(400,300), 20, (255,255,255), 1)

def drawRobotPos(pos, vec):
    angle = angleBetween([0,1], vec)
    robot = pos
    arTL = (robot[0]-robotSize, robot[1]-robotSize)
    arBR = (robot[0]+robotSize, robot[1]+robotSize)

    rTL = rotate(robot, arTL, 3.14/4)
    rBR = rotate(robot, arBR, -3.14/4)

    cv2.rectangle(img,rTL,rBR,(0,255,0),1)

def initArena():
    drawArena()
    drawMarks()

if __name__ == "__main__":
    initArena()
    drawRobotPos((200,200), [1,1])
    cv2.imshow('Goalkeeper Simulation',img)
    key = cv2.waitKey(0)