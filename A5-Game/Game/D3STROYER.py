# compete against the provided test players by running runRobotRace.py
# adapt the file runRobotRace.py: register your module in robot_module_names
# python3 runRobotRace.py --number 100 --viz viz.gif
# file has to be in Game folder.
# extract frames:
# ffmpeg -i viz.gif -vf "select=eq(n\,0)" -q:v 3 firstframe.png

import math
import copy
from collections import deque
from game_utils import Direction as D
from game_utils import TileStatus
from game_utils import Map
from player_base import Player
from shortestpaths import AllShortestPaths

# =================================
# Tuning constants
# =================================

#  escape exit if we crash
STUCK_EXIT = 3
MEMORY_LEN = 8

# What map are we playing on ?
MAZE_DENSITY = 0.28     #above, we say it is maze map
MAP_SAMPLE_ROUNDS = 30  #rounds before we decide on strategy

# Moves per map type
# Open map
OPEN_BIG = 6    # pot > 50
OPEN_MID = 4    # pot > 20 
OPEN_SMALL = 2  # small pot 
# Maze map
MAZE_BIG = 5
MAZE_MID = 3
MAZE_SMALL = 2

# score weights
DIST_PEN = 2       # gold lost per step of distance
ENEMY_CLOSER = 25 

# waiting strategy for low gold situations
WAIT = 8 # rounds of saving beats moving on


class D3STROYER(Player):

    def reset(self, player_id, max_players, width, height):
        self.player_name = "D3STROYER"
        self.ourMap = Map(width, height)

        # position hist to detect stuck situations
        self._pos_history: list[tuple] = []

        # escape mode
        self._escape_mode = False
        self._escape_path: list[tuple] = []

        # map type detection
        self._wall_count = 0
        self._known_count = 0
        self._map_type = "unknown"  # "maze" | "open" | "unknown"
        self._round_num = 0

        # repositioning (map fully explored & nothing to do)
        self._center = (width // 2, height // 2)

        # Jumping
        self._jumps_ok = False #updated with first move call

    def round_begin(self, r):
        self._round_num = r
        #pass
    
    # ---- direction helpers ----
    def _as_direction(self,curpos,nextpos):
            for d in D:
                    diff = d.as_xy()
                    if (curpos[0] + diff[0], curpos[1] + diff[1]) ==  nextpos:
                            return d
            return None

    def _as_directions(self,curpos,path):
            return [self._as_direction(x,y) for x,y in zip([curpos]+path,path)]
    
    # ---- Map helpers ---
    def _update_map(self, status):
        for x in range(self.ourMap.width):
            for y in range(self.ourMap.height):
                tile = status.map[x,y]
                if status.map[x,y].status != TileStatus.Unknown:
                    old = self.ourMap[x,y].status
                    self.ourMap[x,y].status = tile.status

                    if old == TileStatus.Unknown:
                        self._known_count += 1
                        if tile.status == TileStatus.Wall:
                            self._wall_count += 1
    
    def _update_map_type(self):
        if self._map_type != "unknown":
            return
        if self._round_num < MAP_SAMPLE_ROUNDS or self._known_count == 0:
            return
        density = self._wall_count / self._known_count
        self._map_type = "maze" if density >= MAZE_DENSITY else "open"

    def _map_bounds(self, pos):
        x, y = pos
        
        if x < 0 or x >= self.ourMap.width:
            return False

        if y < 0 or y >= self.ourMap.height:
            return False

        return True
    
    
    def _adj_cells(self, pos, use_jumps=False):
        x,y = pos
        for d in D:
            dx, dy = d.as_xy()
            nxt = (x + dx, y + dy)
            if not self._map_bounds(nxt):
                continue
            tile_status = self.ourMap[nxt].status
            if tile_status != TileStatus.Wall:
                yield nxt
            elif use_jumps:
                jump = (x+2 * dx, y + 2 * dy)
                if self._map_bounds(jump) and self.ourMap[jump].status == TileStatus.Empty:
                    yield jump

    # ---- frontier exploration ----

    def _is_frontier(self, pos):

        if self.ourMap[pos].status != TileStatus.Empty:
            return False

        for cell in self._adj_cells(pos):

            if self.ourMap[cell].status == TileStatus.Unknown:
                return True

        return False
    
    def _shortest_path_to_target(self, start, target, use_jumps = False):

        queue = deque([start])
        visited = {start}
        prev = {}

        while queue:
            cur = queue.popleft()

            if cur != start and self._is_frontier(cur):
                path = [cur]
                while cur in prev:
                    cur = prev[cur]
                    path.append(cur)
                path.reverse()

                return path

            for nxt in self._adj_cells(cur, use_jumps=use_jumps):
                if nxt in visited:
                    continue

                if self.ourMap[nxt].status not in (TileStatus.Empty, TileStatus.Unknown):
                    continue

                visited.add(nxt)
                prev[nxt] = cur
                queue.append(nxt)

        return []
    
    def _shortest_path_to_frontier(self, start):
        return self._shortest_path_to_target(start, self._is_frontier, use_jumps=self._jumps_ok)
    
    def _shortest_path_to_pos(self, start, target):
        return self._shortest_path_to_target(start, lambda p: p == target, use_jumps=self._jumps_ok)
    
    # Escape logic if stuck
    def _update_history(self, pos):
        self._pos_history.append(pos)
        if len(self._pos_history) > MEMORY_LEN:
            self._pos_history.pop(0)

    def _is_stuck(self, curpos):
        if len(self._pos_history) < MEMORY_LEN:
            return False
        recent = self._pos_history[-MEMORY_LEN:]
        return len(set(recent)) <= 2 
    
    def _escape_direction(self, curpos):
        #find most-recent repeated pos, then BSF to frontier or gol
        if len(self._pos_history) < 2 :
            return []
        
        blocked = set(self._pos_history[-MEMORY_LEN:])
        blocked.discard(curpos)

        # BFS
        queue = deque([curpos])
        visited = {curpos}
        prev = {}

        while queue:
            cur = queue.popleft()
            if cur != curpos and self._is_frontier(cur):
                path = []
                node = cur
                while node in prev:
                    path.append(node)
                    node = prev[node]
                path.reverse()
                return path
 
            for nxt in self._adj_cells(cur, use_jumps=self._jumps_ok):
                if nxt in visited or nxt in blocked:
                    continue
                if self.ourMap[nxt].status != TileStatus.Empty:
                    continue
                visited.add(nxt)
                prev[nxt] = cur
                queue.append(nxt)
 
        return []

    # ---- Cost helper ----
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

    # not used at the moment
    def _found_gold(self, status, gx, gy):
        # returns True if gold is in visible map
        tile = status.map[gx, gy]
        return tile.status != TileStatus.Unknown 

    #---- waiting strategy  ----
    def _should_wait(self, status, distance, pot_value):
        """
            option A: go now 
            option B: wait k rounds, then go
        """
        if self._map_type == "maze":
            return False # in maze moving is almost always better
        
        max_moves = self._affordable_moves(status.gold)
        move_cost = D3STROYER._movement_cost(min(max_moves, distance))
        deficit = move_cost - (pot_value - distance)
        return deficit > WAIT
    
    # ---- Gold target -----
    def _best_gold_target(self, status, curpos):
        best_score = -999999
        best_gold = None
        best_path = None

        for gLoc, gold_value in status.goldPots.items():

            tempMap = copy.deepcopy(self.ourMap)
            paths = AllShortestPaths(gLoc, tempMap)

            for other_status in status.others:

                if other_status is None:
                    continue

                other_pos = (other_status.x,other_status.y)
                other_path = paths.shortestPathFrom(other_pos)

                if other_path:
                    for tile in other_path[:2]:
                        tempMap[tile].status = TileStatus.Wall
                
            paths = AllShortestPaths(gLoc, tempMap)
            path = paths.shortestPathFrom(curpos)

            if not path:
                continue

            path = path[1:]
            path.append(gLoc)

            distance = len(path)

            score = gold_value - 2 * distance
            
            for other_status in status.others:
                if other_status is None:
                    continue

                enemy_pos = (other_status.x,other_status.y)

                enemy_path = paths.shortestPathFrom(enemy_pos)

                if enemy_path:
                    enemy_distance = len(enemy_path)
                    if enemy_distance < distance:
                        score -= 25

            if score > best_score:
                best_score = score
                best_gold = gLoc
                best_path = path
            
        return best_gold, best_path

    def _num_moves_to_make(self, status, distance, pot_value):
        max_affordable = self._affordable_moves(status.gold)
        
        if self._map_type == "open":
            if pot_value > 50:
                base = OPEN_BIG
            elif pot_value > 20:
                base = OPEN_MID
            else:
                base = OPEN_SMALL
        else:
            # maze or unknown 
            if pot_value > 50:
                base = MAZE_BIG
            elif pot_value > 20:
                base = MAZE_MID
            else:
                base = MAZE_SMALL
 
        n = min(base, distance, max_affordable)
 
        # never pay more than we'd collect
        while n > 0 and D3STROYER._movement_cost(n) >= pot_value:
            n -= 1
 
        return n
 
    # ---- Reposition to center ----
    def _reposition_to_center(self, curpos):
        #move to center if nothing to do
        if curpos == self._center:
            return []
        
        cx, cy = self._center
        if self.ourMap[cx, cy].status != TileStatus.Empty:
            # find nearest empty cell to center
            for radius in range(1, max(self.ourMap.width, self.ourMap.height)):
                found = False
                for dx in range(-radius, radius + 1):
                    for dy in range(-radius, radius + 1):
                        if abs(dx) != radius and abs(dy) != radius:
                            continue
                        nx, ny = cx + dx, cy + dy
                        if (self._map_bounds((nx, ny)) and
                                self.ourMap[nx, ny].status == TileStatus.Empty):
                            self._center = (nx, ny)
                            found = True
                            break
                    if found:
                        break
                if found:
                    break
 
        path = self._shortest_path_to_pos(curpos, self._center)
        return path

    
    def move(self, status):
        self._update_map(status)
        self._update_map_type()

        try:
            self._jumps_ok = status.params.jumps_ok
        except AttributeError:
            self._jumps_ok = False

        curpos = (status.x,status.y)

        assert len(status.goldPots) > 0

        # escape mode
        if self._is_stuck(curpos):
            self._escape_mode = True
 
        # TO-DO: in low gold situations, we now do one step per round towards gold, change to center, or to no moves at all ?
        if self._escape_mode:
            if not self._escape_path or curpos == self._escape_path[-1]:
                self._escape_path = self._escape_direction(curpos)
                if not self._escape_path:
                    self._escape_mode = False   
                else:
                    # leave escape mode once we reach the end of the escape path
                    pass
 
            if self._escape_mode and self._escape_path:
                try:
                    idx = self._escape_path.index(curpos)
                    step = self._escape_path[idx + 1: idx + 2]
                except (ValueError, IndexError):
                    step = self._escape_path[:1]
 
                if not step:
                    self._escape_mode = False
                else:
                    if curpos == self._escape_path[-1]:
                        self._escape_mode = False
                    return self._as_directions(curpos, step)

        # find best gold target
        gLoc, bestpath = self._best_gold_target(status, curpos)

        if bestpath is None:
            return self._fallback_move(status, curpos)
        
        distance = len(bestpath)

        if distance > status.goldPotRemainingRounds:
            return self._fallback_move(status, curpos)

        pot_value = status.goldPots[gLoc]

        if pot_value < distance:
            return self._fallback_move(status, curpos)

        if self._should_wait(status, distance, pot_value):
            return self._as_directions(curpos, bestpath[:1])
        
        numMoves = self._num_moves_to_make(status, distance, pot_value)

        if numMoves == 0:
            return self._fallback_move(status, curpos)

        return self._as_directions(curpos,bestpath[:numMoves])
    
    def _fallback_move(self, status, curpos):
        frontier_path = self._shortest_path_to_frontier(curpos)
        if len(frontier_path) >= 1:
            steps = min(2, len(frontier_path))
            return self._as_directions(curpos, frontier_path[:steps])
 
        # fully explored — reposition to center so we're ready for next gold pot
        center_path = self._reposition_to_center(curpos)
        if center_path:
            return self._as_directions(curpos, center_path[:2])
 

        gLoc, bestpath = self._best_gold_target(status, curpos)
        if bestpath:
            return self._as_directions(curpos, bestpath[:1])
 
        return []


    def set_mines(self, status):
        """
        The player answers with a list of positions, where mines
        should be set.
        """
        raise NotImplementedError("'setting mines' not implemented in '%s'." % self.__class__)

players = [ D3STROYER()]