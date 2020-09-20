# -*- coding: utf-8 -*-
"""Märkesdefinitioner inkl delmoment med kort och lång beskrivning."""

import urllib
import logging
import datetime
from operator import attrgetter
from collections import namedtuple
from flask import Blueprint, make_response, redirect, render_template, request


from google.appengine.ext import ndb # pylint: disable=import-error

import htmlform
import lagerbidrag
import scoutnet
import sensus
from excelreport import ExcelReport
from jsonreport import JsonReport
from data import Meeting, Person, ScoutGroup, Semester, Troop, TroopPerson, UserPrefs
from dakdata import DakData, Deltagare, Sammankomst
from start import semester_sort


Krav = namedtuple("Krav", "index short long")

badges = Blueprint('badges_page', __name__, template_folder='templates') # pylint : disable=invalid-name

@badges.route('/')
@badges.route('/<sgroup_url>', methods=['POST', 'GET'])
@badges.route('/<sgroup_url>/', methods=['POST', 'GET'])
@badges.route('/<sgroup_url>/<troop_url>', methods=['POST', 'GET'])
@badges.route('/<sgroup_url>/<troop_url>/', methods=['POST', 'GET'])
@badges.route('/<sgroup_url>/<troop_url>/<key_url>', methods=['POST', 'GET'])
@badges.route('/<sgroup_url>/<troop_url>/<key_url>/', methods=['POST', 'GET'])
def show(sgroup_url=None, troop_url=None, key_url=None):
    user = UserPrefs.current()
    if not user.hasAccess():
        return "denied badges", 403

    breadcrumbs = [{'link':'/', 'text':'Hem'}]
    section_title = u'Märken/Kår'
    breadcrumbs.append({'link':'/badges', 'text':section_title})
    baselink = '/badges/'

    scoutgroup = None
    if sgroup_url is not None:
        sgroup_key = ndb.Key(urlsafe=sgroup_url)
        scoutgroup = sgroup_key.get()
        baselink += sgroup_url + "/"
        breadcrumbs.append({'link':baselink, 'text':scoutgroup.getname()})
    
    troop = None
    semester = user.activeSemester.get()
    if troop_url is not None:
        baselink += troop_url + "/"
        troop_key = ndb.Key(urlsafe=troop_url)
        troop = troop_key.get()
        breadcrumbs.append({'link':baselink, 'text':troop.getname()})
        semester = troop.semester_key.get()
    
    logging.info("In BADGES")
    
    # render main pages
    if scoutgroup is None or troop is None:
        section_title = 'Märken för kår'
        newEB = {'name': "C-skeppare",
                 'shortdesc': ['Utrustning', 'Sjökort', 'Revning'],
                 'longdesc':['Kontrollera att behövlig utrustning finns ombord',
                             'Visa grundläggande kunskap om sjökort alternativt har tagit förarbevis',
                             'Skär i försegel och revad stor, sätt segel och lägg ut, slå vid lämpligt tillfälle ut revet']}
        return render_template('badgeform.html',
                               heading=section_title,
                               baselink=baselink,
                               eb=newEB,
                               breadcrumbs=breadcrumbs)
    elif key_url is not None:
        meeting = ndb.Key(urlsafe=key_url).get()
        section_title = meeting.getname()
        baselink += key_url + "/"
        breadcrumbs.append({'link':baselink, 'text':section_title})
        return render_template('meeting.html',
                               heading=section_title,
                               baselink=baselink,
                               existingmeeting=meeting,
                               breadcrumbs=breadcrumbs,
                               semester=troop.semester_key.get())