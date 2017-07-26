import sys,os
from unittest import TestCase
from matchbox_api_utils import MatchData

class TestImport(TestCase):
    def test_can_create_obj(self):
        self.func = MatchData()

    def test_can_load_dataset(self):
        test_data = os.path.join(os.path.dirname(__file__),'mb_obj.json')
        self.data = MatchData(dumped_data=test_data)
