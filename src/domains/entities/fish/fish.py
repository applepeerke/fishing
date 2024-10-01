import random
from numpy import random as np_random
from src.domains.entities.enums import SpeciesEnum, ActiveAt, CarpSubspecies
from src.utils.functions import get_random_name

hours_of_activity = {
    ActiveAt.Day: [7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17],
    ActiveAt.Night: [18, 19, 20, 21, 22, 23, 0, 1, 2, 3, 4, 5, 6],
    ActiveAt.Both: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23]
}

age_division = np_random.normal(loc=8, scale=3, size=(1, 100))[0]


class Fish:
    @property
    def name(self):
        return self._name

    @property
    def age(self):
        return self._age

    @property
    def weight_in_g(self):
        return self._weight_in_g

    @property
    def length(self):
        return self._length

    def __init__(self):
        self._name = get_random_name(10)
        self._age = abs(int(age_division[random.randint(0, 99)]))  # Do not allow < 0.
        self._weight_in_g = 0
        self._length = 0


class FishSpecies(Fish):

    @property
    def species_name(self):
        return self._species_name

    @property
    def active_at(self):
        return self._active_at

    @property
    def hours_of_activity(self):
        return self._hours_of_activity

    @property
    def relative_density(self):
        return self._relative_density

    @property
    def yearly_growth_in_cm(self):
        return self._yearly_growth_in_cm

    @property
    def yearly_growth_in_g(self):
        return self._yearly_growth_in_g

    @property
    def minium_length_to_keep(self):
        return self._minimum_length_to_keep

    def __init__(self,
                 species_name: SpeciesEnum,
                 subspecies_name,
                 active_at: ActiveAt,
                 relative_density: int,
                 yearly_growth_in_cm: int,
                 yearly_growth_in_g: int,
                 max_length: int,
                 max_weight: int,
                 minimum_length_to_keep: int
                 ):
        """
        @param species_name: One of SpeciesEnum.
        @param active_at: Day/Night/Both
        @param relative_density: no. of fishes of this species compared to Roach = 100.
        @param yearly_growth_in_cm: % increase of body length per year (in cm).
        @param yearly_growth_in_g:  % increase of body mass per year (in g).
        @param max_length:  % maximum length in cm.
        @param max_weight:  % maximum weight in g.
        @param minimum_length_to_keep: minimum length to keep a catch.
        """
        super().__init__()
        self._species_name = species_name
        self._subspecies_name = subspecies_name
        self._active_at = active_at
        self._max_length = max_length
        self._max_weight = max_weight
        self._yearly_growth_in_cm = self._get_random_growth(yearly_growth_in_cm)
        self._yearly_growth_in_g = self._get_random_growth(yearly_growth_in_g)
        self._relative_density = relative_density
        self._hours_of_activity = hours_of_activity[active_at]
        self._minimum_length_to_keep = minimum_length_to_keep

        # Carp: 5-12 cm/year, max. 120 => random growth * age
        #       0.5-5 lbs/year, max. 80 => random growth * age
        self._length = min(self._age * self._yearly_growth_in_cm, self._max_length)
        self._weight_in_g = min(self._age * self._yearly_growth_in_g, self._max_weight)

    @staticmethod
    def _get_random_growth(growth_rate):
        """ Fuzz some with the growth rate """
        return growth_rate + random.randint(0, growth_rate) - int((growth_rate / 2))


class Ale(FishSpecies):
    def __init__(self):
        super().__init__(
            SpeciesEnum.Ale,
            None,
            ActiveAt.Night,
            15,
            10,
            50,
            150,
            400,
            20,
        )


class Carp(FishSpecies):
    def __init__(self):
        super().__init__(
            SpeciesEnum.Carp,
            CarpSubspecies.Scale,
            ActiveAt.Night,
            20,
            8,
            800,
            120,
            30000,
            15
        )


class Pike(FishSpecies):
    def __init__(self):
        super().__init__(
            SpeciesEnum.Pike,
            None,
            ActiveAt.Day,
            10,
            8,
            400,
            140,
            20000,
            25
        )


class Perch(FishSpecies):
    def __init__(self):
        super().__init__(
            SpeciesEnum.Perch,
            None,
            ActiveAt.Day,
            30,
            3,
            200,
            60,
            5000,
            10
        )


class Roach(FishSpecies):
    def __init__(self):
        super().__init__(
            SpeciesEnum.Roach,
            None,
            ActiveAt.Day,
            100,
            2,
            100,
            40,
            2000,
            15
        )
