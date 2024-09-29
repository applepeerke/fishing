import random

from src.constants import STRIPE
from src.db import crud
from src.domains.entities.enums import ActiveAt, SpeciesEnum
from src.domains.entities.fish.models import Fish
from src.domains.entities.fishingwater.models import FishingWater
from src.domains.entities.species.species import Species
from src.services.simulation.fishing_session import FishingSession
from src.services.simulation.planning import Planning
from src.utils.functions import get_random_item
from src.utils.logging.log import logger


class Simulation:

    def __init__(self):
        self._fishing_session = {}
        self._species_def = {}
        self._fishing_waters = {}
        self._fishes_per_species_per_water = {}  # {water_id: {species_name: [fishes] }}
        self._starting_hours_of_fishing_sessions_today = {}

    async def run(self, db):
        # Create fishing planning
        planning = Planning()
        calendar = await planning.create_planning(db, year=2025)

        # Get fish species definitions
        self._species_def = {species_enum: Species(species_enum) for species_enum in SpeciesEnum}

        # List fishes per fishing water
        self._fishing_waters = {water.id: water for water in await crud.get_all(db, FishingWater)}
        fishes = [fish for fish in await crud.get_all(db, Fish)]

        # List fishes per species per water
        self._fishes_per_species_per_water = {}
        for fish in fishes:
            species_name = fish.species
            water_name = self._get_water_name(fish.fishingwater_id)
            if water_name:
                if water_name not in self._fishes_per_species_per_water:
                    self._fishes_per_species_per_water[water_name] = {}
                if species_name not in self._fishes_per_species_per_water[water_name]:
                    self._fishes_per_species_per_water[water_name][species_name] = []
                # Add the fish
                self._fishes_per_species_per_water[water_name][species_name].append(fish)

        # Logging
        fishermen_names = {self._get_full_name(fm) for fm_set in calendar.values() for fm in fm_set}
        fishingwater_names = {self._get_water_name(Id) for Id in self._fishing_waters}
        logger.info(STRIPE)
        logger.info(f'Fishermen: {", ".join(fishermen_names)}')
        logger.info('Fishingwaters:')

        for water_name in fishingwater_names:
            fish_text = [f'{species_name}({len(fishes)})'
                         for species_name, fishes in self._fishes_per_species_per_water[water_name].items()]
            logger.info(f'{water_name}: {", ".join(fish_text)}')
        logger.info(STRIPE)
        # Fish the year around
        [self._process_day(calender_date, fishermen) for calender_date, fishermen in calendar.items() if fishermen]
        logger.info(STRIPE)

    def _process_day(self, calender_date, fishermen):
        """
        For every day:
        # Calculate a random fishing start_time per fisherman
        # (depending on the species he is fishing for)
        """
        self._starting_hours_of_fishing_sessions_today = {
            fisherman.id: self._get_random_starting_hour(fisherman)
            for fisherman in fishermen
        }
        # For every hour:
        [self._process_hour(calender_date, hour, fisherman) for hour in range(24) for fisherman in fishermen]

    def _process_hour(self, calender_date, hour, fisherman):
        fisherman_starting_hour_of_today = self._starting_hours_of_fishing_sessions_today[fisherman.id]
        fullname = self._get_full_name(fisherman)
        session = self._fishing_session.get(fullname, None)

        # Start fishing session
        if hour == fisherman_starting_hour_of_today:
            self._start_fishing(fisherman, calender_date, hour)
        # End fishing session
        elif session:
            session.hours_fished += 1
            if session.hours_fished == fisherman.fishing_session_duration:
                self._end_fishing(session, fullname, calender_date, hour)
                self._fishing_session[fullname] = None

        # Try to catch fishes (all fishermen)
        self._wait_for_fish(calender_date, hour)

    def _get_random_starting_hour(self, fisherman) -> int:
        species = self._species_def[fisherman.fish_species]
        fish_activity = species.active_at
        if fish_activity == ActiveAt.Day:
            return random.randint(6, 12)
        elif fish_activity == ActiveAt.Night:
            return random.randint(19, 23)
        elif fish_activity == ActiveAt.Both:
            return random.randint(6, 20)
        else:
            raise NotImplementedError(f' Fish activity "{fish_activity}" is not implemented.')

    def _start_fishing(self, fisherman, calender_date, hour):
        fullname = self._get_full_name(fisherman)
        # Must not already being fishing (having a not_empty session)
        if fullname in self._fishing_session and self._fishing_session[fullname]:
            return
        fishingwater = self._get_random_fishingwater(fisherman)
        if not fishingwater:
            logger.warning(f'{self._get_log_prefix(calender_date, hour)} '
                           f'{fullname} could NOT start fishing. He has no fishing water.')
        fishingwater_name = self._get_water_name(fishingwater.id)
        # Calculate expected encounters per hour
        fish_relative_density = self._species_def[fisherman.fish_species].relative_density
        expected_encounters_per_hour = fishingwater.density * fish_relative_density / 100
        self._fishing_session[fullname] = FishingSession(
            fishingwater_name=fishingwater_name,
            species=self._species_def[fisherman.fish_species],
            hours_fished=0,
            session_duration=fisherman.fishing_session_duration,
            caught_fishes=set(),
            encounters=0.0,
            encounters_per_hour_expected=expected_encounters_per_hour
        )
        logger.info(f'{self._get_log_prefix(calender_date, hour)}'
                    f'{fullname} starts fishing at {fishingwater_name}.')

    def _end_fishing(self, session, fullname, calender_date, hour):
        if session.caught_fishes:
            caught_species_names = ", ".join(self._get_species_names(session.caught_fishes))
            text = f'The catch was {len(session.caught_fishes)} of {caught_species_names}'
        else:
            text = 'No catch.'
        logger.info(f'{self._get_log_prefix(calender_date, hour)}{fullname} ends fishing. {text}')

    def _wait_for_fish(self, calender_date, hour):
        """
        Every water has a density: fishes per m3 = 0.1-1.
        Every fish has a Fish.relative_density of 1-100%, where Roach (the most common fish) is 100%.
        For simplicity, I assume that every hour every  fish moves to another m3.
        Every hour the Encounters is incremented with [FishingWater.density * (Fish.density / 100) ])
        When Encounters > 1 this is the amount of fishes caught. After inspecting the fish it is set to 0 again.
        """
        for fisherman_fullname, session in self._fishing_session.items():
            if session:
                species_name = session.species.species_name
                session.encounters += session.encounters_per_hour_expected
                # Threshold is reached when potentially >= 1 fish is encountered (N.B. this may be 10 as well).
                if session.encounters > 1:
                    encounter_count = int(session.encounters)
                    caught_count = 0
                    # Evaluate the potential fish(es) caught
                    for i in range(encounter_count):
                        # There may be no fishes left in the water ... so possible encounters are not real
                        species_count = self._get_species_count(session.fishingwater_name, species_name)
                        fish = self._get_random_fish(session.fishingwater_name, species_name)
                        if fish:
                            # Keep the fish(es) in a life-net
                            session.caught_fishes.append(fish)
                            caught_count += 1
                            # Show your catch to the world
                            logger.info(f'{self._get_log_prefix(calender_date, hour)}'
                                        f'{fisherman_fullname} caught a {species_name} of {fish.length} cm and '
                                        f'{fish.weight_in_g/500} lbs.')
                        elif species_count > 0:
                            # Last fish caught
                            logger.warning(f'{self._get_log_prefix(calender_date, hour)}'
                                           f'{fisherman_fullname} CAUGHT THE LAST FISH !!!')

                    # Continue fishing
                    session.encounters = 0.0

    @staticmethod
    def _get_log_prefix(calender_date, hour):
        return f'{calender_date[:14]} - {str(hour).zfill(2)}.00: '

    def _get_random_fish(self, water_name, species_name) -> Fish | None:
        fishes = self._fishes_per_species_per_water[water_name][species_name]
        if not fishes:
            return None
        index = random.randint(0, len(fishes) - 1)
        fish = fishes.pop(index)
        return fish

    def _get_water_name(self, water_id) -> str:
        water: FishingWater = self._fishing_waters.get(water_id, None)
        return f'{water.location} ({water.water_type})' if water else None

    @staticmethod
    def _get_full_name(fisherman) -> str:
        return f'{fisherman.forename} {fisherman.surname}'

    @staticmethod
    def _get_species_names(fishes: [Species]):
        return list({fish.species for fish in fishes})

    @staticmethod
    def _get_random_fishingwater(fisherman) -> FishingWater | None:
        return get_random_item(fisherman.fishingwaters)

    def _get_species_count(self, water_name, species_name) -> int:
        return len(self._fishes_per_species_per_water[water_name][species_name])
