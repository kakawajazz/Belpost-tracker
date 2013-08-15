# coding: utf-8
import time
import os
import urllib
import errno
import json
import logging
import socket

from settings import settings
from lxml import html, etree
from lxml.etree import tostring
from datetime import datetime
from cStringIO import StringIO
from math import ceil


class SchemaBase(object):
    _classVersion = None

    def __str__(self):
        return unicode(self).encode('utf8')

    def classVersion(self):
        return self._classVersion


class LogLevel:
    INFO = logging.INFO
    WARN = logging.WARN
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL
    DEBUG = logging.DEBUG


class LogEntry(SchemaBase):
    level = LogLevel.INFO
    host = None
    sender = None
    stamp = None
    message = None

    def __init__(self, sender, message, level=LogLevel.INFO):
        self._classVersion = 1
        self.message = message
        self.level = level
        self.host = socket.gethostname()
        self.sender = sender.__class__.__name__
        self.stamp = time.time()


    def __unicode__(self):
        return self.message


class log(object):
    loggerRoutingKey = 'trackerLog'

    @staticmethod
    def __getLoggerHost():
        return socket.gethostname()

    @staticmethod
    def sendLog(sender, message, level, loggerFilePath=settings.trackFolder + 'tracker.log'):
        print datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S, %f'), sender.__class__.__name__, \
            {LogLevel.DEBUG: 'DEBUG', LogLevel.INFO: 'INFO', LogLevel.WARN: 'WARN', LogLevel.ERROR: 'ERROR',
             LogLevel.CRITICAL: 'CRITICAL', }[level], message
        date = datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S, %f ')
        message = date + message
        logging.basicConfig(filename=loggerFilePath,
                            filemode='a',
                            format='%(message)s',
                            datefmt='%H:%M:%S',
                            level=level)
        logging.info(message)

    @staticmethod
    def info(sender, message):
#        log.sendLog(sender, message, LogLevel.INFO)
        pass

    @staticmethod
    def warn(sender, message):
        log.sendLog(sender, message, LogLevel.WARN)

    @staticmethod
    def error(sender, message):
        log.sendLog(sender, message, LogLevel.ERROR)

    @staticmethod
    def critical(sender, message):
        log.sendLog(sender, message, LogLevel.CRITICAL)

    @staticmethod
    def debug(sender, message):
        log.sendLog(sender, message, LogLevel.DEBUG)


class Tracker(settings):
    phoneNumber = settings.phoneNumber
    apiId = settings.apiId
    trackFolder = settings.trackFolder
    response = None
    fullPath = None
    parsedData = None
    lastParsedChangeTime = None
    lastRecordedChangeTime = None

    def __init__(self, number, name, locality, transformation):
        self.smsURL = None
        self.trying = 1
        self.successful = False
        self.changed = None
        self.number = number
        self.name = name
        if locality == 'local':
            self.locality = '1'
        else:
            self.locality = '2'
        self.transformation = transformation
        self.apiURL = 'http://search.belpost.by/ajax/search?item=' + self.number + '&internal=' + self.locality
        log.info(self, 'Starting track processing: %s: %s' % (self.name, self.number))
        self.fullPath = self.defineFullPath()
        self.response = self.defineResponse(self.apiURL)
        self.parseTable()
        self.defineLastParsedChangeTime()
        self.alreadyRecorded = self.checkIfFileExist()
        self.checkEarlyRecord()
        self.final()

    def defineFullPath(self):
        log.info(self, 'Defining full path for %s' % (self.number))
        return self.trackFolder + self.number

    def defineResponse(self, apiURL):
        log.info(self, 'Defining response for %s' % (self.number))
        try:
            response = urllib.urlopen(apiURL)
            self.responseCode = response.getcode()
            if self.responseCode is not 200:
                raise log.error(self, 'Server response status: %s' % (self.responseCode,))
            else:
                log.info(self, 'Server status: %s' % self.responseCode)
                return tostring(html.fromstring(response.read())).strip()
        except Exception as e:
            log.error(self, 'Couldn\'t get server response: %s' % (e.message,))
            return None

    def parser(self, source):
        results = []
        source = etree.XML(source)
        rows = iter(source)
        headers = [col.text for col in next(rows)]
        for row in rows:
            values = [col.text for col in row]
            data = dict(zip(headers, values))
            res = json.dumps(data, ensure_ascii=False)
#            res = json.dumps(data)
            results.append(res.encode('latin-1'))
#            results.append(res)
        return results

    def parseTable(self):
        log.info(self, 'Parsing table for %s' % (self.number,))
        try:
            if len(self.response):
                tables = html.fromstring(self.response).xpath('//table')
                if len(tables) is 0:
                    log.error(self, 'Tracking number looks illegal, maybe it is too early to track: %s' % (self.number,))
                    raise Exception('Illegal tracking number: %s' % (self.number,))
                if len(tables) is 1:
                    source = self.response.replace('<!--', '').replace('-->', '').replace('\n', '')\
                        .replace('  ', '').replace('  ', '').replace('  ', '')\
                        .replace('</td><td class="theader">', '</th><th>').replace('<td class="theader">', '<th>')\
                        .replace('</td></tr>', '</th></tr>', 1)
                    self.parsedData = self.parser(source)
                elif len(tables) is 2:
                    parser = etree.HTMLParser()
                    table1 = etree.parse(StringIO(self.response), parser)
                    table1 = tostring(table1.find('//table'))
                    table1 = table1[:table1.index('</table>') + 8]
                    table1 = table1.replace('<!--', '').replace('-->', '').replace('\n', '')\
                        .replace('  ', '').replace('  ', '').replace('  ', '')\
                        .replace('</td><td class="theader">', '</th><th>').replace('<td class="theader">', '<th>')\
                        .replace('</td></tr>', '</th></tr>', 1)
                    parsedData1 = self.parser(table1)
                    log.info(self, 'Getting second table of response.')
                    table2 = etree.parse(StringIO(self.defineResponse(self.apiURL.replace('&internal=2', '&internal=1'))), parser)
                    etree.strip_tags(table2, 'a')
                    table2 = tostring(table2.find('//table'))
                    table2 = table2[table2.index('<table width="100%" class="tbl">'):]
                    table2 = table2.replace('<!--', '').replace('-->', '').replace('\n', '')\
                        .replace('  ', '').replace('  ', '').replace('  ', '')\
                        .replace('</td><td class="theader">', '</th><th>').replace('<td class="theader">', '<th>')\
                        .replace('</td></tr>', '</th></tr>', 1)
                    parsedData2 = self.parser(table2)
                    resultData = parsedData1 + parsedData2
                    self.parsedData = resultData
        except Exception as e:
            log.error(self, 'Table parsing error: %s' % (e.message))
            raise

    def defineLastParsedChangeTime(self):
        log.info(self, 'Defining last parsed record time for %s' % (self.number,))
        self.lastParsedChangeTime = json.loads(self.parsedData[-1])
        try:
            self.lastParsedChangeTime = time.mktime(datetime.strptime(self.lastParsedChangeTime[u'Дата'], '%Y-%m-%d %H:%M:%S').timetuple())
        except:
            self.lastParsedChangeTime = time.mktime(datetime.strptime(self.lastParsedChangeTime[u'Дата'], '%d.%m.%Y %H:%M:%S').timetuple())

    def checkIfFileExist(self):
        log.info(self, 'Checking file existing: %s' % (self.fullPath,))
        try:
            with open(self.fullPath):
                log.info(self, 'File already exist: %s' % (self.fullPath,))
                return True
        except IOError:
            log.info(self, 'File doesn\'t exist: %s' % (self.fullPath,))
            return False

    def checkEarlyRecord(self):
        if self.alreadyRecorded:
            try:
                log.info(self, 'Checking early recorded track: %s' % (self.fullPath,))
                f = open(self.fullPath, 'r')
                oldTrack = f.readlines()
                f.close()
                log.info(self, 'Early recorded track has been got: %s' % (self.fullPath,))
                self.lastRecordedChangeTime = json.loads(oldTrack[-1])[u'Дата']
                try:
                    self.lastRecordedChangeTime = time.mktime(datetime.strptime(self.lastRecordedChangeTime, '%Y-%m-%d %H:%M:%S').timetuple())
                except:
                    self.lastRecordedChangeTime = time.mktime(datetime.strptime(self.lastRecordedChangeTime, '%d.%m.%Y %H:%M:%S').timetuple())
                if self.lastRecordedChangeTime < self.lastParsedChangeTime:
                    self.changed = True
                    self.composeAndSend()
                elif self.lastRecordedChangeTime == self.lastParsedChangeTime:
                    self.changed = False
                    self.successful = True
                    log.info(self, 'Track didn\'t changed: %s' % (self.fullPath,))
            except:
                log.error(self, 'Cannot open early recorded file and get last change data: %s' % (self.fullPath,))
        else:
            self.composeAndSend()
            self.changed = True

    def composeAndSend(self):
        try:
            self.action = json.loads(self.parsedData[-1], encoding='UTF-8')[u'Событие']
            try:
                self.office = json.loads(self.parsedData[-1], encoding='UTF-8')[u'POST OFFICE']
            except:
                self.office = ''
            self.message = self.name.encode('utf8') + ': ' + self.action.encode('utf8') + ' ' + self.office.encode('utf8')
            log.debug(self, 'Message: %s' % self.message)
            if len(self.message) > 70 and self.transformation == 'split':
                smsCount = int(ceil(float(len(self.message)) / 70))
                for i in range(smsCount):
                    message = self.message[(70 * i):(70 * (i + 1))]
                    log.debug(self, 'Sms message: %s' % message)
                    self.smsUrl = "http://sms.ru/sms/send?api_id=" + self.apiId + "&to=" + self.phoneNumber + "&text=" + message
                    log.debug(self, 'Sms URL: %s' % self.smsUrl)
                    self.sendSMS()
            elif len(self.message) > 70 and self.transformation == 'translit':
                self.message = self.translit(self.message)
                smsCount = int(ceil(float(len(self.message)) / 160))
                for i in range(smsCount):
                    message = self.message[(160 * i):(160 * (i + 1))]
                    log.debug(self, 'Sms message: %s' % message)
                    self.smsUrl = "http://sms.ru/sms/send?api_id=" + self.apiId + "&to=" + self.phoneNumber + "&text=" + message
                    log.debug(self, 'Sms URL: %s' % self.smsUrl)
                    self.sendSMS()
            else:
                log.debug(self, 'Sms message: %s' % self.message)
                self.smsUrl = "http://sms.ru/sms/send?api_id=" + self.apiId + "&to=" + self.phoneNumber + "&text=" + self.message
                log.debug(self, 'Sms URL: %s' % self.smsUrl)
                self.sendSMS()
                return True
        except Exception as e:
            log.error(self, 'Cannot compose SMS: %s' % e.message)


    def translit(self, message):
        try:
            symbols = {
                'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','ё':'e','ж':'zh','з':'z','и':'i','й':'j','к':'k','л':'l','м':'m','н':'n','о':'o','п':'p','р':'r','с':'s','т':'t','у':'u','ф':'f','х':'h','ц':'c','ч':'ch','ш':'sh','щ':'sch',"ъ":"'",'ы':'y','ь':"'",'э':'e','ю':'ju','я':'ja',
                'А':'A','Б':'B','В':'V','Г':'G','Д':'D','Е':'E','Ё':'E','Ж':'ZH','З':'Z','И':'I','Й':'J','К':'K','Л':'L','М':'M','Н':'N','О':'O','П':'P','Р':'R','С':'S','Т':'T','У':'U','Ф':'F','Х':'H','Ц':'C','Ч':'CH','Ш':'SH','Щ':'SCH','Ъ':"'",'Ы':'Y','Ь':"'",'Э':'E','Ю':'Ju','Я':'Ja'
            }
            for k in symbols.keys():
                message = message.replace(k, symbols[k])
            return message
        except Exception as e:
            log.error(self, 'Cannot translit message: %s' % (e.message,))
            raise

    def sendSMS(self):
        try:
            self.response = urllib.urlopen(self.smsUrl)
        except Exception as e:
            log.error(self, 'Cannot open sms URL: %s' % e.message)
        if self.response.getcode() is 200 and self.trying <= 3:
            try:
                self.responseBody = self.response.read() + '    '
                if self.responseBody[:3] == '100':
                    log.debug(self, 'Notification were sent')
                    self.successful = True
                else:
                    log.debug(self, 'Something going wrong. Response report: %s' % self.responseBody)
                    self.successful = False
                    log.debug(self, 'Waiting for next trying...')
                    time.sleep(60)
                    log.debug(self, 'Trying to send again: "%s": %s' % (self.message, self.smsUrl))
                    self.trying += 1
                    self.sendSMS()
            except Exception as e:
                self.successful = False
                log.error(self, 'Fail checkSuccess: %s' % e.message)
        else:
            log.error(self, 'Invalid Sms-URL: response status %s, response body: %s' % (self.response.getcode(), self.responseBody))

    def makeRecord(self):
        log.info(self, 'Making record: %s' % (self.fullPath,))
        try:
            os.makedirs(self.trackFolder)
            self.write()
        except OSError as exception:
            self.write()
            if exception.errno != errno.EEXIST:
                log.error(self, 'Error occurred while making record: %s' % (exception.message,))
                raise

    def write(self):
        log.info(self, 'Writing self: %s' % (self.fullPath,))
        try:
            f = open(self.fullPath, 'w+')
            for data in self.parsedData:
                f.write(data + '\n')
                log.debug(self, data)
            f.close()
            log.debug(self, 'Track has been written: %s' % (self.fullPath,))
        except Exception as e:
            log.error(self, 'Cannot write track %s: %s' % (self.fullPath, e.message))

    def final(self):
        if self.successful and self.changed:
            self.makeRecord()
            log.debug(self, 'Processing complete successfully: %s \n' % (self.fullPath,))
        elif self.successful and not self.changed:
            log.debug(self, 'Processing complete successfully: %s \n' % (self.fullPath,))
        elif self.successful is False:
            log.debug(self, 'Processing incomplete: %s \n' % (self.fullPath,))

for item in settings.items:
    tracker = Tracker(item[0], item[1], item[2], item[3])