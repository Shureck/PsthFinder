"""

Bidirectional Breadth-First grid planning

author: Erwin Lejeune (@spida_rwin)

See Wikipedia article (https://en.wikipedia.org/wiki/Breadth-first_search)

"""

import math

import matplotlib.pyplot as plt
import numpy as np
import json
import slamtec
import threading
import signal
show_animation = False
pose = None
arrr = []
# with open('array.txt', 'r') as f:
#     arrr = json.load(f)
# print(arrr)

# #рассчитать уравнение прямой между двумя точками
# def calc_line_equation(p1, p2):
#     if p1[0] == p2[0]:
#         m = float("inf")
#         c = p1[0]
#     else:
#         m = (p1[1] - p2[1]) / (p1[0] - p2[0])
#         c = p1[1] - m * p1[0]
#     return [m, c]

# #для всех точек из массива arrr получить уравнение прямой между двумя точками
# def get_line_equation(arrr):
#     line_equation = []
#     for i in range(len(arrr) - 1):
#         line_equation.append(calc_line_equation(arrr[i], arrr[i + 1]))
#     return line_equation

# arr_MC = get_line_equation(arrr)
# #для каждой пары точек из arrr сгенерировать точки между ними с шагом в 0.1
# def get_points_between_two_points(p1, p2):
#     points = []
#     m, c = calc_line_equation(p1, p2)
#     if m == float("inf"):
#         for i in range(p1[0], p2[0], 0.1):
#             points.append([i, p1[1]])
#     else:
#         for i in np.arange(p1[0], p2[0], 0.1):
#             points.append([i, m * i + c])
#     print(points)
#     return points



# #построить график для всех точек из массива arrr
# def draw_graph(arrr):
#     points = []
#     for i in range(len(arrr) - 1):
#         points += get_points_between_two_points(arrr[i], arrr[i + 1])
#         # plt.plot()
#     # print("**********************")
#     # plt.plot([x[0] for x in arrr], [x[1] for x in arrr], 'go')
#     # plt.plot([x[0] for x in points], [x[1] for x in points], 'o')
#     # plt.show()
#     return points
# draw_graph(arrr)

# arrr.extend(draw_graph(arrr))
exit_event = threading.Event()
def getData():
    
    sl = slamtec.SlamtecMapper("192.168.11.1",1445, False)
    while True:
        # if exit_event.is_set():
        #     break

        arr = sl.get_laser_scan(True)
        pose = sl.get_pose()
        arrr = []
        for index in arr:

            x = pose['x'] + index[1] * math.cos(index[0] + pose['yaw'])
            y = pose['y'] + index[1] * math.sin(index[0] + pose['yaw'])
            #Посчитать дистанцию между pose[x],pose[y] и x,y
            dist = math.hypot(x - pose['x'], y - pose['y'])
            if dist > 0.3:
                arrr.append([x,y])


def signal_handler(signum, frame):
    exit_event.set()

# signal.signal(signal.SIGINT, signal_handler)
# a = threading.Thread(target=getData)
# a.start()

class BidirectionalBreadthFirstSearchPlanner:

    def __init__(self, ox, oy, resolution, rr):
        """
        Initialize grid map for bfs planning

        ox: x position list of Obstacles [m]
        oy: y position list of Obstacles [m]
        resolution: grid resolution [m]
        rr: robot radius[m]
        """

        self.min_x, self.min_y = None, None
        self.max_x, self.max_y = None, None
        self.x_width, self.y_width, self.obstacle_map = None, None, None
        self.resolution = resolution
        self.rr = rr
        self.calc_obstacle_map(ox, oy)
        self.motion = self.get_motion_model()

    class Node:
        def __init__(self, x, y, cost, parent_index, parent):
            self.x = x  # index of grid
            self.y = y  # index of grid
            self.cost = cost
            self.parent_index = parent_index
            self.parent = parent

        def __str__(self):
            return str(self.x) + "," + str(self.y) + "," + str(
                self.cost) + "," + str(self.parent_index)

    def planning(self, sx, sy, gx, gy):
        """
        Bidirectional Breadth First search based planning

        input:
            s_x: start x position [m]
            s_y: start y position [m]
            gx: goal x position [m]
            gy: goal y position [m]

        output:
            rx: x position list of the final path
            ry: y position list of the final path
        """

        start_node = self.Node(self.calc_xy_index(sx, self.min_x),
                               self.calc_xy_index(sy, self.min_y), 0.0, -1,
                               None)
        goal_node = self.Node(self.calc_xy_index(gx, self.min_x),
                              self.calc_xy_index(gy, self.min_y), 0.0, -1,
                              None)

        open_set_A, closed_set_A = dict(), dict()
        open_set_B, closed_set_B = dict(), dict()
        open_set_B[self.calc_grid_index(goal_node)] = goal_node
        open_set_A[self.calc_grid_index(start_node)] = start_node

        meet_point_A, meet_point_B = None, None

        while 1:
            if len(open_set_A) == 0:
                print("Open set A is empty..")
                break

            if len(open_set_B) == 0:
                print("Open set B is empty")
                break

            current_A = open_set_A.pop(list(open_set_A.keys())[0])
            current_B = open_set_B.pop(list(open_set_B.keys())[0])

            c_id_A = self.calc_grid_index(current_A)
            c_id_B = self.calc_grid_index(current_B)

            closed_set_A[c_id_A] = current_A
            closed_set_B[c_id_B] = current_B

            # show graph
            if show_animation:  # pragma: no cover
                plt.plot(self.calc_grid_position(current_A.x, self.min_x),
                         self.calc_grid_position(current_A.y, self.min_y),
                         "xc")
                plt.plot(self.calc_grid_position(current_B.x, self.min_x),
                         self.calc_grid_position(current_B.y, self.min_y),
                         "xc")
                # for stopping simulation with the esc key.
                plt.gcf().canvas.mpl_connect(
                    'key_release_event',
                    lambda event: [exit(0) if event.key == 'escape' else None])
                if len(closed_set_A.keys()) % 10 == 0:
                    plt.pause(0.001)

            if c_id_A in closed_set_B:
                print("Find goal")
                meet_point_A = closed_set_A[c_id_A]
                meet_point_B = closed_set_B[c_id_A]
                break

            elif c_id_B in closed_set_A:
                print("Find goal")
                meet_point_A = closed_set_A[c_id_B]
                meet_point_B = closed_set_B[c_id_B]
                break

            # expand_grid search grid based on motion model
            for i, _ in enumerate(self.motion):
                breakA = False
                breakB = False

                node_A = self.Node(current_A.x + self.motion[i][0],
                                   current_A.y + self.motion[i][1],
                                   current_A.cost + self.motion[i][2],
                                   c_id_A, None)
                node_B = self.Node(current_B.x + self.motion[i][0],
                                   current_B.y + self.motion[i][1],
                                   current_B.cost + self.motion[i][2],
                                   c_id_B, None)

                n_id_A = self.calc_grid_index(node_A)
                n_id_B = self.calc_grid_index(node_B)

                # If the node is not safe, do nothing
                if not self.verify_node(node_A):
                    breakA = True

                if not self.verify_node(node_B):
                    breakB = True

                if (n_id_A not in closed_set_A) and \
                        (n_id_A not in open_set_A) and (not breakA):
                    node_A.parent = current_A
                    open_set_A[n_id_A] = node_A

                if (n_id_B not in closed_set_B) and \
                        (n_id_B not in open_set_B) and (not breakB):
                    node_B.parent = current_B
                    open_set_B[n_id_B] = node_B

        rx, ry = self.calc_final_path_bidir(
            meet_point_A, meet_point_B, closed_set_A, closed_set_B)
        return rx, ry

    # takes both set and meeting nodes and calculate optimal path
    def calc_final_path_bidir(self, n1, n2, setA, setB):
        rxA, ryA = self.calc_final_path(n1, setA)
        rxB, ryB = self.calc_final_path(n2, setB)

        rxA.reverse()
        ryA.reverse()

        rx = rxA + rxB
        ry = ryA + ryB

        return rx, ry

    def calc_final_path(self, goal_node, closed_set):
        # generate final course
        try:
            rx, ry = [self.calc_grid_position(goal_node.x, self.min_x)], [
                self.calc_grid_position(goal_node.y, self.min_y)]
            n = closed_set[goal_node.parent_index]
            while n is not None:
                rx.append(self.calc_grid_position(n.x, self.min_x))
                ry.append(self.calc_grid_position(n.y, self.min_y))
                n = n.parent
            return rx, ry
        except Exception as e:
            print(e)
        return [], []

    def calc_grid_position(self, index, min_position):
        """
        calc grid position

        :param index:
        :param min_position:
        :return:
        """
        pos = index * self.resolution + min_position
        return pos

    def calc_xy_index(self, position, min_pos):
        return round((position - min_pos) / self.resolution)

    def calc_grid_index(self, node):
        return (node.y - self.min_y) * self.x_width + (node.x - self.min_x)

    def verify_node(self, node):
        px = self.calc_grid_position(node.x, self.min_x)
        py = self.calc_grid_position(node.y, self.min_y)

        if px < self.min_x:
            return False
        elif py < self.min_y:
            return False
        elif px >= self.max_x:
            return False
        elif py >= self.max_y:
            return False

        # collision check
        if self.obstacle_map[node.x][node.y]:
            return False

        return True

    def calc_obstacle_map(self, ox, oy):

        self.min_x = round(min(ox))
        self.min_y = round(min(oy))
        self.max_x = round(max(ox))
        self.max_y = round(max(oy))
        print("min_x:", self.min_x)
        print("min_y:", self.min_y)
        print("max_x:", self.max_x)
        print("max_y:", self.max_y)

        self.x_width = round((self.max_x - self.min_x) / self.resolution)
        self.y_width = round((self.max_y - self.min_y) / self.resolution)
        print("x_width:", self.x_width)
        print("y_width:", self.y_width)

        # obstacle map generation
        self.obstacle_map = [[False for _ in range(self.y_width)]
                             for _ in range(self.x_width)]
        for ix in range(self.x_width):
            x = self.calc_grid_position(ix, self.min_x)
            for iy in range(self.y_width):
                y = self.calc_grid_position(iy, self.min_y)
                for iox, ioy in zip(ox, oy):
                    d = math.hypot(iox - x, ioy - y)
                    if d <= self.rr:
                        self.obstacle_map[ix][iy] = True
                        break

    @staticmethod
    def get_motion_model():
        # dx, dy, cost
        motion = [[1, 0, 1],
                  [0, 1, 1],
                  [-1, 0, 1],
                  [0, -1, 1],
                  [-1, -1, math.sqrt(2)],
                  [-1, 1, math.sqrt(2)],
                  [1, -1, math.sqrt(2)],
                  [1, 1, math.sqrt(2)]]

        return motion


def main():
    print(__file__ + " start!!")

    # start and goal position
    sx = 0.0  # [m]
    sy = 0.0  # [m]
    gx = 0.0  # [m]
    gy = 3.0  # [m]
    grid_size = 0.1  # [m]
    robot_radius = 0.2  # [m]

    # set obstacle positions
    ox, oy = [], []
    
     # set obstacle positions
    sl = slamtec.SlamtecMapper("192.168.11.1",1445, False)

    import time

    
    fig = plt.figure("KKK")
    ax = fig.gca()
    fig.show()

    while True:

        # if len(arrr) == 0 or pose == None:
        #     continue 
        arr = sl.get_laser_scan(True)
        pose = sl.get_pose()

        #очистить график
        ax.cla()

        arrr = []
        for index in arr:

            x = pose['x'] + index[1] * math.cos(index[0] + pose['yaw'])
            y = pose['y'] + index[1] * math.sin(index[0] + pose['yaw'])
            #Посчитать дистанцию между pose[x],pose[y] и x,y
            dist = math.hypot(x - pose['x'], y - pose['y'])
            if dist > 0.3:
                arrr.append([x,y])

        arrr.extend(arrr)

        ox = [x[0] for x in arrr]
        oy = [x[1] for x in arrr]

        # if show_animation:  # pragma: no cover
        ax.quiver(pose['x'], pose['y'], 1.0*math.cos(pose['yaw']), 1.0*math.sin(pose['yaw']), color='b', units='xy', scale=1)
        ax.plot(ox, oy, ".k")
        ax.plot(sx, sy, "og")
        ax.plot(gx, gy, "ob")
        ax.grid(True)
        ax.axis("equal")

        bi_bfs = BidirectionalBreadthFirstSearchPlanner(
            ox, oy, grid_size, robot_radius)
        rx, ry = bi_bfs.planning(sx, sy, gx, gy)

        # if show_animation:  # pragma: no cover
        ax.plot(rx, ry, "-r")

        fig.canvas.draw()
        plt.pause(0.1)


if __name__ == '__main__':
    main()
