# coding=utf-8

import datetime
from dateutil import tz
from tornado.web import authenticated
import sickbeard
from sickbeard import (
    db, logger, network_timezones,
)
from sickrage.helper.common import try_int
from sickbeard.server.web.core.base import BaseHandler


class CalendarHandler(BaseHandler):
    def get(self):
        if sickbeard.CALENDAR_UNPROTECTED:
            self.write(self.calendar())
        else:
            self.calendar_auth()

    @authenticated
    def calendar_auth(self):
        self.write(self.calendar())

    # Raw iCalendar implementation by Pedro Jose Pereira Vieito (@pvieito).
    #
    # iCalendar (iCal) - Standard RFC 5545 <http://tools.ietf.org/html/rfc5546>
    # Works with iCloud, Google Calendar and Outlook.
    def calendar(self):
        """ Provides a subscribeable URL for iCal subscriptions
        """

        logger.log(u"Receiving iCal request from %s" % self.request.remote_ip)

        # Create a iCal string
        ical = 'BEGIN:VCALENDAR\r\n'
        ical += 'VERSION:2.0\r\n'
        ical += 'X-WR-CALNAME:Medusa\r\n'
        ical += 'X-WR-CALDESC:Medusa\r\n'
        ical += 'PRODID://Sick-Beard Upcoming Episodes//\r\n'

        future_weeks = try_int(self.get_argument('future', 52), 52)
        past_weeks = try_int(self.get_argument('past', 52), 52)

        # Limit dates
        past_date = (datetime.date.today() + datetime.timedelta(weeks=-past_weeks)).toordinal()
        future_date = (datetime.date.today() + datetime.timedelta(weeks=future_weeks)).toordinal()

        # Get all the shows that are not paused and are currently on air (from kjoconnor Fork)
        main_db_con = db.DBConnection()
        calendar_shows = main_db_con.select(
            "SELECT show_name, indexer_id, network, airs, runtime FROM tv_shows WHERE ( status = 'Continuing' OR status = 'Returning Series' ) AND paused != '1'")
        for show in calendar_shows:
            # Get all episodes of this show airing between today and next month
            episode_list = main_db_con.select(
                "SELECT indexerid, name, season, episode, description, airdate FROM tv_episodes WHERE airdate >= ? AND airdate < ? AND showid = ?",
                (past_date, future_date, int(show["indexer_id"])))

            utc = tz.gettz('GMT')

            for episode in episode_list:

                air_date_time = network_timezones.parse_date_time(episode['airdate'], show["airs"],
                                                                  show['network']).astimezone(utc)
                air_date_time_end = air_date_time + datetime.timedelta(
                    minutes=try_int(show["runtime"], 60))

                # Create event for episode
                ical += 'BEGIN:VEVENT\r\n'
                ical += 'DTSTART:' + air_date_time.strftime("%Y%m%d") + 'T' + air_date_time.strftime(
                    "%H%M%S") + 'Z\r\n'
                ical += 'DTEND:' + air_date_time_end.strftime(
                    "%Y%m%d") + 'T' + air_date_time_end.strftime(
                        "%H%M%S") + 'Z\r\n'
                if sickbeard.CALENDAR_ICONS:
                    ical += 'X-GOOGLE-CALENDAR-CONTENT-ICON:https://lh3.googleusercontent.com/-Vp_3ZosvTgg/VjiFu5BzQqI/AAAAAAAA_TY/3ZL_1bC0Pgw/s16-Ic42/medusa.png\r\n'
                    ical += 'X-GOOGLE-CALENDAR-CONTENT-DISPLAY:CHIP\r\n'
                ical += u'SUMMARY: {0} - {1}x{2} - {3}\r\n'.format(
                    show['show_name'], episode['season'], episode['episode'], episode['name']
                )
                ical += 'UID:Medusa-' + str(datetime.date.today().isoformat()) + '-' + \
                    show['show_name'].replace(" ", "-") + '-E' + str(episode['episode']) + \
                    'S' + str(episode['season']) + '\r\n'
                if episode['description']:
                    ical += u'DESCRIPTION: {0} on {1} \\n\\n {2}\r\n'.format(
                        (show['airs'] or '(Unknown airs)'),
                        (show['network'] or 'Unknown network'),
                        episode['description'].splitlines()[0])
                else:
                    ical += 'DESCRIPTION:' + (show['airs'] or '(Unknown airs)') + ' on ' + (
                        show['network'] or 'Unknown network') + '\r\n'

                ical += 'END:VEVENT\r\n'

        # Ending the iCal
        ical += 'END:VCALENDAR'

        return ical
