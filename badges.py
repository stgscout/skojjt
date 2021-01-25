# -*- coding: utf-8 -*-
"""Märkesdefinitioner inkl delmoment med kort och lång beskrivning."""

import urllib
import logging
import datetime
from operator import attrgetter
from collections import namedtuple
from flask import Blueprint, make_response, render_template, request


from google.appengine.ext import ndb # pylint: disable=import-error

import htmlform
from data import Meeting, Person, ScoutGroup, Semester, Troop, TroopPerson, UserPrefs
from dakdata import DakData, Deltagare, Sammankomst
from start import semester_sort
from data_badge import Badge, BadgePart, BadgePartDone, TroopBadge

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
@badges.route('/<sgroup_url>/person/<person_url>/')  # List of badges for a person
@badges.route('/<sgroup_url>/person/<person_url>/<badge_url>/', methods=['POST', 'GET'])
@badges.route('/<sgroup_url>/person/<person_url>/<badge_url>/<action>/', methods=['POST', 'GET'])
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

    if troop_url is None and person_url is None:  # scoutgroup level
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
                name = "Nytt"
                badge_parts = []
            else:
                section_title = "Märke"
                badge_key = ndb.Key(urlsafe=badge_url)
                badge = badge_key.get()
                name = badge.name
                badge_parts = badge.get_parts()

            baselink += 'badge/' + badge_url + "/"
            if action is not None:
                baselink += action + '/'
            breadcrumbs.append({'link': baselink, 'text': name})

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
                return "ok"
            else:  # Update an existing badge
                badge_key = ndb.Key(urlsafe=badge_url)
                badge = badge_key.get()
                badge.update(name, parts)
                return "ok"
        else:
            return "Unsupported method %s" % request.method, 500

    if troop_url is not None and badge_url is None:
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
            breadcrumbs.append({'link': baselink, 'text': "Märken %s" % troop.name})
            troop_badges = TroopBadge.get_badges_for_troop(troop)
            logging.info("Nr troop_badges is %d" % len(troop_badges))
            troop_badge_names = [tb.name for tb in troop_badges]
            return render_template('badges_for_troop.html',
                                   name=troop.name,
                                   heading=section_title,
                                   baselink=baselink,
                                   breadcrumbs=breadcrumbs,
                                   badges=badges,
                                   troop_badge_names=troop_badge_names,
                                   scoutgroup=scoutgroup)
        # POST
        new_badge_names = request.form['badges'].split("|")
        logging.info(new_badge_names)
        TroopBadge.update_for_troop(troop, new_badge_names)
        return "ok"

    if troop_url is not None and badge_url is not None:
        troop_key = ndb.Key(urlsafe=troop_url)
        troop = troop_key.get()
        badge_key = ndb.Key(urlsafe=badge_url)
        badge = badge_key.get()
        if request.method == "POST":
            logging.info("POST %s %s" % (troop.name, badge.name))
            update = request.form['update']
            if update == "":
                return "ok"  # Return ok to Ajax call 
            new_progress = update.split(",")
            examiner_name = UserPrefs.current().name
            logging.info("new_progress %s" % new_progress)
            for prog in new_progress:
                scout_url, idx = prog.split(":")
                badge_part_idx = int(idx)
                scout_key = ndb.Key(urlsafe=scout_url)
                logging.info("Update: %s %s %d %s", scout_key, badge_key, badge_part_idx, examiner_name)
                BadgePartDone.create(scout_key, badge_key, badge_part_idx, examiner_name)
            return "ok"  # Return ok to Ajax call
        if request.method == "GET":
            logging.info("GET %s %s" % (troop.name, badge.name))
            # Since we come from /start/... instead of /badges/... replace part links
            for bc in breadcrumbs:
                bc['link'] = bc['link'].replace('badges', 'start')
                bc['text'] = bc['text'].replace('Märken', 'Kårer')
            baselink += "troop/" + troop_url + "/" + badge_url + "/"
            breadcrumbs.append({'link': baselink, 'text': "%s %s" % (troop.name, badge.name)})
            personbaselink = '/badges/' + sgroup_url + '/person/'
            section_title = "%s för %s" % (badge.name, troop.name)
            troop_persons = TroopPerson.getTroopPersonsForTroop(troop_key)
            # Remove leaders since they are not candidates for badges
            troop_persons = [tp for tp in troop_persons if not tp.leader]
            persons = []
            persons_dict = {}
            persons_progess = []
            for troop_person in troop_persons:
                person_key = troop_person.person
                person = troop_person.person.get()
                persons.append(person)
                persons_progess.append(BadgePartDone.progress(person_key, badge_key))
                persons_dict[person_key] = person
            badge_parts = badge.get_parts()
            parts_progress = []  # [part][person] boolean matrix
            for part in badge_parts:
                person_done = []
                for progress in persons_progess:
                    for part_done in progress:
                        if part_done.idx == part.idx:
                            person_done.append(True)
                            break
                    else:  # No break
                        person_done.append(False)
                parts_progress.append(person_done)
            return render_template('troop_badge.html',
                                   heading=badge.name,
                                   baselink=baselink,
                                   personbaselink=personbaselink,
                                   breadcrumbs=breadcrumbs,
                                   troop=troop,
                                   badge=badge,
                                   badge_parts=badge_parts,
                                   persons=persons,
                                   troop_persons=troop_persons,
                                   parts_progress=parts_progress)

    if person_url is not None:
        person_key = ndb.Key(urlsafe=person_url)
        person = person_key.get()
        baselink = "/badges/" + sgroup_url + '/person/' + person_url + '/'
        breadcrumbs.append({'link': baselink, 'text': "%s" % person.getname()})
        if badge_url is None:
            logging.info("Badges for %s" % person.getname())
            badge_parts_done = BadgePartDone.query(BadgePartDone.person_key == person_key).fetch()
            badge_keys = set()
            for part in badge_parts_done:
                badge_keys.add(part.badge_key)
            badges = []
            for badge_key in badge_keys:
                badges.append(badge_key.get())
            badges.sort(key=lambda x: x.name)

            return render_template('badgelist_person.html',
                                   baselink=baselink,
                                   breadcrumbs=breadcrumbs,
                                   badges=badges,
                                   badge_parts_done=badge_parts_done)
        # badge_url is not none

    if person_url is not None and badge_url is not None:
        person_key = ndb.Key(urlsafe=person_url)
        badge_key = ndb.Key(urlsafe=badge_url)
        badge = badge_key.get()
        if request.method == "POST":
            idx = int(request.form['idx'])
            examiner_name = UserPrefs.current().name
            logging.info("Setting badge %s idx %s for %s" % (badge.name, idx, person.getname()))
            BadgePartDone.create(person_key, badge_key, idx, examiner_name)
            return "ok"

        logging.info("Badge %s for %s" % (badge.name, person.getname()))
        baselink += badge_url + "/"
        breadcrumbs.append({'link': baselink, 'text': "%s" % badge.name})
        badge_parts = badge.get_parts()
        parts_done = BadgePartDone.progress(person_key, badge_key)
        d_pos = 0
        done = []
        Done = namedtuple('Done', 'idx date examiner done')
        for bp in badge_parts:
            if d_pos >= len(parts_done):
                done.append(Done(bp.idx, "- - -", "- - -", False))
                continue
            pd = parts_done[d_pos]
            if pd.idx == bp.idx:
                done.append(Done(pd.idx, pd.date.strftime("%Y-%m-%d"), pd.examiner_name, True))
                d_pos += 1
            else:
                done.append(Done(bp.idx, "- - -", "- - -", False))

        logging.info("DONE: %s" % done)

        return render_template('badgeparts_person.html',
                               person=person,
                               baselink=baselink,
                               breadcrumbs=breadcrumbs,
                               badge=badge,
                               badge_parts=badge_parts,
                               done=done,
                               change=(action == "change"))

    # note that we set the 404 status explicitly
    return "Page not found", 404
