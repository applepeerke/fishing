from src.domains.entities.fish.fish import FishSpecies


class FishingSession:

    def __init__(self,
                 fishingwater_name,
                 species: FishSpecies,
                 session_duration: int,
                 encounters_per_hour_expected: float,
                 hours_fished=0,
                 encounters=0.0,
                 caught_fishes=None
                 ):
        self._fishingwater_name: str = fishingwater_name
        self._species: FishSpecies = species
        self._session_duration: int = session_duration
        self._encounters_per_hour_expected: float = encounters_per_hour_expected
        self._hours_fished: int = hours_fished
        self._caught_fishes: list = caught_fishes or []
        self._encounters: float = encounters

    @property
    def fishingwater_name(self):
        return self._fishingwater_name

    @property
    def species(self):
        return self._species

    @property
    def session_duration(self):
        return self._session_duration

    @property
    def encounters_per_hour_expected(self):
        return self._encounters_per_hour_expected

    @property
    def hours_fished(self):
        return self._hours_fished

    @property
    def caught_fishes(self):
        return self._caught_fishes

    @property
    def encounters(self):
        return self._encounters

    """
    Setters
    """

    @hours_fished.setter
    def hours_fished(self, value):
        self._hours_fished = value

    @caught_fishes.setter
    def caught_fishes(self, value):
        self._caught_fishes = value

    @encounters.setter
    def encounters(self, value):
        self._encounters = value
