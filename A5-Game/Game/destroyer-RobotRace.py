#!/user/bin/env python3

"""
    First bot version. 
    The bot called Destroyer, moves towards the gold. If The gold is in the same tile as the bot, with more than one mover per round. 
    If another player is in the way, the bot crashes instead of find a way around. 

    Pro:
    - works well if the way to the gold is known and nothing is in its way
    
    Cons:
    - if another bot is in the way, it seems that the bot enters a endless loop of moves. Redoing the same moves over and over again...
    - All moves that are financially feasible will be made, even if the gold is not reached within these moves -> leads to the state, that the bot cannot afford moves anymore. 

    Definetly needs some refinements. 
"""
import random
from game_utils import Direction as D
from game_utils import TileStatus
from game_utils import Map
from player_base import Player

class SimpleBotWithDesruptivePotential(Player):
    
    def reset(self, player_id, max_players, width, height):
        self.player_name = "Destroyer"
        self.ourMap = Map(width, height)

    def round_begin(self, r):
        pass

    def set_mines(self, status):
        return []
    
    def update_map(self, status):

        for x in range(self.ourMap.width):
            for y in range(self.ourMap.height):
                if status.map[x,y].status != TileStatus.Unknown:
                    self.ourMap[x,y].status = status.map[x,y].status

    def prefered_direction(self, curx, cury, gx, gy):
        # curx, cury = position of bot
        # gx, gy     = position of gold
        # dx         = horizontal distance: positive = gold is right | negative = gold is left
        # dy         = vertical distance: positive = gold is above | negative = gold is below
        # horiz      = best horizontal direction
        # vert       = best vertical direction
        # diag_map   = all diagonal combinations, derived from horizontal and vertical moves
         
        preferred = []
        
        dx = gx - curx
        dy = gy - cury

        horiz = D.right if dx > 0 else (D.left if dx < 0 else None)
        vert = D.up if dy > 0 else (D.down if dy < 0 else None)

        if horiz and vert:

            diag_map = {
                (D.right, D.up): D.up_right,
                (D.right, D.down): D.down_right,
                (D.left, D.up): D.up_left,
                (D.left, D.down): D.down_left,
            }

            preferred.append(diag_map[(horiz, vert)])
            preferred.append(horiz)
            preferred.append(vert)
        
        elif horiz:
            preferred.append(horiz)
        elif vert:
            preferred.append(vert)
        
        # fallback: full up with all remaining directions
        all_dirs = list(D)
        random.shuffle(all_dirs)
        for d in all_dirs:
            if d not in preferred:
                preferred.append(d)
        
        return preferred
    
    def neighbors(self, status, nx, ny):
        tile = status.map[nx,ny]
        if tile.obj is not None and tile.obj.is_player():
            return not tile.obj.is_player(status.player)
        return False
    
    def found_gold(self, status, gx, gy):
        # returns True if gold is in visible map
        tile = status.map[gx, gy]
        return tile.status != TileStatus.Unknown 
    
    def affordable_moves(self, gold):
        """
        How many moves can we afford?
        cost(k) = 1+2+...+k = k*(k+1)/2  ≤ gold
        Solve for largest k where k*(k+1)/2 ≤ gold.
        """
        k = 0
        while (k+1) * (k+2) // 2 <= gold:
            k += 1
        return k
    
    def best_direction(self, status, curx, cury, gx, gy):
        # curx, cury = position of bot
        # gx, gy     = position of gold
        # dx         = horizontal distance: positive = gold is right | negative = gold is left
        # dy         = vertical distance: positive = gold is above | negative = gold is below
         

        preferred = self.prefered_direction(curx, cury, gx, gy)

        best_free = None
        
        for d in preferred:
            dx,dy = d.as_xy()
            nx, ny =curx + dx , cury + dy

            if nx < 0 or nx >= self.ourMap.width:
                continue
            if ny < 0 or ny >= self.ourMap.height:
                continue

            tile_status = self.ourMap[nx,ny].status

            if tile_status == TileStatus.Wall or tile_status == TileStatus.Mine:
                continue

            if self.neighbors(status, nx, ny):
                # player blocks our best route -> ram
                if best_free is None:
                    return (d, None)
                else:
                    continue      # Free path -> don't ram
                
            else:
                return (d, False) # Free, take it
            
        return (None, False) #stuck
    
    def move(self,status):
        self.update_map(status)

        curx, cury = status.x, status.y

        gx, gy = next(iter(status.goldPots))

        if (curx, cury) == (gx,gy):
            return []
        
        #affordable moves this round
        if self.found_gold(status, gx, gy):
            num_moves = self.affordable_moves(status.gold)
        
        else:
            num_moves = 1
        
        moves = []
        x,y = curx, cury
        
        for _ in range(num_moves):
            direction, is_ram = self.best_direction(status, x, y, gx, gy)

            if direction is None:
                break

            moves.append(direction)
            dx, dy = direction.as_xy()
            x += dx
            y += dy
            
            # remaining moves are cancelled anyway after ram
            if is_ram:
                break

            # reaches gold -> stop
            if (x,y) == (gx, gy):
                break
        return moves
    
players = [SimpleBotWithDesruptivePotential()]
