import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.colors import ListedColormap
import numpy as np

from game_utils import TileStatus


class PovIllustrator:
    def __init__(self, maps, positions, player_name, goldpots, others, health, gold, vizfile, framerate):
        print(f'Illustrating POV for {player_name}')
        self.maps = maps
        self.positions = positions
        self.player_name = player_name
        self.vizfile = vizfile
        self.frame_per_second = framerate
        self.goldpots_history = goldpots
        self.others_history = others
        self.health_history = health
        self.gold_history = gold
        
        self.width = maps[0].width
        self.height = maps[0].height
         
    def _map_to_array(self, m):
        arr = np.zeros((self.height, self.width), dtype=int)

        for x in range(self.width):
            for y in range(self.height):
                status = m[x, y].status
                if status == TileStatus.Unknown:
                    val = 0
                elif status == TileStatus.Empty:
                    val = 1
                elif status == TileStatus.Wall:
                    val = 2
                elif status == TileStatus.Mine:
                    val = 3
                else:
                    val = 1

                arr[y, x] = val

        return arr

    def illustrate(self):
        fig, self.ax = plt.subplots(figsize=(8, 8))

        self.ax.tick_params(bottom=False, left=False)
        self.ax.set_xticklabels([])
        self.ax.set_yticklabels([])
        self.ax.set_xlim(-0.5, self.width - 0.5)
        self.ax.set_ylim(-0.5, self.height - 0.5)
        
        self.stats_text = self.ax.text(0.5, -0.08,"",transform=self.ax.transAxes,ha='center',va='top',fontsize=12)

        self.goldpots = self.ax.scatter(x=[], y=[], marker='*', edgecolors='k', c='gold')
        self.others_scatter = self.ax.scatter([], [],marker='X',c='crimson',edgecolors='k', s=100, zorder=2.5)
        
        cmap = ListedColormap([
            '#444444',  # unknown
            '#ffffff',  # empty
            '#111111',  # wall
            '#cc3333',  # mine
        ])

        first = self._map_to_array(self.maps[0])
        self.img = self.ax.imshow(first, cmap=cmap, vmin=0, vmax=3, origin='lower')

        x, y = self.positions[0]
        self.robot = self.ax.scatter([x], [y],marker='D',c='dodgerblue',edgecolors='k', s=120, zorder=3)

        anim = FuncAnimation(fig,self._illustrate_round,frames=len(self.maps),)

        anim.save(self.vizfile, dpi=80, fps=self.frame_per_second)
        
   
    def _illustrate_round(self, i):
        arr = self._map_to_array(self.maps[i])
        self.img.set_data(arr)

        x, y = self.positions[i]
        self.robot.set_offsets([[x, y]])

        gold_dict = self.goldpots_history[i]
        gold_pos = list(gold_dict.keys())
        gold_amount = list(gold_dict.values())
        self.goldpots.remove()

        gold_arr = np.array(gold_pos, dtype=float)

        self.goldpots = self.ax.scatter(
            gold_arr[:, 0],
            gold_arr[:, 1],
            marker='*',
            edgecolors='k',
            c='gold',
            s=np.array(gold_amount, dtype=float),
            zorder=2
        )
        
        others = self.others_history[i]
        other_pos = [(x, y) for (_, x, y) in others]

        if other_pos:
            other_arr = np.array(other_pos, dtype=float)
            self.others_scatter.set_offsets(other_arr)
        else:
            self.others_scatter.set_offsets(np.empty((0, 2), dtype=float))
        
        # Title and health gold status text
            
        self.ax.set_title(f"{self.player_name} POV - Round {i+1}", fontsize=16)
        
        health = self.health_history[i]
        gold = self.gold_history[i]

        self.stats_text.set_text(f"Health: {health}   |   Gold: {gold}")