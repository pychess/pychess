
import os
import re
import tempfile

import cairo
from gi.repository import Gtk, Gdk, Rsvg

from pychess.widgets.Background import hexcol


class OverlayWindow(Gtk.Window):
    """ This class knows about being an overlaywindow and some svg stuff """

    cache = {
    }  # Class global self.cache for svgPath:rsvg and (svgPath,w,h):surface

    def __init__(self, parent):
        Gtk.Window.__init__(self, type=Gtk.WindowType.POPUP)

        # set RGBA visual for the window so transparency works
        self.set_app_paintable(True)
        visual = self.get_screen().get_rgba_visual()
        if visual:
            self.set_visual(visual)
        self.myparent = parent

    # ===========================================================================
    #   The overlay stuff
    # ===========================================================================

    def paintTransparent(self, cairoContext):
        if self.is_composited():
            cairoContext.set_operator(cairo.OPERATOR_CLEAR)
            cairoContext.set_source_rgba(0, 0, 0, 0)
            cairoContext.paint()
            cairoContext.set_operator(cairo.OPERATOR_OVER)

    def digAHole(self, svgShape, width, height):

        # FIXME
        # For Python 2.x pycairo does not support/implement cairo.Region()
        # https://bugs.launchpad.net/ubuntu/+source/pygobject/+bug/1028115/comments/8
        return

        # Create a bitmap and clear it
        mask = cairo.ImageSurface(cairo.FORMAT_A1, width, height)
        mcontext = cairo.Context(mask)
        mcontext.set_source_rgb(0, 0, 0)
        mcontext.set_operator(cairo.OPERATOR_DEST_OUT)
        mcontext.paint()

        # Paint our shape
        surface = self.getSurfaceFromSvg(svgShape, width, height)
        mcontext.set_operator(cairo.OPERATOR_OVER)
        mcontext.set_source_surface(surface, 0, 0)
        mcontext.paint()

        # Apply it only if aren't composited, in which case we only need input
        # masking
        try:
            mregion = Gdk.cairo_region_create_from_surface(mask)
        except TypeError:
            return

        if self.is_composited():
            self.get_window().input_shape_combine_region(mregion, 0, 0)
        else:
            self.get_window().shape_combine_region(mregion, 0, 0)

    def translateCoords(self, x, y):
        top_level = self.myparent.get_toplevel()
        window = top_level.get_window()
        if window is None:
            print("   !!! get_window() returned None for", self.myparent, top_level)
        else:
            x_loc1, y_loc1 = window.get_position()
            translate_x = self.myparent.translate_coordinates(self.myparent.get_toplevel(),
                                                              x, y)
            x = x_loc1 + translate_x[0]
            y = y_loc1 + translate_x[1]
        return x, y

    # ===========================================================================
    #   The SVG stuff
    # ===========================================================================

    def getSurfaceFromSvg(self, svgPath, width, height):
        path = os.path.abspath(svgPath)
        if (path, width, height) in self.cache:
            return self.cache[(path, width, height)]
        else:
            if path in self.cache:
                svg = self.cache[path]
            else:
                svg = self.__loadNativeColoredSvg(path)
                self.cache[path] = svg
            surface = self.__svgToSurface(svg, width, height)
            self.cache[(path, width, height)] = surface
            return surface

    def getSizeOfSvg(self, svgPath):
        path = os.path.abspath(svgPath)
        if path not in self.cache:
            svg = self.__loadNativeColoredSvg(path)
            self.cache[path] = svg
        svg = self.cache[path]
        return (svg.props.width, svg.props.height)

    def __loadNativeColoredSvg(self, svgPath):
        TEMP_PATH = os.path.join(tempfile.gettempdir(), "pychess_theamed.svg")

        # return hex string #rrggbb
        def getcol(col):
            found, color = sytle_ctxt.lookup_color(col)
            # not found colors are black
            if not found:
                print("color not found in overlaywindow.py:", col)
            return hexcol(color)

        sytle_ctxt = self.get_style_context()

        colorDic = {"#18b0ff": getcol("p_light_selected"),
                    "#575757": getcol("p_text_aa"),
                    "#e3ddd4": getcol("p_bg_color"),
                    "#d4cec5": getcol("p_bg_insensitive"),
                    "#ffffff": getcol("p_base_color"),
                    "#000000": getcol("p_fg_color")}

        data = open(svgPath).read()
        data = re.sub(
            "|".join(colorDic.keys()),
            lambda m: m.group() in colorDic and colorDic[m.group()] or m.group(),
            data)
        f_handle = open(TEMP_PATH, "w")
        f_handle.write(data)
        f_handle.close()
        svg = Rsvg.Handle.new_from_file(TEMP_PATH)
        os.remove(TEMP_PATH)
        return svg

    def __svgToSurface(self, svg, width, height):
        assert isinstance(width, int)
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        context = cairo.Context(surface)
        context.set_operator(cairo.OPERATOR_SOURCE)
        if svg.props.width != width or svg.props.height != height:
            context.scale(width / float(svg.props.width),
                          height / float(svg.props.height))
        svg.render_cairo(context)
        return surface

    def __onStyleSet(self, self_, oldstyle):
        self.cache.clear()
