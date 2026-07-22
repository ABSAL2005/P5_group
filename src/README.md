Changes to ga.py so far:


Changed three parts of the code: Individual_Grid, Individual_DE, and generate_successors. Did not touch ga(), metrics.py, or pathfinding.py.

generate_successors now keeps a small group of the best levels, so the best score never goes down. For the rest, it picks a few random levels at a time and uses the best one as a parent. Two parents make new child levels.

Individual_Grid.mutate gives each tile a small chance to change into a new tile. Common tiles (empty space, walls) are picked more often than rare ones (pipes, enemies), so levels don't turn into random noise. The bottom row (the floor) only ever becomes a gap or stays solid, so most of the floor stays walkable.

Individual_Grid.generate_children makes new levels by mixing two parent levels. It picks two random spots and swaps everything between those spots between the two parents. This keeps tall shapes like pipes mostly in one piece, while still mixing up big parts of the level. Both children are kept and used.

Individual_Grid.calculate_fitness scores each level. It rewards levels for having decoration and being fair to play, so levels feel less empty and more interesting. It takes points away if a level can't be beaten, or if it's almost all empty space.

Individual_DE.calculate_fitness scores levels in the same spirit as the Grid version above: same kind of reward for decoration and fairness, same kind of point loss for levels that can't be beaten or are too empty. It also takes points away for too many stairs, and now also for too many pipes, since too many pipes feels more like a maze than a Mario level.

Individual_DE.mutate gives each piece of the level its own small chance to change. This part of the code was split into its own smaller piece, so it can run on many elements instead of just one. There's also a small chance to add a new piece or remove one, so the level can grow or shrink over time. The part that mixes two parent levels together was not changed — it only needs to be explained in the writeup.

Also added two small helpers, one for each encoding, that pick new random pieces for a level. They favor common, simple pieces over rare ones, instead of picking evenly at random.