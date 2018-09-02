#!/usr/bin/env python3
from twython import Twython, TwythonStreamer, TwythonError
from twitter_keys import *
from datetime import datetime, timedelta, timezone
from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools
from google_config import *
import time

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly', 'https://www.googleapis.com/auth/spreadsheets.readonly']
locations = {'dj_calendar': 'Null Sector', 'live_calendar': 'Stage B'}

debug = True
dry_run = True
sleep_time = 300


class Event:

    def __init__(self, name=None, id=None, cal_id=None):
        self.name = name
        self.id = id
        self.cal_id = cal_id
        self.start_time = None
        self.end_time = None
        self.started = False
        self.description = None
        self.location = None
        self.have_tweeted_current = False
        self.have_tweeted_next = False

    def tweeted_current(self):
        if self.have_tweeted_current is False:
            self.have_tweeted_current = True

    def tweeted_next(self):
        if self.have_tweeted_next is False:
            self.have_tweeted_next = True

def fetchEvents(service, cal_id):
    # Call the Calendar API
    now = datetime.utcnow().isoformat() # + 'Z' # 'Z' indicates UTC time
    future = str(datetime.isoformat(datetime.fromisoformat(now) + timedelta(hours=1)))
    events_result = service.events().list(calendarId=cal_id, timeMin=now + 'Z', timeMax=future + 'Z',
                                          maxResults=2, singleEvents=True, orderBy='startTime').execute()
    events = events_result.get('items', [])

    if not events:
        return(None)
    else:
        return(events)


def getTwitterHandle(sheets, name):

    results = sheets.spreadsheets().values().get(spreadsheetId=gsheets['spreadsheet_id'], range=gsheets['name_range']).execute()
    names = results.get('values', [])
    for n in names:
        if name in n:
            # offset by 2 for header row and 1 indexing.
            idx = str(2 + names.index(n))

    try:
        results = sheets.spreadsheets().values().get(spreadsheetId=gsheets['spreadsheet_id'], range=gsheets['twitter_col']+idx).execute()
        twitter_handle = results.get('values', [])[0][0]
        return twitter_handle
    except:
        return None



def parseEvents(events):

    current = Event()
    next_up = Event()

    start = datetime.fromisoformat(events[0]['start'].get('dateTime'))
    tz_info = start.tzinfo
    now = datetime.now(tz_info)

    if start < now:
        current = Event(name = events[0]['summary'], id = events[0]['id'], cal_id = events[0]['iCalUID'])
        current.start_time = datetime.fromisoformat(events[0]['start'].get('dateTime'))
        current.end_time = datetime.fromisoformat(events[0]['end'].get('dateTime'))
        try:
            current.name = events[0]['summary']
            current.description = events[0]['description']
        except:
            pass

        # See if there's an upcoming show.
        try:
            next_up = Event(name = events[1]['summary'], id = events[1]['id'], cal_id = events[1]['iCalUID'])
            next_up.start_time = datetime.fromisoformat(events[1]['start'].get('dateTime'))
            next_up.end_time = datetime.fromisoformat(events[1]['end'].get('dateTime'))
            try:
                next_up.name = events[1]['summary']
                next_up.description = events[1]['description']
            except:
                pass
        except:
            pass

    else:
        next_up = Event(name = events[0]['summary'], id = events[0]['id'], cal_id = events[0]['iCalUID'])
        next_up.start_time = datetime.fromisoformat(events[0]['start'].get('dateTime'))
        next_up.end_time = datetime.fromisoformat(events[0]['end'].get('dateTime'))
        try:
            next_up.name = events[1]['summary']
            next_up.description = events[1]['description']
        except:
            pass

    r = {'current': current, 'next_up': next_up}

    return(r)


def tweet_now(twitter, show, location, twitter_handle=None):
    try:
        if getattr(show, 'name', None) is not None:
            if twitter_handle:
                name = twitter_handle
            else:
                name = getattr(show, 'name')
            msg = '%s is playing now over in %s' % (name, location)
            tweet(twitter, msg)
    except:
        print('ERROR: Couldn\'t tweet: %s' % msg)


def tweet_next(twitter, show, location, delta, twitter_handle=None):
    try:
        if getattr(show, 'name', None) is not None:
            description = getattr(show, 'description', None)
            if twitter_handle:
                name = twitter_handle
            else:
                name = getattr(show, 'name')
            if description is not None:
                msg = 'In %d minutes, %s, %s, in %s' % (delta, name, description, location)
            else:
                msg = 'In %d minutes, %s will be playing in %s' % (delta, name, location)
            tweet(twitter, msg)
    except:
        print('ERROR: Couldn\'t tweet: %s' % msg)


def tweet(twitter, msg):
    print('Tweeting: %s' % msg)
    try:
        if not dry_run:
            twitter.update_status(status=msg)
        pass

    except TwythonError as e:
        if debug:
            print(e)
        pass


def main():

    twitter = Twython(APP_KEY, APP_SECRET, ACCESS_KEY, ACCESS_SECRET)
    store = file.Storage('token.json')
    creds = store.get()
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets('credentials.json', SCOPES)
        creds = tools.run_flow(flow, store)
    service = build('calendar', 'v3', http=creds.authorize(Http()))
    sheets = build('sheets', 'v4', http=creds.authorize(Http()))
    current = Event()
    next_up = Event()

    while True:
        for cal in goog_calendars:
            location = locations[cal]
            events = fetchEvents(service, goog_calendars[cal])
            if events:
                new = parseEvents(events)
                print()
                if getattr(current, 'name', None) == getattr(new['current'], 'name', None):
                    if debug:
                        print('DEBUG: %s is still playing in %s' % (getattr(current, 'name'), location))
                    pass

                #Check currently playing
                elif getattr(new['current'], 'name', None) is not None:
                    current = new['current']
                    twitter_handle = getTwitterHandle(sheets, getattr(new['current'], 'name'))
                    if twitter_handle:
                        tweet_now(twitter, current, location, twitter_handle)
                    else:
                        tweet_now(twitter, current, location)
                    current.tweeted_current()

                # Check next up
                if getattr(next_up, 'name') == getattr(new['next_up'], 'name'):
                    if debug:
                        print('DEBUG: %s is still next up in %s' % (getattr(next_up, 'name'), location))
                    pass
                elif getattr(new['next_up'], 'name') is not None:
                    next_up = new['next_up']
                    delta = int(((getattr(next_up, 'start_time') - datetime.now(timezone.utc)) / timedelta(minutes=1)))
                    if delta <= 15:
                        twitter_handle = getTwitterHandle(sheets, getattr(new['next_up'], 'name'))
                        if twitter_handle:
                            tweet_next(twitter, next_up, location, delta, twitter_handle)
                        else:
                            tweet_next(twitter, next_up, location, delta)
            elif debug:
                print('DEBUG: No upcoming events found in calendar: %s' % cal)

        time.sleep(sleep_time)



if __name__ == '__main__':
    main()