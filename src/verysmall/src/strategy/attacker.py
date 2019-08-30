from strategy.behaviour import *
from strategy.base_trees import BaseTree, FreeWayAttack
from strategy.actions.state_behaviours import InState
from strategy.actions.game_behaviours import IsBallInsideCentralArea
from strategy.strategy_utils import GameStates, behind_ball
from strategy.actions.movement_behaviours import StopAction, GoToBallUsingUnivector, SpinTask
from robot_module.movement.definitions import OpCodes
from strategy.actions.decorators import IgnoreFailure
from strategy.arena_utils import inside_rectangle, RIGHT, LEFT

import numpy as np
import rospy


class Attacker(BaseTree):

    def __init__(self, name='behave'):
        super().__init__(name)

        normal = Sequence('Normal')
        normal.add_child(InState('CheckNormalState', GameStates.NORMAL))
        normal.add_child(enemy_goalline_behaviour("seilabeio"))
        normal.add_child(self.naive_go_to_ball())

        #normal.add_child(GoToBallUsingUnivector('FollowBall'))  # FollowBall
        normal.add_child(SpinTask('Spin'))  # Spin
        self.add_child(normal)
        
    def naive_go_to_ball(self) -> TreeNode:
        tree = Sequence("Go ball when ball in central area")
        tree.add_child(IsBallInsideCentralArea("Check ball"))
        go_to_ball = GoToBallUsingUnivector("AttackBallInTheMiddle", 
                                            max_speed=150,
                                            acceptance_radius=7,
                                            speed_prediction=False)
        tree.add_child(go_to_ball)

        return tree

class enemy_goalline_behaviour(TreeNode):
    
    def run(self, blackboard: BlackBoard):
        self.robot_position = blackboard.robot.position
        ball_position = blackboard.ball.position
        
        if blackboard.enemy_goal.side == LEFT:
            enemy_goalline = 16
            #16cm in arena means the goal line
            
            if self.robot_position[0] <= enemy_goalline and ball_position[0] <= enemy_goalline:
                debug_print = "Pinto"
                rospy.logfatal(debug_print)
        else:
            enemy_goalline = 134
            #16cm in arena means the another goal line
            
            if self.robot_position[0] >= enemy_goalline and ball_position[0] >= enemy_goalline:
                debug_print = "Pinto"
                rospy.logfatal(debug_print)

        return TaskStatus.SUCCESS, (OpCodes.INVALID, 0, 0, 0)
        