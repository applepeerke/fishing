import random

from src.domains.entities.enums import SpeciesEnum, ActiveAt
from src.utils.functions import get_random_name

hours_of_activity = {
    ActiveAt.Day: [7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17],
    ActiveAt.Night: [18, 19, 20, 21, 22, 23, 0, 1, 2, 3, 4, 5, 6],
    ActiveAt.Both: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23]
}

class Species:

    @property
    def species_name(self):
        return self._species_name

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

    @property
    def active_at(self):
        return self._active_at

    @property
    def hours_of_activity(self):
        return self._hours_of_activity

    @property
    def relative_density(self):
        return self._relative_density

    def __init__(self, species_name: str | SpeciesEnum, age=None):
        self._species_name = species_name.value \
            if isinstance(species_name, SpeciesEnum) \
            else species_name
        self._age = age if age else random.randint(1, 20)  # Do not allow 0 to prevent negative weight.
        self._name = get_random_name(10)
        self._active_at = None
        self._hours_of_activity = []
        self._relative_density: int = 0
        self._weight_in_g = 0
        self._length = 0

        if species_name == SpeciesEnum.Ale:
            self._weight_in_g = self._get_random_growth(50)
            self._length = self._get_random_growth(8)
            self._active_at = ActiveAt.Night
            self._relative_density = 15
        elif species_name == SpeciesEnum.Carp:
            self._weight_in_g = self._get_random_growth(1000)
            self._length = self._get_random_growth(5)
            self._active_at = ActiveAt.Both
            self._relative_density = 20
        elif species_name == SpeciesEnum.Pike:
            self._weight_in_g = self._get_random_growth(500)
            self._length = self._get_random_growth(5)
            self._active_at = ActiveAt.Day
            self._relative_density = 10
        elif species_name == SpeciesEnum.Perch:
            self._weight_in_g = self._get_random_growth(200)
            self._length = self._get_random_growth(3)
            self._active_at = ActiveAt.Day
            self._relative_density = 30
        elif species_name == SpeciesEnum.Roach:
            self._weight_in_g = self._get_random_growth(200)
            self._length = self._get_random_growth(2)
            self._active_at = ActiveAt.Day
            self._relative_density = 100
        else:
            raise NotImplementedError

        self._hours_of_activity = hours_of_activity[self._active_at]

    def _get_random_growth(self, avg_gram_growth_per_year):
        return (self._age * avg_gram_growth_per_year
                + self._get_fuzz(avg_gram_growth_per_year))

    @staticmethod
    def _get_fuzz(value):
        """ random maximized on value +/- half of the value """
        return random.randint(0, value) - (value / 2)
