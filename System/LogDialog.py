import gtk, pango, os.path

from Log import log
from Log import DEBUG, LOG, WARNING, ERROR

w = gtk.Window()
w.set_title("Pychess - Log Viewer")
iconpath = os.path.join(os.path.split(__file__)[0], "../glade/pychess24.png")
w.set_icon(gtk.gdk.pixbuf_new_from_file(iconpath))

notebook = gtk.Notebook()
notebook.show()
w.add(notebook)

tv = gtk.TextView()
pango_ctx = tv.get_pango_context()
font_desc = tv.get_style().font_desc
font_desc.set_family("Monospace")
metrics = pango_ctx.get_metrics(font_desc)

width = pango.PIXELS(metrics.get_approximate_char_width())*80
height = pango.PIXELS(metrics.get_ascent()+metrics.get_descent())*24

task2book = {}
def newMessage (log, task, message, type):

    if not task in task2book:
    
        view = gtk.TextView ()
        view.set_editable(False)
        vp = gtk.Viewport()
        vp.set_shadow_type(gtk.SHADOW_NONE)
        vp.add(view)
        scroll = gtk.ScrolledWindow()
        scroll.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        scroll.set_size_request(width, height)
        scroll.add(vp)

        notebook.append_page (scroll, gtk.Label(task))
        textbuffer = view.get_buffer()
        textbuffer.create_tag(str(DEBUG), family='Monospace')
        textbuffer.create_tag(str(LOG), family='Monospace', weight=pango.WEIGHT_BOLD)
        textbuffer.create_tag(str(WARNING), family='Monospace', foreground="red")
        textbuffer.create_tag(str(ERROR), family='Monospace', weight=pango.WEIGHT_BOLD, foreground="red") 
        task2book[task] = textbuffer
    else: textbuffer = task2book[task]
    
    textbuffer.insert_with_tags_by_name(textbuffer.get_end_iter(), message, str(type))

from gobject import idle_add
log.connect ("logged", lambda *a: idle_add(newMessage,*a))

def show ():
    w.show_all()
    
def hide ():
    w.hide()
