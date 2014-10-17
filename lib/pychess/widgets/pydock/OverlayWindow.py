import os
import re
import sys

import cairo
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GObject

if sys.platform == 'win32':
    from pychess.System.WinRsvg import rsvg
else:
    from gi.repository import Rsvg


class OverlayWindow (Gtk.Window):
    """ This class knows about being an overlaywindow and some svg stuff """
    
    cache = {} # Class global self.cache for svgPath:rsvg and (svgPath,w,h):surface
    
    def __init__ (self, parent):
        Gtk.Window.__init__(self, Gtk.WindowType.POPUP)

        # set RGBA visual for the window so transparency works
        self.set_app_paintable(True)
        visual = self.get_screen().get_rgba_visual()
        if visual:
            self.set_visual(visual)
        self.myparent = parent
    
    #===========================================================================
    #   The overlay stuff
    #===========================================================================
    
    def paintTransparent (self, cairoContext):
        if self.is_composited():
            cairoContext.set_operator(cairo.OPERATOR_CLEAR)
            cairoContext.set_source_rgba(0,0,0,0)
            cairoContext.paint()
            cairoContext.set_operator(cairo.OPERATOR_OVER)
    
    def digAHole (self, svgShape, width, height):
        
        # FIXME       
        # Create a bitmap and clear it
        #mask = Gdk.Pixmap(None, width, height, 1)
        #mcontext = mask.cairo_create()
        #mcontext.set_source_rgb(0, 0, 0)
        #mcontext.set_operator(cairo.OPERATOR_DEST_OUT)
        #mcontext.paint()

        # Paint our shape
        #surface = self.getSurfaceFromSvg(svgShape, width, height)
        #mcontext.set_operator(cairo.OPERATOR_OVER)
        #mcontext.set_source_surface(surface, 0, 0)
        #mcontext.paint()

        # Apply it only if aren't composited, in which case we only need input
        # masking
        #if self.is_composited():
        #    self.window.input_shape_combine_mask(mask, 0, 0)
        #else: self.window.shape_combine_mask(mask, 0, 0)

        surface = self.getSurfaceFromSvg(svgShape, width, height)
        ctx = self.get_window().cairo_create()
        ctx.set_source_surface(surface, 0, 0)
        ctx.paint()

    def translateCoords (self, x, y):
        tl = self.myparent.get_toplevel()
        x1, y1 = tl.get_window().get_position()
        tx = self.myparent.translate_coordinates(self.myparent.get_toplevel(), x, y)
        x = x1 + tx[0]
        y = y1 + tx[1]
        return x, y
    
    #===========================================================================
    #   The SVG stuff
    #===========================================================================
    
    def getSurfaceFromSvg (self, svgPath, width, height):
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
    
    def getSizeOfSvg (self, svgPath):
        path = os.path.abspath(svgPath)
        if not path in self.cache:
            svg = self.__loadNativeColoredSvg(path)
            self.cache[path] = svg
        svg = self.cache[path]
        return (svg.props.width, svg.props.height)
    
    def __loadNativeColoredSvg (self, svgPath):
        def colorToHex (color, state):
            color = getattr(self.myparent.get_style(), color)[state]
            pixels = (color.red, color.green, color.blue)
            return "#"+"".join(hex(c/256)[2:].zfill(2) for c in pixels)
        
        TEMP_PATH = "/tmp/pychess_theamed.svg"
        # FIXME
        #colorDic = {"#18b0ff": colorToHex("light", Gtk.StateType.SELECTED),
        #            "#575757": colorToHex("text_aa", Gtk.StateType.PRELIGHT),
        #            "#e3ddd4": colorToHex("bg", Gtk.StateType.NORMAL),
        #            "#d4cec5": colorToHex("bg", Gtk.StateType.INSENSITIVE),
        #            "#ffffff": colorToHex("base", Gtk.StateType.NORMAL),
        #            "#000000": colorToHex("fg", Gtk.StateType.NORMAL)}
        colorDic = {"#18b0ff": "#85bcf6",
                    "#575757": "#898c8d",
                    "#e3ddd4": "#ededed",
                    "#d4cec5": "#ededed",
                    "#ffffff": "#ffffff",
                    "#000000": "#313739"}
        
        data = file(svgPath).read()
        data = re.sub("|".join(colorDic.keys()),
                      lambda m: m.group() in colorDic and colorDic[m.group()] or m.group(),
                      data)
        f = file(TEMP_PATH, "w")
        f.write(data)
        f.close()
        svg = Rsvg.Handle.new_from_file(TEMP_PATH)
        os.remove(TEMP_PATH)
        return svg
    
    def __svgToSurface (self, svg, width, height):
        assert type(width) == int
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        context = cairo.Context(surface)
        context.set_operator(cairo.OPERATOR_SOURCE)
        if svg.props.width != width or svg.props.height != height:
            context.scale(width/float(svg.props.width),
                          height/float(svg.props.height))
        svg.render_cairo(context)
        return surface
    
    def __onStyleSet (self, self_, oldstyle):
        self.cache.clear()
