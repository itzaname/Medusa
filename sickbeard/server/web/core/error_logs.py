# coding=utf-8

import io
import os
import re
from tornado.routes import route
import sickbeard
from sickbeard import (
    classes, logger, ui,
)
from sickrage.helper.encoding import ek
from sickbeard.server.web.core.base import WebRoot, PageTemplate


@route('/errorlogs(/?.*)')
class ErrorLogs(WebRoot):
    def __init__(self, *args, **kwargs):
        super(ErrorLogs, self).__init__(*args, **kwargs)

    def ErrorLogsMenu(self, level):
        menu = [
            {'title': 'Clear Errors', 'path': 'errorlogs/clearerrors/', 'requires': self.haveErrors() and level == logger.ERROR, 'icon': 'ui-icon ui-icon-trash'},
            {'title': 'Clear Warnings', 'path': 'errorlogs/clearerrors/?level=' + str(logger.WARNING), 'requires': self.haveWarnings() and level == logger.WARNING, 'icon': 'ui-icon ui-icon-trash'},
            {'title': 'Submit Errors', 'path': 'errorlogs/submit_errors/', 'requires': self.haveErrors() and level == logger.ERROR, 'class': 'submiterrors', 'confirm': True, 'icon': 'ui-icon ui-icon-arrowreturnthick-1-n'},
        ]

        return menu

    def index(self, level=logger.ERROR):
        try:
            level = int(level)
        except Exception:
            level = logger.ERROR

        t = PageTemplate(rh=self, filename="errorlogs.mako")
        return t.render(header="Logs &amp; Errors", title="Logs &amp; Errors",
                        topmenu="system", submenu=self.ErrorLogsMenu(level),
                        logLevel=level, controller="errorlogs", action="index")

    @staticmethod
    def haveErrors():
        if len(classes.ErrorViewer.errors) > 0:
            return True

    @staticmethod
    def haveWarnings():
        if len(classes.WarningViewer.errors) > 0:
            return True

    def clearerrors(self, level=logger.ERROR):
        if int(level) == logger.WARNING:
            classes.WarningViewer.clear()
        else:
            classes.ErrorViewer.clear()

        return self.redirect("/errorlogs/viewlog/")

    def viewlog(self, minLevel=logger.INFO, logFilter="<NONE>", logSearch=None, maxLines=1000):

        def Get_Data(Levelmin, data_in, lines_in, regex, Filter, Search, mlines):

            lastLine = False
            numLines = lines_in
            numToShow = min(maxLines, numLines + len(data_in))

            finalData = []

            for x in reversed(data_in):
                match = re.match(regex, x)

                if match:
                    level = match.group(7)
                    logName = match.group(8)
                    if level not in logger.LOGGING_LEVELS:
                        lastLine = False
                        continue

                    if logSearch and logSearch.lower() in x.lower():
                        lastLine = True
                        finalData.append(x)
                        numLines += 1
                    elif not logSearch and logger.LOGGING_LEVELS[level] >= minLevel and (logFilter == '<NONE>' or logName.startswith(logFilter)):
                        lastLine = True
                        finalData.append(x)
                        numLines += 1
                    else:
                        lastLine = False
                        continue

                elif lastLine:
                    finalData.append("AA" + x)
                    numLines += 1

                if numLines >= numToShow:
                    return finalData

            return finalData

        t = PageTemplate(rh=self, filename="viewlogs.mako")

        minLevel = int(minLevel)

        logNameFilters = {
            '<NONE>': u'&lt;No Filter&gt;',
            'DAILYSEARCHER': u'Daily Searcher',
            'BACKLOG': u'Backlog',
            'SHOWUPDATER': u'Show Updater',
            'CHECKVERSION': u'Check Version',
            'SHOWQUEUE': u'Show Queue',
            'SEARCHQUEUE': u'Search Queue (All)',
            'SEARCHQUEUE-DAILY-SEARCH': u'Search Queue (Daily Searcher)',
            'SEARCHQUEUE-BACKLOG': u'Search Queue (Backlog)',
            'SEARCHQUEUE-MANUAL': u'Search Queue (Manual)',
            'SEARCHQUEUE-FORCED': u'Search Queue (Forced)',
            'SEARCHQUEUE-RETRY': u'Search Queue (Retry/Failed)',
            'SEARCHQUEUE-RSS': u'Search Queue (RSS)',
            'SHOWQUEUE-FORCE-UPDATE': u'Search Queue (Forced Update)',
            'SHOWQUEUE-UPDATE': u'Search Queue (Update)',
            'SHOWQUEUE-REFRESH': u'Search Queue (Refresh)',
            'SHOWQUEUE-FORCE-REFRESH': u'Search Queue (Forced Refresh)',
            'FINDPROPERS': u'Find Propers',
            'POSTPROCESSOR': u'Post Processor',
            'FINDSUBTITLES': u'Find Subtitles',
            'TRAKTCHECKER': u'Trakt Checker',
            'EVENT': u'Event',
            'ERROR': u'Error',
            'TORNADO': u'Tornado',
            'Thread': u'Thread',
            'MAIN': u'Main',
        }

        if logFilter not in logNameFilters:
            logFilter = '<NONE>'

        regex = r"^(\d\d\d\d)\-(\d\d)\-(\d\d)\s*(\d\d)\:(\d\d):(\d\d)\s*([A-Z]+)\s*(.+?)\s*\:\:\s*(.*)$"

        data = []

        if ek(os.path.isfile, logger.log_file):
            with io.open(logger.log_file, 'r', encoding='utf-8') as f:
                data = Get_Data(minLevel, f.readlines(), 0, regex, logFilter, logSearch, maxLines)

        for i in range(1, int(sickbeard.LOG_NR)):
            if ek(os.path.isfile, logger.log_file + "." + str(i)) and (len(data) <= maxLines):
                with io.open(logger.log_file + "." + str(i), 'r', encoding='utf-8') as f:
                    data += Get_Data(minLevel, f.readlines(), len(data), regex, logFilter, logSearch, maxLines)

        return t.render(
            header="Log File", title="Logs", topmenu="system",
            logLines=u"".join(data), minLevel=minLevel, logNameFilters=logNameFilters,
            logFilter=logFilter, logSearch=logSearch,
            controller="errorlogs", action="viewlogs")

    def submit_errors(self):
        submitter_result, issue_id = logger.submit_errors()
        logger.log(submitter_result, (logger.INFO, logger.WARNING)[issue_id is None])
        submitter_notification = ui.notifications.error if issue_id is None else ui.notifications.message
        submitter_notification(submitter_result)

        return self.redirect("/errorlogs/")
