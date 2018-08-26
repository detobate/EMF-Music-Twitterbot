#!/usr/bin/env python3
import twython
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools
from calendar_config import *

# If modifying these scopes, delete the file token.json.
SCOPES = 'https://www.googleapis.com/auth/calendar.readonly'


class Event:

    def __init__(self, name, id, cal_id):
        self.name = name
        self.id = id
        self.cal_id = cal_id
        self.start_time = None
        self.end_time = None
        self.started = False
        self.description = None
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
    #now = datetime.utcnow().isoformat() + '+01:00'
    future = str(datetime.isoformat(datetime.fromisoformat(now) + timedelta(hours=1)))
    events_result = service.events().list(calendarId=cal_id, timeMin=now + 'Z', timeMax=future + 'Z',
                                          maxResults=2, singleEvents=True, orderBy='startTime').execute()
    events = events_result.get('items', [])

    if not events:
        return(None)
    else:
        return(events)

def parseEvents(events):

    current = None
    next_up = None

    start = datetime.fromisoformat(events[0]['start'].get('dateTime'))
    tz_info = start.tzinfo
    now = datetime.now(tz_info)

    if start < now:
        current = Event(name = events[0]['summary'], id = events[0]['id'], cal_id = events[0]['iCalUID'])
        current.start_time = datetime.fromisoformat(events[0]['start'].get('dateTime'))
        current.end_time = datetime.fromisoformat(events[0]['end'].get('dateTime'))
        try:
            current.name = events[0]['description']
        except:
            pass

        # See if there's an upcoming show.
        try:
            next_up = Event(name = events[1]['summary'], id = events[1]['id'], cal_id = events[1]['iCalUID'])
            next_up.start_time = datetime.fromisoformat(events[1]['start'].get('dateTime'))
            next_up.end_time = datetime.fromisoformat(events[1]['end'].get('dateTime'))
            try:
                next_up.name = events[1]['description']
            except:
                pass
        except:
            pass

    else:
        next_up = Event(name = events[0]['summary'], id = events[0]['id'], cal_id = events[0]['iCalUID'])
        next_up.start_time = datetime.fromisoformat(events[0]['start'].get('dateTime'))
        next_up.end_time = datetime.fromisoformat(events[0]['end'].get('dateTime'))
        try:
            next_up.name = events[1]['description']
        except:
            pass

    r = {'current': current, 'next_up': next_up}

    return(r)

def tweet_now(show):
    try:
        if getattr(show, 'name') is not None:
            print('Currently Playing: %s' % getattr(show, 'name'))
    except:
        pass

def tweet_next(show):
    try:
        if getattr(show, 'name') is not None:
            print('Next Up: %s' % getattr(show, 'name'))
    except:
        pass

def main():

    store = file.Storage('token.json')
    creds = store.get()
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets('credentials.json', SCOPES)
        creds = tools.run_flow(flow, store)
    service = build('calendar', 'v3', http=creds.authorize(Http()))

    for cal in goog_calendars:
        events = fetchEvents(service, goog_calendars[cal])
        if events:
            new = parseEvents(events)
            print()
            try:
                if current['name'] == getattr(new['current'], 'name'):
                    pass
                else:
                    current = new['current']
                    tweet_now(current)
            except:
                current = new['current']
                tweet_now(current)

            try:
                if next_up['name'] == getattr(new['next_up'], 'name'):
                    pass
                else:
                    next_up = new['next_up']
                    tweet_next(next_up)
            except:
                next_up = new['next_up']
                tweet_next(next_up)

        else:
            print('No upcoming events found in calendar: %s' % cal)



if __name__ == '__main__':
    main()