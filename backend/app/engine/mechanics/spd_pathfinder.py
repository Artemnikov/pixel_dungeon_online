# Copyright (C) 2026 ArtemNikov
#
"""Port of the parts of SPD `com.watabou.utils.PathFinder` that mob retreat
(`Mob.getFurther` -> `Dungeon.flee` -> `PathFinder.getStepBack`) needs.

Cells are flat indices `x + y * width`; `passable` is a flat list of bools.
"""

from collections import deque
from typing import List, Optional

_MAX = 2 ** 31 - 1


class _Grid:
    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.size = width * height
        w = width
        self.dir = [-1, +1, -w, +w, -w - 1, -w + 1, +w - 1, +w + 1]
        self.dir_lr = [-1 - w, -1, -1 + w, -w, +w, +1 - w, +1, +1 + w]

    def neighbours_lr(self, step: int):
        start = 3 if step % self.width == 0 else 0
        end = 3 if (step + 1) % self.width == 0 else 0
        for i in range(start, len(self.dir_lr) - end):
            yield step + self.dir_lr[i]


def _build_escape_distance_map(g: _Grid, cur: int, frm: int, look_ahead: int,
                               passable: List[bool], distance: List[int]) -> int:
    for i in range(g.size):
        distance[i] = _MAX
    dest_dist = _MAX
    queue = deque([frm])
    distance[frm] = 0
    dist = 0
    while queue:
        step = queue.popleft()
        dist = distance[step]
        if dist > dest_dist:
            return dest_dist
        if step == cur:
            dest_dist = dist + look_ahead
        next_distance = dist + 1
        for n in g.neighbours_lr(step):
            if 0 <= n < g.size and passable[n] and distance[n] > next_distance:
                queue.append(n)
                distance[n] = next_distance
    return dist


def _build_distance_map_to_goals(g: _Grid, frm: int, goals: List[bool],
                                 passable: List[bool], distance: List[int]) -> bool:
    if goals[frm]:
        return False
    for i in range(g.size):
        distance[i] = _MAX
    queue = deque()
    for i in range(g.size):
        if goals[i]:
            queue.append(i)
            distance[i] = 0
    found = False
    while queue:
        step = queue.popleft()
        if step == frm:
            found = True
            break
        next_distance = distance[step] + 1
        for n in g.neighbours_lr(step):
            if n == frm or (0 <= n < g.size and passable[n] and distance[n] > next_distance):
                queue.append(n)
                distance[n] = next_distance
    return found


def get_step_back(width: int, height: int, cur: int, frm: int, look_ahead: int,
                  passable: List[bool], can_approach_from_pos: bool) -> int:
    """`PathFinder.getStepBack`: a step from `cur` that retreats from `frm`."""
    g = _Grid(width, height)
    passable = list(passable)
    distance = [_MAX] * g.size
    d = _build_escape_distance_map(g, cur, frm, look_ahead, passable, distance)
    if d == 0:
        return -1

    if not can_approach_from_pos:
        new_d = distance[cur]
        queued = [False] * g.size
        queue = deque([cur])
        queued[cur] = True
        while queue:
            step = queue.popleft()
            if distance[step] > new_d:
                new_d = distance[step]
            for n in g.neighbours_lr(step):
                if 0 <= n < g.size and passable[n]:
                    if distance[n] < distance[cur]:
                        passable[n] = False
                    elif distance[n] >= distance[step] and not queued[n]:
                        queue.append(n)
                        queued[n] = True
        d = min(new_d, d)

    goals = [distance[i] == d for i in range(g.size)]
    if not _build_distance_map_to_goals(g, cur, goals, passable, distance):
        return -1

    min_d = distance[cur]
    mins = cur
    for off in g.dir:
        n = cur + off
        if not (0 <= n < g.size):
            continue
        if distance[n] < min_d:
            min_d = distance[n]
            mins = n
    return mins


def flee_step(game, mob, floor, floor_id: int, frm_xy, fov_cells=None,
              chars: bool = True) -> Optional[tuple]:
    """`Dungeon.flee(ch, from, level.passable, fieldOfView, true)` -> (dx, dy) or None."""
    w, h = floor.width, floor.height
    flags = floor.flags
    if flags is None:
        floor.rebuild_flags()
        flags = floor.flags
    passable = [False] * (w * h)
    flying = bool(getattr(mob, "flying", False))
    large = "LARGE" in getattr(mob, "properties", [])
    for y in range(h):
        for x in range(w):
            ok = flags.passable[y][x] or (flying and flags.avoid[y][x])
            if large and not flags.open_space[y][x]:
                ok = False
            passable[x + y * w] = ok
    cur = mob.pos.x + mob.pos.y * w
    passable[cur] = True
    frm = frm_xy[0] + frm_xy[1] * w

    occupied = set()
    for m in floor.mobs.values():
        if m.is_alive and m.id != mob.id:
            occupied.add(m.pos.x + m.pos.y * w)
    for p in game._players_on_floor(floor_id):
        if p.is_alive:
            occupied.add(p.pos.x + p.pos.y * w)

    can_approach = not (mob.has_buff("terror") or mob.has_buff("dread"))
    look = 8 if can_approach else 4
    step = get_step_back(w, h, cur, frm, look, passable, can_approach)
    while step != -1 and step in occupied and chars:
        passable[step] = False
        step = get_step_back(w, h, cur, frm, look, passable, can_approach)
    if step == -1 or step == cur:
        return None
    return (step % w - mob.pos.x, step // w - mob.pos.y)
