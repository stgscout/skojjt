# -*- coding: utf-8 -*-
"""Märkesdefinitioner inkl delmoment med kort och lång beskrivning."""

import urllib
import logging
import datetime
from operator import attrgetter
from collections import namedtuple
from flask import Blueprint, make_response, redirect, render_template, request, redirect


from google.appengine.ext import ndb # pylint: disable=import-error

import htmlform
from data import Meeting, Person, ScoutGroup, Semester, Troop, TroopPerson, UserPrefs
from dakdata import DakData, Deltagare, Sammankomst
from start import semester_sort
from data_badge import Badge, BadgePart, TroopBadge


Krav = namedtuple("Krav", "index short long")

badges = Blueprint('badges_page', __name__, template_folder='templates')  # pylint : disable=invalid-name

@badges.route('/')
@badges.route('/<sgroup_url>')  # List of badges for a scout group
@badges.route('/<sgroup_url>/')
@badges.route('/<sgroup_url>/badge/<badge_url>', methods=['POST', 'GET'])  # A specific badge, post with newbadge
@badges.route('/<sgroup_url>/badge/<badge_url>/', methods=['POST', 'GET'])  # A specific badge, post with newbadge
@badges.route('/<sgroup_url>/badge/<badge_url>/<action>', methods=['POST', 'GET'])  # A specific badge, post with newbadge
@badges.route('/<sgroup_url>/badge/<badge_url>/<action>/', methods=['POST', 'GET'])  # A specific badge, post with newbadge
@badges.route('/<sgroup_url>/troop/<troop_url>', methods=['POST', 'GET'])  # List of badges for a troop
@badges.route('/<sgroup_url>/troop/<troop_url>/', methods=['POST', 'GET'])
@badges.route('/<sgroup_url>/troop/<troop_url>/<badge_url>', methods=['POST', 'GET'])  # Status/Update
@badges.route('/<sgroup_url>/troop/<troop_url>/<badge_url>/', methods=['POST', 'GET'])
@badges.route('/<sgroup_url>/person/<person_url>')  # List of badges for a person
@badges.route('/<sgroup_url>/person/<person_url>/')  # List of badges for a person
@badges.route('/<sgroup_url>/person/<person_url>/<badge_url>', methods=['POST', 'GET'])  # Status/Update
@badges.route('/<sgroup_url>/person/<person_url>/<badge_url>/', methods=['POST', 'GET'])
def show(sgroup_url=None, badge_url=None, troop_url=None, person_url=None, action=None):
    logging.info("badges.py: sgroup_url=%s, badge_url=%s, troop_url=%s, person_url=%s, action=%s",
                 sgroup_url, badge_url, troop_url, person_url, action)
    user = UserPrefs.current()
    if not user.hasAccess():
        return "denied badges", 403

    breadcrumbs = [{'link': '/', 'text': 'Hem'}]
    section_title = u'Märken'
    breadcrumbs.append({'link': '/badges', 'text': section_title})
    baselink = '/badges/'

    scoutgroup = None
    if sgroup_url is not None:
        sgroup_key = ndb.Key(urlsafe=sgroup_url)
        scoutgroup = sgroup_key.get()
        baselink += sgroup_url + "/"
        breadcrumbs.append({'link': baselink, 'text': scoutgroup.getname()})

    if scoutgroup is None:
        return render_template(
            'index.html',
            heading=section_title,
            baselink=baselink,
            items=ScoutGroup.getgroupsforuser(user),
            breadcrumbs=breadcrumbs,
            username=user.getname())

    if troop_url is None:  # scoutgroup level
        if badge_url is None:
            logging.info("Render list of all badges")
            section_title = 'Märken för kår'
            badges = Badge.get_badges(sgroup_key)
            logging.info("Length of badges is %d", len(badges))

            return render_template('badgelist.html',
                                    heading=section_title,
                                    baselink=baselink,
                                    badges=badges,
                                    breadcrumbs=breadcrumbs)

        logging.info("Render badge")
        logging.info("badge_url=%s, action=%s", badge_url, action)
        if request.method == "GET":
            if badge_url == "newbadge":  # Get form for or create new
                section_title = "Nytt märke"
                name = ""
                badge_parts = []
            else:
                section_title = "Märke"
                badge_key = ndb.Key(urlsafe=badge_url)
                badge = badge_key.get()
                name = badge.name
                badge_parts = badge.get_parts()

            baselink += badge_url + "/"
            breadcrumbs.append({'link': baselink, 'text': section_title})

            return render_template('badge.html',
                                    name=name,
                                    heading=section_title,
                                    baselink=baselink,
                                    breadcrumbs=breadcrumbs,
                                    badge_parts=badge_parts,
                                    action=action,
                                    scoutgroup=scoutgroup)
        if request.method == "POST":
            name = request.form['name']
            part_strs = request.form['parts'].split("::")
            # TODO. Check possible utf-8/unicode problem here
            parts = [p.split("|") for p in part_strs]
            logging.info("name: %s, parts: %s", name, parts)
            if badge_url == "newbadge":
                badge = Badge.create(name, sgroup_key, parts)
                return redirect(breadcrumbs[-2]['link'])
            else:  # Update an existing badge
                badge_key = ndb.Key(urlsafe=badge_url)
                badge = badge_key.get()
                badge.update(name, parts)
                return redirect(breadcrumbs[-2]['link'])
        else:
            return "Unsupported method %s" % request.method

    if badge_url is None:
        logging.info("TROOP_URL without BADGE_URL")
        troop_key = ndb.Key(urlsafe=troop_url)
        troop = troop_key.get()
        if request.method == "GET":
            # Since we come from /start/... instead of /badges/... replace part links
            for bc in breadcrumbs:
                bc['link'] = bc['link'].replace('badges', 'start')
                bc['text'] = bc['text'].replace('Märken', 'Kårer')
            baselink += "troop/" + troop_url + "/"
            badges = Badge.get_badges(sgroup_key)
            semester_key = troop.semester_key
            semester = semester_key.get()
            semester_name = semester.getname()
            section_title = "Märken för %s %s" % (troop.name, semester_name)
            breadcrumbs.append({'link': baselink, 'text': "Märken %s %s" % (troop.name, semester_name)})
            troop_badges = ['arne']
            return render_template('badges_for_troop.html',
                                   name=troop.name,
                                   heading=section_title,
                                   baselink=baselink,
                                   breadcrumbs=breadcrumbs,
                                   badges=badges,
                                   troop_badges=troop_badges,
                                   scoutgroup=scoutgroup)
        # POST
        new_badge_names = request.form['badges'].split("|")
        logging.info(new_badge_names)
        TroopBadge.update_for_troop(troop, new_badge_names)
        return redirect(breadcrumbs[-2]['link'])

    if badge_url is not None:
        logging.info("BADGE FOR TROOP")
        troop_key = ndb.Key(urlsafe=troop_url)
        troop = troop_key.get()
        badge_key = ndb.Key(urlsafe=badge_url)
        badge = badge_key.get()
        if request.method == "GET":
            baselink += "troop/" + troop_url + "/" + badge_url + "/"
            section_title = "%s för %s" % (badge.name, troop.name)
            troop_persons = TroopPerson.getTroopPersonsForTroop(troop_key)
            persons = []
            persons_dict = {}
            for troop_person in troop_persons:
                person_key = troop_person.person
                person = troop_person.person.get()
                persons.append(person)
                persons_dict[person_key] = person
            badge_parts = badge.get_parts()
            parts_progress = []  # [part][person] boolean matrix
            for part in badge_parts:
                person_progress = []
                for troop_person in troop_persons:
                    # Check if specific part is done
                    person_progress.append(True)
                parts_progress.append(person_progress)
            logging.info("persons = %d" % len(persons))
            logging.info("parts_progress %s" % parts_progress)
            return render_template('troop_badge.html',
                                   heading=badge.name,
                                   baselink=baselink,
                                   breadcrumbs=breadcrumbs,
                                   troop=troop,
                                   badge=badge,
                                   badge_parts=badge_parts,
                                   persons=persons,
                                   troop_persons=troop_persons,
                                   parts_progress=parts_progress)

    """ # There must be a troop_url
    badge = None
    if badge_url is not None:
        baselink += badge_url + "/"
        badge_key = ndb.Key(urlsafe=badge_url)
        badge = badge_key.get()
        section_title = "Märke"
        breadcrumbs.append({'link': baselink, 'text': badge.name})
        badge_parts = badge.get_parts()
        logging.info(badge_parts)
        return render_template('badge.html',
                               name=badge.name,
                               heading=section_title,
                               baselink=baselink,
                               breadcrumbs=breadcrumbs,
                               badge_parts=badge_parts,
                               scoutgroup=scoutgroup)
        # Show or edit badge further down """