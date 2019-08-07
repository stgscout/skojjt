# -*- coding: utf-8 -*-
"""
Calculate data needed and fill in forms for lägerbidragsansökan (hike grants).

The limits and data needed depends on region.
Göteborg has 2-14 nights, age 7-25, and includes som older people.
Stocholm has 2-7 days, age 7-20, and does not include older people.
Stockholm also needs postal address for each scout.
"""
import io
import copy
from datetime import datetime
import math
import urllib
from collections import namedtuple
from flask import render_template, make_response

from dataimport import Meeting, Troop, logging

RegionLimits = namedtuple('RegionLimits', ['min_days', 'max_days', 'min_age', 'max_age', 'count_over_max_age'])


LIMITS = {'gbg' : RegionLimits(3, 15, 7, 25, True),  # min 2 nights, max 14 nights, 7-25 yers + some older
          'sthlm' : RegionLimits(2, 7, 7, 20, False)} # min 2 days, max 7 days, 7-20 years


def render_lagerbidrag(request, scoutgroup, context, sgroup_key=None, user=None, trooppersons=None, troop_key=None):
    if context == "group":
        assert sgroup_key is not None
        assert user is not None
        troops = Troop.getTroopsForUser(sgroup_key, user)
    elif context == "troop":
        assert trooppersons is not None
        assert troop_key is not None
    else:
        raise ValueError("Context %s unknown" % context)

    region = request.args.get('region')
    limits = LIMITS[region]
    fromDate = request.form['fromDate']
    toDate = request.form['toDate']
    site = request.form['site']
    contactperson = request.form['contactperson']
    try:
        if context == "group":
            bidrag = createLagerbidragGroup(limits, scoutgroup, troops, contactperson, site, fromDate, toDate)
        else:
            bidrag = createLagerbidrag(limits, scoutgroup, trooppersons, troop_key, contactperson, site, fromDate, toDate)
        if region == 'gbg':
            return response_gbg(bidrag)
        elif region == 'sthlm':
            return response_sthlm(bidrag)
    except ValueError as e:
        return render_template('error.html', error=str(e))


def response_gbg(bidrag):
    result = render_template(
        'lagerbidrag.html',
        bidrag=bidrag.bidrag,
        persons=bidrag.persons,
        numbers=bidrag.numbers)
    response = make_response(result)
    return response


def response_sthlm(container):
    from mailmerge import MailMerge

    bidrag = container.bidrag
    persons = container.persons

    nr_persons = container.nr_persons_total
    persons = persons[:nr_persons]

    start = datetime.strptime(bidrag.dateFrom, '%Y-%m-%d')
    end = datetime.strptime(bidrag.dateTo, '%Y-%m-%d')
    nr_days = (end - start).days + 1

    data = {
        'kundnummer': u'4140027',
        'foreningsnamn': u'Sjöscoutkåren S:t Göran',
        'ledare': u'Torbjörn Einarsson',
        'ledartelefon': u'072-20 325 88',
        'ledaremail': u'torbjorn.einarsson@stgscout.se',
        'lov': u'X',
        'helg': u'\u2610',
        'lagerplats': bidrag.site,
        'startdatum': bidrag.dateFrom,
        'slutdatum': bidrag.dateTo,
        'datum': '2019-07-29',
        'firmatecknare': u'Torbjörn Einarsson',
        'firmatecknartelefon': '072-20 325 88',
        'antalmedlemmar': str(nr_persons),
        'antaldagar': str(nr_days)  # Should be total number of days
    }

    persons_per_page = 16
    nr_pages, rest = divmod(nr_persons, persons_per_page)
    if rest > 0:
        nr_pages += 1
    pages = []
    for page_nr in range(nr_pages):
        page_data = copy.deepcopy(data)
        persons_in_page = persons[page_nr * persons_per_page:(page_nr + 1) * persons_per_page]
        for i, person in enumerate(persons_in_page):
            nr = i + 1
            page_data['namn%d' % nr] = person.name
            page_data['pa%d' % nr] = person.postal_address
            page_data['ar%d' % nr] = str(person.year)
        pages.append(page_data)

    document = MailMerge('templates/lagerbidragsmall.docx')
    document.merge_pages(pages)

    bytesIO = io.BytesIO()
    document.write(bytesIO)
    resultbytes = bytesIO.getvalue()

    doc_name = "Lagerbidrag_%s_%s_%s.docx" % (bidrag.site, bidrag.dateFrom, bidrag.dateTo)
    ascii_doc_name = doc_name.encode('ascii', 'ignore')

    response = make_response(resultbytes)
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    response.headers['Content-Disposition'] = 'attachment; filename=' + urllib.quote(ascii_doc_name)
    return response


def person_sort(a, b):
    if a.year == b.year:
        if a.name > b.name:
            return 1
        else:
            return -1
    elif a.year > b.year:
        return 1
    else:
        return -1


class LagerBidragContainer:
    bidrag = ""
    nr_young_persons = 0
    nr_older_persons = 0
    nr_under_min_age = 0
    nr_persons_total = 0

    def __init__(self):
        self.persons = []
        self.numbers = []


class LagerPerson():

    def __init__(self, person="", name="", year="", age=0, postal_address=""):
        self.person = person
        self.name = name
        self.year = year
        self.age = age
        self.postal_address = postal_address
        self.days = 0


class LagerBidrag():
    contact = ""
    kar = ""
    account = ""
    dateFrom = ""
    dateTo = ""
    site = ""
    address = ""
    zipCode = ""
    phone = ""
    email = ""
    uptoMaxAge = 0
    overMaxAge = 0
    nights = 0
    days = 0
    divider = 25

    def __init__(self, kar):
        self.kar = kar


def _add_person(person, persons, year, days=None):
    "Create LagerPerson from person and add to persons lists."
    person_ob = person.get()
    postal_address = "%s %s" % (person_ob.zip_code, person_ob.zip_name)
    lager_person = LagerPerson(person, person_ob.getname(), person_ob.birthdate.year, person_ob.getyearsoldthisyear(year), postal_address)
    if days is not None:
        lager_person.days = days
    persons.append(lager_person)


def createLagerbidragGroup(limits, scoutgroup, troops, contactperson, site, from_date, to_date):

    from_date_time = datetime.strptime(from_date + " 00:00", "%Y-%m-%d %H:%M")
    to_date_time = datetime.strptime(to_date + " 23:59", "%Y-%m-%d %H:%M")
    year = to_date_time.year
    persons = []
    person_days = {}

    validateLagetbidragInput(from_date_time, to_date_time, limits)

    for troop in troops:
        # Count number of days participating
        for meeting in Meeting.query(Meeting.datetime >= from_date_time, Meeting.datetime <= to_date_time, Meeting.troop == troop.key).fetch():
            for person in meeting.attendingPersons:
                if not person in person_days:
                    person_days[person] = 1
                else:
                    person_days[person] += 1

    # Collect number of persons
    for person, days in person_days.iteritems():
        _add_person(person, persons, year, days)

    return createLagerbidragReport(limits, scoutgroup, persons, contactperson, site, from_date, to_date)


def createLagerbidrag(limits, scoutgroup, trooppersons, troopkey_key, contactperson, site, from_date, to_date):

    from_date_time = datetime.strptime(from_date + " 00:00", "%Y-%m-%d %H:%M")
    to_date_time = datetime.strptime(to_date + " 23:59", "%Y-%m-%d %H:%M")
    year = to_date_time.year
    persons = []

    validateLagetbidragInput(from_date_time, to_date_time, limits)

    # Collect number of persons
    for troopperson in trooppersons:
        _add_person(troopperson.person, persons, year)

    # Count number of days participating
    for meeting in Meeting.query(Meeting.datetime >= from_date_time, Meeting.datetime <= to_date_time, Meeting.troop == troopkey_key).fetch():
        for person in persons:
            is_attending = person.person in meeting.attendingPersons
            if is_attending:
                person.days += 1

    return createLagerbidragReport(limits, scoutgroup, persons, contactperson, site, from_date, to_date)


def validateLagetbidragInput(from_date_time, to_date_time, limits):
    "Check the number of days compared to limits."
    delta = to_date_time.date() - from_date_time.date()
    nr_days = delta.days + 1  # The 00:00 - 23:59 does not give any extra day
    if nr_days > limits.max_days:
        raise ValueError('Lägret får max vara %d dagar' % limits.max_days)
    if nr_days < limits.min_days:
        raise ValueError('Lägret måsta vara minst %d dagar' % limits.min_days)


def createLagerbidragReport(limits, scoutgroup, persons, contactperson, site, from_date, to_date):
    container = LagerBidragContainer()

    bidrag=LagerBidrag(scoutgroup.getname())
    bidrag.email = scoutgroup.epost
    bidrag.phone = scoutgroup.telefon
    bidrag.address = scoutgroup.adress
    bidrag.zipCode = scoutgroup.postadress
    bidrag.account = scoutgroup.bankkonto
    bidrag.contact = contactperson
    bidrag.site = site
    bidrag.dateFrom = from_date
    bidrag.dateTo = to_date

    container.persons = persons

    # Filter out persons participation at least limits.min_days days
    container.persons = [p for p in container.persons if p.days >= limits.min_days]

    # Sort by number of days to get the persons over limits.max_age with most days first
    container.persons.sort(key=lambda x: x.days, reverse=True)

    # sum number of persons and days for person under max_age
    for person in container.persons:
        if person.age > limits.max_age:
            bidrag.overMaxAge = bidrag.overMaxAge + 1
            container.nr_older_persons += 1
        elif person.age >= limits.min_age:
            bidrag.uptoMaxAge = bidrag.uptoMaxAge + 1
            bidrag.nights += person.days - 1
            bidrag.days += person.days
            container.nr_young_persons += 1
        else:
            container.nr_under_min_age += 1

    if limits.count_over_max_age:
        # Count number of days for person over max_age
        allowed_over_max_age = math.floor(bidrag.uptoMaxAge / 3)
        count_over_max_age = 0
        for person in container.persons:
            if count_over_max_age == allowed_over_max_age:
                break
            if person.age > limits.max_age:
                count_over_max_age += 1
                bidrag.nights += person.days - 1
                bidrag.days += person.days

    container.persons.sort(person_sort)

    number_of_persons = container.nr_young_persons + container.nr_older_persons + container.nr_under_min_age
    assert number_of_persons == len(container.persons)
    container.nr_persons_total = number_of_persons

    # Set up divider to get two columns of data (used by Gbg template)
    tmp_divider = int(math.ceil(number_of_persons / 2.0))
    bidrag.divider = 25 if tmp_divider < 25 else tmp_divider
    # Add empty persons
    container.persons.extend([LagerPerson() for i in range(0, bidrag.divider * 2 - len(container.persons))])
    container.numbers = range(0, bidrag.divider)

    container.bidrag = bidrag
    return container