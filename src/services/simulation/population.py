from src.domains.entities.enums import WaterType
from src.domains.entities.fishspecies.models import FishSpecies
from src.domains.entities.fishingwater.models import FishingWater, FLOATING_WATER
from src.services.test.functions import create_a_random_fish


class Population:
    def __init__(self):
        self. _fishingwaters = {}
        self. _fishingwater_species_fishes = {}

    def add_fishes(self, fishingwater: FishingWater, species_name, fishes: [FishSpecies]):
        # Ini Fishingwater
        self._fishingwaters[fishingwater.id] = fishingwater
        # Ini Fishingwater_species_fishes
        if fishingwater.id not in self._fishingwater_species_fishes:
            self._fishingwater_species_fishes[fishingwater.id] = {}
        if species_name not in self._fishingwater_species_fishes[fishingwater.id]:
            self._fishingwater_species_fishes[fishingwater.id][species_name] = []
        # Add fishes
        [self._fishingwaters[fishingwater.id][species_name].append(fish) for fish in fishes]
        # Recalculate density in still water
        # # Todo TER:
        #     self._fishingwaters[fishingwater.id][species_name].density =

    def catch_a_fish(self, fishingwater: FishingWater, species_name) -> FishSpecies | None:
        if species_name not in self._fishingwaters[fishingwater.id]:
            return None
        fish = self._fishingwaters[fishingwater.id][species_name].pop()
        # Add a new fish in floating water or sea
        if fishingwater.water_type in FLOATING_WATER:
            self._fishingwaters[fishingwater.id][species_name].append(create_a_random_fish(species_name))
        return fish


