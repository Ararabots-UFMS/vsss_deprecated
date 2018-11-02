import sys
import os
import rospy
import numpy as np
from zagueiro import Zagueiro, MyModel
sys.path[0] = path = root_path = os.environ['ROS_ARARA_ROOT']+"src/robot/"
from movement.functions.movement import Movement
from utils.json_handler import JsonHandler
path += '../parameters/bodies.json'
from arena_sections import *
from ball_range import *

jsonHandler = JsonHandler()
bodies_unpack = jsonHandler.read(path, escape=True)

SOFTWARE = 0
HARDWARE = 1

ZAGUEIRO_SPEED = 169
DEF_X_POS = [75.0/2.0, 75 + 75.0/2.0]

class ZagueiroController():

    def __init__(self, _robot_body="Nenhum", _debug_topic = None):
        self.pid_type = SOFTWARE
        self.position = None
        self.orientation = None
        self.team_speed = None
        self.enemies_position = None
        self.enemies_speed = None
        self.ball_position = None
        self.team_side = None
        self.robot_body = _robot_body
        rospy.logfatal(self.robot_body)
        self.pid_list = [bodies_unpack[self.robot_body]['KP'],
                         bodies_unpack[self.robot_body]['KI'],
                         bodies_unpack[self.robot_body]['KD']]

        if(not self.team_side):
            #Attack_in right side
            self.attack_goal = np.array([150.0, 65.0])
        else:
            #Attack_in left side
            self.attack_goal = np.array([0.0, 65.0])


        self.defend_position = np.array([0,0])

        self.stop = MyModel(state='stop')
        self.zagueiro = Zagueiro(self.stop)

        self.movement = Movement(self.pid_list, error=10, attack_goal=self.attack_goal, _pid_type=self.pid_type, _debug_topic=_debug_topic)


    def set_pid_type(self, _type):
        """
        Change pid type
        :return:
        """
        self.pid_type = _type
        self.movement.set_pid_type(_type=self.pid_type)



    def update_game_information(self, position, orientation, team_speed, enemies_position, enemies_speed, ball_position, team_side):
        """
        Update game variables
        :param position:
        :param orientation:
        :param team_speed:
        :param enemies_position:
        :param enemies_speed:
        :param ball_position:
        """
        self.position = position
        self.orientation = orientation
        self.team_speed = team_speed
        self.enemies_position = enemies_position
        self.enemies_speed = enemies_speed
        self.ball_position = ball_position
        self.team_side = team_side
        self.movement.univet_field.update_attack_side(not self.team_side)

    def update_pid(self):
        """
        Update pid
        :return:
        """
        self.pid_list = [bodies_unpack[self.robot_body]['KP'], bodies_unpack[self.robot_body]['KI'], bodies_unpack[self.robot_body]['KD']]
        self.movement.update_pid(self.pid_list)




    def set_to_stop_game(self):
        """
        Set state stop in the state machine

        :return: int, int
        """
        self.stop.state = 'stop'
        return 0, 0, SOFTWARE

    def in_normal_game(self):
        rospy.logfatal(self.zagueiro.current_state)

        """
        Transitions in normal game state

        :return: int, int
        """
        if self.zagueiro.is_stop:
            self.zagueiro.stop_to_normal()

        if self.zagueiro.is_normal:

            if(not self.team_side): ############    team_side =  0
                #rospy.logfatal("team side 0")
                if((section(self.ball_position) not in [LEFT_GOAL, LEFT_GOAL_AREA]) and self.ball_position[0] <= 75.0):
                    s = section(self.ball_position)
                    if s in xrange(LEFT_UP_CORNER,DOWN_BORDER+1) or s in xrange(LEFT_DOWN_BOTTOM_LINE, RIGHT_UP_BOTTOM_LINE+1):
                        self.zagueiro.normal_to_border()
                    self.zagueiro.normal_to_defend()
                else:
                     self.zagueiro.normal_to_wait_ball()

            else:               ############    team_side = 1
                if((section(self.ball_position) not in [RIGHT_GOAL, RIGHT_GOAL_AREA]) and self.ball_position[0] > 75.0):
                    if(near_ball(self.ball_position, self.position)):
                        self.zagueiro.normal_to_do_spin()
                    else:
                        self.zagueiro.normal_to_defend()
                else:
                     self.zagueiro.normal_to_wait_ball()

            if section(self.position) in [LEFT_GOAL, LEFT_GOAL_AREA] or section(self.position) in [RIGHT_GOAL, RIGHT_GOAL_AREA]:
                self.zagueiro.normal_to_area()
            sr = section(self.ball_position)
            if not near_ball(self.position, self.ball_position, 7.5) and sr in [LEFT_UP_BOTTOM_LINE, LEFT_DOWN_BOTTOM_LINE, RIGHT_UP_BOTTOM_LINE, RIGHT_DOWN_BOTTOM_LINE, UP_BORDER, DOWN_BORDER]:
                self.zagueiro.normal_to_locked()


        if self.zagueiro.is_area:
            return self.in_area()
        elif self.zagueiro.is_defend:
            return self.in_defend()
        elif (self.zagueiro.is_wait_ball):
            return self.in_wait_ball()
        elif self.zagueiro.is_do_spin :
            return self.in_spin()
        elif self.zagueiro.is_move:
            return self.in_move()
        elif self.zagueiro.is_border:
            return self.in_border()
        elif self.zagueiro.is_locked:
            return self.in_locked()
        else:
            rospy.logfatal("aqui deu ruim, hein moreno")
            return 0, 0, self.pid_type


    def in_defend(self):
        rospy.logfatal(self.zagueiro.current_state)
        if section(self.position) in [LEFT_GOAL, LEFT_GOAL_AREA] or section(self.position) in [RIGHT_GOAL, RIGHT_GOAL_AREA]:
            self.zagueiro.defend_to_area()
            return self.in_area()

        if(not ((not self.team_side) and (section(self.ball_position) not in [LEFT_GOAL, LEFT_GOAL_AREA]) and self.ball_position[0] <= 75.0 or (self.team_side) and(section(self.ball_position) not in [RIGHT_GOAL, RIGHT_GOAL_AREA]) and self.ball_position[0] > 75.0)):
            self.zagueiro.defend_to_wait_ball()
            return self.in_wait_ball()
        else:
            s = section(self.ball_position)
            if s in xrange(LEFT_UP_CORNER,DOWN_BORDER+1) or s in xrange(LEFT_DOWN_BOTTOM_LINE, RIGHT_UP_BOTTOM_LINE+1):
                self.zagueiro.defend_to_border()
                return self.in_border()
            if(near_ball(self.ball_position, self.position)):
                self.zagueiro.defend_to_do_spin()
                rospy.logfatal(self.zagueiro.current_state)
                return self.in_spin()
            else:
                self.zagueiro.defend_to_move()
                rospy.logfatal(self.zagueiro.current_state)
                return self.in_move();


    def in_spin(self):
        rospy.logfatal(self.zagueiro.current_state)
        self.zagueiro.do_spin_to_defend()
        if self.team_side == LEFT:
            if self.ball_position[1] < 65:
                ccw = True
            else:
                ccw = False
        else:
            if self.ball_position[1] < 65:
                ccw = False
            else:
                ccw = True


        param1, param2, param3 = self.movement.spin(ZAGUEIRO_SPEED, ccw)

        return param1, param2, self.pid_type

    def in_move(self):
        if section(self.position) in [LEFT_GOAL, LEFT_GOAL_AREA] or section(self.position) in [RIGHT_GOAL, RIGHT_GOAL_AREA]:
            self.zagueiro.move_to_area()
            return self.in_area()
        rospy.logfatal(self.zagueiro.current_state)
        # self.zagueiro.move_to_move()
        param1, param2, param3 = self.movement.do_univector(
            ZAGUEIRO_SPEED,
            self.position,
            [np.cos(self.orientation), np.sin(self.orientation)],
            self.team_speed,
            self.enemies_position,
            self.enemies_speed,
            self.ball_position
            )
        if param3:
            self.zagueiro.move_to_do_spin()
            return self.in_spin()
        return param1, param2, self.pid_type

    def in_wait_ball(self):
        rospy.logfatal(self.zagueiro.current_state)
        if section(self.position) in [LEFT_GOAL, LEFT_GOAL_AREA] or section(self.position) in [RIGHT_GOAL, RIGHT_GOAL_AREA]:
            self.zagueiro.wait_ball_to_area()
            return self.in_area()

        if((not self.team_side) and (section(self.ball_position) not in [LEFT_GOAL, LEFT_GOAL_AREA]) and self.ball_position[0] <= 75.0 or (self.team_side) and(section(self.ball_position) not in [RIGHT_GOAL, RIGHT_GOAL_AREA]) and self.ball_position[0] > 75.0):
            self.zagueiro.wait_ball_to_defend()
            return self.in_defend()
        else:
            self.defend_position[0] = DEF_X_POS[self.team_side]
            self.defend_position[1] = self.ball_position[1]

            param1, param2, param3 = self.movement.move_to_point(
                ZAGUEIRO_SPEED,
                self.position,
                [np.cos(self.orientation), np.sin(self.orientation)],
                self.defend_position
            )


            return param1, param2, self.pid_type




    def in_freeball_game(self):
        """
        Transitions in freeball state

        :return: int, int
        """
        if self.zagueiro.is_stop:
            self.zagueiro.stop_to_freeball()

        if self.zagueiro.is_freeball:
            self.zagueiro.freeball_to_normal()

        if self.zagueiro.is_normal:
            return self.in_normal_game()

    def in_penalty_game(self):
        """
        Transitions in penalty state

        :return: int, int
        """
        if self.zagueiro.is_stop:
            self.zagueiro.stop_to_penalty()

        if self.zagueiro.is_penalty:
            self.zagueiro.penalty_to_normal()

        if self.zagueiro.is_normal:
            return self.in_normal_game()

    def in_meta_game(self):
        """
        Transitions in meta state

        :return: int, int
        """
        if self.zagueiro.is_stop:
            self.zagueiro.stop_to_meta()

        if self.zagueiro.is_meta:
            self.zagueiro.meta_to_normal()

        if self.zagueiro.is_normal:
            return self.in_normal_game()

    def in_border(self):
        # rospy.logfatal(self.zagueiro.current_state)
        if section(self.position) in [LEFT_GOAL, LEFT_GOAL_AREA] or section(self.position) in [RIGHT_GOAL, RIGHT_GOAL_AREA]:
            self.zagueiro.border_to_area()
            return self.in_area()
        sb = section(self.ball_position)
        if sb in xrange(LEFT_UP_CORNER,DOWN_BORDER+1) or sb in xrange(LEFT_DOWN_BOTTOM_LINE, RIGHT_UP_BOTTOM_LINE+1):
            rospy.logfatal("to na borda")
            robot_vector = [np.cos(self.orientation), np.sin(self.orientation)]
            if(near_ball(self.ball_position, self.position, 7.5)):
                self.zagueiro.border_to_do_spin()
                return self.in_spin()
            else:
                param1, param2, param3 = self.movement.move_to_point(ZAGUEIRO_SPEED, self.position, robot_vector, self.ball_position)
                rospy.logfatal(param3)
                return param1, param2, self.pid_type
        else:
            self.zagueiro.border_to_normal()
            return self.in_normal_game()

    def in_area(self):
        rospy.logfatal(self.zagueiro.current_state)
        if section(self.position) in [LEFT_GOAL, LEFT_GOAL_AREA] or section(self.position) in [RIGHT_GOAL, RIGHT_GOAL_AREA]:
            robot_vector = [np.cos(self.orientation), np.sin(self.orientation)]
            param1, param2, param3 = self.movement.move_to_point(ZAGUEIRO_SPEED, self.position, robot_vector, self.defend_position)
            return param1, param2, self.pid_type
        else:
            self.zagueiro.area_to_normal()
            return 0, 0, self.pid_type

    def in_locked(self):
        if not near_ball(self.position, self.ball_position, 7.5):
            sr = section(self.ball_position)
            if sr == UP_BORDER:
                if angleBetween(self.position, [self.position[0], 135],abs=True) <= 30.0:
                    self.zagueiro.locked_to_do_spin()
                    return self.in_spin()
            elif sr == DOWN_BORDER:
                if angleBetween(self.position, [self.position[0], -5], abs=True) <= 30.0:
                    self.zagueiro.locked_to_do_spin()
                    return self.in_spin()
            elif sr in [LEFT_DOWN_BOTTOM_LINE, LEFT_UP_BOTTOM_LINE]:
                if angleBetween(self.position, [0, self.position[1]],abs=True) <= 30.0:
                    self.zagueiro.locked_to_do_spin()
                    return self.in_spin()
            elif sr in [RIGHT_UP_BOTTOM_LINE, RIGHT_DOWN_BOTTOM_LINE]:
                if angleBetween(self.position, [self.position[0], 155],abs=True) <= 30.0:
                    self.zagueiro.locked_to_do_spin()
                    return self.in_spin()
        self.zagueiro.area_to_normal()
        return self.in_normal_game()
