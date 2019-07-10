import sys
import os
import rospy
import numpy as np
import math
from .naive_attacker_strategy import NaiveAttacker, MyModel
from robot_module.movement.functions.movement import Movement
from utils.json_handler import JsonHandler
import strategy.strategy_utils as strategy_utils
from strategy.strategy_utils import *
from utils import math_utils

bodies_unpack = JsonHandler().read("parameters/bodies.json", escape = True)

HARDWARE = 1
SOFTWARE = 0
CENTER_Y = 65
CENTER_X = 75
SPEED_DEFAULT = 150
MAX_X = 150
LIMIT_RANGE = 75


class NaiveAttackerController():


    def __init__(self,_robot_obj,  _robot_body = "Nenhum", _debug_topic = None):
        self.pid_type = SOFTWARE
        self.robot = _robot_obj
        self.speed = None
        self.position = None
        self.orientation = None
        self.robot_speed = None
        self.enemies_position = None
        self.enemies_speed = None
        self.ball_position = None
        self.team_side = None
        self.team_speed = None

        self.position_buffer =[]
        self.borders = [
            UP_BORDER,
            DOWN_BORDER,
            LEFT_DOWN_BOTTOM_LINE,
            LEFT_UP_BOTTOM_LINE,
            RIGHT_DOWN_BOTTOM_LINE,
            RIGHT_UP_BOTTOM_LINE,
            LEFT_UP_CORNER,
            LEFT_DOWN_CORNER,
            RIGHT_UP_CORNER,
            RIGHT_DOWN_CORNER
            ]

        self.robot_body = _robot_body
        rospy.logfatal(self.robot_body)
        self.pid_list = [bodies_unpack[self.robot_body]['KP'],
                         bodies_unpack[self.robot_body]['KI'],
                         bodies_unpack[self.robot_body]['KD']]

        self.model = MyModel(state='stop')
        self.NaiveAttacker = NaiveAttacker(self.model)

        self.attack_goal = np.array([150.0, 65.0])

        self.movement = Movement(self.pid_list, error=10, attack_goal=self.attack_goal, _debug_topic = _debug_topic)

    def update_game_information(self):
        """
        Update game variables
        :param position:
        :param orientation:
        :param speed
        :param team_speed:
        :param enemies_position:
        :param enemies_speed:
        :param team_side
        :param ball_position:
        """
        self.position = self.robot.position
        self.orientation = self.robot.orientation
        self.speed = self.robot.speed
        self.team_speed = self.robot.team_speed
        self.enemies_position = self.robot.enemies_position
        self.enemies_speed = self.robot.enemies_speed
        self.ball_position = self.robot.ball_position
        self.team_side = self.robot.team_side
        self.attack_goal[0] = 0.0 + (not self.team_side)*150
        self.movement.univet_field.update_attack_side(not self.team_side)
        self.robot.add_to_buffer(self.position_buffer, 60, self.position)

    def set_to_stop_game(self):
        """
        Set state stop in the state machine

        :return: int, int
        """
        self.model.state = 'stop'
        return 0, 0, 0

    def in_stuck(self):


        if (strategy_utils.section(self.position) == CENTER):
            self.model.state = 'normal'

        robot_vector = [np.cos(self.orientation), np.sin(self.orientation)]
        goal_vector  = [65,65]

        left, right, done = self.movement.move_to_point(
            speed = SPEED_DEFAULT,
            robot_position=self.position,
            robot_vector=[np.cos(self.orientation), np.sin(self.orientation)],
            goal_position = [65,65]
        )

        return left, right, self.pid_type


    def in_normal_game(self):
        """
        Transitions in normal game state

        :return: int, int
        """
        if self.NaiveAttacker.is_stop:
            self.NaiveAttacker.stop_to_normal()

        if self.robot.get_stuck(self.position) and (strategy_utils.section(self.position) != CENTER):
            self.model.state = "stuck"

        rospy.logfatal(self.NaiveAttacker.current_state)

        if self.NaiveAttacker.is_normal:
            # Caso a bola esteja no campo de ataque
            if strategy_utils.on_attack_side(self.ball_position, self.team_side, LIMIT_RANGE):
                # Verifica se a bola esta nas bordas
                if (strategy_utils.section(self.ball_position) in self.borders):
                    self.NaiveAttacker.normal_to_border()
                else:
                    self.NaiveAttacker.normal_to_reach_ball()
            # Caso o a bola esteja na defesa manda o atacante para um ponto fixo
            else:
                self.NaiveAttacker.normal_to_point()


        if self.NaiveAttacker.is_reach_ball:

            # Caso a bola esteja na defesa muda o estado para o point
            if not strategy_utils.on_attack_side(self.ball_position, self.team_side, LIMIT_RANGE):
                self.NaiveAttacker.reach_ball_to_point()
            else:
                #caso o robo esteja na borda e no ataque
                if(strategy_utils.section(self.ball_position) in self.borders):
                    self.NaiveAttacker.reach_ball_to_border()

                # Caso a bola esteja no range de chute
                if (behind_ball(self.ball_position, self.position, self.team_side)):
                    self.NaiveAttacker.reach_ball_to_spin()



        if self.NaiveAttacker.is_border:

            # Caso a bola esteja na defesa
            if not (strategy_utils.on_attack_side(self.ball_position, self.team_side, LIMIT_RANGE)):
                self.NaiveAttacker.border_to_point()
            else:
                # Caso a bola esteja nas bordas
                if(strategy_utils.section(self.ball_position) in self.borders):
                    # Caso a bola esteja em ponto para chute
                    if (distance_point(self.ball_position, self.position) < 8):
                        self.NaiveAttacker.border_to_spin()
                else:
                    self.NaiveAttacker.border_to_reach_ball()

        if self.NaiveAttacker.is_go_to_point:
            # Posicao de espera do robo
            wait_position_x = CENTER_X + ((-1)**self.team_side)*20
            position_center = [wait_position_x, CENTER_Y]

            # Caso a bola estja no ataque muda o estado para o reach ball
            if strategy_utils.on_attack_side(self.ball_position, self.team_side, LIMIT_RANGE):
                self.NaiveAttacker.point_to_reach_ball()
            
            # Verifica se a posicao atual do robo esta em uma margem de erro aceitavel
            if (distance_point(self.position, position_center) < 10):
                # Caso o robo esteja na defesa
                if not strategy_utils.on_attack_side(self.ball_position, self.team_side, LIMIT_RANGE):
                    self.NaiveAttacker.point_to_wait_ball()

        if self.NaiveAttacker.is_wait_ball:
            # Caso a bola passe para o ataque, troca de espado para ataque
            if strategy_utils.on_attack_side(self.ball_position, self.team_side, LIMIT_RANGE):
                self.NaiveAttacker.wait_to_reach_ball()

        if self.NaiveAttacker.is_spin:
            if (strategy_utils.distance_point(self.ball_position, self.position) > 7):
                if (strategy_utils.section(self.position) != CENTER):
                    self.NaiveAttacker.spin_to_border()
                else:
                    self.NaiveAttacker.spin_to_reach_ball()


        if self.NaiveAttacker.is_stuck:
            return self.in_stuck()

        # Se estado esta como borda
        if self.NaiveAttacker.is_border:
            return self.in_border()

        # Caso o estado estaja normal
        elif self.NaiveAttacker.is_reach_ball:
            return self.in_reach_ball()

        # Caso a bola esteja no campo de defesa
        elif self.NaiveAttacker.is_go_to_point:
            return self.in_point()

        # Estado de espera da bola
        elif self.NaiveAttacker.is_wait_ball:
            return self.in_wait_ball()

        # Estado de chute
        elif self.NaiveAttacker.is_spin:
            return self.in_spin()

    def in_reach_ball(self):
        """
        Transitions in the reach ball state

        :return: int, int
        """

        # Segue a bola com o univector
        left, right, done = self.movement.do_univector(
            speed = SPEED_DEFAULT,
            robot_position=self.position,
            robot_vector=[np.cos(self.orientation), np.sin(self.orientation)],
            robot_speed=self.speed,
            obstacle_position=self.enemies_position.reshape((-1, 2)),
            obstacle_speed=[[0,0]]*5,
            ball_position=self.ball_position,
            only_forward=False,
            speed_prediction=False
        )

        return left, right, self.pid_type

    def in_border(self):

        robot_vector = [np.cos(self.orientation), np.sin(self.orientation)]
        goal_vector  = [self.ball_position[0]-self.position[0], self.ball_position[1]-self.position[1]]

        left, right, done = self.movement.do_univector_ball(
            speed = SPEED_DEFAULT,
            robot_position=self.position,
            robot_vector=[np.cos(self.orientation), np.sin(self.orientation)],
            robot_speed=self.speed,
            obstacle_position=np.resize(self.enemies_position, (-1, 2)),
            obstacle_speed=[[0,0]]*5,
            ball_position=self.ball_position,

        )

        return left, right, self.pid_type

    def in_point(self):

        # Posicao de espera do robo
        wait_position_x = CENTER_X + ((-1)**self.team_side)*20
        position_center = [wait_position_x, CENTER_Y]


        left, right, done = self.movement.move_to_point(
            speed = SPEED_DEFAULT,
            robot_position=self.position,
            robot_vector=[np.cos(self.orientation), np.sin(self.orientation)],
            goal_position = position_center
        )

        return left, right, self.pid_type

    def in_wait_ball(self):

        # Caso contrario, apenas espera com o robo parado
        robot_vector = [np.cos(self.orientation), np.sin(self.orientation)]
        # Vetor da robo pra bola
        goal_vector  = [self.ball_position[0]-self.position[0], self.ball_position[1]-self.position[1]]

        #turn the front side to face the ball
        left, right, done = self.movement.head_to(
            robot_vector=(robot_vector),
            goal_vector=(goal_vector),
            multiplicator=0.5
        )
        return left, right, self.pid_type


    def in_spin(self):
        """[summary]

        [Function to shoot theft if theft is behind the ball]

        Returns:
            [array (angle, speed)] -- [Returns to spin the robbies]
        """        

        # Pega o lado que o robo tem que girar
        spin_side = spin_direction(self.ball_position, self.position, self.team_side)
        # Chama a funcao de spin

        if self.team_side == 0:
            left, right, done = self.movement.spin(255, not spin_side)
        else:
            left, right, done = self.movement.spin(255, spin_side)    


        return left, right, self.pid_type

    def in_freeball_game(self):
        """
        Transitions in freeball state

        :return: int, int
        """
        if self.NaiveAttacker.is_stop:
            self.NaiveAttacker.stop_to_freeball()

        if self.NaiveAttacker.is_freeball:
            self.NaiveAttacker.freeball_to_normal()

        if self.NaiveAttacker.is_normal:
            return self.in_normal_game()

    def in_penalty_game(self):
        """
        Transitions in penalty state

        :return: int, int
        """
        if self.NaiveAttacker.is_stop:
            self.NaiveAttacker.stop_to_penalty()

        if self.NaiveAttacker.is_penalty:
            self.NaiveAttacker.penalty_to_normal()

        if self.NaiveAttacker.is_normal:
            return self.in_normal_game()

    def in_meta_game(self):
        """
        Transitions in meta state

        :return: int, int
        """
        if self.NaiveAttacker.is_stop:
            self.NaiveAttacker.stop_to_meta()

        if self.NaiveAttacker.is_meta:
            self.NaiveAttacker.meta_to_normal()

        if self.NaiveAttacker.is_normal:
            return self.in_normal_game()


# import sys
# import os
# import rospy
# import numpy as np
# import math
# from naive_attacker_strategy import NaiveAttacker, MyModel
# sys.path[0] = path = root_path = os.environ['ROS_ARARA_ROOT']+"src/robot/"
# from movement.functions.movement import Movement
# from utils.json_handler import JsonHandler
# import strategy.strategy_utils as strategy_utils

# from strategy.strategy_utils import *
# from utils import math_utils

# path += '../parameters/bodies.json'

# jsonHandler = JsonHandler()
# bodies_unpack = jsonHandler.read(path, escape = True)

# HARDWARE = 1
# SOFTWARE = 0
# CENTER_Y = 65
# CENTER_X = 75
# SPEED_DEFAULT = 150
# MAX_X = 150
# LIMIT_RANGE = 75

# class NaiveAttackerController():


#     def __init__(self,_robot_obj,  _robot_body = "Nenhum", _debug_topic = None):
#         self.pid_type = SOFTWARE
#         self.robot = _robot_obj
#         self.speed = None
#         self.position = None
#         self.orientation = None
#         self.robot_speed = None
#         self.enemies_position = None
#         self.enemies_speed = None
#         self.ball_position = None
#         self.team_side = None
#         self.team_speed = None

#         self.position_buffer =[]
#         self.borders = [
#             UP_BORDER,
#             DOWN_BORDER,
#             LEFT_DOWN_BOTTOM_LINE,
#             LEFT_UP_BOTTOM_LINE,
#             RIGHT_DOWN_BOTTOM_LINE,
#             RIGHT_UP_BOTTOM_LINE,
#             LEFT_UP_CORNER,
#             LEFT_DOWN_CORNER,
#             RIGHT_UP_CORNER,
#             RIGHT_DOWN_CORNER
#             ]

#         self.robot_body = _robot_body
#         rospy.logfatal(self.robot_body)
#         self.pid_list = [bodies_unpack[self.robot_body]['KP'],
#                          bodies_unpack[self.robot_body]['KI'],
#                          bodies_unpack[self.robot_body]['KD']]

#         self.model = MyModel(state='stop')
#         self.NaiveAttacker = NaiveAttacker(self.model)

#         self.attack_goal = np.array([150.0, 65.0])

#         self.movement = Movement(self.pid_list, error=10, attack_goal=self.attack_goal, _debug_topic = _debug_topic)

#     def update_game_information(self):
#         """
#         Update game variables
#         :param position:
#         :param orientation:
#         :param speed
#         :param team_speed:
#         :param enemies_position:
#         :param enemies_speed:
#         :param team_side
#         :param ball_position:
#         """
#         self.position = self.robot.position
#         self.orientation = self.robot.orientation
#         self.speed = self.robot.speed
#         self.team_speed = self.robot.team_speed
#         self.enemies_position = self.robot.enemies_position
#         self.enemies_speed = self.robot.enemies_speed
#         self.ball_position = self.robot.ball_position
#         self.team_side = self.robot.team_side
#         self.attack_goal[0] = 0.0 + (not self.team_side)*150
#         self.movement.univet_field.update_attack_side(not self.team_side)
#         self.robot.add_to_buffer(self.position_buffer, 60, self.position)

#     def set_to_stop_game(self):
#         """
#         Set state stop in the state machine

#         :return: int, int
#         """
#         self.model.state = 'stop'
#         return 0, 0, 0

#     def in_stuck(self):


#         if (strategy_utils.section(self.position) == CENTER):
#             self.model.state = 'normal'
#         left, right, done = self.movement.move_to_point(
#                 speed = SPEED_DEFAULT,
#                 robot_position=self.position,
#                 robot_vector=[np.cos(self.orientation), np.sin(self.orientation)],
#                 goal_position = [65,65]
#             )

#         return left, right, self.pid_type


#     def in_normal_game(self):
#         """
#         Transitions in normal game state

#         :return: int, int
#         """
#         if self.NaiveAttacker.is_stop:
#             self.NaiveAttacker.stop_to_normal()

#         if self.robot.get_stuck(self.position) and (strategy_utils.section(self.position) != CENTER):
#            self.model.state = "stuck"

#         if self.NaiveAttacker.is_normal:
#             # Caso a bola esteja no campo de ataque
#             if strategy_utils.on_attack_side(self.ball_position, self.team_side, LIMIT_RANGE):
#                 # Verifica se a bola esta nas bordas
#                 if (strategy_utils.section(self.ball_position) in self.borders):
#                     self.NaiveAttacker.normal_to_border()
#                 else:
#                     self.NaiveAttacker.normal_to_reach_ball()
#             # Caso o a bola esteja na defesa manda o atacante para um ponto fixo
#             else:
#                 self.NaiveAttacker.normal_to_point()

#         if self.NaiveAttacker.is_stuck:import sys
# import os
# import rospy
# import numpy as np
# import math
# from naive_attacker_strategy import NaiveAttacker, MyModel
# sys.path[0] = path = root_path = os.environ['ROS_ARARA_ROOT']+"src/robot/"
# from movement.functions.movement import Movement
# from utils.json_handler import JsonHandler
# import strategy.strategy_utils as strategy_utils

# from strategy.strategy_utils import *
# from utils import math_utils

# path += '../parameters/bodies.json'

# jsonHandler = JsonHandler()
# bodies_unpack = jsonHandler.read(path, escape = True)

# HARDWARE = 1
# SOFTWARE = 0
# CENTER_Y = 65
# CENTER_X = 75
# SPEED_DEFAULT = 150
# MAX_X = 150
# LIMIT_RANGE = 75

# class NaiveAttackerController():


#     def __init__(self,_robot_obj,  _robot_body = "Nenhum", _debug_topic = None):
#         self.pid_type = SOFTWARE
#         self.robot = _robot_obj
#         self.speed = None
#         self.position = None
#         self.orientation = None
#         self.robot_speed = None
#         self.enemies_position = None
#         self.enemies_speed = None
#         self.ball_position = None
#         self.team_side = None
#         self.team_speed = None

#         self.position_buffer =[]
#         self.borders = [
#             UP_BORDER,
#             DOWN_BORDER,
#             LEFT_DOWN_BOTTOM_LINE,
#             LEFT_UP_BOTTOM_LINE,
#             RIGHT_DOWN_BOTTOM_LINE,
#             RIGHT_UP_BOTTOM_LINE,
#             LEFT_UP_CORNER,
#             LEFT_DOWN_CORNER,
#             RIGHT_UP_CORNER,
#             RIGHT_DOWN_CORNER
#             ]

#         self.robot_body = _robot_body
#         rospy.logfatal(self.robot_body)
#         self.pid_list = [bodies_unpack[self.robot_body]['KP'],
#                          bodies_unpack[self.robot_body]['KI'],
#                          bodies_unpack[self.robot_body]['KD']]

#         self.model = MyModel(state='stop')
#         self.NaiveAttacker = NaiveAttacker(self.model)

#         self.attack_goal = np.array([150.0, 65.0])

#         self.movement = Movement(self.pid_list, error=10, attack_goal=self.attack_goal, _debug_topic = _debug_topic)

#     def update_game_information(self):
#         """
#         Update game variables
#         :param position:
#         :param orientation:
#         :param speed
#         :param team_speed:
#         :param enemies_position:
#         :param enemies_speed:
#         :param team_side
#         :param ball_position:
#         """
#         self.position = self.robot.position
#         self.orientation = self.robot.orientation
#         self.speed = self.robot.speed
#         self.team_speed = self.robot.team_speed
#         self.enemies_position = self.robot.enemies_position
#         self.enemies_speed = self.robot.enemies_speed
#         self.ball_position = self.robot.ball_position
#         self.team_side = self.robot.team_side
#         self.attack_goal[0] = 0.0 + (not self.team_side)*150
#         self.movement.univet_field.update_attack_side(not self.team_side)
#         self.robot.add_to_buffer(self.position_buffer, 60, self.position)

#     def set_to_stop_game(self):
#         """
#         Set state stop in the state machine

#         :return: int, int
#         """
#         self.model.state = 'stop'
#         return 0, 0, 0

#     def in_stuck(self):


#         if (strategy_utils.section(self.position) == CENTER):
#             self.model.state = 'normal'
#         left, right, done = self.movement.move_to_point(
#                 speed = SPEED_DEFAULT,
#                 robot_position=self.position,
#                 robot_vector=[np.cos(self.orientation), np.sin(self.orientation)],
#                 goal_position = [65,65]
#             )

#         return left, right, self.pid_type


#     def in_normal_game(self):
#         """
#         Transitions in normal game state

#         :return: int, int
#         """
#         if self.NaiveAttacker.is_stop:
#             self.NaiveAttacker.stop_to_normal()

#         if self.robot.get_stuck(self.position) and (strategy_utils.section(self.position) != CENTER):
#            self.model.state = "stuck"

#         if self.NaiveAttacker.is_normal:
#             # Caso a bola esteja no campo de ataque
#             if strategy_utils.on_attack_side(self.ball_position, self.team_side, LIMIT_RANGE):
#                 # Verifica se a bola esta nas bordas
#                 if (strategy_utils.section(self.ball_position) in self.borders):
#                     self.NaiveAttacker.normal_to_border()
#                 else:
#                     self.NaiveAttacker.normal_to_reach_ball()
#             # Caso o a bola esteja na defesa manda o atacante para um ponto fixo
#             else:
#                 self.NaiveAttacker.normal_to_point()

#         if self.NaiveAttacker.is_stuck:
#             return self.in_stuck()

#         # Se estado esta como borda
#         if self.NaiveAttacker.is_border:
#             return self.in_border()

#         # Caso o estado estaja normal
#         elif self.NaiveAttacker.is_reach_ball:
#             return self.in_reach_ball()

#         # Caso a bola esteja no campo de defesa
#         elif self.NaiveAttacker.is_go_to_point:
#             return self.in_point()

#         # Estado de espera da bola
#         elif self.NaiveAttacker.is_wait_ball:
#             return self.in_wait_ball()

#         # Estado de chute
#         elif self.NaiveAttacker.is_spin:
#             return self.in_spin()

#         # Estado de corrida do robo na borda
#         elif self.NaiveAttacker.is_walk_border:
#             return self.in_walk_border()

#     def in_reach_ball(self):
#         """
#         Transitions in the reach ball state

#         :return: int, int
#         """
#         if not strategy_utils.on_attack_side(self.ball_position, self.team_side, LIMIT_RANGE):
#             self.NaiveAttacker.reach_ball_to_point()
#             return self.in_point()

#         # Caso o robo esteja na borda
#         if(strategy_utils.section(self.ball_position) in self.borders):

#             self.NaiveAttacker.reach_ball_to_border()
#             return self.in_border()

#         # Caso a bola esteja no range de chute
#         if (behind_ball(self.ball_position, self.position, self.team_side)):
#             self.NaiveAttacker.reach_ball_to_spin()
#             return self.in_spin()
#         else:

#             # Segue a bola com o univector
#             left, right, done = self.movement.do_univector(
#                 speed = SPEED_DEFAULT,
#                 robot_position=self.position,
#                 robot_vector=[np.cos(self.orientation), np.sin(self.orientation)],
#                 robot_speed=self.speed,
#                 obstacle_position=np.resize(self.enemies_position, (-1, 2)),
#                 obstacle_speed=[[0,0]]*5,
#                 ball_position=self.ball_position,
#                 only_forward=False,
#                 speed_prediction=True
#             )

#             return left, right, self.pid_type

#     def in_border(self):

#         if self.NaiveAttacker.is_stuck:
#             return self.in_stuck()

#         # Caso a bola esteja na defesa, manda o robo para o estado de espera
#         if not (strategy_utils.on_attack_side(self.ball_position, self.team_side, LIMIT_RANGE)):
#             self.NaiveAttacker.border_to_point()
#             return self.in_point()
#         else:
#             # Caso o robo ainda esteja na borda
#             if(strategy_utils.section(self.ball_position) in self.borders):

#                 if (distance_point(self.ball_position, self.position) < 8):
#                     self.NaiveAttacker.border_to_spin()
#                     return self.in_spin()

#                 robot_vector = [np.cos(self.orientation), np.sin(self.orientation)]
#                 goal_vector  = [self.ball_position[0]-self.position[0], self.ball_position[1]-self.position[1]]

#                 left, right, done = self.movement.do_univector_ball(
#                     speed = SPEED_DEFAULT,
#                     robot_position=self.position,
#                     robot_vector=[np.cos(self.orientation), np.sin(self.orientation)],
#                     robot_speed=self.speed,
#                     obstacle_position=np.resize(self.enemies_position, (-1, 2)),
#                     obstacle_speed=[[0,0]]*5,
#                     ball_position=self.ball_position,
#                 )

#                 return left, right, self.pid_type

#             # Caso a bola nao esteja na borda
#             else:
#                 self.NaiveAttacker.border_to_reach_ball()
#                 return self.in_reach_ball()

#     def in_point(self):

#         # Posicao de espera do robo
#         wait_position_x = CENTER_X + ((-1)**self.team_side)*20
#         position_center = [wait_position_x, CENTER_Y]

#         # Caso a bola estja no ataque muda o estado para o reach ball
#         if strategy_utils.on_attack_side(self.ball_position, self.team_side, 10):
#             self.NaiveAttacker.point_to_reach_ball()

#         # Verifica se a posicao atual do robo esta em uma margem de erro aceitavel
#         if (distance_point(self.position, position_center) < 10):
#             if not strategy_utils.on_attack_side(self.ball_position, self.team_side, LIMIT_RANGE):
#                 self.NaiveAttacker.point_to_wait_ball()
#         else:
#             if not strategy_utils.on_attack_side(self.ball_position, self.team_side, LIMIT_RANGE):
#                 # Manda o robo para a posicao de espera com o univector

#                 left, right, done = self.movement.move_to_point(
#                     speed = SPEED_DEFAULT,
#                     robot_position=self.position,
#                     robot_vector=[np.cos(self.orientation), np.sin(self.orientation)],
#                     goal_position = position_center
#                 )

#                 return left, right, self.pid_type

#         if self.NaiveAttacker.is_reach_ball:
#             return self.in_reach_ball()

#         elif self.NaiveAttacker.is_wait_ball:
#             return self.in_wait_ball()

#     def in_wait_ball(self):

#         # Caso a bola passe para o ataque, troca de espado para ataque
#         if strategy_utils.on_attack_side(self.ball_position, self.team_side, LIMIT_RANGE):
#             self.NaiveAttacker.wait_to_reach_ball()
#             return self.in_reach_ball()

#         # Caso contrario, apenas espera com o robo parado
#         robot_vector = [np.cos(self.orientation), np.sin(self.orientation)]
#         # Vetor da robo pra bola
#         goal_vector  = [self.ball_position[0]-self.position[0], self.ball_position[1]-self.position[1]]

#         #turn the front side to face the ball
#         left, right, done = self.movement.head_to(
#             robot_vector=(robot_vector),
#             goal_vector=(goal_vector),
#             multiplicator=0.5
#         )
#         return left, right, self.pid_type


#     def in_spin(self):
#         """[summary]

#         [Function to shoot theft if theft is behind the ball]

#         Returns:
#             [array (angle, speed)] -- [Returns to spin the robbies]
#         """
#         # Caso a bola nao estaja no range de chute persegue a bola
#         if (strategy_utils.distance_point(self.ball_position, self.position) > 7):
#             if (strategy_utils.section(self.position) != 10):
#                 self.NaiveAttacker.spin_to_border()
#             else:
#                 self.NaiveAttacker.spin_to_reach_ball()

#         if self.NaiveAttacker.is_reach_ball:
#             return self.in_reach_ball()

#         if self.NaiveAttacker.is_border:
#             return self.in_border()

#         # Pega o lado que o robo tem que girar
#         spin_side = spin_direction(self.ball_position, self.position, self.team_side)

#         # Chama a funcao de spin
#         if self.team_side == LEFT:
#             left, right, done = self.movement.spin(255, not spin_side)
#         else:
#             left, right, done = self.movement.spin(255, spin_side)


#         return left, right, SOFTWARE

#     def in_freeball_game(self):
#         """
#         Transitions in freeball state

#         :return: int, int
#         """
#         if self.NaiveAttacker.is_stop:
#             self.NaiveAttacker.stop_to_freeball()

#         if self.NaiveAttacker.is_freeball:
#             self.NaiveAttacker.freeball_to_normal()

#         if self.NaiveAttacker.is_normal:
#             return self.in_normal_game()

#     def in_penalty_game(self):
#         """
#         Transitions in penalty state

#         :return: int, int
#         """
#         if self.NaiveAttacker.is_stop:
#             self.NaiveAttacker.stop_to_penalty()

#         if self.NaiveAttacker.is_penalty:
#             self.NaiveAttacker.penalty_to_normal()

#         if self.NaiveAttacker.is_normal:
#             return self.in_normal_game()

#     def in_meta_game(self):
#         """
#         Transitions in meta state

#         :return: int, int
#         """
#         if self.NaiveAttacker.is_stop:
#             self.NaiveAttacker.stop_to_meta()

#         if self.NaiveAttacker.is_meta:
#             self.NaiveAttacker.meta_to_normal()

#         if self.NaiveAttacker.is_normal:
#             return self.in_normal_game()

#             return self.in_stuck()

#         # Se estado esta como borda
#         if self.NaiveAttacker.is_border:
#             return self.in_border()

#         # Caso o estado estaja normal
#         elif self.NaiveAttacker.is_reach_ball:
#             return self.in_reach_ball()

#         # Caso a bola esteja no campo de defesa
#         elif self.NaiveAttacker.is_go_to_point:
#             return self.in_point()

#         # Estado de espera da bola
#         elif self.NaiveAttacker.is_wait_ball:
#             return self.in_wait_ball()

#         # Estado de chute
#         elif self.NaiveAttacker.is_spin:
#             return self.in_spin()

#         # Estado de corrida do robo na borda
#         elif self.NaiveAttacker.is_walk_border:
#             return self.in_walk_border()

#     def in_reach_ball(self):
#         """
#         Transitions in the reach ball state

#         :return: int, int
#         """
#         if not strategy_utils.on_attack_side(self.ball_position, self.team_side, LIMIT_RANGE):
#             self.NaiveAttacker.reach_ball_to_point()
#             return self.in_point()

#         # Caso o robo esteja na borda
#         if(strategy_utils.section(self.ball_position) in self.borders):

#             self.NaiveAttacker.reach_ball_to_border()
#             return self.in_border()

#         # Caso a bola esteja no range de chute
#         if (behind_ball(self.ball_position, self.position, self.team_side)):
#             self.NaiveAttacker.reach_ball_to_spin()
#             return self.in_spin()
#         else:

#             # Segue a bola com o univector
#             left, right, done = self.movement.do_univector(
#                 speed = SPEED_DEFAULT,
#                 robot_position=self.position,
#                 robot_vector=[np.cos(self.orientation), np.sin(self.orientation)],
#                 robot_speed=self.speed,
#                 obstacle_position=np.resize(self.enemies_position, (-1, 2)),
#                 obstacle_speed=[[0,0]]*5,
#                 ball_position=self.ball_position,
#                 only_forward=False,
#                 speed_prediction=True
#             )

#             return left, right, self.pid_type

#     def in_border(self):

#         if self.NaiveAttacker.is_stuck:
#             return self.in_stuck()

#         # Caso a bola esteja na defesa, manda o robo para o estado de espera
#         if not (strategy_utils.on_attack_side(self.ball_position, self.team_side, LIMIT_RANGE)):
#             self.NaiveAttacker.border_to_point()
#             return self.in_point()
#         else:
#             # Caso o robo ainda esteja na borda
#             if(strategy_utils.section(self.ball_position) in self.borders):

#                 if (distance_point(self.ball_position, self.position) < 8):
#                     self.NaiveAttacker.border_to_spin()
#                     return self.in_spin()

#                 robot_vector = [np.cos(self.orientation), np.sin(self.orientation)]
#                 goal_vector  = [self.ball_position[0]-self.position[0], self.ball_position[1]-self.position[1]]

#                 left, right, done = self.movement.do_univector_ball(
#                     speed = SPEED_DEFAULT,
#                     robot_position=self.position,
#                     robot_vector=[np.cos(self.orientation), np.sin(self.orientation)],
#                     robot_speed=self.speed,
#                     obstacle_position=np.resize(self.enemies_position, (-1, 2)),
#                     obstacle_speed=[[0,0]]*5,
#                     ball_position=self.ball_position,
#                 )

#                 return left, right, self.pid_type

#             # Caso a bola nao esteja na borda
#             else:
#                 self.NaiveAttacker.border_to_reach_ball()
#                 return self.in_reach_ball()

#     def in_point(self):

#         # Posicao de espera do robo
#         wait_position_x = CENTER_X + ((-1)**self.team_side)*20
#         position_center = [wait_position_x, CENTER_Y]

#         # Caso a bola estja no ataque muda o estado para o reach ball
#         if strategy_utils.on_attack_side(self.ball_position, self.team_side, 10):
#             self.NaiveAttacker.point_to_reach_ball()

#         # Verifica se a posicao atual do robo esta em uma margem de erro aceitavel
#         if (distance_point(self.position, position_center) < 10):
#             if not strategy_utils.on_attack_side(self.ball_position, self.team_side, LIMIT_RANGE):
#                 self.NaiveAttacker.point_to_wait_ball()
#         else:
#             if not strategy_utils.on_attack_side(self.ball_position, self.team_side, LIMIT_RANGE):
#                 # Manda o robo para a posicao de espera com o univector

#                 left, right, done = self.movement.move_to_point(
#                     speed = SPEED_DEFAULT,
#                     robot_position=self.position,
#                     robot_vector=[np.cos(self.orientation), np.sin(self.orientation)],
#                     goal_position = position_center
#                 )

#                 return left, right, self.pid_type

#         if self.NaiveAttacker.is_reach_ball:
#             return self.in_reach_ball()

#         elif self.NaiveAttacker.is_wait_ball:
#             return self.in_wait_ball()

#     def in_wait_ball(self):

#         # Caso a bola passe para o ataque, troca de espado para ataque
#         if strategy_utils.on_attack_side(self.ball_position, self.team_side, LIMIT_RANGE):
#             self.NaiveAttacker.wait_to_reach_ball()
#             return self.in_reach_ball()

#         # Caso contrario, apenas espera com o robo parado
#         robot_vector = [np.cos(self.orientation), np.sin(self.orientation)]
#         # Vetor da robo pra bola
#         goal_vector  = [self.ball_position[0]-self.position[0], self.ball_position[1]-self.position[1]]

#         #turn the front side to face the ball
#         left, right, done = self.movement.head_to(
#             robot_vector=(robot_vector),
#             goal_vector=(goal_vector),
#             multiplicator=0.5
#         )
#         return left, right, self.pid_type


#     def in_spin(self):
#         """[summary]

#         [Function to shoot theft if theft is behind the ball]

#         Returns:
#             [array (angle, speed)] -- [Returns to spin the robbies]
#         """
#         # Caso a bola nao estaja no range de chute persegue a bola
#         if (strategy_utils.distance_point(self.ball_position, self.position) > 7):
#             if (strategy_utils.section(self.position) != 10):
#                 self.NaiveAttacker.spin_to_border()
#             else:
#                 self.NaiveAttacker.spin_to_reach_ball()

#         if self.NaiveAttacker.is_reach_ball:
#             return self.in_reach_ball()

#         if self.NaiveAttacker.is_border:
#             return self.in_border()

#         # Pega o lado que o robo tem que girar
#         spin_side = spin_direction(self.ball_position, self.position, self.team_side)

#         # Chama a funcao de spin
#         if self.team_side == LEFT:
#             left, right, done = self.movement.spin(255, not spin_side)
#         else:
#             left, right, done = self.movement.spin(255, spin_side)


#         return left, right, SOFTWARE

#     def in_freeball_game(self):
#         """
#         Transitions in freeball state

#         :return: int, int
#         """
#         if self.NaiveAttacker.is_stop:
#             self.NaiveAttacker.stop_to_freeball()

#         if self.NaiveAttacker.is_freeball:
#             self.NaiveAttacker.freeball_to_normal()

#         if self.NaiveAttacker.is_normal:
#             return self.in_normal_game()

#     def in_penalty_game(self):
#         """
#         Transitions in penalty state

#         :return: int, int
#         """
#         if self.NaiveAttacker.is_stop:
#             self.NaiveAttacker.stop_to_penalty()

#         if self.NaiveAttacker.is_penalty:
#             self.NaiveAttacker.penalty_to_normal()

#         if self.NaiveAttacker.is_normal:
#             return self.in_normal_game()

#     def in_meta_game(self):
#         """
#         Transitions in meta state

#         :return: int, int
#         """
#         if self.NaiveAttacker.is_stop:
#             self.NaiveAttacker.stop_to_meta()

#         if self.NaiveAttacker.is_meta:
#             self.NaiveAttacker.meta_to_normal()

#         if self.NaiveAttacker.is_normal:
#             return self.in_normal_game()
