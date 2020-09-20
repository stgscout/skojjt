# -*- coding: utf-8 -*-
"""Badge class is used to define and track märken and certifikat."""

from google.appengine.api import memcache, users
from google.appengine.ext import ndb

from data import ScoutGroup, Troop, Person, PropertyWriteTracker



class Badge(ndb.Model):
    "Märkesdefinition för en scoutkår. Namn på märket + lista av krav."
    name = ndb.StringProperty(required=True)
    scoutgroup = ndb.KeyProperty(kind=ScoutGroup, required=True)
    #image = ndb.BlobProperty()

    @staticmethod
    def create(name, scoutgroup_key):
        return Badge(name=name, scoutgroup_key)


    # get_by_id is there already

class BadgePart(ndb.Model):
    "Märkesdel"
    badge = ndb.KeyProperty(kind=Badge)
    idx = ndb.IntegerProperty()  # For sorting
    short_desc = ndb.StringProperty()
    long_desc = ndb.StringProperty()


    @staticmethod
    def getOrCreate(badge, idx):
        badge_parts = 
        if m != None:
            if m.name != name or m.duration != duration or m.ishike != ishike:
                m.name = name
                m.duration = duration
                m.ishike = ishike
                m.put()
        else:
            m = Meeting(id=Meeting.getId(datetime, troop_key),
                datetime=datetime,
                name=name,
                troop=troop_key,
                duration=duration,
                ishike=ishike
                )
        troopmeeting_keys = memcache.get(Meeting.__getMemcacheKeyString(troop_key))
        if troopmeeting_keys is not None and m.key not in troopmeeting_keys:
            troopmeeting_keys.append(m.key)
            memcache.replace(Meeting.__getMemcacheKeyString(troop_key), troopmeeting_keys)


class BadgePartDone(ndb.Model):
    "Del som är gjord inkl. datum och vem som infört i Skojjt."
    person = ndb.KeyProperty(kind=Person)
    badge_part = ndb.KeyProperty(kind=BadgePart)
    datetime = ndb.DateProperty(required=True)
    examiner = Person


class BadgeProgress(ndb.Model):
    "Märkesprogress för en person."
    badge = ndb.KeyProperty(kind=Badge)
    person = ndb.KeyProperty(kind=Person)
    registered = ndb.BoolProperty()  # Registrerat i scoutnet
    awarded = ndb.BoolProperty()  # Utdelat till scouten
    # Lista av vilka delar som är godkända inkl. datum (och ledare)
    passed = ndb.KeyProperty(kind=BadgePartDone, repeated=True)


class TroopBadges(ndb.Model):
    "Märke för avdelning och termin."
    troop = ndb.KeyProperty(kind=Troop)
    badges = ndb.KeyProperty("Badge", repeated=True)

