class TileType:
    VOID = 0
    WALL = 1
    FLOOR = 2
    DOOR = 3
    STAIRS_UP = 4
    STAIRS_DOWN = 5
    FLOOR_WOOD = 6
    FLOOR_WATER = 7
    FLOOR_COBBLE = 8
    FLOOR_GRASS = 9
    LOCKED_DOOR = 10
    SECRET_TRAP = 11
    TRAP = 12
    INACTIVE_TRAP = 13
    EMBERS = 14
    REGION_DECO = 15
    REGION_DECO_ALT = 16
    WALL_DECO = 17
    EMPTY_DECO = 18
    HIGH_GRASS = 19
    SECRET_DOOR = 20
    LOCKED_EXIT = 21
    OPEN_DOOR = 22
    FURROWED_GRASS = 30
    CRYSTAL_DOOR = 31
    BARRICADE = 32
    CHASM = 33


class RoomKind:
    STANDARD = "standard"
    SPECIAL = "special"
    HIDDEN = "hidden"


class TrapType:
    WORN_DART = "worn_dart"
    TENGU_DART = "tengu_dart"
    BURNING_TRAP = "burning_trap"
    BLAZING_TRAP = "blazing_trap"
    SHOCKING_TRAP = "shocking_trap"
    STORM_TRAP = "storm_trap"
    CHILLING_TRAP = "chilling_trap"
    TOXIC_TRAP = "toxic_trap"
    POISON_DART_TRAP = "poison_dart_trap"
    CONFUSION_TRAP = "confusion_trap"
    FLOCK_TRAP = "flock_trap"
    SUMMONING_TRAP = "summoning_trap"
    TELEPORTATION_TRAP = "teleportation_trap"
    GATEWAY_TRAP = "gateway_trap"
    ALARM_TRAP = "alarm_trap"
    OOZE_TRAP = "ooze_trap"
    GRIPPING_TRAP = "gripping_trap"
    GEYSER_TRAP = "geyser_trap"
    FROST_TRAP = "frost_trap"
    CORROSION_TRAP = "corrosion_trap"
    ROCKFALL_TRAP = "rockfall_trap"
    GUARDIAN_TRAP = "guardian_trap"
    WARPING_TRAP = "warping_trap"
    PITFALL_TRAP = "pitfall_trap"
    DISINTEGRATION_TRAP = "disintegration_trap"
    FLASHING_TRAP = "flashing_trap"
    WEAKENING_TRAP = "weakening_trap"
    DISARMING_TRAP = "disarming_trap"
    CURSING_TRAP = "cursing_trap"
    DISTORTION_TRAP = "distortion_trap"
    GRIM_TRAP = "grim_trap"
    EXPLOSIVE_TRAP = "explosive_trap"

    CAN_BE_HIDDEN = {
        WORN_DART: False,
        TENGU_DART: True,
        BURNING_TRAP: True,
        BLAZING_TRAP: True,
        SHOCKING_TRAP: True,
        STORM_TRAP: True,
        CHILLING_TRAP: True,
        TOXIC_TRAP: True,
        POISON_DART_TRAP: False,
        CONFUSION_TRAP: True,
        FLOCK_TRAP: True,
        SUMMONING_TRAP: True,
        TELEPORTATION_TRAP: True,
        GATEWAY_TRAP: True,
        ALARM_TRAP: True,
        OOZE_TRAP: True,
        GRIPPING_TRAP: True,
        GEYSER_TRAP: True,
        FROST_TRAP: True,
        CORROSION_TRAP: True,
        ROCKFALL_TRAP: False,
        GUARDIAN_TRAP: True,
        WARPING_TRAP: True,
        PITFALL_TRAP: True,
        DISINTEGRATION_TRAP: False,
        FLASHING_TRAP: True,
        WEAKENING_TRAP: True,
        DISARMING_TRAP: True,
        CURSING_TRAP: True,
        DISTORTION_TRAP: True,
        GRIM_TRAP: False,
        EXPLOSIVE_TRAP: True,
    }


class TrapVisual:
    RED = 0
    ORANGE = 1
    YELLOW = 2
    GREEN = 3
    TEAL = 4
    VIOLET = 5
    WHITE = 6
    GREY = 7
    BLACK = 8

    DOTS = 0
    WAVES = 1
    GRILL = 2
    STARS = 3
    DIAMOND = 4
    CROSSHAIR = 5
    LARGE_DOT = 6

    # (color, shape) per SPD trap subclass
    MAPPING = {
        TrapType.WORN_DART: (GREY, CROSSHAIR),
        TrapType.TENGU_DART: (GREEN, CROSSHAIR),
        TrapType.BURNING_TRAP: (ORANGE, DOTS),
        TrapType.BLAZING_TRAP: (ORANGE, STARS),
        TrapType.SHOCKING_TRAP: (YELLOW, DOTS),
        TrapType.STORM_TRAP: (YELLOW, STARS),
        TrapType.CHILLING_TRAP: (WHITE, DOTS),
        TrapType.TOXIC_TRAP: (GREEN, GRILL),
        TrapType.POISON_DART_TRAP: (GREEN, CROSSHAIR),
        TrapType.CONFUSION_TRAP: (TEAL, GRILL),
        TrapType.FLOCK_TRAP: (WHITE, WAVES),
        TrapType.SUMMONING_TRAP: (TEAL, WAVES),
        TrapType.TELEPORTATION_TRAP: (TEAL, DOTS),
        TrapType.GATEWAY_TRAP: (TEAL, CROSSHAIR),
        TrapType.ALARM_TRAP: (RED, DOTS),
        TrapType.OOZE_TRAP: (GREEN, DOTS),
        TrapType.GRIPPING_TRAP: (GREY, DOTS),
        TrapType.GEYSER_TRAP: (TEAL, DIAMOND),
        TrapType.FROST_TRAP: (WHITE, STARS),
        TrapType.CORROSION_TRAP: (GREY, GRILL),
        TrapType.ROCKFALL_TRAP: (GREY, DIAMOND),
        TrapType.GUARDIAN_TRAP: (RED, STARS),
        TrapType.WARPING_TRAP: (TEAL, STARS),
        TrapType.PITFALL_TRAP: (RED, DIAMOND),
        TrapType.DISINTEGRATION_TRAP: (VIOLET, CROSSHAIR),
        TrapType.FLASHING_TRAP: (GREY, STARS),
        TrapType.WEAKENING_TRAP: (GREEN, WAVES),
        TrapType.DISARMING_TRAP: (RED, LARGE_DOT),
        TrapType.CURSING_TRAP: (VIOLET, WAVES),
        TrapType.DISTORTION_TRAP: (TEAL, LARGE_DOT),
        TrapType.GRIM_TRAP: (GREY, LARGE_DOT),
        TrapType.EXPLOSIVE_TRAP: (ORANGE, DIAMOND),
    }

    @staticmethod
    def sprite_index(color: int, shape: int) -> int:
        return color + shape * 16

    @staticmethod
    def disarmed_index(shape: int) -> int:
        return TrapVisual.BLACK + shape * 16
