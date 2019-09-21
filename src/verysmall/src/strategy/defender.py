import rospy

from strategy.behaviour import *
from strategy.actions.movement_behaviours import MarkBallOnAxis, GoToBallUsingUnivector, SpinTask, \
    GoToBallUsingMove2Point, ChargeWithBall, GoBack
from strategy.actions.state_behaviours import InState
from strategy.actions.game_behaviours import IsBallInRangeOfDefense, IsBallInBorder, AmIInDefenseField, IsNearBall
from strategy.strategy_utils import GameStates
from strategy.base_trees import BaseTree


class Defender(BaseTree):

    def __init__(self, name="behave"):
        super().__init__(name)

        normal = Sequence("Normal")
        normal.add_child(InState('CheckNormalState', GameStates.NORMAL))

        defend = Selector("Defend")

        border = Sequence("Border")
        border.add_child(IsBallInRangeOfDefense("RangeOfDefense"))
        border.add_child(IsBallInBorder("BallInBorder"))
        border.add_child(GoToBallUsingMove2Point("Move2Point", speed=120, acceptance_radius=7))
        border.add_child(SpinTask("Spin", invert=True))
        defend.add_child(border)

        middle = Sequence("Middle")
        middle.add_child(IsBallInRangeOfDefense("InRangeOfDefense"))
        middle.add_child(GoToBallUsingUnivector("UsingUnivector", acceptance_radius=5, max_speed=130,
                                                speed_prediction=False))
        middle.add_child(ChargeWithBall("ChargeWithBall"))

        defend.add_child(middle)

        mark = Sequence("Mark")

        reposition = Selector("reposition")
        kick = Sequence("Kick")
        kick.add_child(IsNearBall("nearBall"))
        kick.add_child(SpinTask("Spin", invert=True))

        reposition.add_child(kick)
        reposition.add_child(AmIInDefenseField("AmIInAttackField"))
        reposition.add_child(GoBack("GoBack", acceptance_radius=15))

        mark.add_child(reposition)
        
        mark.add_child(MarkBallOnAxis("MarkBallonAxis", predict_ball=False))

        defend.add_child(mark)
        normal.add_child(defend)
        self.add_child(normal)
