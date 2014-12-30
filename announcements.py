#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from getpass import getpass
from smtplib import SMTP, SMTPConnectError, SMTPAuthenticationError, SMTPRecipientsRefused
from email.mime.text import MIMEText

mail = 'pychess@gmail.com'
passw = getpass('password: ')
smtp = 'smtp.gmail.com'
to = 'python-announce-list@python.org, pygtk@daa.com.au'
subject = '[ANNOUNCE] PyChess Staunton 0.10'

body = """========================================
Announcement for PyChess Staunton 0.10
========================================

We have had a lot of last minute fixes since the release
candidate. A few of them for bugs that have been around a long time.
In particular there has been a lot of stabilization of CECP and UCI,
so they should now work with an even wider set of engines. You can
even run windows engines through wine.

Another important addition to our project is our new website at
pychess.org. The website has a good introduction to the client and the
community, and in the future it will hopefully be filled with chess
related functionality. Sharing your games online could be a great such
future.

The main new features of the release are still:

* Support for chess variants, PyChess? now allows you to play Fischer
Random with your majors huffled, to play Losers chess with being mated
as your goal, or simply playing odds chess as an additional way of
giving a player a handicap.

* On-line play which has been enhanced with chat support. Besides
chatting with your opponent, the FICS community has several channels,
in which you can discuss chess and varies of other topics.

* The FICS support has also been improved with built-in Timeseal
support. This helps to terminate lag, and is especially helpful in
very fast games, like bullet chess.

* If you prefer to play off-line, PyChess? now lets you choose from
eight different play-strengths. The built in PyChess? engine has as
well been extended 'in both extremes' now making many more human like
mistakes in the easy mode, and playing at more than double strength in
the hard mode, utilizing end game tables.

* UI-wise, PyChess? takes use of a new pure-python docking widget,
which lets you rearrange the sidepanels by wish.

I would really like to thank everyone who have helped to move Staunton
forward to a release, and I hope our next release - PyChess? Anderssen
1.0 - will be out on a slightly shorter cycle.

Please help spread the news of the release to users around the world,
And if you notice that the translation for your language isn't fully
updated, head to Rosetta now, and we'll fix it in the 0.10.1 release.

========================================
About PyChess
========================================

PyChess is a gtk chess client, originally developed for
gnome, but running well under all other linux desktops. (Which we know
of, at least). PyChess is 100% python code, from the top of the UI to
the bottom of the chess engine, and all code is licensed under the Gnu
Public License.

The goal of PyChess is to provide an advanced chess client for linux
following the Gnome Human Interface Guidelines. The client should be
usable to those new to chess, who just want to play a short game and
get back to their work, as well as those who wants to use the computer
to further enhance their play.

Very briefly, the following gives a picture of how far we have come. In
our minds however, we have only finished 10% of the stuff we want.

* Lets you play against lots of chess engines in the CECP and UCI
formats in many different difficulties. The easiest one being very
easy.

* If you like to play against other of the human speices, PyChess
supports online play on the FICS servers.

* Games can be saved in the PGN, EPD and FEN chess fileformats for
later continuation or analysis.

* If you make mistakes or is going for lunch, PyChess lets you undo or
pause the game at any time. However if you play online, you need to
wait for you opponent to accept the offer.

* When you are in lack of inspiration, PyChess offers an opening book
and so called hint- and spy- arrows, which shows you what the computer
would do in your place, and what it would do if you opponent could
move just now.

* Further, PyChess offers a rich and while simple interface, with
sound, animation and Human Interface in the main row.

If you would like help fix the translation of PyChess in your
language, see http://code.google.com/p/pychess/wiki/RosettaTranslates
to get started.

Thanks, PyChess team

Homepage: http://pychess.org
Downloads: http://pychess.org/downloads
Screenshots: http://pychess.org/about
Project page: http://code.google.com/p/pychess
Bug list: http://code.google.com/p/pychess/issues/list
Mailing list: http://groups.google.com/group/pychess-people
"""

if __name__ == '__main__':
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = mail
    msg['To'] = to
    try:
        server = SMTP(smtp)
    except SMTPConnectError as ex:
        print('\n%s'%ex)
    print('\nConnecting to Gmail account...')
    try:
        server.login(mail, passw)
    except SMTPAuthenticationError as ex:
        print('\n%s'%ex)
    print('Sending message...')
    try:
        server.sendmail(mail, to, msg.as_string())
    except SMTPRecipientsRefused as ex:
        print('\n%s'%ex)
    print('Email send ok.')
    server.quit()
