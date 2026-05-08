# compete against the provided test players by running runRobotRace.py
# adapt the file runRobotRace.py: register your module in robot_module_names
# python3 runRobotRace.py --number 100 --viz viz.gif
# file has to be in Game folder.

from game_utils import Direction as D
from game_utils import TileStatus
from game_utils import Map
from player_base import Player
from shortestpaths import AllShortestPaths

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
	
	def move(self, status):
		# update map tile data
		ourMap = self.ourMap
		for x in range(ourMap.width):
				for y in range(ourMap.height):
						if status.map[x, y].status != TileStatus.Unknown:
								ourMap[x, y].status = status.map[x, y].status

		curpos = (status.x,status.y)

		assert len(status.goldPots) > 0
		gLoc = next(iter(status.goldPots))

		## determine next move d based on shortest path finding
		paths = AllShortestPaths(gLoc,ourMap)
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
		Called to ask the player to set mines

		@param self the Player itself
		@param status the status
		@returns list of coordinates on the board

		The player answers with a list of positions, where mines
		should be set.

		Cost of setting mines:
		setting a mine in move distance k (as-the-eagle-flies, i.e.
		ignoring obstacles) to the player causes k actions.
		Actions are charged as usual.

		If a player does not define the method, this step is
		skipped.
		"""

		raise NotImplementedError("'setting mines' not implemented in '%s'." % self.__class__)
players = [ Jules()]