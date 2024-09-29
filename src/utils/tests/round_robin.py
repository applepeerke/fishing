class RoundRobin:
    def __init__(self, base_list: list, start_entry=None):
        self._list = base_list
        self._start_entry = start_entry
        if start_entry and start_entry not in base_list:
            raise ValueError
        self._i = self._list.index(start_entry) if start_entry else 0

    def next(self):
        self._i += 1
        if self._i == len(self._list):
            self._i = 0
        return self._list[self._i]
