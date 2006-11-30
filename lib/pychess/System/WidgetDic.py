class WidgetDic:
    """ A simple class that wraps a the glade get_widget function
        into the python __getitem__ version """
        
    def __init__ (self, widgets):
        self.widgets = widgets
        
    def __getitem__ (self, key):
        return self.widgets.get_widget(key)
