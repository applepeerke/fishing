import random

from src.constants import STRIPE
from src.db import crud
from src.domains.entities.enums import ActiveAt, SpeciesEnum
from src.domains.entities.fish.fish import FishSpecies, Fish
from src.domains.entities.fishingwater.models import FishingWater, FLOATING_WATER
from src.domains.entities.fishspecies.models import FishSpecies
from src.services.simulation.fishing_session import FishingSession
from src.services.simulation.functions import fishspecies_to_random_fish
from src.services.simulation.planning import Planning
from src.utils.functions import get_random_item
from src.utils.logging.log import logger

SIM_FISHES = 'fishes'
SIM_INITIAL_FISH_COUNT = 'initial_fish_count'
SIM_CAUGHT = 'caught'
SIM_ADDED = 'added'


class Simulation:

    def __init__(self):
        self._fishing_session = {}
        self._species_def = {}
        self._fishing_waters = {}
        self._fishes_per_species_per_water = {}  # {water_id: {species_name: fishes}}
        self._starting_hours_of_fishing_sessions_today = {}

    async def run(self, db, start_year: int, no_of_fishing_days: int):
        """
        Runs from the data in the db, which was created in method "populate_fishing_with_random_data".
        """
        # Create fishing planning
        planning = Planning()
        calendar = await planning.create_planning(db, start_year, no_of_fishing_days)
        self._fishes_per_species_per_water = {}

        # Get fish species definitions
        self._species_def = {species_enum: fishspecies_to_random_fish(species_enum) for species_enum in SpeciesEnum}

        # List fishes per fishing water.
        self._fishing_waters = {water.id: water for water in await crud.get_all(db, FishingWater)}

        # {species_name: [FishSpecies]}
        fish_specieses = {
            species_enum: await crud.get_where(db, FishSpecies, FishSpecies.species_name, species_enum)
            for species_enum in self._species_def
        }

        # Initialize simulation data.
        [self._initialize_simulation_data(water_id=water_id, species_name=species_name)
            for water_id, water in self._fishing_waters.items()
            for species_name, specieses in fish_specieses.items()
            for _ in specieses]

        # Add a random fish per water per species occurrences.
        [self._add_simulation_data(
            water_id=water_id,
            species_name=species_name,
            att_name=SIM_FISHES,
            att_value=fishspecies_to_random_fish(species_name)
        )
            for water_id, water in self._fishing_waters.items()
            for species_name, specieses in fish_specieses.items()
            for _ in specieses]

        # Get fisherman names from the calendar planning.
        fishermen_names = {
            self._get_full_name(fm, True)
            for fm_set in calendar.values()
            for fm in fm_set
        }

        # Logging header
        logger.info(STRIPE)
        logger.info(f'Fishermen . . . : {", ".join(fishermen_names)}')
        logger.info('Fishingwaters . :')

        for water_id, water in self._fishing_waters.items():
            logger.info(
                (f'  {self._get_water_name(water_id)} m3={water.m3}, fish_density={round(water.density, 2)}: '
                 f'{", ".join([f'{species_name.value}({len(specieses)})' 
                    for species_name, specieses in fish_specieses.items()])}')
)
        logger.info(f'Start year . . . : {start_year}')
        logger.info(f'Fishing days . . : {no_of_fishing_days}')
        logger.info(STRIPE)

        if not fishermen_names or not self._fishing_waters:
            return

        # Fish the year around
        [self._process_day(calender_date, fishermen)
         for calender_date, fishermen in calendar.items() if fishermen]

        # Summary
        logger.info(STRIPE)
        logger.info('Fishes caught:')
        for water_id in self._fishes_per_species_per_water:
            logger.info(f'  Water: {self._get_water_name(water_id)}:')
            for species_enum, data in self._fishes_per_species_per_water[water_id].items():
                caught = data[SIM_CAUGHT]
                new_fishes = data[SIM_ADDED]
                suffix = f'{len(new_fishes)} were added (floating water or sea).' if len(new_fishes) > 0 else ''
                if len(caught) > 0:
                    initial_count = data[SIM_INITIAL_FISH_COUNT]
                    logger.info(f'    {species_enum.value}: '
                                f'{len(caught)} of {initial_count} caught. {suffix}')
        logger.info(STRIPE)

    def _initialize_simulation_data(self, water_id, species_name):

        if water_id not in self._fishes_per_species_per_water:
            self._fishes_per_species_per_water[water_id] = {}
        if species_name not in self._fishes_per_species_per_water:
            self._fishes_per_species_per_water[water_id][species_name] = {}
            self._fishes_per_species_per_water[water_id][species_name][SIM_FISHES] = []
            self._fishes_per_species_per_water[water_id][species_name][SIM_INITIAL_FISH_COUNT] = 0
            self._fishes_per_species_per_water[water_id][species_name][SIM_CAUGHT] = []
            self._fishes_per_species_per_water[water_id][species_name][SIM_ADDED] = []

    def _add_simulation_data(self, water_id, species_name, att_name, att_value):
        self._fishes_per_species_per_water[water_id][species_name][att_name].append(att_value)
        if att_name == SIM_FISHES:
            self._fishes_per_species_per_water[water_id][species_name][SIM_INITIAL_FISH_COUNT] += 1

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
        [self._process_hour(calender_date, hour, fisherman)
         for hour in range(24)
         for fisherman in fishermen]

    def _process_hour(self, calender_date, hour, fisherman):
        fisherman_starting_hour_of_today = self._starting_hours_of_fishing_sessions_today[fisherman.id]
        fullname = self._get_full_name(fisherman)
        session = self._fishing_session.get(fullname, None)

        # Start fishing session
        if hour == fisherman_starting_hour_of_today:
            self._start_fishing_session(fisherman, calender_date, hour)

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

    def _start_fishing_session(self, fisherman, calender_date, hour):
        fullname = self._get_full_name(fisherman)

        # Must not already being fishing (having a not_empty session)
        if fullname in self._fishing_session and self._fishing_session[fullname]:
            return

        # Determine the fishing water
        fishingwater: FishingWater = self._get_random_fishingwater(fisherman)
        if not fishingwater:
            logger.warning(f'{self._get_log_prefix(calender_date, hour)} '
                           f'{fullname} could NOT start fishing. He has no fishing water.')

        species: FishSpecies = self._species_def[fisherman.fish_species]

        self._fishing_session[fullname] = FishingSession(
            fishingwater_id=fishingwater.id,
            species=species,
            hours_fished=0,
            session_duration=fisherman.fishing_session_duration,
            caught_fishes=set(),
            encounters=0.0,
            encounters_per_hour_expected=self._calculate_encounters_per_hour(fishingwater, species)
        )
        logger.info(f'{self._get_log_prefix(calender_date, hour)}'
                    f'{fullname} starts fishing at {self._get_water_name(fishingwater.id)}.')

    @staticmethod
    def _calculate_encounters_per_hour(fishingwater: FishingWater, species: FishSpecies):
        """
        Calculate expected encounters per hour. Recalculate after every catch.
        Minimum is 1 encounter per 5 hour.
        """
        fish_relative_density = species.relative_density
        # Fish not present in the water: Useless fishing here.
        if fishingwater.density == 0:
            logger.info(
                f'It is useless fishing here. The {species.species_name} is not present in {fishingwater.location}.')
            return 0
        expected_encounters_per_hour = max(fishingwater.density * fish_relative_density / 100, 0.2)
        return expected_encounters_per_hour

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
            if not session:
                continue
            session.encounters += session.encounters_per_hour_expected
            # Threshold is reached when potentially >= 1 fish is encountered (N.B. this may be 10 as well).
            if session.encounters > 1:
                encounter_count = int(session.encounters)
                # Evaluate the potential fish(es) caught
                [self._evaluate_encounter(fisherman_fullname, session, calender_date, hour)
                 for _ in range(encounter_count)]
                # Continue fishing
                session.encounters = 0.0

    def _evaluate_encounter(self, fisherman_fullname, session: FishingSession, calender_date, hour):
        species_name = session.species.species_name

        # Fish was caught
        valid_fish: Fish = self._encounter_random_fish(session.fishingwater_id, species_name)
        if not valid_fish:
            logger.info(f'{self._get_log_prefix(calender_date, hour)}'
                        f'{fisherman_fullname} almost caught a {species_name.value}.{self._remark}')
            return

        # Keep the fish in a life-net
        session.caught_fishes.append(valid_fish)

        # Recalculate fish water density
        fishingwater = self._fishing_waters[session.fishingwater_id]
        fishingwater.add_fishes_to_still_water(-1)
        session.encounters_per_hour_expected = self._calculate_encounters_per_hour(fishingwater, session.species)

        # Last fish of this species in the water?
        species_fishes = self._fishes_per_species_per_water[session.fishingwater_id][species_name][SIM_FISHES]
        smart_fishes_count = sum(1 for f in species_fishes if f.caught_count > 0)
        suffix = ' THIS WAS THE LAST (NOT SMART) FISH !!!' \
            if len(species_fishes) == smart_fishes_count \
            else ''

        # Show your catch to the world
        logger.info(f'{self._get_log_prefix(calender_date, hour)}'
                    f'{fisherman_fullname} caught a {species_name.value} of {valid_fish.length} cm and '
                    f'{valid_fish.weight_in_g / 500} lbs.{self._remark}{suffix}')

    @staticmethod
    def _get_log_prefix(calender_date, hour):
        return f'{calender_date[:14]} - {str(hour).zfill(2)}.00: '

    def _encounter_random_fish(self, water_id, species_name) -> Fish | None:
        self._remark = ''

        # No fish of this species.
        if species_name not in self._fishes_per_species_per_water[water_id]:
            self._remark = f' Fish species {species_name} does not occur in this water.'
            return None

        fishes_per_species = self._fishes_per_species_per_water[water_id][species_name][SIM_FISHES]

        # No fish of this species left.
        if not fishes_per_species:
            self._remark = ' This was not a fish.'
            return None

        fish = fishes_per_species.pop(0)  # Not last one, because it may be appended again.

        # Too smart: not hooked.
        if fish.caught_count > 0:
            fishes_per_species.append(fish)
            self._remark = ' Fish was not hooked, it was caught earlier.'
            return None

        # Too small: throw back.
        if fish.length <= fish.minium_length_to_keep:
            fish.caught_count += 1
            fishes_per_species.append(fish)
            self._remark = ' Fish thrown back, it has not the required minimum length.'
            return None

        # Floating water: add a new random fish
        if self._is_water_floating(water_id):
            new_fish = fishspecies_to_random_fish(species_name)
            fishes_per_species.append(new_fish)
            self._add_simulation_data(water_id, species_name, att_name=SIM_ADDED, att_value=new_fish)
            self._remark = ' A same fish species added to the floating water.'

        # Valid caught fish.
        self._add_simulation_data(water_id, species_name, att_name=SIM_CAUGHT, att_value=fish)
        return fish

    def _get_water_name(self, water_id) -> str:
        water: FishingWater = self._fishing_waters.get(water_id, None)
        return f'{water.location} ({water.water_type})' if water else None

    def _is_water_floating(self, water_id) -> bool:
        water: FishingWater = self._fishing_waters.get(water_id, None)
        return True if water.water_type in FLOATING_WATER else False

    @staticmethod
    def _get_full_name(fisherman, species=False) -> str:
        full_name = f'{fisherman.forename} {fisherman.surname}'
        if species:
            full_name = f'{full_name} ({fisherman.fish_species})'
        return full_name

    @staticmethod
    def _get_species_names(fishes: [FishSpecies]):
        return list({fish.species_name for fish in fishes})

    @staticmethod
    def _get_random_fishingwater(fisherman) -> FishingWater | None:
        return get_random_item(fisherman.fishingwaters)
