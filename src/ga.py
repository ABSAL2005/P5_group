import copy
import heapq
import metrics
import multiprocessing.pool as mpool
import os
import random
import shutil
import time
import math

width = 200
height = 16

options = [
    "-",  # an empty space
    "X",  # a solid wall
    "?",  # a question mark block with a coin
    "M",  # a question mark block with a mushroom
    "B",  # a breakable block
    "o",  # a coin
    "|",  # a pipe segment
    "T",  # a pipe top
    "E",  # an enemy
    #"f",  # a flag, do not generate
    #"v",  # a flagpole, do not generate
    #"m"  # mario's start position, do not generate
]

# Weights for each tile type. Empty space and walls show up most, since
# real levels are mostly that. Pipes, coins, etc. show up less.
option_weights = [
    40,  # "-"
    20,  # "X"
    4,   # "?"
    1,   # "M"
    6,   # "B"
    6,   # "o"
    2,   # "|"
    1,   # "T"
    4,   # "E"
]


def weighted_choice(items, weights):
    # Picks one item using the weights. Adds up all weights, picks a
    # random point in that range, then walks the list until we pass
    # that point.
    total = 0
    i = 0
    while i < len(weights):
        total = total + weights[i]
        i = i + 1

    r = random.uniform(0, total)
    upto = 0
    i = 0
    while i < len(items):
        upto = upto + weights[i]
        if upto >= r:
            return items[i]
        i = i + 1
    return items[len(items) - 1]


# The level as a grid of tiles


class Individual_Grid(object):
    __slots__ = ["genome", "_fitness"]

    def __init__(self, genome):
        self.genome = copy.deepcopy(genome)
        self._fitness = None

    # Update this individual's estimate of its fitness.
    # This can be expensive so we do it once and then cache the result.
    def calculate_fitness(self):
        measurements = metrics.metrics(self.to_level())
        # Print out the possible measurements or look at the implementation of metrics.py for other keys:
        # print(measurements.keys())
        # Default fitness function: Just some arbitrary combination of a few criteria.  Is it good?  Who knows?
        # STUDENT Modify this, and possibly add more metrics.  You can replace this with whatever code you like.
        coefficients = {}
        coefficients["meaningfulJumpVariance"] = 0.5
        coefficients["negativeSpace"] = 0.6
        coefficients["pathPercentage"] = 0.5
        coefficients["emptyPercentage"] = 0.6
        coefficients["linearity"] = -0.5
        coefficients["solvability"] = 2.0
        coefficients["decorationPercentage"] = 0.3
        coefficients["leniency"] = 0.2

        total = 0.0
        for key in coefficients:
            total = total + coefficients[key] * measurements[key]

        penalties = 0
        # big point loss if the level can't be beaten
        if measurements["solvability"] < 1.0:
            penalties = penalties - 5
        # small point loss if the level is mostly empty
        if measurements["emptyPercentage"] > 0.9:
            penalties = penalties - 1

        self._fitness = total + penalties
        return self

    # Return the cached fitness value or calculate it as needed.
    def fitness(self):
        if self._fitness is None:
            self.calculate_fitness()
        return self._fitness

    # Mutate a genome into a new genome.  Note that this is a _genome_, not an individual!
    def mutate(self, genome):
        # STUDENT implement a mutation operator, also consider not mutating this individual
        # STUDENT also consider weighting the different tile types so it's not uniformly random
        # STUDENT consider putting more constraints on this to prevent pipes in the air, etc

        # chance each tile has to change. kept low
        mutation_rate = 0.01
        left = 1
        right = width - 1
        floor_row = height - 1
        floor_options = ["-", "X"]
        floor_weights = [1, 9]

        y = 0
        while y < height:
            x = left
            while x < right:
                if random.random() < mutation_rate:
                    if y == floor_row:
                        # floor row only turns into a gap or stays solid,
                        # so mutation can add a gap but not wreck the floor
                        genome[y][x] = weighted_choice(floor_options, floor_weights)
                    else:
                        genome[y][x] = weighted_choice(options, option_weights)
                x = x + 1
            y = y + 1
        return genome

    # Create zero or more children from self and other
    def generate_children(self, other):
        # STUDENT Which one should you take?  Self, or other?  Why?
        # STUDENT consider putting more constraints on this to prevent pipes in the air, etc

        # pick two random columns and swap everything between them
        # between the two parents. keeps tall shapes like pipes mostly
        # in one piece, but still mixes up big parts of the level.
        # makes two children so both halves get used.
        left = 1
        right = width - 1
        pt1 = random.randint(left, right - 1)
        pt2 = random.randint(left, right - 1)
        lo = pt1
        hi = pt2
        if lo > hi:
            temp = lo
            lo = hi
            hi = temp

        genome_a = copy.deepcopy(self.genome)
        genome_b = copy.deepcopy(other.genome)

        y = 0
        while y < height:
            x = lo
            while x < hi:
                temp = genome_a[y][x]
                genome_a[y][x] = genome_b[y][x]
                genome_b[y][x] = temp
                x = x + 1
            y = y + 1

        # do mutation; note we're returning a tuple here
        new_genome_a = self.mutate(genome_a)
        new_genome_b = self.mutate(genome_b)
        return (Individual_Grid(new_genome_a), Individual_Grid(new_genome_b))

    # Turn the genome into a level string (easy for this genome)
    def to_level(self):
        return self.genome

    # These both start with every floor tile filled with Xs
    # STUDENT Feel free to change these
    @classmethod
    def empty_individual(cls):
        g = []
        row = 0
        while row < height:
            r = []
            col = 0
            while col < width:
                r.append("-")
                col = col + 1
            g.append(r)
            row = row + 1

        col = 0
        while col < width:
            g[15][col] = "X"
            col = col + 1

        g[14][0] = "m"
        g[7][-1] = "v"
        col = 8
        while col < 14:
            g[col][-1] = "f"
            col = col + 1
        col = 14
        while col < 16:
            g[col][-1] = "X"
            col = col + 1
        return cls(g)

    @classmethod
    def random_individual(cls):
        # STUDENT consider putting more constraints on this to prevent pipes in the air, etc
        # STUDENT also consider weighting the different tile types so it's not uniformly random
        g = []
        row = 0
        while row < height:
            r = []
            col = 0
            while col < width:
                r.append(weighted_choice(options, option_weights))
                col = col + 1
            g.append(r)
            row = row + 1

        col = 0
        while col < width:
            g[15][col] = "X"
            col = col + 1

        g[14][0] = "m"
        g[7][-1] = "v"
        g[8:14][-1] = ["f"] * 6
        g[14:16][-1] = ["X", "X"]
        return cls(g)


def offset_by_upto(val, variance, min=None, max=None):
    val += random.normalvariate(0, variance**0.5)
    if min is not None and val < min:
        val = min
    if max is not None and val > max:
        val = max
    return int(val)


def clip(lo, val, hi):
    if val < lo:
        return lo
    if val > hi:
        return hi
    return val


def random_design_element():
    # picks one random type, then builds it. one branch per type,
    # instead of one big list of options to choose from.
    choice = random.randint(0, 7)
    if choice == 0:
        return (random.randint(1, width - 2), "0_hole", random.randint(1, 8))
    elif choice == 1:
        madeof = random.choice(["?", "X", "B"])
        return (random.randint(1, width - 2), "1_platform", random.randint(1, 8), random.randint(0, height - 1), madeof)
    elif choice == 2:
        return (random.randint(1, width - 2), "2_enemy")
    elif choice == 3:
        return (random.randint(1, width - 2), "3_coin", random.randint(0, height - 1))
    elif choice == 4:
        breakable = random.choice([True, False])
        return (random.randint(1, width - 2), "4_block", random.randint(0, height - 1), breakable)
    elif choice == 5:
        has_powerup = random.choice([True, False])
        return (random.randint(1, width - 2), "5_qblock", random.randint(0, height - 1), has_powerup)
    elif choice == 6:
        dx = random.choice([-1, 1])
        return (random.randint(1, width - 2), "6_stairs", random.randint(1, height - 4), dx)
    else:
        return (random.randint(1, width - 2), "7_pipe", random.randint(2, height - 4))


def mutate_one_element(de):
    # takes one design element, changes one of its values, returns the
    # new one. its own function so mutate() can call it on many elements.
    x = de[0]
    de_type = de[1]
    choice = random.random()
    new_de = de
    if de_type == "4_block":
        y = de[2]
        breakable = de[3]
        if choice < 0.33:
            x = offset_by_upto(x, width / 8, min=1, max=width - 2)
        elif choice < 0.66:
            y = offset_by_upto(y, height / 2, min=0, max=height - 1)
        else:
            breakable = not de[3]
        new_de = (x, de_type, y, breakable)
    elif de_type == "5_qblock":
        y = de[2]
        has_powerup = de[3]  # boolean
        if choice < 0.33:
            x = offset_by_upto(x, width / 8, min=1, max=width - 2)
        elif choice < 0.66:
            y = offset_by_upto(y, height / 2, min=0, max=height - 1)
        else:
            has_powerup = not de[3]
        new_de = (x, de_type, y, has_powerup)
    elif de_type == "3_coin":
        y = de[2]
        if choice < 0.5:
            x = offset_by_upto(x, width / 8, min=1, max=width - 2)
        else:
            y = offset_by_upto(y, height / 2, min=0, max=height - 1)
        new_de = (x, de_type, y)
    elif de_type == "7_pipe":
        h = de[2]
        if choice < 0.5:
            x = offset_by_upto(x, width / 8, min=1, max=width - 2)
        else:
            h = offset_by_upto(h, 2, min=2, max=height - 4)
        new_de = (x, de_type, h)
    elif de_type == "0_hole":
        w = de[2]
        if choice < 0.5:
            x = offset_by_upto(x, width / 8, min=1, max=width - 2)
        else:
            w = offset_by_upto(w, 4, min=1, max=width - 2)
        new_de = (x, de_type, w)
    elif de_type == "6_stairs":
        h = de[2]
        dx = de[3]  # -1 or 1
        if choice < 0.33:
            x = offset_by_upto(x, width / 8, min=1, max=width - 2)
        elif choice < 0.66:
            h = offset_by_upto(h, 8, min=1, max=height - 4)
        else:
            dx = -dx
        new_de = (x, de_type, h, dx)
    elif de_type == "1_platform":
        w = de[2]
        y = de[3]
        madeof = de[4]  # from "?", "X", "B"
        if choice < 0.25:
            x = offset_by_upto(x, width / 8, min=1, max=width - 2)
        elif choice < 0.5:
            w = offset_by_upto(w, 8, min=1, max=width - 2)
        elif choice < 0.75:
            y = offset_by_upto(y, height, min=0, max=height - 1)
        else:
            madeof = random.choice(["?", "X", "B"])
        new_de = (x, de_type, w, y, madeof)
    elif de_type == "2_enemy":
        # enemies used to never change once placed. now they can
        # move left/right a bit.
        x = offset_by_upto(x, width / 8, min=1, max=width - 2)
        new_de = (x, de_type)
    return new_de

# Inspired by https://www.researchgate.net/profile/Philippe_Pasquier/publication/220867545_Towards_a_Generic_Framework_for_Automated_Video_Game_Level_Creation/links/0912f510ac2bed57d1000000.pdf


class Individual_DE(object):
    # Calculating the level isn't cheap either so we cache it too.
    __slots__ = ["genome", "_fitness", "_level"]

    # Genome is a heapq of design elements sorted by X, then type, then other parameters
    def __init__(self, genome):
        self.genome = list(genome)
        heapq.heapify(self.genome)
        self._fitness = None
        self._level = None

    # Calculate and cache fitness
    def calculate_fitness(self):
        measurements = metrics.metrics(self.to_level())
        # STUDENT Add more metrics?
        # STUDENT Improve this with any code you like

        coefficients = {}
        coefficients["meaningfulJumpVariance"] = 0.5
        coefficients["negativeSpace"] = 0.6
        coefficients["pathPercentage"] = 0.5
        coefficients["emptyPercentage"] = 0.6
        coefficients["linearity"] = -0.5
        coefficients["solvability"] = 2.0
        coefficients["decorationPercentage"] = 0.3
        coefficients["leniency"] = 0.2

        total = 0.0
        for key in coefficients:
            total = total + coefficients[key] * measurements[key]

        # count stairs and pipes in one pass through the genome
        stairs_count = 0
        pipe_count = 0
        i = 0
        while i < len(self.genome):
            de_type = self.genome[i][1]
            if de_type == "6_stairs":
                stairs_count = stairs_count + 1
            elif de_type == "7_pipe":
                pipe_count = pipe_count + 1
            i = i + 1

        penalties = 0
        # too many stairs looks repetitive
        if stairs_count > 5:
            penalties = penalties - 2
        # too many pipes feels more like a maze than a Mario level
        if pipe_count > 8:
            penalties = penalties - 2
        # same point losses as Individual_Grid, for the same reasons
        if measurements["solvability"] < 1.0:
            penalties = penalties - 5
        if measurements["emptyPercentage"] > 0.9:
            penalties = penalties - 1

        # STUDENT If you go for the FI-2POP extra credit, you can put constraint calculation in here too and cache it in a new entry in __slots__.
        self._fitness = total + penalties
        return self

    def fitness(self):
        if self._fitness is None:
            self.calculate_fitness()
        return self._fitness

    def mutate(self, new_genome):
        # old code only changed one element per call, no matter the
        # genome size. now every element gets its own small chance to
        # change (using mutate_one_element). also a small chance to add
        # or remove an element, so the genome size can change too.
        element_mutation_rate = 0.05
        add_chance = 0.02
        remove_chance = 0.02

        i = 0
        while i < len(new_genome):
            if random.random() < element_mutation_rate:
                new_genome[i] = mutate_one_element(new_genome[i])
            i = i + 1

        if random.random() < add_chance:
            new_genome.append(random_design_element())

        if random.random() < remove_chance and len(new_genome) > 1:
            remove_index = random.randint(0, len(new_genome) - 1)
            new_genome.pop(remove_index)

        return new_genome

    def generate_children(self, other):
        # STUDENT How does this work?  Explain it in your writeup.
        pa = random.randint(0, len(self.genome) - 1)
        pb = random.randint(0, len(other.genome) - 1)
        a_part = self.genome[:pa] if len(self.genome) > 0 else []
        b_part = other.genome[pb:] if len(other.genome) > 0 else []
        ga = a_part + b_part
        b_part = other.genome[:pb] if len(other.genome) > 0 else []
        a_part = self.genome[pa:] if len(self.genome) > 0 else []
        gb = b_part + a_part
        # do mutation
        return Individual_DE(self.mutate(ga)), Individual_DE(self.mutate(gb))

    # Apply the DEs to a base level.
    def to_level(self):
        if self._level is None:
            base = Individual_Grid.empty_individual().to_level()
            for de in sorted(self.genome, key=lambda de: (de[1], de[0], de)):
                # de: x, type, ...
                x = de[0]
                de_type = de[1]
                if de_type == "4_block":
                    y = de[2]
                    breakable = de[3]
                    base[y][x] = "B" if breakable else "X"
                elif de_type == "5_qblock":
                    y = de[2]
                    has_powerup = de[3]  # boolean
                    base[y][x] = "M" if has_powerup else "?"
                elif de_type == "3_coin":
                    y = de[2]
                    base[y][x] = "o"
                elif de_type == "7_pipe":
                    h = de[2]
                    base[height - h - 1][x] = "T"
                    for y in range(height - h, height):
                        base[y][x] = "|"
                elif de_type == "0_hole":
                    w = de[2]
                    for x2 in range(w):
                        base[height - 1][clip(1, x + x2, width - 2)] = "-"
                elif de_type == "6_stairs":
                    h = de[2]
                    dx = de[3]  # -1 or 1
                    for x2 in range(1, h + 1):
                        for y in range(x2 if dx == 1 else h - x2):
                            base[clip(0, height - y - 1, height - 1)][clip(1, x + x2, width - 2)] = "X"
                elif de_type == "1_platform":
                    w = de[2]
                    h = de[3]
                    madeof = de[4]  # from "?", "X", "B"
                    for x2 in range(w):
                        base[clip(0, height - h - 1, height - 1)][clip(1, x + x2, width - 2)] = madeof
                elif de_type == "2_enemy":
                    base[height - 2][x] = "E"
            self._level = base
        return self._level

    @classmethod
    def empty_individual(_cls):
        # STUDENT Maybe enhance this
        g = []
        return Individual_DE(g)

    @classmethod
    def random_individual(_cls):
        # STUDENT Maybe enhance this
        elt_count = random.randint(8, 128)
        g = []
        i = 0
        while i < elt_count:
            g.append(random_design_element())
            i = i + 1
        return Individual_DE(g)


Individual = Individual_Grid


def generate_successors(population):
    results = []
    # STUDENT Design and implement this
    # Hint: Call generate_children() on some individuals and fill up results.

    pop_size = len(population)

    # copy the best few levels as-is into the next round, so the best
    # score never drops. costs a bit of diversity, but keeps progress.
    elite_count = int(0.05 * pop_size)
    if elite_count < 2:
        elite_count = 2

    elites = sorted(population, key=Individual.fitness, reverse=True)
    i = 0
    while i < elite_count:
        results.append(copy.deepcopy(elites[i]))
        i = i + 1

    # pick a few random levels, use the best one as a parent. bigger
    # groups pick stronger parents more often (less diversity). smaller
    # groups let weaker levels win sometimes (more diversity).
    tournament_size = 5

    def tournament_select():
        sample_size = tournament_size
        if pop_size < sample_size:
            sample_size = pop_size
        contenders = random.sample(population, sample_size)
        best = contenders[0]
        i = 1
        while i < len(contenders):
            if contenders[i].fitness() > best.fitness():
                best = contenders[i]
            i = i + 1
        return best

    while len(results) < pop_size:
        parent_a = tournament_select()
        parent_b = tournament_select()
        children = parent_a.generate_children(parent_b)
        i = 0
        while i < len(children):
            if len(results) >= pop_size:
                break
            results.append(children[i])
            i = i + 1

    return results[0:pop_size]


def ga():
    # STUDENT Feel free to play with this parameter
    pop_limit = 480
    # Code to parallelize some computations
    batches = os.cpu_count()
    if pop_limit % batches != 0:
        print("It's ideal if pop_limit divides evenly into " + str(batches) + " batches.")
    batch_size = int(math.ceil(pop_limit / batches))
    with mpool.Pool(processes=os.cpu_count()) as pool:
        init_time = time.time()
        # STUDENT (Optional) change population initialization
        population = [Individual.random_individual() if random.random() < 0.9
                      else Individual.empty_individual()
                      for _g in range(pop_limit)]
        # But leave this line alone; we have to reassign to population because we get a new population that has more cached stuff in it.
        population = pool.map(Individual.calculate_fitness,
                              population,
                              batch_size)
        init_done = time.time()
        print("Created and calculated initial population statistics in:", init_done - init_time, "seconds")
        generation = 0
        start = time.time()
        now = start
        print("Use ctrl-c to terminate this loop manually.")
        try:
            while True:
                now = time.time()
                # Print out statistics
                if generation > 0:
                    best = max(population, key=Individual.fitness)
                    print("Generation:", str(generation))
                    print("Max fitness:", str(best.fitness()))
                    print("Average generation time:", (now - start) / generation)
                    print("Net time:", now - start)
                    with open("levels/last.txt", 'w') as f:
                        for row in best.to_level():
                            f.write("".join(row) + "\n")
                generation += 1
                # STUDENT Determine stopping condition
                stop_condition = False
                if stop_condition:
                    break
                # STUDENT Also consider using FI-2POP as in the Sorenson & Pasquier paper
                gentime = time.time()
                next_population = generate_successors(population)
                gendone = time.time()
                print("Generated successors in:", gendone - gentime, "seconds")
                # Calculate fitness in batches in parallel
                next_population = pool.map(Individual.calculate_fitness,
                                           next_population,
                                           batch_size)
                popdone = time.time()
                print("Calculated fitnesses in:", popdone - gendone, "seconds")
                population = next_population
        except KeyboardInterrupt:
            pass
    return population


if __name__ == "__main__":
    final_gen = sorted(ga(), key=Individual.fitness, reverse=True)
    best = final_gen[0]
    print("Best fitness: " + str(best.fitness()))
    now = time.strftime("%m_%d_%H_%M_%S")
    # STUDENT You can change this if you want to blast out the whole generation, or ten random samples, or...
    for k in range(0, 10):
        with open("levels/" + now + "_" + str(k) + ".txt", 'w') as f:
            for row in final_gen[k].to_level():
                f.write("".join(row) + "\n")    