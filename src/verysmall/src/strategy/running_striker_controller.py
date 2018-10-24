import sys
import os
import rospy
import numpy as np
from running_striker import RunningStriker, Striker
from arena_sections import *
from ball_range import *
sys.path[0] = path = root_path = os.environ['ROS_ARARA_ROOT']+"src/robot/"
from movement.functions.movement import Movement
from utils.json_handler import JsonHandler
path += '../parameters/robots_pid.json'

jsonHandler = JsonHandler()
univector_list = jsonHandler.read(path)

KP = univector_list['robot_1']['KP']
KD = univector_list['robot_1']['KD']
KI = univector_list['robot_1']['KI']


class RunningStrikerController():

    def __init__(self, _team_side):
        self.position = None
        self.orientation = None
        self.robot_speed = None
        self.enemies_position = None
        self.enemies_speed = None
        self.ball_position = None

        #left is default
        self.team_side = _team_side

        self.stop = Striker(state='Stop')
        self.RunningStriker = RunningStriker(self.stop)
        self.attack_goal = not self.team_side
        # if (self.team_side == LEFT):
        #     self.attack_goal = RIGHT
        # else:
        #     self.attack_goal = LEFT

        self.movement = Movement([KP, KD, KI], error=10, attack_goal=self.attack_goal)

    def update_game_information(self, position, orientation, robot_speed, enemies_position, enemies_speed, ball_position, team_side):
        """
        Update game variables
        :param position:
        :param orientation:
        :param robot_speed:
        :param enemies_position:
        :param enemies_speed:
        :param ball_position:
        """
        self.position = position
        self.orientation = orientation
        self.robot_speed = robot_speed
        self.enemies_position = enemies_position
        self.enemies_speed = enemies_speed
        self.ball_position = ball_position
        self.team_side = team_side

    def set_to_stop_game(self):
        """
        Set state stop in the state machine

        :return: int, int
        """
        self.stop.state = 'stop'
        return 0, 0

    def in_normal_game(self):
        """
        Transitions in normal game state

        :return: int, int
        """
        # if self.RunningStriker.is_stop:
        #     self.RunningStriker.stop_to_normal()

        if self.RunningStriker.is_normal:
            if on_extended_attack_side(self.position, self.team_side):
                if section(self.ball_position) in [UP_BORDER, DOWN_BORDER]:
                    self.RunningStriker.normal_to_border()
                    # return self.RunningStriker.in_border()
                else:
                    self.RunningStriker.normal_to_univector()
            else:
                self.RunningStriker.normal_to_point()

        if self.RunningStriker.is_border:
            return self.RunningStriker.in_border_state()

        if self.RunningStriker.is_univector:
            return self.RunningStriker.in_univector_state()

        if self.RunningStriker.is_point:
            return self.RunningStriker.in_point_state()


    def in_freeball_game(self):
        """
        Transitions in freeball state

        :return: int, int
        """
        if self.RunningStriker.is_stop:
            self.RunningStriker.stop_to_freeball()

        if self.RunningStriker.is_freeball:
            self.RunningStriker.freeball_to_normal()

        if self.RunningStriker.is_normal:
            return self.in_normal_game()

    def in_penalty_game(self):
        """
        Transitions in penalty state

        :return: int, int
        """
        if self.RunningStriker.is_stop:
            self.RunningStriker.stop_to_penalty()

        if self.RunningStriker.is_penalty:
            self.RunningStriker.penalty_to_normal()

        if self.RunningStriker.is_normal:
            return self.in_normal_game()

    def in_meta_game(self):
        """
        Transitions in meta state

        :return: int, int
        """
        if self.RunningStriker.is_stop:
            self.RunningStriker.stop_to_meta()

        if self.RunningStriker.is_meta:
            self.RunningStriker.meta_to_normal()

        if self.RunningStriker.is_normal:
            return self.in_normal_game()

    def in_univector_state(self):
        """
        State univector return left wheel and right wheel speeds

        :return: int, int
        """
        self.RunningStriker.univector_to_univector()
        # if in
        # if inside_range(self.ball_position[0], self.ball_position[0]+ ROBOT_SIZE, self.robot_position[0]):
        if behind_ball(self.ball_position, self.robot_position, self.team_side):
            self.RunningStriker.univector_to_running()
            return self.in_running()
        else:
            if on_extended_attack_side(self.ball_position):
                self.RunningStriker.univector_to_univector()
                left, right, _ = self.movement.do_univector(
                    speed = 180,
                    robot_position=self.position,
                    robot_vector=[np.cos(self.orientation), np.sin(self.orientation)],
                    robot_speed=[0, 0],
                    obstacle_position=np.resize(self.enemies_position, (5, 2)),
                    obstacle_speed=[[0,0]]*5,
                    ball_position=self.ball_position
                )
                return left, right
            else:
                left, right, done = self.movement.move_to_point(
                    speed = 60,
                    robot_position = self.robot_position,
                    robot_vector = [np.cos(self.orientation), np.sin(self.orientation)],
                    goal_position = self.ball_position)
                self.RunningStriker.univector_to_normal()
                return left, right

    def in_running(self):
        self.RunningStriker.running_to_running()
        if not behind_ball(self.ball_position, self.robot_position, self.team_side):
            self.RunningStriker.running_to_normal()
            return

        left, right, done = self.movement.move_to_point(
            speed = 60,
            robot_position = self.robot_position,
            robot_vector = [np.cos(self.orientation), np.sin(self.orientation)],
            goal_position = self.ball_position)
        if notdone:
            return left, right

        goal = goal_position(self.team_side) - self.robot_position
        self.RunningStriker.running_to_running()
        self.movement.follow_vector(
            speed = 120,
            robot_vector=[np.cos(self.orientation), np.sin(self.orientation)],
            goal_vector = [np.cos(goal), np.sin(goal)]
        )
        return left, right

    def in_point(self):
        position_center = np.array([75,65])
        self.RunningStriker.point_to_point()
        left, right, done = self.movement.move_to_point(
            speed = 60,
            robot_position = self.robot_position,
            robot_vector = [np.cos(self.orientation), np.sin(self.orientation)],
            goal_position = position_center)
        if done:
            self.RunningStriker.point_to_stop()
        return left, right

    def in_border(self):
        if section(self.ball_position) in [UP_BORDER, DOWN_BORDER]:
            left, right, done = self.movement.move_to_point(
                speed = 60,
                robot_position = self.robot_position,
                robot_vector = [np.cos(self.orientation), np.sin(self.orientation)],
                goal_position = self.ball_position)
            if near_ball(self.ball_position, self.robot_position):
                left, right, _ = self.movement.spin()
                self.RunningStriker.border_to_normal()
                return left, right
            else:
                self.RunningStriker.border_to_border()
                return left, right
        else:
            self.RunningStriker.border_to_normal()
            position_center = np.array([75,65])
            left, right, done = self.movement.move_to_point(
                speed = 60,
                robot_position = self.robot_position,
                robot_vector = [np.cos(self.orientation), np.sin(self.orientation)],
                goal_position = position_center)
            if done:
                self.RunningStriker.point_to_stop()
            return left, right


#fazer as transições no in_normal_game e retornar o valor das velocidades em cada função de ação dos estados
