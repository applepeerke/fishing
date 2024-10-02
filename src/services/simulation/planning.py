import random
from calendar import monthrange
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.db import crud
from src.domains.entities.enums import Frequency
from src.domains.entities.fisherman.models import Fisherman
from src.utils.logging.log import logger
from src.utils.tests.round_robin import RoundRobin


class Planning:

    def __init__(self):
        self._day_names = [self._get_day_name(2025, day) for day in range(1, 8)]
        self._daily_schedule = {}

    async def create_planning(self, db: AsyncSession, year, no_of_fishing_days: int = 365) -> dict:
        """
        Create daily schedule for a year. Populate the schedule with the fishermen fishing days.
        @return Schedule = {'yyyy-mm-dd-dayname' : {fisherman_id}}
        """
        # Create daily schedule for a year
        self._get_daily_schedule_for_a_year(year, no_of_fishing_days)

        # Get all active fishermen
        fishermen = [f for f in await crud.get_all(db, Fisherman) if f.fishingwaters and f.fishing_days]

        # Populate the schedule with the fishermen fishing days
        for fisherman in fishermen:
            day_names = [day.name.value for day in fisherman.fishing_days]
            if not all(day_name in self._day_names for day_name in day_names):
                raise ValueError(f'Not all fisherman day names "{day_names}" '
                                 f'are present in datetime values "{self._day_names}"')
            if fisherman.frequency == Frequency.Weekly:
                [fishermen_set.add(fisherman) for ymd, fishermen_set in self._daily_schedule.items()
                 if self._get_ds_key_element(ymd, 3) in day_names]
            elif fisherman.frequency == Frequency.Monthly:
                monthly_fishing_days = self._get_monthly_days(year, day_names)
                [fishermen_set.add(fisherman) for ymd, fishermen_set in self._daily_schedule.items()
                 if ymd in monthly_fishing_days]

        resulting_fishermen = set()
        for fishermen_set in self._daily_schedule.values():
            for fisherman in fishermen_set:
                resulting_fishermen.add(fisherman)

        if len(fishermen) != len(resulting_fishermen):
            missing = [fisherman for fisherman in fishermen if fisherman not in resulting_fishermen]
            logger.warning(f'Fishermen: {", ".join(missing)} do not fish in this planning.')

        return self._daily_schedule

    def _get_daily_schedule_for_a_year(self, year, no_of_fishing_days):
        start_date = datetime.strptime(f'{year}0101', '%Y%m%d')
        day_name = start_date.strftime("%A")
        day_names_cycle = RoundRobin(self._day_names, day_name)

        days_count = 0
        years = [year + n for n in range(max(int(no_of_fishing_days / 365), 1))]
        for year in years:
            for month in range(1, 13):
                for day in range(1, monthrange(year, month)[1] + 1):
                    self._daily_schedule[self._get_ds_key(year, month, day, day_name)] = set()
                    day_name = day_names_cycle.next()
                    days_count += 1
                    if days_count > no_of_fishing_days:
                        return

    def _get_monthly_days(self, year, day_names) -> set:
        """ For every month get a random day listed in fisherman's fishing days. """
        monthly_days = set()
        for month in range(1, 13):
            found = False
            count = 0
            while not found and count < 1000:
                count += 1
                day = random.randint(1, 28)  # random day number
                # Is it a fishing day?
                for day_name in day_names:
                    key = self._get_ds_key(year, month, day, day_name)
                    if key in self._daily_schedule:
                        # Yes, the day number is a fishing day
                        monthly_days.add(key)
                        break
        return monthly_days

    @staticmethod
    def _get_ds_key(year, month, day, day_name) -> str:
        return f'{year}-{str(month).zfill(2)}-{str(day).zfill(2)}-{day_name}'

    @staticmethod
    def _get_ds_key_element(key, index=None):
        """ Return specific element or mmdd """
        # key = "yyyy-mm-dd-dayname"
        elements = key.split('-')
        return elements[index] if index else f'{elements[1]}{elements[2]}'

    @staticmethod
    def _get_day_name(year, day_no: int) -> str:
        date = datetime.strptime(f'{year}010{day_no}', '%Y%m%d')
        return date.strftime("%A")
