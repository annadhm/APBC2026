# compete against the provided test players by running runRobotRace.py
# adapt the file runRobotRace.py: register your module in robot_module_names
# python3 runRobotRace.py --number 100 --viz viz.gif
# file has to be in Game folder.
# extract frames:
# ffmpeg -i viz.gif -vf "select=eq(n\,0)" -q:v 3 firstframe.png

from game_utils import Direction as D
from game_utils import TileStatus
from game_utils import Map
from player_base import Player

from collections import deque
import copy
# from game_utils import Direction as D, MoveStatus
# from game_utils import Tile, TileStatus, TileObject
import random

import numpy as np

class AllShortestPaths:
    def __init__(self,sink,map):
        self.sink = sink
        self.map = map

        self.width=map.width
        self.height=map.height

        # self.wallmap = np.zeros((self.height, self.width), dtype='bool')

        # for x in range(self.width):
        #     for y in range(self.height):
        #         self.wallmap[x,y] = self.map[x,y].status == TileStatus.Wall

        wm = [ [ self.map[x,y].status == TileStatus.Wall for y in range(self.height) ]
               for x in range(self.width) ]

        self.wallmap = np.array(wm,dtype='bool')

        self.dist = np.negative(np.ones((self.height, self.width), dtype='int'))

        self._calcDistances()

    # return the non-Wall neighbors of a field (x,y)
    def nonWallNeighborsIter(self,xy):

        (x,y) = xy
        xs=[x]
        if x>0: xs.append(x-1)
        if x<self.width-1: xs.append(x+1)

        ys=[y]
        if y>0: ys.append(y-1)
        if y<self.height-1: ys.append(y+1)

        for x in xs:
            for y in ys:
                if not self.wallmap[x,y]:
                    if (x,y)==xy: continue
                    yield (x,y)

    def _calcDistances(self):
        front = deque()
        front.append(self.sink)

        assert type(self.sink) == tuple
        self.dist[self.sink] = 0

        while front:
            xy=front.popleft()
            for neighbor in self.nonWallNeighborsIter(xy):
                if self.dist[neighbor]<0:
                    front.append(neighbor)
                    self.dist[neighbor] = self.dist[xy] + 1

    def shortestPathFrom(self, xy):
        if self.dist[xy]<0:
            return []

        path = list()
        curdist = self.dist[xy]

        while xy != self.sink:
            path.append(xy)

            # find preceeding neighbor
            for neighbor in self.nonWallNeighborsIter(xy):
                if self.dist[neighbor] ==  curdist-1:
                    curdist -= 1
                    xy = neighbor
                    break
        return path

    def randomShortestPathFrom(self, xy):
        if self.dist[xy]<0:
            return []

        path = list()
        curdist = self.dist[xy]

        while xy != self.sink:
            path.append(xy)

            potentialNextXYs = list()
            # find preceeding neighbor
            for neighbor in self.nonWallNeighborsIter(xy):
                if self.dist[neighbor] ==  curdist-1:
                    potentialNextXYs.append(neighbor)
            assert len(potentialNextXYs)>0
            xy = random.choice(potentialNextXYs)
            curdist -= 1
        return path


class Jules(Player):

    def reset(self, player_id, max_players, width, height):
        self.player_name = "Jules"
        self.ourMap = Map(width, height)

    def round_begin(self, r):
        pass
    
    def _as_direction(self,curpos,nextpos):
            for d in D:
                    diff = d.as_xy()
                    if (curpos[0] + diff[0], curpos[1] + diff[1]) ==  nextpos:
                            return d
            return None

    def _as_directions(self,curpos,path):
            return [self._as_direction(x,y) for x,y in zip([curpos]+path,path)]
    
    def _update_map(self, status):
        for x in range(self.ourMap.width):
            for y in range(self.ourMap.height):
                if status.map[x,y].status != TileStatus.Unknown:
                    self.ourMap[x,y].status = status.map[x,y].status

    def _found_gold(self, status, gx, gy):
        # returns True if gold is in visible map
        tile = status.map[gx, gy]
        return tile.status != TileStatus.Unknown 
    
    def _affordable_moves(self, gold):
        """
        How many moves can we afford?
        cost(k) = 1+2+...+k = k*(k+1)/2  ≤ gold
        Solve for largest k where k*(k+1)/2 ≤ gold.
        """
        k = 0
        while (k+1) * (k+2) // 2 <= gold:
            k += 1
        return k

    def move(self, status):
        self._update_map(status)

        curpos = (status.x,status.y)

        assert len(status.goldPots) > 0
        gLoc = next(iter(status.goldPots))

        ## determine next move d based on shortest path finding
        paths = AllShortestPaths(gLoc,self.ourMap)
        # TODO: predict paths other players will take
        # TODO: aviod other players so we don't get suck or stunlocked
        bestpath = paths.shortestPathFrom(curpos)

        bestpath = bestpath[1:]
        bestpath.append( gLoc )

        distance=len(bestpath)
        # TODO: tweak numMoves based on amount of gold and distance to gold?
        numMoves = 2
        # TODO: if low amount of gold in pot don't go for it
        ## don't move if the pot is too far away
        if numMoves>0 and distance/numMoves > status.goldPotRemainingRounds:
                numMoves = 0

        return self._as_directions(curpos,bestpath[:numMoves])

    def set_mines(self, status):
        """
        The player answers with a list of positions, where mines
        should be set.
        """
        raise NotImplementedError("'setting mines' not implemented in '%s'." % self.__class__)

players = [ Jules()]
