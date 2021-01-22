# -*- coding: utf-8 -*-
"""Badge class används för märken och cerifikat och deras olika delar."""
import logging

from google.appengine.api import memcache, users
from google.appengine.ext import ndb

from data import ScoutGroup, Troop, Person, PropertyWriteTracker


class Badge(ndb.Model):
    "Märkesdefinition för en scoutkår. Kraven ligger separat som BadgePart."
    name = ndb.StringProperty(required=True)
    scoutgroup = ndb.KeyProperty(kind=ScoutGroup, required=True)
    # TODO. Add image = ndb.BlobProperty()

    @staticmethod
    def create(name, scoutgroup_key, badge_parts):
        badge = Badge(name=name, scoutgroup=scoutgroup_key)
        badge_key = badge.put()
        for badge_part in badge_parts:
            bp = BadgePart(badge=badge_key,
                           idx=int(badge_part[0]),
                           short_desc=badge_part[1],
                           long_desc=badge_part[2])
            bp.put()

    def get_parts(self):
        return BadgePart.query(BadgePart.badge == self.key).order(BadgePart.idx).fetch()

    def update(self, name, badge_parts):
        if name != self.name:
            self.name = name
            self.put()
        prevs = BadgePart.query(BadgePart.badge == self.key).order(BadgePart.idx).fetch()
        for old, new in zip(prevs, badge_parts):
            if old.idx != int(new[0]):
                logging.info("Badge part numbers don't match: %d %d" % (old.idx, int(new[0])))
                break
            if old.short_desc != new[1] or old.long_desc != new[2]:
                old.short_desc = new[1]
                old.long_desc = new[2]
                old.put()
        if len(badge_parts) > len(prevs):
            for new in badge_parts[len(prevs):]:
                bp = BadgePart(badge=self.key,
                               idx=int(new[0]),
                               short_desc=new[1],
                               long_desc=new[2])
                bp.put()
        else:
            for bp in prevs[len(badge_parts):]:
                bp.delete()
        # If remove, also remove all BadgePartDone


    # get_by_id is there already

    @staticmethod
    def get_badges(scoutgroup_key):
        badges = []
        logging.info("GET_BADGES")
        if scoutgroup_key is not None:
            badges = Badge.query(Badge.scoutgroup == scoutgroup_key).fetch()
        return badges


class BadgePart(ndb.Model):
    "Märkesdel med idx för att sortera"
    badge = ndb.KeyProperty(kind=Badge, required=True)
    idx = ndb.IntegerProperty(required=True)  # For sorting
    short_desc = ndb.StringProperty(required=True)
    long_desc = ndb.StringProperty(required=True)

    @staticmethod
    def get_or_create(badge_key, idx, short_desc, long_desc):
        badge_part = BadgePart.get_by_id(badge_key, idx)
        if badge_part is None:
            badge_part = BadgePart.create(badge_key, idx, short_desc, long_desc)
            badge_part.put()
        if short_desc != badge_part.short_desc or long_desc != badge_part.long_desc:
            badge_part.short_desc = short_desc
            badge_part.long_desc = long_desc
            badge_part.put()
        # TODO. Check if we should cache something


class BadgePartDone(ndb.Model):
    "Del som är gjord inkl. datum och vem som infört i Skojjt."
    badge_key = ndb.KeyProperty(kind=Badge, required=True)
    person_key = ndb.KeyProperty(kind=Person, required=True)
    idx = ndb.IntegerProperty(required=True)
    datetime = ndb.DateProperty(required=True)
    examiner = Person


class BadgeProgress(ndb.Model):
    "Märkesprogress för en person."
    badge_key = ndb.KeyProperty(kind=Badge)
    person_key = ndb.KeyProperty(kind=Person)
    registered = ndb.BooleanProperty()  # Registrerat i scoutnet
    awarded = ndb.BooleanProperty()  # Utdelat till scouten
    # Lista av vilka delar som är godkända inkl. datum (och ledare)
    # This can be found by quering get_by_
    #  with passed = ndb.KeyProperty(kind=BadgePartDone, repeated=True)

    @staticmethod
    def getOrCreate(badge_key, person_id):
        badge_progress = BadgeProgress.get_by_id(badge_key, person_id)
        if badge_progress is None:
            badge_progress = BadgeProgress.create(badge_key, person_id)
            badge_progress.put()
        return badge_progress
        # TODO. Check if we should cache something

    @staticmethod
    def create(badge_key, person_id):
        badge_progress = BadgeProgress(
            badge_key=badge_key,
            person_id=person_id,
            registered=False,
            awarded=False
        )
        return badge_progress

    def get_progress(self):
        parts_done = BadgePartDone.query(
            BadgePartDone.Badge_key == self.badge_key,
            BadgePartDone.person_key == self.person_id)
        parts_idx = [p.idx for p in parts_done]
        return {
            'registered': parts_done.registered,
            'awarded': parts_done.awarded,
            'parts_done': parts_idx.sorted()}


class TroopBadge(ndb.Model):
    "Märke för avdelning och termin."
    troop_key = ndb.KeyProperty(kind=Troop)
    badge_key = ndb.KeyProperty(kind=Badge)
    idx = ndb.IntegerProperty(required=True)  # For sorting

    @staticmethod
    def get_badges_for_troop(troop):
        tps = TroopBadge.query(TroopBadge.troop_key == troop.key).order(TroopBadge.idx).fetch()
        return [Badge.get_by_id(tp.badge_key.id()) for tp in tps]

    @staticmethod
    def update_for_troop(troop, name_list):
        old_troop_badges = TroopBadge.query(TroopBadge.troop_key == troop.key).order(TroopBadge.idx).fetch() 
        old_badges = [Badge.get_by_id(tp.badge_key.id()) for tp in old_troop_badges]
        nr_old_troop_badges = len(old_troop_badges)
        logging.info("New are %d, old were %d" % (len(name_list), nr_old_troop_badges))
        # First find keys to remove
        to_remove = []
        for old in old_badges:
            if old.name not in name_list:
                to_remove.append(old.key)
        # Next remove them from the troop badges
        for old_key in to_remove:
            for otb in old_troop_badges:
                if otb.badge_key == old_key:
                    otb.key.delete()
        # Now find really new names
        really_new = []
        for name in name_list:
            for old in old_badges:
                if old.name == name:
                    break
            else:
                really_new.append(name)
        if len(really_new) == 0:
            return
        logging.info("Really new are %d" % len(really_new))
        allbadges = Badge.get_badges(troop.scoutgroup)
        idx = nr_old_troop_badges
        for badge in allbadges:
            if badge.name in really_new:
                tb = TroopBadge(troop_key=troop.key, badge_key=badge.key, idx=idx)
                tb.put()
                idx += 1

