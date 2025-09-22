import numpy as np, random

grid_h, grid_w = 0, 0 # wird von maze gesetzt

def a_star(maze, startpos, endpos):
    open_nodes = [startpos]
    closed_nodes = set() # pos : path_length (um am Ende checkpoints zu platzieren)
    g_score = {startpos: 0}

    def evaluate_node(g, pos):
        # Manhatten Distanz (Keine Diagonalen Bewegungen)
        dx, dy = (abs(endpos[0] - pos[0]) , abs(endpos[1] - pos[1]))
        h = dx + dy
        return g + h

    f_score = {startpos: evaluate_node(0, startpos)}
    came_from = {}

    while open_nodes:
        # Node mit dem aktuell besten score aussuchen
        cur_node = min(open_nodes, key=lambda pos: f_score.get(pos, float('inf')))

        # Path Erstellen sobald Ziel gefunden
        if cur_node == endpos:
            path = []
            while cur_node in came_from:
                path.append(cur_node)
                cur_node = came_from[cur_node]
            path.append(startpos)
            path.reverse()
            return path

        open_nodes.remove(cur_node)
        closed_nodes.add(cur_node)

        # Alle neighbours prüfen und bewerten
        for neighbour in get_a_star_neighbours(cur_node):
            if maze[neighbour] == 1 or neighbour in closed_nodes:
                continue

            # g score hochzählen, da distanz + 1
            tentative_g = g_score[cur_node] + 1

            if neighbour not in g_score or tentative_g < g_score[neighbour]:
                came_from[neighbour] = cur_node
                g_score[neighbour] = tentative_g
                f_score[neighbour] = evaluate_node(tentative_g, neighbour)

                if neighbour not in open_nodes:
                    open_nodes.append(neighbour)

    return [startpos]


def get_a_star_neighbours(rc):
    r, c = rc
    neighbours = []
    if r > 0:
        neighbours.append((r - 1, c))
    if r < grid_h-1:
        neighbours.append((r + 1, c))
    if c > 0:
        neighbours.append((r, c - 1))
    if c < grid_w-1:
        neighbours.append((r, c + 1))

    return neighbours

def wilsons_maze(h: int, w: int, random_changes: int = 1):
    global grid_w, grid_h
    height = int(h*0.5)
    width = int(w*0.5)

    grid_h = height * 2 + 1
    grid_w = width * 2 + 1

    maze = np.ones((grid_h, grid_w), dtype=np.uint8)
    unvisited = {(r, c) for r in range(height) for c in range(width)}

    def to_grid(rc):
        return rc[0] * 2 + 1, rc[1] * 2 + 1
    def get_neighbours(rc):
        r, c = rc
        neighbours = []
        if r > 0:
            neighbours.append((r - 1, c))
        if r < height-1:
            neighbours.append((r + 1, c))
        if c > 0:
            neighbours.append((r, c - 1))
        if c < width-1:
            neighbours.append((r, c + 1))

        return neighbours

    start = random.choice(list(unvisited))
    maze[to_grid(start)] = 0
    unvisited.remove(start)


    while unvisited:
        walk_start = random.choice(list(unvisited))
        path = [walk_start]
        while path[-1] in unvisited:
            r, c = path[-1]
            neighbours = get_neighbours((r, c))
            next_cell = random.choice(neighbours)

            if next_cell in path:
                idx = path.index(next_cell)
                path = path[:idx+1]
            else:
                path.append(next_cell)

        for i in range(len(path)):
            r, c = path[i]
            gr, gc = to_grid(path[i])

            maze[to_grid((r, c))] = 0
            if i > 0:
                pr, pc = to_grid(path[i-1])
                wall_r = (gr + pr) // 2
                wall_c = (gc + pc) // 2

                maze[wall_r, wall_c] = 0

            if path[i] in unvisited:
                unvisited.remove(path[i])

    for _ in range(random_changes):
        y = random.randint(0, height - 1)
        x = random.randint(0, width - 1)
        if maze[to_grid((y, x))] == 1:
            maze[to_grid((y, x))] = 0

    return maze
