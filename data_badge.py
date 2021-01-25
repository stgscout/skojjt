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
    def create(name, scoutgroup_key, badge_parts_data):
        badge = Badge(name=name, scoutgroup=scoutgroup_key)
        badge_key = badge.put()
        for badge_part in badge_parts_data:
            bp = BadgePart(badge=badge_key,
                           idx=int(badge_part[0]),
                           short_desc=badge_part[1],
                           long_desc=badge_part[2])
            bp.put()
        # TODO. Insert 100 and 101 for Utdelat och Registrerat

    def get_parts(self):
        return BadgePart.query(BadgePart.badge == self.key).order(BadgePart.idx).fetch()

    def update(self, name, badge_parts_data):
        if name != self.name:
            self.name = name
            self.put()
        prevs = BadgePart.query(BadgePart.badge == self.key).order(BadgePart.idx).fetch()
        for old, new in zip(prevs, badge_parts_data):
            if old.idx != int(new[0]):
                logging.info("Badge part numbers don't match: %d %d" % (old.idx, int(new[0])))
                break
            if old.short_desc != new[1] or old.long_desc != new[2]:
                old.short_desc = new[1]
                old.long_desc = new[2]
                old.put()
        if len(badge_parts_data) > len(prevs):
            for new in badge_parts_data[len(prevs):]:
                bp = BadgePart(badge=self.key,
                               idx=int(new[0]),
                               short_desc=new[1],
                               long_desc=new[2])
                bp.put()
        else:
            for bp in prevs[len(badge_parts_data):]:
                bp.delete()
        # TODO: If remove, also remove all BadgePartDone
        # TODO: Handle 100 and 101 properly

    @staticmethod
    def get_badges(scoutgroup_key):
        badges = []
        if scoutgroup_key is not None:
            badges = Badge.query(Badge.scoutgroup == scoutgroup_key).fetch()
        return badges


class BadgePart(ndb.Model):
    """Badge part with index idx for sorting.

    There are special parts:
         idx=100, short_desc=Utdelat
         idx=101, short_desc=Registrerat
    to keep track of what has been awarded and registrered.
    """
    badge = ndb.KeyProperty(kind=Badge, required=True)
    idx = ndb.IntegerProperty(required=True)  # For sorting
    short_desc = ndb.StringProperty(required=True)
    long_desc = ndb.StringProperty(required=True)


class BadgePartDone(ndb.Model):
    "Part that has been done including date and who registered in Skojjt."
    badge_key = ndb.KeyProperty(kind=Badge, required=True)
    person_key = ndb.KeyProperty(kind=Person, required=True)
    idx = ndb.IntegerProperty(required=True)  # idx for BadgePart
    date = ndb.DateTimeProperty(auto_now_add=True)
    examiner_name = ndb.StringProperty(required=True)

    @staticmethod
    def create(person_key, badge_key, badge_part_idx, examiner_name):
        bpd = BadgePartDone(person_key=person_key, badge_key=badge_key,
                            idx=badge_part_idx, examiner_name=examiner_name)
        bpd.put()

    @staticmethod
    def progress(person_key, badge_key):
        "Person progress for specific badge."
        bpd = BadgePartDone.query(ndb.AND(BadgePartDone.person_key == person_key,
                                          BadgePartDone.badge_key == badge_key)).order(BadgePartDone.idx).fetch()
        return bpd


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
