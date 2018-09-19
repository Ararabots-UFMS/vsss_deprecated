import rospy
import sys
import time
import numpy as np
from comunication.sender import Sender
import os
sys.path[0] = root_path = os.environ['ROS_ARARA_ROOT'] + "src/"
from ROS.ros_robot_subscriber import RosRobotSubscriber
from strategy.attacker_with_univector_controller import AttackerWithUnivectorController


class Robot():
    """docstring for Robot"""

    def __init__(self, _robot_name, _tag, _mac_address, _robot_body, isAdversary=False):
        # Parameters
        self.robot_name = _robot_name
        self.robot_id_integer = int(self.robot_name.split("_")[1]) - 1
        self.mac_address = _mac_address # Mac address
        self.robot_body = _robot_body
        self.tag = _tag

        # Receive from vision
        self.ball_position = None
        self.ball_speed = None
        self.team_pos = None
        self.team_orientation = None
        self.team_speed = None
        self.position = None
        self.orientation = None
        self.enemies_position = None
        self.enemies_orientation = None
        self.enemies_speed = None

        # Calculated inside robot
        self.PID = None

        # Receive from game topic
        self.behaviour_type = None
        self.game_state = 0
        self.role = None
        self.penalty_robot = None
        self.freeball_robot = None
        self.meta_robot = None
        self.team_side = 0
        # right(1) or left(0)
        self.left_side = 0
        self.right_side = not self.left_side


        # Open bluetooth socket
        self.bluetooth_sender = Sender(self.robot_id_integer, self.mac_address)
        self.bluetooth_sender.connect()

        self.subs = RosRobotSubscriber(self)

        self.changed_game_state = True
        self.game_state_string = ["Stopped",
                                  "Normal Play",
                                  "Freeball",
                                  "Penaly",
                                  "Meta"]

        self.state_machine = AttackerWithUnivectorController()

    def run(self):
        self.state_machine.update_game_information(position=self.position, orientation=self.orientation,
                                                   robot_speed=[0, 0], enemies_position=self.enemies_position,
                                                   enemies_speed=self.enemies_speed, ball_position=self.ball_position)
        if self.game_state == 0:  # Stopped
            left, right = self.state_machine.set_to_stop_game()
            self.bluetooth_sender.sendPacket(left, right)
        elif self.game_state == 1:  # Normal Play
            left, right = self.state_machine.in_normal_game()
            self.bluetooth_sender.sendPacket(left, right)
        elif self.game_state == 2:  # Freeball
            left, right = self.state_machine.in_freeball_game()
            self.bluetooth_sender.sendPacket(left, right)
        elif self.game_state == 3:  # Penalty
            left, right = self.state_machine.in_penalty_game()
            self.bluetooth_sender.sendPacket(left, right)
        elif self.game_state == 4:  # Meta
            left, right = self.state_machine.in_meta_game()
            self.bluetooth_sender.sendPacket(left, right)
        else:  # I really really really Dont Know
            print("wut")

        if self.changed_game_state:
            rospy.logfatal("Robo_" + self.robot_name + ": Run("+self.game_state_string[self.game_state]+") side: " +
                           str(self.team_side))
            self.changed_game_state = False

    def read_parameters(self):
        #TODO: ler parametros do robot na funcao init
        pass

    def debug(self):
        pass

    def bluetooth_detach(self):
        if self.bluetooth_sender is not None:
            self.bluetooth_sender.closeSocket()
