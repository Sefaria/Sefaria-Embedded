# -*- coding: utf-8 -*-
alef_bet = [
  ("א", 1),
    ("ב", 2),
    ("ג", 3),
    ("ד", 4),
    ("ה", 5),
    ("ו", 6),
    ("ז", 7),
    ("ח", 8),
    ("ט", 9),
    ("י", 10),
    ("כ", 20),
    ("ל", 30),
    ("מ", 40),
    ("נ", 50),
    ("ס", 60),
    ("ע", 70),
    ("פ", 80),
    ("צ", 90),
    ("ק", 100),
    ("ר", 200),
    ("ש", 300),
    ("ת", 400),
]

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

def getGematriyaOfNumber(n):
    return getNextLetter(10, n, "")