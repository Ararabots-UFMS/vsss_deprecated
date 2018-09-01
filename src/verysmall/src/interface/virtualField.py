import cv2 as cv
import math
import numpy as np
import rospy
import time
from auxiliary import *
import copy


class virtualField():
    """ class constructor 

        constroi um objeto campo virtual com tamanho padrao,
        se tamanho nao informado, de 850 x 650 pixels e flag rbg
        (Red, Green, Blue), onde:

          parametros do construtor:
            width - largura da imagem do campo virtual
            height - altura da imagem do campo virtual
            is_rgb - flag tipo de cor utilizada

          atributos do objeto:
            width - largura da imagem do campo virtual
            height - altura da imagem do campo virtual
            field - imagem a ser mostrada na interface
            raw field - imagem com apenas as linhas do campo desenhadas (instanciada como uma imagem preta)
            widht_conv - fator de conversao cm x proporcao em pixels para a largura
            height_conv - fator de conversao cm x proporcao em pixels para a altura
            angle_conversion_factor - fator de conversao de angulo de rotacao do robo
            field_origin - ponto, em proporcao de pixels, definido como origem (0,0) do campo virtual
            ball_radius -  tamanho da bola, em proporcao
            mark_radius -  tamanho das marcas de freeball, em propocao
            robot_side_size - tamanho do nosso robo, em proporcao
            away_team_radius - tamanho do robo adversario, em proporcao
            text_font - fonte a ser utilizada nos textos mostrados
            colors - dicionario de cores utilizado pelo campo virtual

          saida:
            objeto campo virtual
        
        """

    def __init__(self, width=850, height=650, is_rgb=False):
        # 1 cm for 4 pixels
        self.width = width
        self.height = height
        self.field = None
        self.raw_field = np.zeros((self.height, self.width, 3), np.uint8)

        self.width_conv = 0.88136 * self.width / 150
        self.height_conv = 0.998 * self.height / 130
        self.angle_conversion_factor = 180 / math.pi

        self.field_origin = (self.proportion_width(5.882), self.proportion_height(99.9))
        self.ball_radius = self.proportion_average(1.5)
        self.mark_radius = self.proportion_average(0.3)
        self.robot_side_size = self.proportion_average(4.5)
        self.away_team_radius = self.proportion_average(2.5)

        self.text_font = cv.FONT_HERSHEY_SIMPLEX

        if is_rgb:
            self.colors = {"blue": [0, 0, 255],
                           "orange": [255, 100, 0],
                           "white": [255, 255, 255],
                           "yellow": [255, 255, 0],
                           "red": [255, 0, 0],
                           "green": [116, 253, 0],
                           "dgreen": [0, 104, 0],
                           "black": [0, 0, 0],
                           "mark": [30, 30, 30],
                           "gray": [150, 150, 150],
                           "magenta": [202, 31, 123]
                           }
        else:
            self.colors = {"blue": [255, 0, 0],
                           "orange": [0, 100, 255],
                           "white": [255, 255, 255],
                           "yellow": [0, 255, 255],
                           "red": [0, 0, 255],
                           "green": [0, 104, 0],
                           "dgreen": [0, 253, 116],
                           "black": [0, 0, 0],
                           "mark": [30, 30, 30],
                           "gray": [150, 150, 150],
                           "magenta": [123, 31, 202]
                           }


    '''  delay no plot, ajuste/teste de fps'''
    def pause(self, n):
        """system pause for n FPS"""
        time.sleep(1.0 / n)




    ''' recebe uma imagem preta e faz nela, o plot de todas as linhas do campo, markers e etc.
        
        entrada
          field eh a imagem que recebera o plot 
        

          cada retangulo recebe dois vertices opostos e uma cor
          cada linha recebe dois pontos e uma cor
          cada ciculo recebe o centro, o raio e a cor
       
        saida
          uma imagem de fundo preto com todas as linhas do campo desenhadas 


        '''

    def plot_arena(self, field):

        # border line
        cv.rectangle(field, (self.proportion_width(5.882), self.proportion_height(0.1)),
                     (self.proportion_width(94.018), self.proportion_height(99.9)), self.colors["white"])

        # midfield line
        cv.line(field, (self.proportion_width(50), self.proportion_height(0.1)),
                (self.proportion_width(50), self.proportion_height(99.9)), self.colors["white"])

        # left goal and outfield areas
        cv.rectangle(field, (self.proportion_width(0.1), self.proportion_height(34.615)),
                     (self.proportion_width(5.882), self.proportion_height(65.385)), self.colors["white"])

        # right goal and outfield areas
        cv.rectangle(field, (self.proportion_width(94.018), self.proportion_height(34.615)),
                     (self.proportion_width(99.9), self.proportion_height(65.385)), self.colors["white"])

        # left and rigth goal areas
        cv.rectangle(field, (self.proportion_width(5.882), self.proportion_height(23.076)),
                     (self.proportion_width(14.705), self.proportion_height(76.924)), self.colors["white"])
        cv.rectangle(field, (self.proportion_width(85.295), self.proportion_height(23.076)),
                     (self.proportion_width(94.018), self.proportion_height(76.924)), self.colors["white"])

        # left and right ellipses
        cv.ellipse(field, (self.proportion_width(14.705), self.proportion_height(50.0)),
                   (self.proportion_width(2.941), self.proportion_height(7.692)), 180, 90.0, 270.0, self.colors["white"])
        cv.ellipse(field, (self.proportion_width(85.295), self.proportion_height(50.0)),
                   (self.proportion_width(2.941), self.proportion_height(7.692)), 0, 90.0, 270.0, self.colors["white"])

        # corner lines
        cv.line(field, (self.proportion_width(10), self.proportion_height(0.1)),
                (self.proportion_width(5.882), self.proportion_height(5.384)), self.colors["white"])
        cv.line(field, (self.proportion_width(90), self.proportion_height(0.1)),
                (self.proportion_width(94.018), self.proportion_height(5.384)), self.colors["white"])
        cv.line(field, (self.proportion_width(5.882), self.proportion_height(94.616)),
                (self.proportion_width(10), self.proportion_height(99.9)), self.colors["white"])
        cv.line(field, (self.proportion_width(94.018), self.proportion_height(94.616)),
                (self.proportion_width(90), self.proportion_height(99.9)), self.colors["white"])

        # midfield circle
        cv.circle(field, (self.proportion_width(50), self.proportion_height(50)), self.proportion_average(13),
                  self.colors["white"])

        # left freeball markers
        cv.line(field, (self.proportion_width(26.941), self.proportion_height(19.230)),
                (self.proportion_width(28.941), self.proportion_height(19.230)), self.colors["white"], 1)
        cv.line(field, (self.proportion_width(27.941), self.proportion_height(20.530)),
                (self.proportion_width(27.941), self.proportion_height(17.930)), self.colors["white"], 1)

        cv.line(field, (self.proportion_width(26.941), self.proportion_height(80.770)),
                (self.proportion_width(28.941), self.proportion_height(80.770)), self.colors["white"], 1)
        cv.line(field, (self.proportion_width(27.941), self.proportion_height(82.070)),
                (self.proportion_width(27.941), self.proportion_height(79.470)), self.colors["white"], 1)

        cv.line(field, (self.proportion_width(26.941), self.proportion_height(50.0)),
                (self.proportion_width(28.941), self.proportion_height(50.0)), self.colors["white"], 1)
        cv.line(field, (self.proportion_width(27.941), self.proportion_height(51.3)),
                (self.proportion_width(27.941), self.proportion_height(48.7)), self.colors["white"], 1)

        # rigth freeball markers
        cv.line(field, (self.proportion_width(71.059), self.proportion_height(19.230)),
                (self.proportion_width(73.059), self.proportion_height(19.230)), self.colors["white"], 1)
        cv.line(field, (self.proportion_width(72.059), self.proportion_height(17.930)),
                (self.proportion_width(72.059), self.proportion_height(20.530)), self.colors["white"], 1)

        cv.line(field, (self.proportion_width(71.059), self.proportion_height(80.770)),
                (self.proportion_width(73.059), self.proportion_height(80.770)), self.colors["white"], 1)
        cv.line(field, (self.proportion_width(72.059), self.proportion_height(79.470)),
                (self.proportion_width(72.059), self.proportion_height(82.070)), self.colors["white"], 1)

        cv.line(field, (self.proportion_width(71.059), self.proportion_height(50.0)),
                (self.proportion_width(73.059), self.proportion_height(50.0)), self.colors["white"], 1)
        cv.line(field, (self.proportion_width(72.059), self.proportion_height(48.7)),
                (self.proportion_width(72.059), self.proportion_height(51.3)), self.colors["white"], 1)

        # left robot markers
        cv.circle(field, (self.proportion_width(16.176), self.proportion_height(19.230)), self.mark_radius,
                  self.colors["gray"], -1)
        cv.circle(field, (self.proportion_width(16.176), self.proportion_height(80.770)), self.mark_radius,
                  self.colors["gray"], -1)
        cv.circle(field, (self.proportion_width(39.705), self.proportion_height(19.230)), self.mark_radius,
                  self.colors["gray"], -1)
        cv.circle(field, (self.proportion_width(39.705), self.proportion_height(80.770)), self.mark_radius,
                  self.colors["gray"], -1)

        # right robot markers
        cv.circle(field, (self.proportion_width(83.824), self.proportion_height(19.230)), self.mark_radius,
                  self.colors["gray"], -1)
        cv.circle(field, (self.proportion_width(83.824), self.proportion_height(80.770)), self.mark_radius,
                  self.colors["gray"], -1)
        cv.circle(field, (self.proportion_width(60.295), self.proportion_height(19.230)), self.mark_radius,
                  self.colors["gray"], -1)
        cv.circle(field, (self.proportion_width(60.295), self.proportion_height(80.770)), self.mark_radius,
                  self.colors["gray"], -1)



        ''' plot_ball 

             recebe a coordenada do centro da bola,
             verifica onde a bola esta e caso esteja
             dentro de uma das areas ou um dos gols,
             colore a mesma antes.

             faz um deepcopy da imagem com as linhas
             do campo plotadas

             validate - copia da info crua da visao para verificar/validar
                      posicao da bola
             ball_center - posicao convertida de cm para pixels e a partir da origem do campo virtual

             sequencia de ifs verifica se bola dentro do gol ou da area do gol

             por final plota a bola e ignora objetos fora do campo caso a visao retorne (0,0)

            saida - a imagem do campo com a bola impressa na posicao lida do ros e, caso seja verdadeiro
            area ou gol em cor destacada '''

    def plot_ball(self, ball_center):

        self.field = copy.deepcopy(self.raw_field)

        validate = ball_center

        ball_center = unit_convert(ball_center, self.width_conv, self.height_conv)
        ball_center = position_from_origin(ball_center, self.field_origin)



        #validacao gol esquerdo
        if (validate[0] < 0.1 and 45.0 < validate[1] < 85.0):
            cv.rectangle(self.field, (self.proportion_width(0.1), self.proportion_height(34.615)),
                         (self.proportion_width(5.882), self.proportion_height(65.385)), self.colors["green"], -1)

        #validacao gol direito
        elif (validate[0] > 150.0 and 45.0 < validate[1] < 85.0):
            cv.rectangle(self.field, (self.proportion_width(94.018), self.proportion_height(34.615)),
                         (self.proportion_width(99.9), self.proportion_height(65.385)), self.colors["green"], -1)

        #validacao area esquerda
        elif (15.0 >= validate[0] > 0.0 and 30.0 < validate[1] < 100.0 or (
                ((validate[0] - 15) ** 2 / (10) ** 2) + ((validate[1] - 65) ** 2 / (5) ** 2) < 1)):

            cv.rectangle(self.field, (self.proportion_width(5.882), self.proportion_height(23.076)),
                         (self.proportion_width(14.705), self.proportion_height(76.924)), self.colors["dgreen"], -1)

            cv.ellipse(self.field, (self.proportion_width(14.705), self.proportion_height(50.0)),
                       (self.proportion_width(2.941), self.proportion_height(7.692)), 180, 90.0, 270.0,
                       self.colors["dgreen"], -1)

        #validacao area direita
        elif (150.0 > validate[0] >= 135.0 and 30.0 < validate[1] < 100.0 or (
                ((validate[0] - 135) ** 2 / (10) ** 2) + ((validate[1] - 65) ** 2 / (5) ** 2) < 1)):
            cv.rectangle(self.field, (self.proportion_width(85.295), self.proportion_height(23.076)),
                         (self.proportion_width(94.018), self.proportion_height(76.924)), self.colors["dgreen"], -1)
            cv.ellipse(self.field, (self.proportion_width(85.295), self.proportion_height(50.0)),
                       (self.proportion_width(2.941), self.proportion_height(7.692)), 0, 90.0, 270.0,
                       self.colors["dgreen"], -1)

        else:
            pass


        #validacao posicao da bola dentro dos limites do campo
        if validate[0] != 0 or validate[1] !=0:
            cv.circle(self.field, ball_center, self.ball_radius, self.colors["orange"], -1)




    '''  plot_robots - plota os robos de um time em uma determinada cor
          parametros
            - robot_list - lista com posicoes [x,y] de cada robo do time
            - robot_vector - lista com orientacoes dos robos, na ordem da lista anterior
            - color - cor, dentro do dicionario da classe (ou tupla de cor) que os robos devem ser plotados
            - is_away - flag para diferenciar nosso time do time adversario e plotar cada time de forma diferente
          funcionamento
            percorre a lista de robos, verifica se a posicao e valida, diferencia o robo pela flag is_away, 
            converte a informacao recebida para pixels e faz o plot do robo no campo 

          saida
            imagem do campo com os robos impressos na mesma '''
    
    def plot_robots(self, robot_list, robot_vector, color, is_away=False):
        """plots all contours from all robots of a designed color given as parameter"""
        index = 0
        length = len(robot_list)

        while index < length:

            if robot_list[index][0] != 0 or robot_list[index][1] != 0:

                if is_away:
                    center = position_from_origin(
                        unit_convert(robot_list[index], self.width_conv, self.height_conv), self.field_origin)
                    cv.circle(self.field, center, self.away_team_radius, color, -1)
                    cv.putText(self.field, str(index), center, self.text_font, 0.5, self.colors["white"], 1, cv.LINE_AA)
                else:
                    angle = robot_vector[index]
                    center = position_from_origin(
                        unit_convert(robot_list[index], self.width_conv, self.height_conv), self.field_origin)
                    contour = (center, (self.robot_side_size, self.robot_side_size), -angle * self.angle_conversion_factor)
                    n_contour = cv.boxPoints(contour)
                    n_contour = np.int0(n_contour)
                    cv.drawContours(self.field, [n_contour], -1, color, -1)
                    cv.arrowedLine(self.field, center, (int(center[0] + math.cos(angle) * self.robot_side_size),
                                                        int(center[1] + math.sin(-angle) * self.robot_side_size)),
                                   self.colors["red"], 2)
                    cv.putText(self.field, str(index), center, self.text_font, 0.5, self.colors["black"], 1, cv.LINE_AA)

            index = index + 1





            ''' metodo unico para unificar os plots, recebe todas as informacoes necessarias para plot de cada um dos times e 
                e da bola. tambem recebe informacoes de fps do topico e da visao 

                entrada
                  valores de leitura do ros (centro, lista de robos(ambos os times), lista de vetores (ambos os times), cores dos robos (ambos os times), leitura de fps
                  de visao e ros, flag is away)
                saida
                  imagem completa com todos os robos, a bola e o campo impressos, que sera mostrada na interface do sistema
                '''
    def plot(self, ball_center, robotlistH, robotvecH, colorH, robotlistA, robotvecA, colorA, fps_vision, fps_topic, is_away):
        
        self.plot_ball(ball_center)
        self.plot_robots(robotlistH, robotvecH, colorH)
        self.plot_robots(robotlistA, robotvecA, colorA, is_away)


        ''' usar no maximo 1 casa decimal, substituir os parametros 
            de entrada do metodo pelos lidos no topico e substituir os 
            valores de exemplo no plot abaixo '''
        cv.putText(self.field, "Topic", (self.proportion_width(0.3), self.proportion_height(2.0)), self.text_font, 0.35, self.colors["white"], 1, cv.LINE_AA)
        cv.putText(self.field, "FPS", (self.proportion_width(0.3), self.proportion_height(4.0)), self.text_font, 0.35, self.colors["white"], 1, cv.LINE_AA)
        cv.putText(self.field, str(fps_topic), (self.proportion_width(0.2), self.proportion_height(7.0)), self.text_font, 0.55, self.colors["green"], 1, cv.LINE_AA)
        #cv.putText(self.field, "60.0", (self.proportion_width(0.1), self.proportion_height(7.0)), self.text_font, 0.55, self.colors["green"], 1, cv.LINE_AA)
        
        cv.putText(self.field, "Vision", (self.proportion_width(0.3), self.proportion_height(11.0)), self.text_font, 0.35, self.colors["white"], 1, cv.LINE_AA)
        cv.putText(self.field, "FPS", (self.proportion_width(0.3), self.proportion_height(13.0)), self.text_font, 0.35, self.colors["white"], 1, cv.LINE_AA)
        cv.putText(self.field, str(fps_vision), (self.proportion_width(0.2), self.proportion_height(16.0)), self.text_font, 0.55, self.colors["green"], 1, cv.LINE_AA)
        #cv.putText(self.field, "60.0", (self.proportion_width(0.1), self.proportion_height(16.0)), self.text_font, 0.55, self.colors["green"], 1, cv.LINE_AA)






    def proportion_height(self, proportion):
        """Returns the Y value for the designed vertical screen proportion"""
        return int(self.height * proportion / 100)

    def proportion_width(self, proportion):
        """Returns the X value for the designed horizontal screen proportion"""
        return int(self.width * proportion / 100)

    def proportion_average(self, size):
        return int(((self.width + self.height) * 0.5) * size / 100)
