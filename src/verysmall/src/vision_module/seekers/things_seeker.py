import cv2
import time
import math
import rospy
import numpy as np

from vision_module.seekers.aruco_seeker import ArucoSeeker
from vision_module.seekers.general_object_seeker import GeneralObjSeeker
from vision_module.seekers.general_mult_obj_seeker import GeneralMultObjSeeker
# @author Wellington Castro <wvmcastro>

# Sorry for these globals, but is good for code reading
# Go Ararabots!
ID = 0
POS = 1
ANGLE = 2
SPEED_QUEUE_SIZE = 60.0

class Things:
    # This is an auxiliary class to hold the variables from the things identified
    # by this hawk eye system
    def __init__(self):
        self.id = -1

        self.lost_counter = 0

        # Stores the (x,y) pos from the rebot
        self.pos = np.array([None, None])

        # The orientation is stored in radians in relation with the x axis
        self.orientation = None

        # Stores the (dx/dt, dy/dt) components
        self.speed = np.array([None, None])

        # Saves the time of the last update
        self.last_update = None

        # This variable is used as the kalman filter object
        self.kalman = None

        self.angular_kalman = None

        self.init_kalman()

    def init_angular_kalman(self):
        dt = 1.0
        self.angular_kalman = cv2.KalmanFilter(3, 1, 0)
        self.angular_kalman.transitionMatrix = np.array([[1., dt, .5*dt**2],
                                                         [0., 1., dt],
                                                         [0., 0., 1.]]).reshape(3,3)
        self.angular_kalman.processNoiseCov = 1e-5 * np.eye(3)
        self.angular_kalman.measurementNoiseCov = 1e-1 * np.ones((1, 1))
        self.angular_kalman.measurementMatrix = 0. * np.zeros((1, 3))
        self.angular_kalman.measurementMatrix[0,0] = 1.
        self.angular_kalman.errorCovPost = 1. * np.ones((3, 3))
        self.angular_kalman.statePost = np.array([[0., 0., 0.]]).reshape(3,1)

    def init_kalman(self):
        #estimated frame rate
        dt = 1.0
        self.kalman = cv2.KalmanFilter(6, 2, 0)
        self.kalman.transitionMatrix = np.array([[1., 0., dt, 0, .5*dt**2, 0.],
                                                 [0., 1., 0., dt, 0., .5*dt**2],
                                                 [0., 0., 1., 0., dt, 0.],
                                                 [0., 0., 0., 1., 0., dt],
                                                 [0., 0., 0., 0., 1., 0.],
                                                 [0., 0., 0., 0., 0., 1.]]).reshape(6,6)

        self.kalman.processNoiseCov = 1e-5 * np.eye(6)
        self.kalman.measurementNoiseCov = 1e-1 * np.ones((2, 2))

        self.kalman.measurementMatrix = 0. * np.zeros((2, 6))
        self.kalman.measurementMatrix[0,0] = 1.
        self.kalman.measurementMatrix[1,1] = 1.

        self.kalman.errorCovPost = 1. * np.ones((6, 6))
        self.kalman.statePost = np.array([[0., 0., 0., 0., 0., 0.]]).reshape(6,1)

        self.init_angular_kalman()


    def set_dt(self, time_now):
        dt = time_now - self.last_update
        self.kalman.transitionMatrix[0,2] = dt
        self.kalman.transitionMatrix[1,3] = dt

    def update(self, id, pos, orientation=None):
        now = time.time()
        if self.last_update == None and np.all(pos != None): #first run
            self.init_kalman()
            # A initialization state must be provided to the kalman filter
            self.kalman.statePost = np.array([[pos[0], pos[1], 0., 0., 0., 0.]]).reshape(6,1)
            if orientation != None:
                self.angular_kalman.statePost = np.array([[orientation, 0., 0.]]).reshape(3,1)
            else:

                self.angular_kalman.statePost = np.array([[0, 0., 0.]]).reshape(3,1)
            self.lost_counter = 0
            self.speed = np.array([0, 0])
        else:
            self.kalman.predict()
            self.angular_kalman.predict()

            # updates the kalman filter
            if np.all(pos != None) and self.lost_counter < 60:
                self.kalman.correct(pos.reshape(2,1))
                if orientation != None:
                    self.angular_kalman.correct(np.array([orientation]).reshape(1,1))
                self.lost_counter = 0
            else: # updates the lost counter
                self.lost_counter += 1

            # uses the kalman info
            state = self.kalman.predict()
            pos = np.array([state[0,0], state[1,0]])
            self.speed = np.array([state[2,0], state[3,0]]) * 60.0

            if orientation != None and abs(abs(orientation) - math.pi) < 0.15:
                #self.init_angular_kalman()
                self.angular_kalman.statePost = np.array([[orientation, 0., 0.]]).reshape(3,1)
            elif orientation == None:
                orientation = self.angular_kalman.predict()[0,0]

        if self.lost_counter >= 60: # if the thing was lost in all previous 10 frames
            self.reset()
        else:
            # Updates the robot's state variables
            self.id = id
            self.last_update = now
            self.pos = pos
            self.orientation = orientation


    def reset(self):
        self.pos = np.array([None, None])
        self.last_update = None
        self.speed = None
        self.orientation = None

class HawkEye:
    """ This class will be responsible of locate and identify all objects present
        in the field """
    # https://docs.opencv.org/master/d9/d8b/tutorial_py_contours_hierarchy.html#gsc.tab=0

    def __init__(self, field_origin, conversion_factor, yellow_tag, num_robots_yellow_team,
    num_robots_blue_team, img_shape, aux_params):

        self.field_origin = field_origin
        self.conversion_factor = conversion_factor
        self.rad_to_degree_factor = 180.0/math.pi
        self.num_robots_yellow_team = num_robots_yellow_team
        self.num_robots_blue_team = num_robots_blue_team

        if yellow_tag == "aruco":
            camera_matrix = aux_params[0]
            distortion_vector = aux_params[1]
            self.yellow_team_seeker = ArucoSeeker(camera_matrix,
                                                  distortion_vector,
                                                  self.num_robots_yellow_team)
        else:
            print("falta implementar")

        self.blue_team_seeker = GeneralMultObjSeeker(num_robots_blue_team)

        self.ball_seeker = GeneralObjSeeker(img_shape)

    def pixel_to_real_world(self, pos):
        # This function expects that pos is a 1D numpy array
        pos = pos - self.field_origin
        pos[1] *= -1

        return pos * self.conversion_factor

    def seek_yellow_team(self, img, robots_list):
        """ This function expects a binary image with the team robots and a list
            of Things objects to store the info """

        robots = self.yellow_team_seeker.seek(img, degree=False)
        # TODO: ISSO AQUI UM DIA VAI DAR MERDA
        tags = [9, 14, 18, 23, 28]
        # tags_in_game = []
        k = 0

        len_robots = len(robots)
        for i in range(self.num_robots_yellow_team):
            id = None if k >= len_robots else robots[k][ID]
            if tags[i] == id:
                pos = self.pixel_to_real_world(robots[k][POS])
                _orientation = robots[k][ANGLE]
                k += 1
            else:
                pos, _orientation = None, None

            # if tags[i] in tags_in_game:
            robots_list[i].update(i, pos, orientation=_orientation)

    def seek_ball(self, img, ball):
        """ Expects a binary image with just the ball and a Thing object to
            store the info """

        pos = self.ball_seeker.seek(img)
        if np.all(pos != None):
            pos = self.pixel_to_real_world(pos)

        ball.update(0, pos)

    def seek_blue_team(self, img, robots_list):

        adv_centers = self.blue_team_seeker.seek(img)

        if not(adv_centers is None) and adv_centers.size:
            for i in range(self.num_robots_blue_team):
                pos = self.pixel_to_real_world(adv_centers[i, :])
                robots_list[i].update(i, pos)

    def reset(self):
        self.yellow_team_seeker.reset()
        self.blue_team_seeker.reset()
        self.ball_seeker.reset()

if __name__ == '__main__':
    pass