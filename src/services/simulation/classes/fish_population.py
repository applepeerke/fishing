import random

from src.db import crud
from src.domains.entities.enums import CarpSubspecies, ActiveAt
from src.domains.entities.enums import SpeciesEnum
from src.domains.entities.fish.models import Fish
from src.domains.entities.fish_species.models import FishSpecies, HOURS_OF_ACTIVITY
from src.services.simulation.models.sim_fish import SimFishSpecies, SimAle, SimCarp, SimPerch, SimPike, SimRoach
from src.utils.functions import get_random_item, get_random_index_set
from src.utils.functions import get_random_name

rng = random.SystemRandom()


class FishPopulation:
    def __init__(self, db):
        self._db = db

    async def create_fishspecieses(self, db, no_of_fish_species) -> [FishSpecies]:
        # Default species
        default_species = [e for e in SpeciesEnum]
        if no_of_fish_species < len(default_species):
            default_species = [default_species[i] for i in range(no_of_fish_species)]
        [await crud.add(db, self.create_default_fish_species(s)) for s in default_species]

        # Random species
        [await crud.add(db, self.create_a_random_fish_species())
         for _ in range(no_of_fish_species - len(default_species))]
        return await crud.get_all(db, FishSpecies)

    def create_default_fish_species(self, species_name) -> FishSpecies:
        if species_name == SpeciesEnum.Ale:
            return self._sim_fish_to_fish_species(SimAle())
        elif species_name == SpeciesEnum.Carp:
            return self._sim_fish_to_fish_species(SimCarp())
        elif species_name == SpeciesEnum.Perch:
            return self._sim_fish_to_fish_species(SimPerch())
        elif species_name == SpeciesEnum.Pike:
            return self._sim_fish_to_fish_species(SimPike())
        elif species_name == SpeciesEnum.Roach:
            return self._sim_fish_to_fish_species(SimRoach())
        else:
            raise NotImplementedError(f'Default species "{species_name}" is undefined.')

    @staticmethod
    def _sim_fish_to_fish_species(species: SimFishSpecies) -> FishSpecies:
        return FishSpecies(
            species_name=species.species_name,
            subspecies_name=species.subspecies_name,
            active_at=species.active_at,
            relative_density=species.relative_density,
            minimum_length_to_keep_cm=species.minium_length_to_keep,
            max_length_cm=species.max_length_cm,
            max_weight_g=species.max_weight_g,
            yearly_growth_in_cm=species.yearly_growth_in_cm,
            yearly_growth_in_g=species.yearly_growth_in_g,
            # Derived
            hours_of_activity=species.hours_of_activity
        )

    def create_a_random_fish_species(self, species_name=None) -> FishSpecies:
        species_name = get_random_name(max_length=10) if not species_name else species_name
        active_at = get_random_item([e for e in ActiveAt])
        return FishSpecies(
            species_name=species_name,
            subspecies_name=get_random_item([e for e in CarpSubspecies]) if species_name == SpeciesEnum.Carp else None,
            active_at=active_at,
            relative_density=random.randint(1, 100),
            minimum_length_to_keep_cm=random.randint(10, 80),
            max_length_cm=random.randint(10, 800),
            max_weight_g=random.randint(5, 1000000),
            yearly_growth_in_cm=self._get_random_growth(random.randint(2, 10)),
            yearly_growth_in_g=self._get_random_growth(random.randint(10, 100)),
            # Derived
            hours_of_activity=HOURS_OF_ACTIVITY.get(active_at, [])
        )

    async def create_random_fishes(
            self, db, no_of_fishes: int, specieses: [FishSpecies], no_of_fish_species=None) -> [Fish]:

        # No. of species
        if no_of_fish_species is None:
            no_of_fish_species = len(specieses)

        # Determine max = species with max. relative density (0-100)
        species_random_index_set = get_random_index_set(specieses, no_of_fish_species)

        relative_density_max = max(d for d in [specieses[i].relative_density for i in species_random_index_set])
        # Calculate fish count per species, where the species with the highest density gets the full no_of_fishes.
        fish_count_per_selected_species = {
            s: int((specieses[s].relative_density / relative_density_max) * no_of_fishes)
            for s in species_random_index_set
        }
        # Create the random fishes
        [await crud.add(db, self.create_random_fish(specieses[i]))
         for i, count in fish_count_per_selected_species.items() for _ in range(count)]

        return await crud.get_all(db, Fish)

    @staticmethod
    def create_random_fish(species: FishSpecies, water_id=None) -> Fish:
        age = random.randint(1, 50)
        return Fish(
            fishspecies_id=species.id,
            age=age,
            length_cm=min(age * species.yearly_growth_in_cm, species.max_length_cm),
            weight_g=min(age * species.yearly_growth_in_g, species.max_weight_g),
            caught_count=0,
            fishingwater_id=water_id
        )

    @staticmethod
    def _get_random_growth(growth_rate):
        """ Fuzz some with the growth rate """
        return growth_rate + rng.randint(0, growth_rate) - int((growth_rate / 2))
