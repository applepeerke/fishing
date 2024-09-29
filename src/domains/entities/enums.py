from enum import Enum


class WaterType(str, Enum):
    River = 'River'
    Brook = 'River'
    Lake = 'Lake'
    Canal = 'Canal'
    Pond = 'Pond'
    Sea = 'Sea'


class SpeciesEnum(str, Enum):
    Ale = 'Ale'
    Carp = 'Carp'
    Perch = 'Perch'
    Roach = 'Roach'
    Pike = 'Pike'


class CarpSubspecies(str, Enum):
    Row = 'Row'
    Scale = 'Scale'
    Leather = 'Leather'
    Wild = 'Wild'


class ActiveAt(str, Enum):
    Day = 'Day'
    Night = 'Night'
    Both = 'Both'


class FishStatus(str, Enum):
    Feeding = 'Feeding'
    Sleeping = 'Sleeping'
    Dead = 'Dead'


class Frequency(str, Enum):
    Monthly = 'Monthly'
    Weekly = 'Weekly'


class FishermanStatus(str, Enum):
    Fishing = 'Fishing'
    Sleeping = 'Sleeping'
    Dead = 'Dead'


class Day(str, Enum):
    Sunday = 'Sunday'
    Monday = 'Monday'
    Tuesday = 'Tuesday'
    Wednesday = 'Wednesday'
    Thursday = 'Thursday'
    Friday = 'Friday'
    Saturday = 'Saturday'
