#!/usr/bin/env python3
import random

from game_utils import nameFromPlayerId
from game_utils import Direction as D, MoveStatus
from game_utils import Tile, TileStatus, TileObject
from game_utils import Map, Status
from simulator import Simulator
from player_base import Player
from collections import deque
import copy


class Explorer(Player):
	def reset(self, player_id, max_players, width, height):
		self.player_id = player_id #needed for our debug map
		self.player_name = "Dora" # nameFromPlayerId(player_id)
		self.ourMap = Map(width, height)
		self.directions = {
            (0, 1): D.up,
            (0, -1): D.down,
            (-1, 0): D.left,
            (1, 0): D.right,
            (-1, 1): D.up_left,
            (1, 1): D.up_right,
            (-1, -1): D.down_left,
            (1, -1): D.down_right,
        }

	def round_begin(self, r):
		self.map_new_area(self.status)

	def move(self, status):
		self.map_new_area(status)
		# print("-" * 80)
		print("Internal map:")
		self.print_debug_status(status)
  
		start = (status.x, status.y)
		#enemies = self.visible_player_positions(status)
		
		path = self.shortest_path_to_frontier(start)
		if len(path) < 2:
			return []
		
		moves = []
		for i in range(1, len(path)):
			cur = path[i-1]
			next = path[i]
			dx = next[0] - cur[0]
			dy = next[1] - cur[1]
			moves.append(self.directions[(dx, dy)])

		return moves

	def map_new_area(self, status):
		v = status.params.visibility
		xl = max(0, status.x - v)
		xr = min(self.ourMap.width - 1, status.x + v)
		yd = max(0, status.y - v)
		yu = min(self.ourMap.height - 1, status.y + v)
  
		for x in range(xl, xr + 1):
			for y in range(yd, yu + 1):
				if status.map[x, y].status != TileStatus.Unknown:
					self.ourMap[x, y].status = status.map[x, y].status
    
	def map_bounds(self, pos):
		x, y = pos
		return 0 <= x < self.ourMap.width and 0 <= y < self.ourMap.height

	def adj_cells(self, pos):
		x, y = pos
		for dx, dy in self.directions.keys():
			next = (x + dx, y + dy)
			if self.map_bounds(next):
				yield next
	
	def is_traversable(self, pos):
		return self.ourMap[pos].status == TileStatus.Empty

	def is_frontier(self, pos):
		if not self.is_traversable(pos):
			return False

		for nbr in self.adj_cells(pos):
			if self.ourMap[nbr].status == TileStatus.Unknown:
				return True
		return False

	def shortest_path_to_frontier(self, start):
		queue = deque([start])
		visited = {start}
		prev = {}
        
		while queue:
			cur = queue.popleft()

			if cur != start and self.is_frontier(cur):
				return self.find_path(prev, cur)

			for cell in self.adj_cells(cur):
					if cell in visited:
						continue
					if not self.is_traversable(cell):
						continue
					visited.add(cell)
					prev[cell] = cur
					queue.append(cell)
		return []

	def find_path(self, prev, destination):
		path = [destination]
		while destination in prev:
			destination = prev[destination]
			path.append(destination)
		path.reverse()
		print(path)
		return path
	
	def print_debug_status(self, status):
		debug_map = copy.deepcopy(self.ourMap)
		debug_map[status.x, status.y].obj = TileObject.makePlayer(self.player_id)
		print(f"Player {status.player}")
		print(debug_map)
		print(f"Health: {status.health}")
		print(f"Gold:   {status.gold}")
		print(f"Position: ({status.x}, {status.y})")
		print(f"Gold pots: {status.goldPots}")



players = [Explorer()]