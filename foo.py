#!/usr/bin/env python3
import sys
import os
import json

from pprint import pprint as pp

from Matchbox import *

class Config(object):
    def __init__(self,jfile):
        self.config_data = Config.parse_json(jfile)

    def __getitem__(self,key):
        return self.config_data[key]

    def __iter__(self):
        return iter(self.config_data)

    @classmethod
    def parse_json(cls,jfile):
        with open(jfile) as f:
            return json.load(f)



# mb = MatchboxData('https://matchbox.nci.nih.gov', '', dumped_data = 'dev_files/raw_mb_dump.json', test_patient='10012')
config = Config('config.json')
mb = MatchboxData(config['url'], config['creds'], test_patient='10012')
pp(vars(mb))
