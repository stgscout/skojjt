# DataModellen i Skojjt

Använder Google Appenging ndb.
KeyProperty används för att binda ihop datatyperna.
En del KeyProperties är redundanta, så de är inte med i sammanställningen nedan

De huvudsakliga klasserna är

* ScoutGroup = Kår. Har inga KeyPropertiees
* Person = person i Scoutnet för viss kår. KeyProperty: ScoutGroup
* Troop = Avdelning för en viss termin och kår, KeyProperties: Semester (termin) och ScoutGroup (kår)
* TroopPerson - person som tillhör en avdelning (en viss termin), KeyProperties: Troop, Person
* Meeting - möte/lägerdag för en avdelning och en lista med personer, KeyProperties: Troop, lista av personer

Till detta kommer klasser för Märken (Badges).
Specas i data_badge.py

* Badge = Märke. Kårspecifikt märke/certifikat. KeyProperty: ScoutGroup, lista av BadgePart
* BadgePart = Märkesdel. KeyProperties: Badge
* BadgePartDone - detaljer av godkänd del. KeyProperties: Person, BadgePart
* TroopBadges = Lista av märken för avdelning(och termin): KeyProperties: Troop, List of Badge
* BadgeProgress = Märkesprogress för en person. KeyProperties: Badge, Person, List of BadgePartDone


Hur göra tabeller av relevanta data:

1. Kårnivå lista:
    Sök alla Badge med keyProperty=Scoutgroup
    Lista namn och ikon (om finnes)
2. Lista på märkesdelar på kårnivå
    För ett visst märke, sök efter alla BadgePart med nycker Badge och sortera efter idx
3. På avdelingsnivå per termin
    Sök på TroopBadges med troop som nyckel
4. För listning av progress för avdelning och märke
   För rubriker, sök på märkesdelar för märke
   För personrad, sök på BadgeProgress med nycklar badge och person -> badgeprogress
   badgeprogress -> registered, awarded, list of BadgepartDone
   För varje märkesdel, kolla om den finns i badgepartdone.

   Ta bort märke:

   1. lista all badgepart key Badge
   2. ta bort all badgeprogress för key badge
   För varje badge_part
   3. ta bort all badgepartdone för key badge_part
   4. ta bort all badgepart
   5. för varje troop, lista badge och ta bort om används
   6. ta bort badge på kårnivå

   Ta bort person:
   * Sök alla BadgePartDone på person och ta bort
   * Sök all BadgeProgress på person och ta bort
