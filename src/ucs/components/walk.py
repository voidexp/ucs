from enum import Enum
from typing import List

from raylibpy.spartan import clamp
from ucs.foundation import Actor, Component, Position
from ucs.tilemap import TileMap


class WalkDirection(Enum):
    STOP = 'stop'
    NORTH = 'north'
    SOUTH = 'south'
    EAST = 'east'
    WEST = 'west'


class WalkComponent(Component):

    direction: WalkDirection
    speed: int

    def __init__(self, actor: Actor, speed: int) -> None:
        super().__init__(actor)
        self.direction = WalkDirection.STOP
        self.speed = speed
        self.dst = None

        _walk_components.append(self)

    def destroy(self) -> None:
        _walk_components.remove(self)
        _to_remove.append(self)


_walk_components: List[WalkComponent] = None
_to_remove: List[WalkComponent] = None


def walk_init():
    global _walk_components
    global _to_remove
    _walk_components = []
    _to_remove = []


def walk_update(tilemap: TileMap):
    for garbage in _to_remove:
        col, row = tilemap.pixels_to_coords(garbage.actor.position)
        tilemap.set_occupant_at(col, row, None)
        if garbage.dst is not None:
            tilemap.set_occupant_at(*garbage.dst, None)

    _to_remove.clear()

    for walker in _walk_components:
        col, row = tilemap.pixels_to_coords(walker.actor.position)

        if walker.actor.state is Actor.State.INACTIVE:
            # no movement performed, just set the tile as occupied
            tilemap.set_occupant_at(col, row, walker.actor)
            continue

        # clear current tile
        tilemap.set_occupant_at(col, row, None)

        if walker.dst is None and walker.direction is not WalkDirection.STOP:
            # compute the current tile coordinate from absolute position in
            # pixels
            dst_col, dst_row = _get_adjacent_tile((col, row), walker.direction, tilemap)

            # set the destination, if it's walkable
            if (col, row) != (dst_col, dst_row) and tilemap.is_walkable_at(dst_col, dst_row):
                walker.dst = (dst_col, dst_row)

        energy = walker.speed
        while walker.dst is not None and energy > 0:
            # compute the destination position in pixels from tile coordinates
            dst_x, dst_y = walker.dst
            dst_x = dst_x * tilemap.map.tilewidth + tilemap.x
            dst_y = dst_y * tilemap.map.tileheight + tilemap.y

            # clamp the movement delta to not overshoot the destination position
            x, y = walker.actor.position
            dx = min(abs(dst_x - x), energy)
            dy = min(abs(dst_y - y), energy)

            # update the actor position
            walker.actor.x += dx if dst_x > x else -dx
            walker.actor.y += dy if dst_y > y else -dy

            # consume the energy spent for walking the delta
            energy -= dx + dy

            # check if current destination is reached
            if x == dst_x and y == dst_y:
                if energy == 0 or walker.direction is WalkDirection.STOP:
                    # stop, if requested
                    walker.dst = None
                else:
                    # pick the next destination
                    tile = _get_adjacent_tile(walker.dst, walker.direction, tilemap)
                    walker.dst = tile if tilemap.is_walkable_at(*tile) else None

        # if there's a destination tile, mark it as occupied
        if walker.dst is not None:
            tilemap.set_occupant_at(*walker.dst, walker.actor)
        # otherwise, mark the tile at which the walker stopped as occupied
        else:
            tilemap.set_occupant_at(*tilemap.pixels_to_coords(walker.actor.position), walker.actor)


def _get_adjacent_tile(coord: Position, direction: WalkDirection, tilemap: TileMap) -> Position:
    dst_col, dst_row = coord
     # based on walk direction, pick the destination tile
    if direction is WalkDirection.NORTH:
        dst_row -= 1
    elif direction is WalkDirection.SOUTH:
        dst_row += 1
    elif direction is WalkDirection.WEST:
        dst_col -= 1
    elif direction is WalkDirection.EAST:
        dst_col += 1

    # ensure the tile coordinate is within the tilemap bounds
    dst_row = int(clamp(dst_row, 0, tilemap.map.height))
    dst_col = int(clamp(dst_col, 0, tilemap.map.width))

    return dst_col, dst_row
