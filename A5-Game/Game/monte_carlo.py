# python3 monte_carlo.py -v test.png

import re
import subprocess
import tempfile
from dataclasses import dataclass
from argparse import ArgumentParser
import matplotlib.pyplot as plt
from matplotlib.legend_handler import HandlerTuple
import time


@dataclass
class StatsRecord:
    player_id: str
    player_name: str
    hp: int
    gold: int
    pos: str
    def __init__(self, cols: list[str]):
        self.player_id = cols[0]
        self.player_name = cols[1]
        self.hp = int(cols[2])
        self.gold = int(cols[3])
        self.pos = cols[4]
    def __repr__(self):
        return f"{self.player_id} {self.player_name} {self.hp} {self.gold} {self.pos}"
    
arg_parser = ArgumentParser(description="Robot Race Monte-Carlo Simulator 7000")
arg_parser.add_argument("-n", "--runs",      help="Number of games to simulate", type=int, default=10)
arg_parser.add_argument("-r", "--rounds",    help="Number of rounds per game",   type=int, default=100)
arg_parser.add_argument("-c", "--chunksize", help="Number of games per chunk",   type=int, default=16)
arg_parser.add_argument("-v", "--viz",       help="Output file (eg. viz.png)",   type=str, default="viz.png")
args = arg_parser.parse_args()


numWins = {}
avgGold = {}
results_per_run = []
def analyze_run(i, runs):
    numPlayers = -1
    run = runs[i]
    p,f = run
    f.seek(0)
    results = []
    stats = False
    for line in f:
        if re.match(r"Player\s*Health\s*Gold\s*Position", line):
            stats = True
            numPlayers = 0
            continue
        if re.match(r"Gold Pots:", line):
            stats = False
            continue
        if stats:
            record = StatsRecord(line.split())
            results.append(record)
            numPlayers += 1

    results_per_run.append(results)

    end_result = results[-numPlayers:]
    winner = max(end_result, key=lambda stat: stat.gold)
    if winner.player_name in numWins:
        numWins[winner.player_name] += 1
    else:
        numWins[winner.player_name] = 1

    print(F"Winner: {winner.player_name}")
    for stat in end_result:
        if stat.player_name in avgGold:
            avgGold[stat.player_name] += stat.gold
        else:
            avgGold[stat.player_name] = stat.gold
        print(stat)
    print("")
    return numPlayers

print(f"Simulating {args.runs} runs of {args.rounds} rounds each in chunks of size {args.chunksize}...")
start_time = time.time()

bar_len = 50
runs = []
numPlayers = 0
i = 0
while i < args.runs:
    for j in range(i, min(i + args.chunksize, args.runs)):
        f = tempfile.TemporaryFile(mode='w+')
        p = subprocess.Popen(["python3", "runRobotRace.py", "--number", str(args.rounds)], stdout=f)
        runs.append((p,f))
    for j in range(i, min(i + args.chunksize, args.runs)):
        p,f = runs[j]
        p.wait()
        print("\r" + ((bar_len + 10) * " "))
        print(f"Run {j+1}/{args.runs} completed.")
        numPlayers = analyze_run(j, runs)
        progress = (j+1)/args.runs
        print("[%3d%%]  "%int(100 * progress) + "[" + (int(progress * bar_len) * "#") + (int(bar_len - progress * bar_len) * " ") + "]", end="\r")
    i += args.chunksize


finish_time = time.time()
elapsed_time = finish_time - start_time

print("")
print("All runs completed in %.3f s." %elapsed_time)
print("")


for player_name in avgGold.keys():
    avgGold[player_name] //= args.runs

print(f"Number of wins:      {numWins}")
print(f"Average gold at end: {avgGold}")

x = list(range(args.rounds + 2))


color_per_player = [
    '#ff000044',
    '#00ff0044',
    '#0000ff44',
    '#ffff0044',
    '#00ffff44',
    '#ff00ff44',
]
plots_per_player = [[] for p in range(numPlayers)]
for r in range(args.runs):
    gold_per_player  = [[] for p in range(numPlayers)]
    for i in range(len(results_per_run[r])):
        gold_per_player[i % numPlayers].append(results_per_run[r][i])

    for player_index, y in enumerate(gold_per_player):
        plot = plt.plot(x, list(map(lambda stat: stat.gold, y)),
                        label=y[0].player_name,
                        color=color_per_player[player_index])
        plots_per_player[player_index % numPlayers].extend(plot)
for i, plot in enumerate(plots_per_player):
    plots_per_player[i] = tuple(plot)

plt.title(f"Stats for {args.runs} {"Run" if args.runs==1 else "Runs"} of {args.rounds} Rounds")
plt.xlabel("Rounds")
plt.ylabel("Gold")
plt.legend(
    plots_per_player,
    avgGold.keys(),
    handler_map={tuple: HandlerTuple(ndivide=None)}
)
plt.savefig(args.viz)
