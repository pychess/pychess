# -*- coding: UTF-8 -*-

import sys
from operator import attrgetter
from itertools import groupby

from gi.repository import Gtk

from pychess.Utils.const import WHITE, BLACK, RANDOMCHESS, \
    FISCHERRANDOMCHESS, LOSERSCHESS, UNSUPPORTED, VARIANTS_SHUFFLE, VARIANTS_OTHER, \
    VARIANTS_OTHER_NONSTANDARD

from pychess.ic import GAME_TYPES, VARIANT_GAME_TYPES, TYPE_BLITZ, TYPE_LIGHTNING, \
    TYPE_STANDARD, VariantGameType, time_control_to_gametype

from pychess.ic.FICSObjects import FICSPlayer, get_rating_range_display_text
from pychess.System import conf, uistuff
from pychess.System.prefix import addDataPrefix
from pychess.widgets import mainwindow
from pychess.widgets.ChainVBox import ChainVBox
from pychess.Variants import variants


RATING_SLIDER_STEP = 25


class SeekChallengeSection():

    seekEditorWidgets = (
        "untimedCheck",
        "minutesSpin",
        "gainSpin",
        "strengthCheck",
        "chainAlignment",
        "ratingCenterSlider",
        "toleranceSlider",
        "toleranceHBox",
        "nocolorRadio",
        "whitecolorRadio",
        "blackcolorRadio",
        # variantCombo has to come before other variant widgets so that
        # when the widget is loaded, variantRadio isn't selected by the callback,
        # overwriting the user's saved value for the variant radio buttons
        "variantCombo",
        "noVariantRadio",
        "variantRadio",
        "ratedGameCheck",
        "manualAcceptCheck")

    seekEditorWidgetDefaults = {
        "untimedCheck": [False, False, False],
        "minutesSpin": [15, 10, 2],
        "gainSpin": [10, 0, 12],
        "strengthCheck": [True, True, True],
        "chainAlignment": [True, True, True],
        "ratingCenterSlider": [40, 40, 40],
        "toleranceSlider": [8, 8, 8],
        "toleranceHBox": [False, False, False],
        "variantCombo": [RANDOMCHESS, FISCHERRANDOMCHESS, LOSERSCHESS],
        "noVariantRadio": [True, True, True],
        "variantRadio": [False, False, False],
        "nocolorRadio": [True, True, True],
        "whitecolorRadio": [False, False, False],
        "blackcolorRadio": [False, False, False],
        "ratedGameCheck": [False, False, False],
        "manualAcceptCheck": [False, False, False],
    }

    seekEditorWidgetGettersSetters = {}

    def __init__(self, lounge):
        self.lounge = lounge
        self.widgets = lounge.widgets
        self.connection = lounge.connection

        self.widgets["editSeekDialog"].set_transient_for(mainwindow())
        self.widgets["challengeDialog"].set_transient_for(mainwindow())

        self.finger = None
        conf.set("numberOfFingers", 0)
        self.connection.fm.connect("fingeringFinished", self.onFinger)
        self.connection.fm.finger(self.connection.getUsername())

        self.widgets["untimedCheck"].connect("toggled",
                                             self.onUntimedCheckToggled)
        self.widgets["minutesSpin"].connect("value-changed",
                                            self.onTimeSpinChanged)
        self.widgets["gainSpin"].connect("value-changed",
                                         self.onTimeSpinChanged)
        self.onTimeSpinChanged(self.widgets["minutesSpin"])

        self.widgets["nocolorRadio"].connect("toggled",
                                             self.onColorRadioChanged)
        self.widgets["whitecolorRadio"].connect("toggled",
                                                self.onColorRadioChanged)
        self.widgets["blackcolorRadio"].connect("toggled",
                                                self.onColorRadioChanged)
        self.onColorRadioChanged(self.widgets["nocolorRadio"])

        self.widgets["noVariantRadio"].connect("toggled",
                                               self.onVariantRadioChanged)
        self.widgets["variantRadio"].connect("toggled",
                                             self.onVariantRadioChanged)
        variantcombo = self.widgets["variantCombo"]
        variantcombo.set_name("variantcombo")
        variantComboGetter, variantComboSetter = self.__initVariantCombo(
            variantcombo)
        self.seekEditorWidgetGettersSetters["variantCombo"] = (
            variantComboGetter, variantComboSetter)
        self.widgets["variantCombo"].connect("changed",
                                             self.onVariantComboChanged)

        self.widgets["editSeekDialog"].connect("delete_event", lambda *a: True)
        #        self.widgets["challengeDialog"].connect("delete_event", lambda *a: True)

        self.widgets["strengthCheck"].connect("toggled",
                                              self.onStrengthCheckToggled)
        self.onStrengthCheckToggled(self.widgets["strengthCheck"])
        self.widgets["ratingCenterSlider"].connect(
            "value-changed", self.onRatingCenterSliderChanged)
        self.onRatingCenterSliderChanged(self.widgets["ratingCenterSlider"])
        self.widgets["toleranceSlider"].connect("value-changed",
                                                self.onToleranceSliderChanged)
        self.onToleranceSliderChanged(self.widgets["toleranceSlider"])
        self.widgets["toleranceButton"].connect("clicked",
                                                self.onToleranceButtonClicked)
        self.widgets["toleranceButton"].connect("activate-link",
                                                lambda link_button: True)

        def intGetter(widget):
            return int(widget.get_value())

        self.seekEditorWidgetGettersSetters["minutesSpin"] = (intGetter, None)
        self.seekEditorWidgetGettersSetters["gainSpin"] = (intGetter, None)
        self.seekEditorWidgetGettersSetters["ratingCenterSlider"] = \
            (intGetter, None)
        self.seekEditorWidgetGettersSetters["toleranceSlider"] = \
            (intGetter, None)

        def toleranceHBoxGetter(widget):
            return self.widgets["toleranceHBox"].get_property("visible")

        def toleranceHBoxSetter(widget, visible):
            assert isinstance(visible, bool)
            if visible:
                self.widgets["toleranceHBox"].show()
            else:
                self.widgets["toleranceHBox"].hide()

        self.seekEditorWidgetGettersSetters["toleranceHBox"] = (
            toleranceHBoxGetter, toleranceHBoxSetter)

        self.chainbox = ChainVBox()
        self.widgets["chainAlignment"].add(self.chainbox)

        def chainboxGetter(widget):
            return self.chainbox.active

        def chainboxSetter(widget, is_active):
            self.chainbox.active = is_active

        self.seekEditorWidgetGettersSetters["chainAlignment"] = (
            chainboxGetter, chainboxSetter)

        self.challengee = None
        self.in_challenge_mode = False
        self.seeknumber = 1
        self.widgets["seekButton"].connect("clicked", self.onSeekButtonClicked)
        self.widgets["seekAllButton"].connect("clicked",
                                              self.onSeekAllButtonClicked)
        self.widgets["challengeButton"].connect("clicked",
                                                self.onChallengeButtonClicked)
        self.widgets["challengeDialog"].connect("delete-event",
                                                self.onChallengeDialogResponse)
        self.widgets["challengeDialog"].connect("response",
                                                self.onChallengeDialogResponse)
        self.widgets["editSeekDialog"].connect("response",
                                               self.onEditSeekDialogResponse)

        for widget in ("seek1Radio", "seek2Radio", "seek3Radio",
                       "challenge1Radio", "challenge2Radio",
                       "challenge3Radio"):
            uistuff.keep(self.widgets[widget], widget)

        self.lastdifference = 0
        self.loading_seek_editor = False
        self.savedSeekRadioTexts = [GAME_TYPES["blitz"].display_text] * 3

        for i in range(1, 4):
            self.__loadSeekEditor(i)
            self.__writeSavedSeeks(i)
            self.widgets["seek%sRadioConfigButton" % i].connect(
                "clicked", self.onSeekRadioConfigButtonClicked, i)
            self.widgets["challenge%sRadioConfigButton" % i].connect(
                "clicked", self.onChallengeRadioConfigButtonClicked, i)

        if not self.connection.isRegistred():
            self.chainbox.active = False
            self.widgets["chainAlignment"].set_sensitive(False)
            self.widgets["chainAlignment"].set_tooltip_text(_(
                "The chain button is disabled because you are logged in as a guest. Guests \
                can't establish ratings, and the chain button's state has no effect when \
                there is no rating to which to tie \"Opponent Strength\" to"))

    def onSeekButtonClicked(self, button):
        if self.widgets["seek3Radio"].get_active():
            self.__loadSeekEditor(3)
        elif self.widgets["seek2Radio"].get_active():
            self.__loadSeekEditor(2)
        else:
            self.__loadSeekEditor(1)

        minutes, incr, gametype, ratingrange, color, rated, manual = \
            self.__getSeekEditorDialogValues()
        self.connection.glm.seek(minutes, incr, gametype, rated, ratingrange,
                                 color, manual)

    def onSeekAllButtonClicked(self, button):
        for i in range(1, 4):
            self.__loadSeekEditor(i)
            minutes, incr, gametype, ratingrange, color, rated, manual = \
                self.__getSeekEditorDialogValues()
            self.connection.glm.seek(minutes, incr, gametype, rated, ratingrange,
                                     color, manual)

    def onChallengeButtonClicked(self, button, player=None):
        if player is None:
            player = self.lounge.players_tab.getSelectedPlayer()
            if player is None:
                return
        self.challengee = player
        self.in_challenge_mode = True

        for i in range(1, 4):
            self.__loadSeekEditor(i)
            self.__writeSavedSeeks(i)
        self.__updateRatedGameCheck()
        if self.widgets["seek3Radio"].get_active():
            seeknumber = 3
        elif self.widgets["seek2Radio"].get_active():
            seeknumber = 2
        else:
            seeknumber = 1
        self.__updateSeekEditor(seeknumber, challengemode=True)

        self.widgets["challengeeNameLabel"].set_markup(player.getMarkup())
        self.widgets["challengeeImage"].set_from_pixbuf(
            player.getIcon(size=32))
        title = _("Challenge: ") + player.name
        self.widgets["challengeDialog"].set_title(title)
        self.widgets["challengeDialog"].present()

    def onChallengeDialogResponse(self, dialog, response):
        self.widgets["challengeDialog"].hide()
        if response != 5:
            return True

        if self.widgets["challenge3Radio"].get_active():
            self.__loadSeekEditor(3)
        elif self.widgets["challenge2Radio"].get_active():
            self.__loadSeekEditor(2)
        else:
            self.__loadSeekEditor(1)
        minutes, incr, gametype, ratingrange, color, rated, manual = \
            self.__getSeekEditorDialogValues()
        self.connection.om.challenge(self.challengee.name, gametype, minutes, incr,
                                     rated, color)

    def onSeekRadioConfigButtonClicked(self, configimage, seeknumber):
        self.__showSeekEditor(seeknumber)

    def onChallengeRadioConfigButtonClicked(self, configimage, seeknumber):
        self.__showSeekEditor(seeknumber, challengemode=True)

    def onEditSeekDialogResponse(self, dialog, response):
        self.widgets["editSeekDialog"].hide()
        if response != Gtk.ResponseType.OK:
            return
        self.__saveSeekEditor(self.seeknumber)
        self.__writeSavedSeeks(self.seeknumber)

    def __updateSeekEditor(self, seeknumber, challengemode=False):
        self.in_challenge_mode = challengemode
        self.seeknumber = seeknumber
        if not challengemode:
            self.widgets["strengthFrame"].set_sensitive(True)
            self.widgets["strengthFrame"].set_tooltip_text("")
            self.widgets["manualAcceptCheck"].set_sensitive(True)
            self.widgets["manualAcceptCheck"].set_tooltip_text(_(
                "If set you can refuse players accepting your seek"))
        else:
            self.widgets["strengthFrame"].set_sensitive(False)
            self.widgets["strengthFrame"].set_tooltip_text(_(
                "This option is not applicable because you're challenging a player"))
            self.widgets["manualAcceptCheck"].set_sensitive(False)
            self.widgets["manualAcceptCheck"].set_tooltip_text(_(
                "This option is not applicable because you're challenging a player"))

        self.widgets["chainAlignment"].show_all()
        self.__loadSeekEditor(seeknumber)
        self.widgets["seek%dRadio" % seeknumber].set_active(True)
        self.widgets["challenge%dRadio" % seeknumber].set_active(True)

        self.__updateYourRatingHBox()
        self.__updateRatingCenterInfoBox()
        self.__updateToleranceButton()
        self.__updateRatedGameCheck()
        self.onUntimedCheckToggled(self.widgets["untimedCheck"])

        title = _("Edit Seek: ") + self.widgets["seek%dRadio" %
                                                seeknumber].get_label()[:-1]
        self.widgets["editSeekDialog"].set_title(title)

    def __showSeekEditor(self, seeknumber, challengemode=False):
        self.__updateSeekEditor(seeknumber, challengemode)
        self.widgets["editSeekDialog"].present()

        # ugly hack to fix https://github.com/pychess/pychess/issues/1024
        # self.widgets["editSeekDialog"].queue_draw() doesn't work
        if sys.platform == "win32":
            self.widgets["editSeekDialog"].hide()
            allocation = self.widgets["editSeekDialog"].get_allocation()
            self.widgets["editSeekDialog"].set_size_request(allocation.width,
                                                            allocation.height)
            self.widgets["editSeekDialog"].show()

    # -------------------------------------------------------- Seek Editor

    def __writeSavedSeeks(self, seeknumber):
        """ Writes saved seek strings for both the Seek Panel and the Challenge Panel """
        minutes, gain, gametype, ratingrange, color, rated, manual = \
            self.__getSeekEditorDialogValues()
        self.savedSeekRadioTexts[seeknumber - 1] = \
            time_control_to_gametype(minutes, gain).display_text
        self.__writeSeekRadioLabels()
        seek = {}

        if gametype == GAME_TYPES["untimed"]:
            seek["time"] = gametype.display_text
        elif gain > 0:
            seek["time"] = _("%(minutes)d min + %(gain)d sec/move") % \
                {'minutes': minutes, 'gain': gain}
        else:
            seek["time"] = _("%d min") % minutes

        if isinstance(gametype, VariantGameType):
            seek["variant"] = "%s" % gametype.display_text

        rrtext = get_rating_range_display_text(ratingrange[0], ratingrange[1])
        if rrtext:
            seek["rating"] = rrtext

        if color == WHITE:
            seek["color"] = _("White")
        elif color == BLACK:
            seek["color"] = _("Black")

        if rated and gametype is not GAME_TYPES["untimed"]:
            seek["rated"] = _("Rated")

        if manual:
            seek["manual"] = _("Manual")

        seek_ = []
        challenge = []
        challengee_is_guest = self.challengee and self.challengee.isGuest()
        for key in ("time", "variant", "rating", "color", "rated", "manual"):
            if key in seek:
                seek_.append(seek[key])
                if key in ("time", "variant", "color") or \
                        (key == "rated" and not challengee_is_guest):
                    challenge.append(seek[key])
        seektext = ", ".join(seek_)
        challengetext = ", ".join(challenge)

        if seeknumber == 1:
            self.widgets["seek1RadioLabel"].set_text(seektext)
            self.widgets["challenge1RadioLabel"].set_text(challengetext)
        elif seeknumber == 2:
            self.widgets["seek2RadioLabel"].set_text(seektext)
            self.widgets["challenge2RadioLabel"].set_text(challengetext)
        else:
            self.widgets["seek3RadioLabel"].set_text(seektext)
            self.widgets["challenge3RadioLabel"].set_text(challengetext)

    def __loadSeekEditor(self, seeknumber):
        self.loading_seek_editor = True
        for widget in self.seekEditorWidgets:
            if widget in self.seekEditorWidgetGettersSetters:
                uistuff.loadDialogWidget(
                    self.widgets[widget],
                    widget,
                    seeknumber,
                    get_value_=self.seekEditorWidgetGettersSetters[widget][0],
                    set_value_=self.seekEditorWidgetGettersSetters[widget][1],
                    first_value=self.seekEditorWidgetDefaults[widget][
                        seeknumber - 1])
            elif widget in self.seekEditorWidgetDefaults:
                uistuff.loadDialogWidget(
                    self.widgets[widget],
                    widget,
                    seeknumber,
                    first_value=self.seekEditorWidgetDefaults[widget][
                        seeknumber - 1])
            else:
                uistuff.loadDialogWidget(self.widgets[widget], widget,
                                         seeknumber)

        self.lastdifference = conf.get("lastdifference-%d" % seeknumber)
        self.loading_seek_editor = False

    def __saveSeekEditor(self, seeknumber):
        for widget in self.seekEditorWidgets:
            if widget in self.seekEditorWidgetGettersSetters:
                uistuff.saveDialogWidget(
                    self.widgets[widget],
                    widget,
                    seeknumber,
                    get_value_=self.seekEditorWidgetGettersSetters[widget][0])
            else:
                uistuff.saveDialogWidget(self.widgets[widget], widget,
                                         seeknumber)

        conf.set("lastdifference-%d" % seeknumber, self.lastdifference)

    def __getSeekEditorDialogValues(self):
        if self.widgets["untimedCheck"].get_active():
            minutes = 0
            incr = 0
        else:
            minutes = int(self.widgets["minutesSpin"].get_value())
            incr = int(self.widgets["gainSpin"].get_value())

        if self.widgets["strengthCheck"].get_active():
            ratingrange = [0, 9999]
        else:
            center = int(self.widgets["ratingCenterSlider"].get_value(
            )) * RATING_SLIDER_STEP
            tolerance = int(self.widgets["toleranceSlider"].get_value(
            )) * RATING_SLIDER_STEP
            minrating = center - tolerance
            minrating = minrating > 0 and minrating or 0
            maxrating = center + tolerance
            maxrating = maxrating >= 3000 and 9999 or maxrating
            ratingrange = [minrating, maxrating]

        if self.widgets["nocolorRadio"].get_active():
            color = None
        elif self.widgets["whitecolorRadio"].get_active():
            color = WHITE
        else:
            color = BLACK

        if self.widgets["noVariantRadio"].get_active() or \
           self.widgets["untimedCheck"].get_active():
            gametype = time_control_to_gametype(minutes, incr)
        else:
            variant_combo_getter = self.seekEditorWidgetGettersSetters[
                "variantCombo"][0]
            variant = variant_combo_getter(self.widgets["variantCombo"])
            gametype = VARIANT_GAME_TYPES[variant]

        rated = self.widgets["ratedGameCheck"].get_active() and not \
            self.widgets["untimedCheck"].get_active()
        manual = self.widgets["manualAcceptCheck"].get_active()

        return minutes, incr, gametype, ratingrange, color, rated, manual

    def __writeSeekRadioLabels(self):
        gameTypes = {_("Untimed"): [0, 1],
                     _("Standard"): [0, 1],
                     _("Blitz"): [0, 1],
                     _("Lightning"): [0, 1]}

        for i in range(3):
            gameTypes[self.savedSeekRadioTexts[i]][0] += 1
        for i in range(3):
            if gameTypes[self.savedSeekRadioTexts[i]][0] > 1:
                labelText = "%s #%d:" % \
                    (self.savedSeekRadioTexts[i], gameTypes[
                     self.savedSeekRadioTexts[i]][1])
                self.widgets["seek%dRadio" % (i + 1)].set_label(labelText)
                self.widgets["challenge%dRadio" % (i + 1)].set_label(labelText)
                gameTypes[self.savedSeekRadioTexts[i]][1] += 1
            else:
                self.widgets["seek%dRadio" % (
                    i + 1)].set_label(self.savedSeekRadioTexts[i] + ":")
                self.widgets["challenge%dRadio" % (
                    i + 1)].set_label(self.savedSeekRadioTexts[i] + ":")

    def __updateRatingRangeBox(self):
        center = int(self.widgets["ratingCenterSlider"].get_value(
        )) * RATING_SLIDER_STEP
        tolerance = int(self.widgets["toleranceSlider"].get_value(
        )) * RATING_SLIDER_STEP
        min_rating = center - tolerance
        min_rating = min_rating > 0 and min_rating or 0
        max_rating = center + tolerance
        max_rating = max_rating >= 3000 and 9999 or max_rating

        self.widgets["ratingRangeMinLabel"].set_label("%d" % min_rating)
        self.widgets["ratingRangeMaxLabel"].set_label("%d" % max_rating)

        for widgetName, rating in (("ratingRangeMinImage", min_rating),
                                   ("ratingRangeMaxImage", max_rating)):
            pixbuf = FICSPlayer.getIconByRating(rating)
            self.widgets[widgetName].set_from_pixbuf(pixbuf)

        self.widgets["ratingRangeMinImage"].show()
        self.widgets["ratingRangeMinLabel"].show()
        self.widgets["dashLabel"].show()
        self.widgets["ratingRangeMaxImage"].show()
        self.widgets["ratingRangeMaxLabel"].show()
        if min_rating == 0:
            self.widgets["ratingRangeMinImage"].hide()
            self.widgets["ratingRangeMinLabel"].hide()
            self.widgets["dashLabel"].hide()
            self.widgets["ratingRangeMaxLabel"].set_label("%d↓" % max_rating)
        if max_rating == 9999:
            self.widgets["ratingRangeMaxImage"].hide()
            self.widgets["ratingRangeMaxLabel"].hide()
            self.widgets["dashLabel"].hide()
            self.widgets["ratingRangeMinLabel"].set_label("%d↑" % min_rating)
        if min_rating == 0 and max_rating == 9999:
            self.widgets["ratingRangeMinLabel"].set_label(_("Any strength"))
            self.widgets["ratingRangeMinLabel"].show()

    def __getGameType(self):
        if self.widgets["untimedCheck"].get_active():
            gametype = GAME_TYPES["untimed"]
        elif self.widgets["noVariantRadio"].get_active():
            minutes = int(self.widgets["minutesSpin"].get_value())
            gain = int(self.widgets["gainSpin"].get_value())
            gametype = time_control_to_gametype(minutes, gain)
        else:
            variant_combo_getter = self.seekEditorWidgetGettersSetters[
                "variantCombo"][0]
            variant = variant_combo_getter(self.widgets["variantCombo"])
            gametype = VARIANT_GAME_TYPES[variant]
        return gametype

    def __updateYourRatingHBox(self):
        gametype = self.__getGameType()
        self.widgets["yourRatingNameLabel"].set_label(
            "(" + gametype.display_text + ")")
        rating = self.__getRating(gametype.rating_type)
        if rating is None:
            self.widgets["yourRatingImage"].clear()
            self.widgets["yourRatingLabel"].set_label(_("Unrated"))
            return
        pixbuf = FICSPlayer.getIconByRating(rating)
        self.widgets["yourRatingImage"].set_from_pixbuf(pixbuf)
        self.widgets["yourRatingLabel"].set_label(str(rating))

        center = int(self.widgets["ratingCenterSlider"].get_value(
        )) * RATING_SLIDER_STEP
        rating = self.__clamp(rating)
        difference = rating - center
        if self.loading_seek_editor is False and self.chainbox.active and \
                difference != self.lastdifference:
            newcenter = rating - self.lastdifference
            self.widgets["ratingCenterSlider"].set_value(newcenter //
                                                         RATING_SLIDER_STEP)
        else:
            self.lastdifference = difference

    def __clamp(self, rating):
        assert isinstance(rating, int)
        mod = rating % RATING_SLIDER_STEP
        if mod > RATING_SLIDER_STEP // 2:
            return rating - mod + RATING_SLIDER_STEP
        else:
            return rating - mod

    def __updateRatedGameCheck(self):
        # on FICS, untimed games can't be rated, nor can games against a guest
        if not self.connection.isRegistred():
            self.widgets["ratedGameCheck"].set_active(False)
            sensitive = False
            self.widgets["ratedGameCheck"].set_tooltip_text(_(
                "You can't play rated games because you are logged in as a guest"))
        elif self.widgets["untimedCheck"].get_active():
            sensitive = False
            self.widgets["ratedGameCheck"].set_tooltip_text(
                _("You can't play rated games because \"Untimed\" is checked, ") +
                _("and on FICS, untimed games can't be rated"))
        elif self.in_challenge_mode and self.challengee.isGuest():
            sensitive = False
            self.widgets["ratedGameCheck"].set_tooltip_text(
                _("This option is not available because you're challenging a guest, ") +
                _("and guests can't play rated games"))
        else:
            sensitive = True
            self.widgets["ratedGameCheck"].set_tooltip_text("")
        self.widgets["ratedGameCheck"].set_sensitive(sensitive)

    def __initVariantCombo(self, combo):
        model = Gtk.TreeStore(str)
        cellRenderer = Gtk.CellRendererText()
        combo.clear()
        combo.pack_start(cellRenderer, True)
        combo.add_attribute(cellRenderer, 'text', 0)
        combo.set_model(model)

        groupNames = {VARIANTS_SHUFFLE: _("Shuffle"),
                      VARIANTS_OTHER: _("Other (standard rules)"),
                      VARIANTS_OTHER_NONSTANDARD:
                      _("Other (non standard rules)"), }
        ficsvariants = [
            v
            for k, v in variants.items()
            if k in VARIANT_GAME_TYPES and v.variant not in UNSUPPORTED
        ]
        groups = groupby(ficsvariants, attrgetter("variant_group"))
        pathToVariant = {}
        variantToPath = {}
        for i, (id, group) in enumerate(groups):
            sel_iter = model.append(None, (groupNames[id], ))
            for variant in group:
                subiter = model.append(sel_iter, (variant.name, ))
                path = model.get_path(subiter)
                path = path.to_string()
                pathToVariant[path] = variant.variant
                variantToPath[variant.variant] = path

        # this stops group names (eg "Shuffle") from being displayed in
        # submenus
        def cellFunc(combo, cell, model, sel_iter, data):
            isChildNode = not model.iter_has_child(sel_iter)
            cell.set_property("sensitive", isChildNode)

        combo.set_cell_data_func(cellRenderer, cellFunc, None)

        def comboGetter(combo):
            path = model.get_path(combo.get_active_iter())
            path = path.to_string()
            return pathToVariant[path]

        def comboSetter(combo, variant):
            if variant not in VARIANT_GAME_TYPES:
                variant = LOSERSCHESS
            combo.set_active_iter(model.get_iter(variantToPath[variant]))

        return comboGetter, comboSetter

    def __getRating(self, gametype):
        if self.finger is None:
            return None
        try:
            rating = self.finger.getRating(type=gametype)
        except KeyError:  # the user doesn't have a rating for this game type
            rating = None
        return rating

    def onFinger(self, fm, finger):
        if not finger.getName() == self.connection.getUsername():
            return
        self.finger = finger

        numfingers = conf.get("numberOfFingers") + 1
        conf.set("numberOfFingers", numfingers)
        if conf.get("numberOfTimesLoggedInAsRegisteredUser") == 1 and numfingers == 1:
            standard = self.__getRating(TYPE_STANDARD)
            blitz = self.__getRating(TYPE_BLITZ)
            lightning = self.__getRating(TYPE_LIGHTNING)

            if standard is not None:
                self.seekEditorWidgetDefaults["ratingCenterSlider"][
                    0] = standard // RATING_SLIDER_STEP
            elif blitz is not None:
                self.seekEditorWidgetDefaults["ratingCenterSlider"][
                    0] = blitz // RATING_SLIDER_STEP
            if blitz is not None:
                self.seekEditorWidgetDefaults["ratingCenterSlider"][
                    1] = blitz // RATING_SLIDER_STEP
            if lightning is not None:
                self.seekEditorWidgetDefaults["ratingCenterSlider"][
                    2] = lightning // RATING_SLIDER_STEP
            elif blitz is not None:
                self.seekEditorWidgetDefaults["ratingCenterSlider"][
                    2] = blitz // RATING_SLIDER_STEP

            for i in range(1, 4):
                self.__loadSeekEditor(i)
                self.__updateSeekEditor(i)
                self.__saveSeekEditor(i)
                self.__writeSavedSeeks(i)

        self.__updateYourRatingHBox()

    def onTimeSpinChanged(self, spin):
        minutes = self.widgets["minutesSpin"].get_value_as_int()
        gain = self.widgets["gainSpin"].get_value_as_int()
        name = time_control_to_gametype(minutes, gain).display_text
        self.widgets["timeControlNameLabel"].set_label("%s" % name)
        self.__updateYourRatingHBox()

    def onUntimedCheckToggled(self, check):
        is_untimed_game = check.get_active()
        self.widgets["timeControlConfigVBox"].set_sensitive(
            not is_untimed_game)
        # on FICS, untimed games can't be rated and can't be a chess variant
        self.widgets["variantFrame"].set_sensitive(not is_untimed_game)
        if is_untimed_game:
            self.widgets["variantFrame"].set_tooltip_text(
                _("You can't select a variant because \"Untimed\" is checked, ") +
                _("and on FICS, untimed games have to be normal chess rules"))
        else:
            self.widgets["variantFrame"].set_tooltip_text("")
        self.__updateRatedGameCheck(
        )  # sets sensitivity of widgets["ratedGameCheck"]
        self.__updateYourRatingHBox()

    def onStrengthCheckToggled(self, check):
        strengthsensitive = not check.get_active()
        self.widgets["strengthConfigVBox"].set_sensitive(strengthsensitive)

    def onRatingCenterSliderChanged(self, slider):
        center = int(self.widgets["ratingCenterSlider"].get_value(
        )) * RATING_SLIDER_STEP
        pixbuf = FICSPlayer.getIconByRating(center)
        self.widgets["ratingCenterLabel"].set_label("%d" % (center))
        self.widgets["ratingCenterImage"].set_from_pixbuf(pixbuf)
        self.__updateRatingRangeBox()

        rating = self.__getRating(self.__getGameType().rating_type)
        if rating is None:
            return
        rating = self.__clamp(rating)
        self.lastdifference = rating - center

    def __updateRatingCenterInfoBox(self):
        if self.widgets["toleranceHBox"].get_property("visible") is True:
            self.widgets["ratingCenterInfoHBox"].show()
        else:
            self.widgets["ratingCenterInfoHBox"].hide()

    def __updateToleranceButton(self):
        if self.widgets["toleranceHBox"].get_property("visible") is True:
            self.widgets["toleranceButton"].set_property("label", _("Hide"))
        else:
            self.widgets["toleranceButton"].set_property("label",
                                                         _("Change Tolerance"))

    def onToleranceButtonClicked(self, button):
        if self.widgets["toleranceHBox"].get_property("visible") is True:
            self.widgets["toleranceHBox"].hide()
        else:
            self.widgets["toleranceHBox"].show()
        self.__updateToleranceButton()
        self.__updateRatingCenterInfoBox()

    def onToleranceSliderChanged(self, slider):
        tolerance = int(self.widgets["toleranceSlider"].get_value(
        )) * RATING_SLIDER_STEP
        self.widgets["toleranceLabel"].set_label("±%d" % tolerance)
        self.__updateRatingRangeBox()

    def onColorRadioChanged(self, radio):
        if self.widgets["nocolorRadio"].get_active():
            self.widgets["colorImage"].set_from_file(addDataPrefix(
                "glade/piece-unknown.png"))
            self.widgets["colorImage"].set_sensitive(False)
        elif self.widgets["whitecolorRadio"].get_active():
            self.widgets["colorImage"].set_from_file(addDataPrefix(
                "glade/piece-white.png"))
            self.widgets["colorImage"].set_sensitive(True)
        elif self.widgets["blackcolorRadio"].get_active():
            self.widgets["colorImage"].set_from_file(addDataPrefix(
                "glade/piece-black.png"))
            self.widgets["colorImage"].set_sensitive(True)

    def onVariantRadioChanged(self, radio):
        self.__updateYourRatingHBox()

    def onVariantComboChanged(self, combo):
        self.widgets["variantRadio"].set_active(True)
        self.__updateYourRatingHBox()
        min, gain, gametype, ratingrange, color, rated, manual = \
            self.__getSeekEditorDialogValues()
        self.widgets["variantCombo"].set_tooltip_text(variants[
            gametype.variant_type].__desc__)
