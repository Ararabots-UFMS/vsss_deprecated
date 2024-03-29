from typing import Iterable

from strategy.actions.decorators import InvertOutput, DoNTimes, StatusChanged, KeepRunning
from strategy.actions.game_behaviours import *
from strategy.actions.movement_behaviours import *
from strategy.actions.state_behaviours import InState
from strategy.arena_utils import ArenaSections, LEFT
from strategy.base_trees import BaseTree
from strategy.behaviour import *
from strategy.strategy_utils import GameStates


class GoalKeeper(BaseTree):
    def __init__(self, name: str = "behave"):
        super().__init__(name)

        normal = Sequence("Normal")
        self.add_child(normal)

        normal.add_child(InState("CheckNormalState", GameStates.NORMAL))
        normal_actions = Selector("NormalActions")
        normal.add_child(normal_actions)

        self.do_once = DoNTimes(n=1)
        self.do_once.add_child(AlignWithAxis())

        normal_actions.add_child(self.get_ball_out_of_def_area())

        status_changed = StatusChanged(function=self.reset_counter)
        status_changed.add_child(OutOfGoalAction())

        normal_actions.add_child(status_changed)
        normal_actions.add_child(self.do_once)

        self.mark_ball_on_y = None
        self.mark_ball_on_bottom_line = None

        normal_actions.add_child(self._ball_on_defense_side_tree())
        normal_actions.add_child(self._ball_on_attack_side_tree())

    def reset_counter(self):
        self.do_once.n = 1

    def _ball_on_attack_side_tree(self) -> TreeNode:
        tree = Sequence("BallInAttackSide")
        tree.add_child(IsInAttackSide("VerifyBallInAttack", lambda b: b.ball.position))
        tree.add_child(GoToGoalCenter(max_speed=100, acceptance_radius=3))
        keep_align_action = KeepRunning()
        keep_align_action.add_child(AlignWithAxis())
        tree.add_child(keep_align_action)
        return tree

    def _ball_on_defense_side_tree(self) -> TreeNode:
        tree = Sequence("BallInDefenseSide")

        get_pos = lambda b: b.ball.position_prediction(
            b.ball.get_time_on_axis(axis=0, value=b.robot.position[0]))
        is_ball_in_attack_side = IsInAttackSide("VerifyBallInAttack", get_pos)
        tree.add_child(InvertOutput(child=is_ball_in_attack_side))

        defence_actions = Selector("BallInDefenceActions")
        tree.add_child(defence_actions)

        check_ball_not_in_bottom = InvertOutput(child=IsInDefenseBottomLine(
                                                "BallInBottomLine",
                                                lambda b: b.ball.position))
                                                
        self.mark_ball_on_y = MarkBallOnYAxis([5, 40], [5, 80],
                                              max_speed=120,
                                              acceptance_radius=4)

        keep_align_action = KeepRunning()
        keep_align_action.add_child(AlignWithAxis())

        defence_actions.add_child(Sequence("BallNotInBottom",
                                  [check_ball_not_in_bottom, self.mark_ball_on_y,
                                   keep_align_action]))

        defence_actions.add_child(self._ball_on_bottom_tree())

        return tree

    def run(self, blackboard: BlackBoard) -> Tuple[TaskStatus, ACTION]:
        self.set_y_axis(blackboard)
        self._set_bottom_line_axis(blackboard)
        return super().run(blackboard)

    def set_y_axis(self, blackboard: BlackBoard) -> None:
        a = self.get_clamps(blackboard)
        self.mark_ball_on_y.set_clamps(*a)

    def get_clamps(self, blackboard: BlackBoard) -> Tuple[Iterable, Iterable]:
        s = -1 if blackboard.home_goal.side else 1

        x = blackboard.home_goal.position[0] + s * 2
        return [x, 50], [x, 80]

    def get_ball_out_of_def_area(self) -> TreeNode:
        tree = Sequence("GetBallOutOfDefenseArea")

        inverter = InvertOutput()
        tree.add_child(inverter)
        inverter.add_child(IsInAttackSide("VerifyBallInAttack", lambda b: b.ball.position))

        is_ball_or_enemy_in_critical_position = Selector("IsBallOrEnemyInCritalPosition")
        is_ball_inside_defense_area = IsBallInsideSections(name="IsBallInsideDefenseArea",
                                                           sections=[ArenaSections.LEFT_GOAL_AREA,
                                                                     ArenaSections.RIGHT_GOAL_AREA])

        enemy_near_ball_and_in_critical_position = Sequence('EnemyNearBallAndInCriticalPos')
        enemy_near_ball_and_in_critical_position.add_child(IsEnemyInCriticalPosition())
        enemy_near_ball_and_in_critical_position.add_child(IsEnemyNearBall(acceptance_radius=7))
        enemy_near_ball_and_in_critical_position.add_child(IsEnemyNearRobot(acceptance_radius=15))

        is_ball_or_enemy_in_critical_position.add_child(is_ball_inside_defense_area)
        is_ball_or_enemy_in_critical_position.add_child(enemy_near_ball_and_in_critical_position)
        tree.add_child(is_ball_or_enemy_in_critical_position)
        tree.add_child(GoToBallUsingMove2Point(acceptance_radius=7))

        push_or_spin = Selector("PushOrSpin")
        push_action = Sequence("PushAction")
        push_action.add_child(IsBehindBall("IsBehindBall", 10))
        push_action.add_child(RemoveBallFromGoalArea())

        push_or_spin.add_child(push_action)
        push_or_spin.add_child(SpinTask())

        tree.add_child(push_or_spin)

        return tree

    def _ball_on_bottom_tree(self) -> TreeNode:
        tree = Sequence("BallInBotttomLine")
        tree.add_child(IsInDefenseBottomLine("IsBallInBottomLine",
                                             lambda b : b.ball.position))

        self.mark_ball_on_bottom_line = MarkBallOnYAxis([10, 35], [10, 95],
                                                        max_speed=110,
                                                        acceptance_radius=4)
        tree.add_child(self.mark_ball_on_bottom_line)
        tree.add_child(StopAction())
        return tree

    def _set_bottom_line_axis(self, blackboard: BlackBoard) -> None:
        team_side = blackboard.home_goal.side
        x = 3.5 if team_side == LEFT else 146.5
        self.mark_ball_on_bottom_line._clamp_min[0] = x
        self.mark_ball_on_bottom_line._clamp_max[0] = x


class OutOfGoalAction(Sequence):
    def __init__(self, name: str = "Get Out Of Goal"):
        super().__init__(name)
        self.add_child(IsInsideDefenseGoal("IsGoalkeeperInsideGoal",
                                           lambda b : b.robot.position))
        self.add_child(GetOutOfGoal(max_speed=100, acceptance_radius=4.0))

    def run(self, blackboard: BlackBoard):
        status, action = super().run(blackboard)
        if status == TaskStatus.SUCCESS:
            self.children[1].target_pos = None
        return status, action
