from src.domains.entities.enums import SpeciesEnum, CarpSubspecies
from src.domains.entities.fish.fish import Ale, Carp, Pike, Perch, Roach
from src.domains.entities.fishspecies.models import FishSpecies
from src.utils.functions import get_random_item


species_keys = [k for k in SpeciesEnum.__dict__ if not k.startswith('_')]
subspecies_keys = [k for k in CarpSubspecies.__dict__ if not k.startswith('_')]


def create_a_random_fishspecies(species_name=None, subspecies_name=None) -> FishSpecies:
    if not species_name:
        species_name = get_random_item(species_keys)
    if not subspecies_name:
        subspecies_name = get_random_item(subspecies_keys) if species_name == SpeciesEnum.Carp else None
    fish = fishspecies_to_fish(species_name)
    return FishSpecies(
        species_name=species_name,
        subspecies_name=subspecies_name,
        active_at=fish.active_at,
        relative_density=fish.relative_density
    )


def fishspecies_to_fish(species_name: SpeciesEnum):
    """ Here the occurrences """
    if species_name == SpeciesEnum.Ale:
        return Ale()
    if species_name == SpeciesEnum.Carp:
        return Carp()
    if species_name == SpeciesEnum.Pike:
        return Pike()
    if species_name == SpeciesEnum.Perch:
        return Perch()
    if species_name == SpeciesEnum.Roach:
        return Roach()
    else:
        raise NotImplementedError(f'FishSpecies "{species_name}" is not implemented.')