# -*- coding: utf-8 -*-
import os
import sys
import json
import requests
import subprocess

from matchbox_api_utils import utils


class Matchbox(object):

    """
    **MATCHBox API Connector Class**

    Basic connector class to make a call to the API and load the raw data. Used
    for calling to the MATCHBox API, loading data, and pass along to the
    appropriate calling  classes for make a basic data structure. Can load a
    raw MATCHBox API dataset JSON file, or create one. Requires credentials,
    generally acquired from the config file generated upon package setup.

    Args:
        method (str): API call method to use. Can only choose from ``api``, the
            conventional way to make the call to MATCHBox using the actual API,
            or ``mongo``, the new, preferred way, connecting directly to the 
            MongoDB.

        config (dict): Dictionary of config variables to pass along to this
            object. These are generated by parsing the MATCHBox API Utils config 
            file, and usually contains things like the username, password, URL, 
            etc.

        mongo_collection (str): This is the name of the MongoDB database
            collection for which you want to get data. For now, we are only using
            the ``patients`` and ``treatmentArms`` tables, and so these are the
            only accepted values. In the near future, though, all tables will be
            incorporated.

        params (dict): Parameters to pass along to the API in the request. This
            is onyl when using ``api`` with the ``method`` arg. For example, if 
            you wanted to add "is_oa=True" to the API URL, you can add: ::

                params={'is_oa' : True}

            and this will be passed along to the request.

        make_raw (str): Make a raw, unprocessed MATCHBox API JSON file. Default
            filename will be ``raw_mb_obj`` for the raw MATCHBox patient dataset,
            or ``raw_ta_obj`` for the raw treatment arm dataset. Each will also
            contain the date string of generation. Inputting a string will save
            the file with requested filename.
        
        quiet (bool): Suppress debug and information messages.

            .. todo::
                Fix this arg and make it something like ``verbosity``, which
                will link to the utils.msg() function and allow output at certain
                levels.

    """

    def __init__(self, method, config, params={}, mongo_collection=None, 
        make_raw=None, quiet=False):

        self._params = params
        self._quiet = quiet
        self.today = utils.get_today('short')
        self.api_data = []

        if make_raw is not None:
            if make_raw not in ('ta', 'mb'):
                sys.stderr.write('ERROR: You must choose from "mb" or "ta" '
                    'only when using the "make_raw" argument.\n')
                return None

            raw_files = {
                'mb' : 'raw_mb_dump_%s.json' % self.today,
                'ta' : 'raw_ta_dump_%s.json' % self.today
            }
            sys.stdout.write('Making a raw MATCHBox API dump that can be '
                'loaded for development purposes\nrather than a live call '
                'to MATCHBox prior to parsing and filtering.\n')

        if method == 'api':
            sys.stderr.write("WARN: API calls are soon to be deprecated. Please "
                "transition to MongoDB calls.\n")

            self._url = config.get_config_item('url')
            self._username = config.get_config_item('username')
            self._password = config.get_config_item('password')
            self._client_name = config.get_config_item('client_name')
            self._client_id = config.get_config_item('client_id')
            self._token = self.__get_token()

            # TODO: Remove this. to be replaced by a mongodb call.
            for page in range(1, 14):
                self.api_data += self.__api_call(page)
            if not self._quiet:
                sys.stdout.write("Completed the call successfully!\n")
                sys.stdout.write('   -> return len: %s\n' % str(
                    len(self.api_data))
                )
            if make_raw:
                utils.make_json(outfile=filename, data=self.api_data, sort=True)
                return
        elif method == 'mongo':
            # Only keep patient in here for now.  Will add more as we go.
            collections = ('patient', 'treatmentArms')
            if mongo_collection is None:
                sys.stderr.write('ERROR: You must input a collection when '
                    'making the MongoDB call.\n')
                return None
            elif mongo_collection not in collections:
                sys.stderr.write('ERROR: collection %s is not valid. Please '
                    'only choose from:\n')
                sys.stderr.write('\n'.join(collections))

            outfile = 'raw_%s_dump_%s.json' % (mongo_collection, self.today)
            self._mongo_user = config.get_config_item('mongo_user')
            self._mongo_pass = config.get_config_item('mongo_pass')
            self.api_data = self.__mongo_call(mongo_collection, outfile)
            if make_raw is None:
                os.remove(outfile)
            else:
                # We want a pretty printed JSON file so that it's a bit more 
                # human readable.
                tmpdata = utils.read_json(outfile)
                utils.make_json(outfile=outfile, data=tmpdata)
                sys.stderr.write("Done making a raw MATCHBox data dump file.")
                return
        else:
            sys.stderr.write('ERROR: method %s is not a valid method! Choose '
                'only from "api" or "mongo".\n')
            return None

    def __str__(self):
        return utils.print_json(self.api_data)

    def __repr__(self):
        return '%s: %s' % (self.__class__, self.__dict__)

    def __mongo_call(self, collection, outfile):
        '''
        Now the better way to get a whole DB dump is to make a call to the 
        MongoDB directly.  Will need different creds for this that may not be
        easily obtained for all users, and it may be more difficult to get 
        smaller bits of data, so I'll leave the API call in here.  But, for main
        data export / import, I will start calling this instead now.
        '''

        cmd = [
            'mongoexport',
            '--host', 'adultmatch-production-shard-00-00-tnrm0.mongodb.net:27017,adultmatch-production-shard-00-01-tnrm0.mongodb.net:27017,adultmatch-production-shard-00-02-tnrm0.mongodb.net:27017',
            '--ssl',
            '--username', self._mongo_user,
            '--password', self._mongo_pass,
            '--authenticationDatabase', 'admin',
            '--db', 'Match',
            '--collection', collection,
            '--type', 'json', '--jsonArray',
            '--out', outfile
        ]

        tries = 0
        while tries < 4:
            p = subprocess.Popen(cmd, stderr=subprocess.PIPE, 
                stdout=subprocess.PIPE)
            out, err = p.communicate()
            tries += 1
            if tries == 4:
                sys.stderr.write("Can not get a MongoDB data dump! Can not "
                     "continue.\n")
                sys.stderr.flush()
                return  None
            if p.returncode != 0:
                sys.stderr.write('Error getting data from mongoDB. Trying '
                    'again ({}/{} tries).\n'.format(tries, '4'))
                # TODO: have this output to debug log once we fix the verbosity
                #       arg.
                sys.stderr.write(err.decode('utf-8'))
                sys.stderr.flush()
            else:
                if self._quiet is False:
                    sys.stderr.write('Completed Mongo DB export successfully.\n')
                    sys.stderr.flush()
                break
        return utils.read_json(outfile)

    def __api_call(self, page=None):
        header = {'Authorization' : 'bearer %s' % self._token}
        # For async page requests, will need to update the page number for each 
        # loop.
        if page is not None:
            self._params['page'] = page 

        response = requests.get(self._url, params=self._params, headers=header)
        
        # DEBUG XXX: remove me
        '''
        print('-'*75)
        print(response.links)
        print(response.headers)
        print('page {} -> {}'.format(page, response.url))
        print('status: {}; total returned: {}'.format(response.status_code,
            len(response.json())))
        # print(len(response.json()))
        print(response.json()[0].keys())
        print('-'*75)
        '''

        try: 
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            sys.stderr.write('ERROR: Can not access MATCHBox data. Got error: '
                '%s\n' % e)
            sys.exit(1)
        return response.json()
        
    def __get_token(self):
        body = {
            "client_id" : self._client_id,
            "username" : self._username,
            "password" : self._password,
            "grant_type" : "password",
            "scope" : "openid roles email profile",
            "connection" : self._client_name,
        }
        url = 'https://ncimatch.auth0.com/oauth/ro'
        counter = 0
        while counter < 4:  # Keep it to three attempts.
            counter += 1
            response = requests.post(url, data = body)
            try:
                response.raise_for_status()
                break
            except requests.exceptions.HTTPError as error:
                sys.stderr.write("ERROR: Got an error trying to get an Auth0 "
                    "token! Attempt %s of 3.\n" % counter)
                continue
            except:
                raise

        json_data = response.json()
        return json_data['id_token']
