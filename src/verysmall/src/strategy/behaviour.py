from typing import Tuple
from enum import Enum
from abc import abstractmethod, ABC
import rospy
import numpy as np
from strategy.strategy_utils import GameStates
from strategy.arena_sections import RIGHT, LEFT
from robot_module.movement.definitions import OpCodes

angle = distance = float
speed = int
ACTION = Tuple[OpCodes, angle, speed, distance]
NO_ACTION = (-1, 0, 0, 0)


class TaskStatus(Enum):
    SUCCESS = 0
    FAILURE = 1
    RUNNING = 2


class BlackBoard:
    """docstring for BlackBoard"""

    def __init__(self):
        self.game = Game()

        # self.game_state = None
        # self.team_side = None
        self.enemy_goal = Goal()
        self.home_goal = Goal()
        # self._attack_goal = None
        # self.attack_goal_pos = None
        # self.home_goal_pos = None

        # self.freeball_robot_id = None
        # self.meta_robot_id = None
        # self.penalty_robot_id = None
        self.ball = MovingBody()
        # self.ball_position = None
        # self.ball_speed = None
        self.robot = FriendlyRobot()
        # self.my_id = None
        # self.role = None
        # self.position = None
        # self.true_pos = None
        # self.orientation = None
        # self.speed = None

        # self.team_color = None
        self.home_team = HomeTeam()
        # self.team_pos = None
        # self.team_orientation = None
        # self.team_speed = None

        self.enemy_team = EnemyTeam()
        # self.enemies_position = None
        # self.enemies_orientation = None
        # self.enemies_speed = None

    def __repr__(self):
        return 'BlackBoard:\n'


class TreeNode:
    def __init__(self, name):
        self.name = name
        self.children = []

    def add_child(self, node) -> None:
        self.children.append(node)

    @abstractmethod
    def run(self, blackboard: BlackBoard) -> Tuple[TaskStatus, ACTION]:
        raise Exception("subclass must override run")


class Sequence(TreeNode):
    """
        A sequence runs each task in order until one fails,
        at which point it returns FAILURE. If all tasks succeed, a SUCCESS
        status is returned.  If a subtask is still RUNNING, then a RUNNING
        status is returned and processing continues until either SUCCESS
        or FAILURE is returned from the subtask.
    """

    def __init__(self, name):
        super().__init__(name)

    def run(self, blackboard):
        for c in self.children:
            status, action = c.run(blackboard)

            if status != TaskStatus.SUCCESS:
                return status, action

        return TaskStatus.SUCCESS, NO_ACTION


class Selector(TreeNode):
    """
        A selector runs each task in order until one succeeds,
        at which point it returns SUCCESS. If all tasks fail, a FAILURE
        status is returned.  If a subtask is still RUNNING, then a RUNNING
        status is returned and processing continues until either SUCCESS
        or FAILURE is returned from the subtask.
    """

    def __init__(self, name: str):
        super().__init__(name)

    def run(self, blackboard) -> Tuple[TaskStatus, ACTION]:

        for c in self.children:
            status, action = c.run(blackboard)
            if status != TaskStatus.FAILURE:
                return status, action

        return TaskStatus.FAILURE, NO_ACTION


class MovingBody:
    def __init__(self):
        self.position = np.array([0, 0])
        self.speed = np.array([0, 0])
        self.orientation = .0


class FriendlyRobot(MovingBody):
    def __init__(self):
        super().__init__()
        self.id = 0
        self.role = 0
        self.last_know_location = None

    def __setattr__(self, key, value):
        if key == 'position' and (value[0] or value[1]):
            self.last_know_location = value
        super().__setattr__(key, value)


class Goal:
    def __init__(self):
        self.side = RIGHT
        self.position = np.array([0, 0])

    def __setattr__(self, key, value):
        if key == 'side':
            super().__setattr__(key, value)
            super().__setattr__('position', np.array([value * 150, 65]))


class Game:
    def __init__(self):
        self.state = GameStates.STOPPED
        self.meta_robot_id = 0
        self.freeball_robot_id = 0
        self.penalty_robot_id = 0


class Team(ABC):
    def __init__(self):
        self.position = np.array([0, 0] for _ in range(5))
        self.speed = np.array([0, 0] for _ in range(5))
        self.orientation = np.array([0, 0] for _ in range(5))
        self.robots = None
        self.number_of_robots = 0

    def __len__(self):
        return self.number_of_robots

    def __getitem__(self, item):
        return self.robots[item]


class EnemyTeam(Team):
    def __init__(self):
        super().__init__()
        self.robots = [MovingBody() for _ in range(5)]


class HomeTeam(Team):
    def __init__(self):
        super().__init__()
        self.robots = [FriendlyRobot() for _ in range(5)]
