# -*- coding: utf-8 -*-
alef_bet = [
  (u"א", 1),
    (u"ב", 2),
    (u"ג", 3),
    (u"ד", 4),
    (u"ה", 5),
    (u"ו", 6),
    (u"ז", 7),
    (u"ח", 8),
    (u"ט", 9),
    (u"י", 10),
    (u"כ", 20),
    (u"ל", 30),
    (u"מ", 40),
    (u"נ", 50),
    (u"ס", 60),
    (u"ע", 70),
    (u"פ", 80),
    (u"צ", 90),
    (u"ק", 100),
    (u"ר", 200),
    (u"ש", 300),
    (u"ת", 400),
]

# alef_bet = [
#     ("\u05D0", 1),
#     ("\u05D1", 2),
#     ("\u05D2", 3),
#     ("\u05D3", 4),
#     ("\u05D4", 5),
#     ("\u05D5", 6),
#     ("\u05D6", 7),
#     ("\u05D7", 8),
#     ("\u05D8", 9),
#     ("\u05D9", 10),
#     ("\u05DB", 20),
#     ("\u05DC", 30),
#     ("\u05DE", 40),
#     ("\u05E0", 50),
#     ("\u05E1", 60),
#     ("\u05E2", 70),
#     ("\u05E4", 80),
#     ("\u05E6", 90),
#     ("\u05E7", 100),
#     ("\u05E8", 200),
#     ("\u05E9", 300),
#     ("\u05EA", 400),
# ]

def getNextLetter(depth, m, a):
    for tup in reversed(alef_bet):
        if m >= tup[1]:
            a+= tup[0]
            m-= tup[1]
            depth += 1
            break
    if m <= 0:
      return a
    # if depth >= 10:
      # Maybe throw an error that the requested gematriya
      # is impractically long
    return getNextLetter(depth, m, a)

def sanitize(gematriya):
    return gematriya.replace(u"יה", u"טו").replace(u"יו", u"טז")

def getGematriyaOfNumber(n):
    return sanitize(getNextLetter(10, n, ""))
