# compete against the provided test players by running runRobotRace.py
# adapt the file runRobotRace.py: register your module in robot_module_names
# python3 runRobotRace.py --number 100 --viz viz.gif
# file has to be in Game folder.
# extract frames:
# ffmpeg -i viz.gif -vf "select=eq(n\,0)" -q:v 3 firstframe.png

import math

from game_utils import Direction as D
from game_utils import TileStatus
from game_utils import Map
from player_base import Player
from shortestpaths import AllShortestPaths


class D3STROYER(Player):

    def reset(self, player_id, max_players, width, height):
        self.player_name = "D3STROYER"
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

    @staticmethod
    def _movement_cost(distance):
        return distance * (distance + 1) // 2

    def move(self, status):
        self._update_map(status)

        curpos = (status.x,status.y)

        assert len(status.goldPots) > 0
        gLoc = next(iter(status.goldPots))

        # print(status.others, file=open("status_others.txt", "a"))

        ## determine next move d based on shortest path finding
        paths = AllShortestPaths(gLoc,self.ourMap)

        # predict paths other players will take
        for other_status in status.others:
            if other_status is not None:
                other_pos = other_status.x, other_status.y
                other_path = paths.shortestPathFrom(other_pos)
                # blacklist first n predicted path tiles
                for tile in other_path[:3]:
                    self.ourMap[tile].status = TileStatus.Wall

        # recompute paths after Map update to avoid other players
        paths = AllShortestPaths(gLoc,self.ourMap)

        bestpath = paths.shortestPathFrom(curpos)

        bestpath = bestpath[1:]
        bestpath.append( gLoc )

        distance=len(bestpath)
        
        # try to reach gold in t = log2(distance)
        numMoves = 2
        move_cost = D3STROYER._movement_cost(distance // 2)
        if (distance > numMoves and
            move_cost < status.gold // 4 and
            move_cost * 2 < status.goldPots[gLoc]):
            numMoves = distance // 2

        # TODO: if low amount of gold in pot don't go for it
        ## don't move if the pot is too far away
        if math.log2(distance) > status.goldPotRemainingRounds:
            numMoves = 0

        return self._as_directions(curpos,bestpath[:numMoves])

    def set_mines(self, status):
        """
        The player answers with a list of positions, where mines
        should be set.
        """
        raise NotImplementedError("'setting mines' not implemented in '%s'." % self.__class__)

players = [ D3STROYER()]
