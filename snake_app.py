from PyQt5 import QtGui, QtCore, QtWidgets
from PyQt5.QtCore import Qt
import sys
from typing import List
from snake import *
import numpy as np
from nn_viz import NeuralNetworkViz
from neural_network import FeedForwardNetwork, sigmoid, linear, relu
from settings import settings
from genetic_algorithm.population import Population
from genetic_algorithm.selection import elitism_selection, roulette_wheel_selection, tournament_selection
from genetic_algorithm.mutation import gaussian_mutation, random_uniform_mutation
from genetic_algorithm.crossover import simulated_binary_crossover as SBX
from genetic_algorithm.crossover import uniform_binary_crossover, single_point_binary_crossover, single_row_binary_crossover, uniform_crossover_test
from math import sqrt
import random
import csv


SQUARE_SIZE = (12, 12)



class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self._SBX_eta = self.settings['SBX_eta']
        self._mutation_bins = np.cumsum([self.settings['probability_gaussian'],
                                        self.settings['probability_random_uniform']
        ])
        self._crossover_bins = np.cumsum([self.settings['probability_SBX'],
                                         self.settings['probability_SPBX']
        ])
        self._SPBX_type = self.settings['SPBX_type'].lower()
        self._mutation_rate = self.settings['mutation_rate']

        # Determine size of next gen based off selection type
        self._next_gen_size = None
        if self.settings['selection_type'].lower() == 'plus':
            self._next_gen_size = self.settings['num_parents'] + self.settings['num_offspring']
        elif self.settings['selection_type'].lower() == 'comma':
            self._next_gen_size = self.settings['num_offspring']
        else:
            raise Exception('Selection type "{}" is invalid'.format(self.settings['selection_type']))

        
        self.board_size = settings['board_size']
        self.border = (10, 10, 10, 10)  # Left, Top, Right, Bottom
        self.snake_widget_width = SQUARE_SIZE[0] * self.board_size[0]
        self.snake_widget_height = SQUARE_SIZE[1] * self.board_size[1]

        self.top = 150
        self.left = 150
        self.width = self.snake_widget_width + 700 + self.border[0] + self.border[2]
        self.height = self.snake_widget_height + self.border[1] + self.border[3] + 200
        
        individuals: List[Individual] = []

        for _ in range(self.settings['population_size']):
            individual = Snake(self.board_size, hidden_layer_architecture=self.settings['hidden_network_architecture'],
                              hidden_activation=self.settings['hidden_layer_activation'],
                              output_activation=self.settings['output_layer_activation'],
                              lifespan=self.settings['lifespan'])
            individuals.append(individual)

        self.best_fitness = 0
        self.best_score = 0

        
        # snake = Snake(snake.board_size, chromosome=snake.network.params, start_pos=Point(5,5), hidden_layer_architecture=snake.hidden_layer_architecture)
        # self.population.individuals[0] = snake

        # for individual in self.population.individuals:
        #     individual.encode_chromosome()

        self._current_individual = 0
        # for i in range(0, 65+1):
        #     snake = load_snake('test_selection', 'best_ind' + str(i))
        #     new_snake = Snake(snake.board_size, chromosome=snake.network.params, hidden_layer_architecture=snake.hidden_layer_architecture)
        #     individuals.append(new_snake)

        # random.shuffle(individuals)

        self.population = Population(individuals)


        # snake = load_snake('1_0_MPL_500_1500', 'best_ind350')
        # # snake = load_snake('test_del2', 'best_ind73')
        # snake = Snake((20,20), chromosome=snake.network.params, hidden_layer_architecture=snake.hidden_layer_architecture,
        #               apple_seed=snake.apple_seed, starting_direction=snake.starting_direction, start_pos=snake.start_pos)
        # self.population.individuals[0] = snake
        self.snake = self.population.individuals[self._current_individual]
        # self.snake = snake
        self.current_generation = 0

        self.init_window()

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update)
        # self.timer.setInterval(10)
        self.timer.start(1000./1000)

        # self.show()
        # self.update()

    def init_window(self):
        self.centralWidget = QtWidgets.QWidget(self)
        self.setCentralWidget(self.centralWidget)
        self.setWindowTitle('Snake AI')
        self.setGeometry(self.top, self.left, self.width, self.height)

        # Create the Neural Network window
        self.nn_viz_window = NeuralNetworkViz(self.centralWidget, self.snake)
        self.nn_viz_window.setGeometry(QtCore.QRect(0, 0, 600, self.snake_widget_height + self.border[1] + self.border[3] + 200))
        self.nn_viz_window.setObjectName('nn_viz_window')

        # Create SnakeWidget window
        self.snake_widget_window = SnakeWidget(self.centralWidget, self.board_size, self.snake)
        self.snake_widget_window.setGeometry(QtCore.QRect(600 + self.border[0], self.border[1], self.snake_widget_width, self.snake_widget_height))
        self.snake_widget_window.setObjectName('snake_widget_window')

        # Genetic Algorithm Stats window
        self.ga_window = GeneticAlgoWidget(self.centralWidget, settings)
        self.ga_window.setGeometry(QtCore.QRect(600, self.border[1] + self.border[3] + self.snake_widget_height, self.snake_widget_width + self.border[0] + self.border[2] + 50, 200))
        self.ga_window.setObjectName('ga_window')


    def update(self) -> None:
        self.snake_widget_window.update()
        self.nn_viz_window.update()
        # Current individual is alive
        if self.snake.is_alive:
            self.snake.move()
            if self.snake.score > self.best_score:
                self.best_score = self.snake.score
                self.ga_window.best_score_label.setText(str(self.snake.score))
        # Current individual is dead         
        else:
            # Calculate fitness of current individual
            self.snake.calculate_fitness()
            fitness = self.snake.fitness
            print(self._current_individual, fitness)
            if fitness > self.best_fitness:
                self.best_fitness = fitness
                self.ga_window.best_fitness_label.setText(str(fitness))

            self._current_individual += 1
            
            # Next generation
            if (self.current_generation > 0 and self._current_individual == self._next_gen_size) or\
                (self.current_generation == 0 and self._current_individual == settings['population_size']):
                print('=== 1|0 mu (eta 100, life 5) + lambda (500, 1500) ===')
                print('======================= Gneration {} ======================='.format(self.current_generation))
                print('----Max fitness:', self.population.fittest_individual.fitness)
                print('----Best Score:', self.population.fittest_individual.score)
                print('----Average fitness:', self.population.average_fitness)
                save_snake('1|0_MPL_500_1500_eta100_life5', 'best_ind' + str(self.current_generation), self.population.fittest_individual, settings)
                self.next_generation()
            else:
                
                self.ga_window.current_individual_label.setText('{}/{}'.format(self._current_individual + 1, settings['population_size']))

            self.snake = self.population.individuals[self._current_individual]
            self.snake_widget_window.snake = self.snake
            self.nn_viz_window.snake = self.snake

    def next_generation(self):
        self._increment_generation()
        self._current_individual = 0

        # Calculate fitness of individuals
        for individual in self.population.individuals:
            individual.calculate_fitness()

        save_stats(self.population, r'C:\Users\wilkerso\dev\SnakeAI\stats', '1_0_MPL_500_1500_eta100_life5')
        
        self.population.individuals = elitism_selection(self.population, self.settings['population_size'])
        
        random.shuffle(self.population.individuals)
        next_pop: List[Snake] = []

        # parents + offspring selection type
        if self.settings['selection_type'].lower() == 'plus':
            # Decrement lifespan
            for individual in self.population.individuals:
                individual.lifespan -= 1

            for individual in self.population.individuals:
                params = individual.network.params
                board_size = individual.board_size
                hidden_layer_architecture = individual.hidden_layer_architecture
                hidden_activation = individual.hidden_activation
                output_activation = individual.output_activation
                lifespan = individual.lifespan

                start_pos = individual.start_pos
                apple_seed = individual.apple_seed
                starting_direction = individual.starting_direction
                #@TODO: remove the seed, start pos and direction
                if lifespan > 0:
                    s = Snake(board_size, chromosome=params, hidden_layer_architecture=hidden_layer_architecture,
                            hidden_activation=hidden_activation, output_activation=output_activation,
                            lifespan=lifespan)#,
                            #   start_pos=start_pos, starting_direction=starting_direction, apple_seed=apple_seed)
                    next_pop.append(s)


        while len(next_pop) < self._next_gen_size:
            p1, p2 = roulette_wheel_selection(self.population, 2)

            L = len(p1.network.layer_nodes)
            c1_params = {}
            c2_params = {}

            # Each W_l and b_l are treated as their own chromosome.
            # Because of this I need to perform crossover/mutation on each chromosome between parents
            for l in range(1, L):
                p1_W_l = p1.network.params['W' + str(l)]
                p2_W_l = p2.network.params['W' + str(l)]  
                p1_b_l = p1.network.params['b' + str(l)]
                p2_b_l = p2.network.params['b' + str(l)]

                # Crossover
                # @NOTE: I am choosing to perform the same type of crossover on the weights and the bias.
                c1_W_l, c2_W_l, c1_b_l, c2_b_l = self._crossover(p1_W_l, p2_W_l, p1_b_l, p2_b_l)

                # Mutation
                # @NOTE: I am choosing to perform the same type of mutation on the weights and the bias.
                self._mutation(c1_W_l, c2_W_l, c1_b_l, c2_b_l)

                # Assign children from crossover/mutation
                c1_params['W' + str(l)] = c1_W_l
                c2_params['W' + str(l)] = c2_W_l
                c1_params['b' + str(l)] = c1_b_l
                c2_params['b' + str(l)] = c2_b_l

                # Clip to [-1, 1]
                np.clip(c1_params['W' + str(l)], -1, 1, out=c1_params['W' + str(l)])
                np.clip(c2_params['W' + str(l)], -1, 1, out=c2_params['W' + str(l)])
                np.clip(c1_params['b' + str(l)], -1, 1, out=c1_params['b' + str(l)])
                np.clip(c2_params['b' + str(l)], -1, 1, out=c2_params['b' + str(l)])

            # Create children from chromosomes generated above
            c1 = Snake(p1.board_size, chromosome=c1_params, hidden_layer_architecture=p1.hidden_layer_architecture,
                       hidden_activation=p1.hidden_activation, output_activation=p1.output_activation,
                       lifespan=self.settings['lifespan'])
            c2 = Snake(p2.board_size, chromosome=c2_params, hidden_layer_architecture=p2.hidden_layer_architecture,
                       hidden_activation=p2.hidden_activation, output_activation=p2.output_activation,
                       lifespan=self.settings['lifespan'])

            # Add children to the next generation
            next_pop.extend([c1, c2])
        
        # Set the next generation
        random.shuffle(next_pop)
        self.population.individuals = next_pop

    def _increment_generation(self):
        self.current_generation += 1
        self.ga_window.current_generation_label.setText(str(self.current_generation + 1))

    def _crossover(self, parent1_weights: np.ndarray, parent2_weights: np.ndarray,
                   parent1_bias: np.ndarray, parent2_bias: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        rand_crossover = random.random()
        crossover_bucket = np.digitize(rand_crossover, self._crossover_bins)
        child1_weights, child2_weights = None, None
        child1_bias, child2_bias = None, None

        # SBX
        if crossover_bucket == 0:
            child1_weights, child2_weights = SBX(parent1_weights, parent2_weights, self._SBX_eta)
            child1_bias, child2_bias =  SBX(parent1_bias, parent2_bias, self._SBX_eta)

        # Single point binary crossover (SPBX)
        elif crossover_bucket == 1:
            child1_weights, child2_weights = single_point_binary_crossover(parent1_weights, parent2_weights, major=self._SPBX_type)
            child1_bias, child2_bias =  single_point_binary_crossover(parent1_bias, parent2_bias, major=self._SPBX_type)
        
        else:
            raise Exception('Unable to determine valid crossover based off probabilities')

        return child1_weights, child2_weights, child1_bias, child2_bias

    def _mutation(self, child1_weights: np.ndarray, child2_weights: np.ndarray,
                  child1_bias: np.ndarray, child2_bias: np.ndarray) -> None:
        scale = .2
        rand_mutation = random.random()
        mutation_bucket = np.digitize(rand_mutation, self._mutation_bins)

        mutation_rate = self._mutation_rate
        if self.settings['mutation_rate_type'].lower() == 'decaying':
            mutation_rate = mutation_rate / sqrt(self.current_generation + 1)

        # Gaussian
        if mutation_bucket == 0:
            # Mutate weights
            gaussian_mutation(child1_weights, mutation_rate, scale=scale)
            gaussian_mutation(child2_weights, mutation_rate, scale=scale)

            # Mutate bias
            gaussian_mutation(child1_bias, mutation_rate, scale=scale)
            gaussian_mutation(child2_bias, mutation_rate, scale=scale)
        
        # Uniform random
        elif mutation_bucket == 1:
            # Mutate weights
            random_uniform_mutation(child1_weights, mutation_rate, -1, 1)
            random_uniform_mutation(child2_weights, mutation_rate, -1, 1)

            # Mutate bias
            random_uniform_mutation(child1_bias, mutation_rate, -1, 1)
            random_uniform_mutation(child2_bias, mutation_rate, -1, 1)

        else:
            raise Exception('Unable to determine valid mutation based off probabilities.')


class GeneticAlgoWidget(QtWidgets.QWidget):
    def __init__(self, parent, settings):
        super().__init__(parent)
        font = QtGui.QFont('Times', 10, QtGui.QFont.Normal)
        font_bold = QtGui.QFont('Times', 13, QtGui.QFont.Bold)

        grid = QtWidgets.QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setColumnStretch(1, 5)
        TOP_LEFT = Qt.AlignLeft | Qt.AlignVCenter

        #### Generation stuff ####
        # Generation
        self._create_label_widget_in_grid('Generation:', font_bold, grid, 0, 0, TOP_LEFT)
        self.current_generation_label = self._create_label_widget('1', font)
        grid.addWidget(self.current_generation_label, 0, 1, TOP_LEFT)
        # Current individual
        self._create_label_widget_in_grid('Individual:', font_bold, grid, 1, 0, TOP_LEFT)
        self.current_individual_label = self._create_label_widget('1/{}'.format(settings['population_size']), font)
        grid.addWidget(self.current_individual_label, 1, 1, TOP_LEFT)
        # Best score
        self._create_label_widget_in_grid('Best Score:', font_bold, grid, 2, 0, TOP_LEFT)
        self.best_score_label = self._create_label_widget('0', font)
        grid.addWidget(self.best_score_label, 2, 1, TOP_LEFT)
        # Best fitness
        self._create_label_widget_in_grid('Best Fitness:', font_bold, grid, 3, 0, TOP_LEFT)
        self.best_fitness_label = self._create_label_widget('10', font)
        grid.addWidget(self.best_fitness_label, 3, 1, TOP_LEFT)

        #### GA setting ####
        self._create_label_widget_in_grid('GA Settings', font_bold, grid, 0, 2, TOP_LEFT)
        # Selection type
        selection_type = ' '.join([word.lower().capitalize() for word in settings['selection_type'].split('_')])
        self._create_label_widget_in_grid('Selection Type:', font_bold, grid, 1, 2, TOP_LEFT)
        self._create_label_widget_in_grid(selection_type, font, grid, 1, 3, TOP_LEFT)
        # Crossover type
        prob_SBX = settings['probability_SBX']
        prob_SPBX = settings['probability_SPBX']
        crossover_type = '{:.0f}% SBX, {:.0f}% SPBX'.format(prob_SBX*100, prob_SPBX*100)
        self._create_label_widget_in_grid('Crossover Type:', font_bold, grid, 2, 2, TOP_LEFT)
        self._create_label_widget_in_grid(crossover_type, font, grid, 2, 3, TOP_LEFT)
        # # Elitism
        # num_elitsm = str(settings['num_elitism'])
        # self._create_label_widget_in_grid('Number of Elitism:', font_bold, grid, 3, 2, TOP_LEFT)
        # self._create_label_widget_in_grid(num_elitsm, font, grid, 3, 3, TOP_LEFT)
        # Mutation type
        prob_gaussian = settings['probability_gaussian']
        prob_uniform = settings['probability_random_uniform']
        mutation_type = '{:.0f}% Gaussian, {:.0f}% Random Uniform'.format(prob_gaussian*100, prob_uniform*100)
        self._create_label_widget_in_grid('Mutation Type:', font_bold, grid, 4, 2, TOP_LEFT)
        self._create_label_widget_in_grid(mutation_type, font, grid, 4, 3, TOP_LEFT)
        # Mutation rate
        self._create_label_widget_in_grid('Mutation Rate:', font_bold, grid, 5, 2, TOP_LEFT)
        mutation_rate_percent = '{:.0f}%'.format(settings['mutation_rate'] * 100)
        mutation_rate_type = settings['mutation_rate_type'].lower().capitalize()
        mutation_rate = mutation_rate_percent + ' + ' + mutation_rate_type
        self._create_label_widget_in_grid(mutation_rate, font, grid, 5, 3, TOP_LEFT)

        #### NN setting ####
        self._create_label_widget_in_grid('NN Settings', font_bold, grid, 0, 4, TOP_LEFT)
        # Hidden layer activation
        hidden_layer_activation = ' '.join([word.lower().capitalize() for word in settings['hidden_layer_activation'].split('_')])
        self._create_label_widget_in_grid('Hidden Activation:', font_bold, grid, 1, 4, TOP_LEFT)
        self._create_label_widget_in_grid(hidden_layer_activation, font, grid, 1, 5, TOP_LEFT)
        # Output layer activation
        output_layer_activation = ' '.join([word.lower().capitalize() for word in settings['output_layer_activation'].split('_')])
        self._create_label_widget_in_grid('Output Activation:', font_bold, grid, 2, 4, TOP_LEFT)
        self._create_label_widget_in_grid(output_layer_activation, font, grid, 2, 5, TOP_LEFT)
        # Network architecture
        network_architecture = '[{}, {}, 4]'.format(settings['vision_type'] * 3 + 4 + 4,
                                                    ', '.join([str(num_neurons) for num_neurons in settings['hidden_network_architecture']]))
        self._create_label_widget_in_grid('NN Architecture:', font_bold, grid, 3, 4, TOP_LEFT)
        self._create_label_widget_in_grid(network_architecture, font, grid, 3, 5, TOP_LEFT)
        # Snake vision
        snake_vision = str(settings['vision_type']) + ' directions'
        self._create_label_widget_in_grid('Snake Vision:', font_bold, grid, 4, 4, TOP_LEFT)
        self._create_label_widget_in_grid(snake_vision, font, grid, 4, 5, TOP_LEFT)

        self.setLayout(grid)
        
        self.show()

    def _create_label_widget(self, string_label: str, font: QtGui.QFont) -> QtWidgets.QLabel:
        label = QtWidgets.QLabel()
        label.setText(string_label)
        label.setFont(font)
        return label

    def _create_label_widget_in_grid(self, string_label: str, font: QtGui.QFont, 
                                     grid: QtWidgets.QGridLayout, row: int, col: int, 
                                     alignment: Qt.Alignment) -> None:
        label = QtWidgets.QLabel()
        label.setText(string_label)
        label.setFont(font)
        grid.addWidget(label, row, col, alignment)


class SnakeWidget(QtWidgets.QWidget):
    def __init__(self, parent, board_size=(50, 50), snake=None):
        super().__init__(parent)
        self.board_size = board_size
        # self.setFixedSize(SQUARE_SIZE[0] * self.board_size[0], SQUARE_SIZE[1] * self.board_size[1])
        # self.new_game()
        if snake:
            self.snake = snake
        self.setFocus()

        self.draw_vision = True
        self.show()

    def new_game(self) -> None:
        self.snake = Snake(self.board_size)
    
    def update(self):
        if self.snake.is_alive:
            self.snake.update()
            self.repaint()
        else:
            # dead
            pass

    def draw_border(self, painter: QtGui.QPainter) -> None:
        painter.setRenderHints(QtGui.QPainter.Antialiasing)
        painter.setRenderHints(QtGui.QPainter.HighQualityAntialiasing)
        painter.setRenderHint(QtGui.QPainter.TextAntialiasing)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
        painter.setPen(QtGui.QPen(Qt.black))
        width = self.frameGeometry().width()
        height = self.frameGeometry().height()
        painter.drawLine(0, 0, width, 0)
        painter.drawLine(width, 0, width, height)
        painter.drawLine(0, height, width, height)
        painter.drawLine(0, 0, 0, height)

    def draw_snake(self, painter: QtGui.QPainter) -> None:
        painter.setRenderHints(QtGui.QPainter.HighQualityAntialiasing)
        painter.setPen(QtGui.QPen(Qt.black))
        painter.setBrush(QtGui.QBrush(Qt.red))

        for point in self.snake.snake_array:
            painter.drawRect(point.x * SQUARE_SIZE[0],  # Upper left x-coord
                             point.y * SQUARE_SIZE[1],  # Upper left y-coord
                             SQUARE_SIZE[0],            # Width
                             SQUARE_SIZE[1])            # Height

        if self.draw_vision:
            start = self.snake.snake_array[0]

            if self.snake._drawable_vision[0]:
                for drawable_vision in self.snake._drawable_vision:
                    start_x = start.x * SQUARE_SIZE[0] + SQUARE_SIZE[0]/2
                    start_y = start.y * SQUARE_SIZE[1] + SQUARE_SIZE[1]/2
                    if drawable_vision.apple_location:
                        painter.setPen(QtGui.QPen(Qt.green))
                        end_x = drawable_vision.apple_location.x * SQUARE_SIZE[0] + SQUARE_SIZE[0]/2
                        end_y = drawable_vision.apple_location.y * SQUARE_SIZE[1] + SQUARE_SIZE[1]/2
                        painter.drawLine(start_x, start_y, end_x, end_y)
                        start_x, start_y = end_x, end_y
                    if drawable_vision.self_location:
                        painter.setPen(QtGui.QPen(Qt.red))
                        end_x = drawable_vision.self_location.x * SQUARE_SIZE[0] + SQUARE_SIZE[0]/2
                        end_y = drawable_vision.self_location.y * SQUARE_SIZE[1] + SQUARE_SIZE[1]/2 
                        painter.drawLine(start_x, start_y, end_x, end_y)
                        start_x, start_y = end_x, end_y
                    if drawable_vision.wall_location:
                        painter.setPen(QtGui.QPen(Qt.black))
                        end_x = drawable_vision.wall_location.x * SQUARE_SIZE[0] + SQUARE_SIZE[0]/2
                        end_y = drawable_vision.wall_location.y * SQUARE_SIZE[1] + SQUARE_SIZE[1]/2 
                        painter.drawLine(start_x, start_y, end_x, end_y)


    def draw_apple(self, painter: QtGui.QPainter) -> None:
        apple_location = self.snake.apple_location
        if apple_location:
            painter.setRenderHints(QtGui.QPainter.HighQualityAntialiasing)
            painter.setPen(QtGui.QPen(Qt.black))
            painter.setBrush(QtGui.QBrush(Qt.green))

            painter.drawRect(apple_location.x * SQUARE_SIZE[0],
                             apple_location.y * SQUARE_SIZE[1],
                             SQUARE_SIZE[0],
                             SQUARE_SIZE[1])

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        painter = QtGui.QPainter()
        painter.begin(self)

        self.draw_border(painter)
        self.draw_apple(painter)
        self.draw_snake(painter)
        
        painter.end()

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        key_press = event.key()
        if key_press == Qt.Key_Up:
            self.snake.direction = 'u'
        elif key_press == Qt.Key_Down:
            self.snake.direction = 'd'
        elif key_press == Qt.Key_Right:
            self.snake.direction = 'r'
        elif key_press == Qt.Key_Left:
            self.snake.direction = 'l'

def _calc_stats(data: List[Union[int, float]]) -> Tuple[float, float, float, float, float]:
    mean = np.mean(data)
    median = np.median(data)
    std = np.std(data)
    _min = float(min(data))
    _max = float(max(data))

    return (mean, median, std, _min, _max)

def save_stats(population: Population, path_to_dir: str, fname: str):
    if not os.path.exists(path_to_dir):
        os.makedirs(path_to_dir)

    f = os.path.join(path_to_dir, fname + '.csv')
    
    frames = [individual._frames for individual in population.individuals]
    apples = [individual.score for individual in population.individuals]
    fitness = [individual.fitness for individual in population.individuals]

    write_header = True
    if os.path.exists(f):
        write_header = False

    trackers = [('steps', frames),
                ('apples', apples),
                ('fitness', fitness)
                ]
    stats = ['mean', 'median', 'std', 'min', 'max']

    header = [t[0] + '_' + s for t in trackers for s in stats]

    with open(f, 'a') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=header, delimiter=',')
        if write_header:
            writer.writeheader()

        row = {}
        # Create a row to insert into csv
        for tracker_name, tracker_object in trackers:
            curr_stats = _calc_stats(tracker_object)
            for curr_stat, stat_name in zip(curr_stats, stats):
                entry_name = '{}_{}'.format(tracker_name, stat_name)
                row[entry_name] = curr_stat

        # Write row
        writer.writerow(row)

def load_stats(path_to_stats: str, normalize: Optional[bool] = True):
    data = {}

    fieldnames = None
    trackers_stats = None
    trackers = None
    stats_names = None

    with open(path_to_stats, 'r') as csvfile:
        reader = csv.DictReader(csvfile)

        fieldnames = reader.fieldnames
        trackers_stats = [f.split('_') for f in fieldnames]
        trackers = set(ts[0] for ts in trackers_stats)
        stats_names = set(ts[1] for ts in trackers_stats)
        
        for tracker, stat_name in trackers_stats:
            if tracker not in data:
                data[tracker] = {}
            
            if stat_name not in data[tracker]:
                data[tracker][stat_name] = []

        for line in reader:
            for tracker in trackers:
                for stat_name in stats_names:
                    value = float(line['{}_{}'.format(tracker, stat_name)])
                    data[tracker][stat_name].append(value)
        
    if normalize:
        factors = {}
        for tracker in trackers:
            factors[tracker] = {}
            for stat_name in stats_names:
                factors[tracker][stat_name] = 1.0

        for tracker in trackers:
            for stat_name in stats_names:
                max_val = max([abs(d) for d in data[tracker][stat_name]])
                if max_val == 0:
                    max_val = 1
                factors[tracker][stat_name] = float(max_val)

        for tracker in trackers:
            for stat_name in stats_names:
                factor = factors[tracker][stat_name]
                d = data[tracker][stat_name]
                data[tracker][stat_name] = [val / factor for val in d]

    return data



if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow(settings)
    sys.exit(app.exec_())