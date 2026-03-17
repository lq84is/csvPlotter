import functools, sys
from pyqtgraph.Qt.QtWidgets import *

zeros = (0,0,0,0)
zerosGroupBox = (1, 12, 1, 1)
policyMin = (QSizePolicy.Minimum, QSizePolicy.Minimum)
policyMax = (QSizePolicy.Maximum, QSizePolicy.Maximum)
policyFix = (QSizePolicy.Fixed, QSizePolicy.Fixed)
AlignConstants = ('Qt.AlignLeft','Qt.AlignRight','Qt.AlignHCenter',\
                    'Qt.AlignJustify','Qt.AlignTop','Qt.AlignBottom',\
                    'Qt.AlignVCenter','Qt.AlignBaseline','Qt.AlignCenter',\
                    'Qt.AlignAbsolute')

print_err = print

def getNameOnly(path):
    reducedname = path.split('/')[-1]
    reducedname = reducedname.split('\\')[-1]
    return reducedname

def print_dict(d, print_function):
    for k,v in d.items():
        print_function('{}:{}'.format(type(k), type(v)))
        print_function('{} = {}'.format(k,v))

def trying(print_function):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*arg, **kw):
            try:
                return func(*arg, **kw)
            except Exception as ex:
                print_function('===TRYING BEGIN===')
                print_function('ERROR: {}, {}:\n'
                'exception: {} : {}'
                ''.format(func, func.__name__,type(ex), ex))
                print_function('arg:')
                for a in arg: 
                    print_function('{}'.format(a))
                print_function('kw:\n')
                print_dict(kw, print_function)
                print_function('===TRYING END====')
        return wrapper
    return decorator

def zeroMargins(*widgets):
    for widget in widgets:
        if issubclass(type(widget), QGroupBox):
            widget.setContentsMargins(*zerosGroupBox)
        else:
            widget.setContentsMargins(*zeros)

def safedisconnect(signal):
    try:
        signal.disconnect()
    except TypeError as ex:
        print_err('WARNING: safedisconnect:\n\t')
    except Exception as ex:
        print_err('ERROR: safedisconnect unknown exception:\n\t'
        'signal: {}\n\t'
        'msg: {}\n\t'.format(signal, ex))

def cMix(*classes, desired_name = None):
    '''
    if non-QObject with QObject:
    non-QObject, QObject
    '''
    class Mix(*classes):
        def __init__(self, *arg, **kwarg):
            super().__init__(*arg, **kwarg)
    if desired_name:
        Mix.__name__ = desired_name
        Mix.__qualname__ = desired_name
    else:
        name = 'cMix'
        for c in classes:
            name = name + c.__name__
        Mix.__name__ = name
        Mix.__qualname__ = name
    return Mix

def batch_f(items, func, *arg, **kw):
    '''for item in items:func(item, *arg, **kw)'''
    for item in items:
        func(item, *arg, **kw)

def prp(lst, prop, func = None):
    '''print(func(listItem.prop)) '''
    for l in lst:
        if func: print_err(func(getattr(l, prop)))
        else: print_err(getattr(l, prop))

def remap(a, a_min, a_max, b_min, b_max):
    return (((a - a_min) * (b_max - b_min)) / (a_max- a_min)) + b_min

def strToClass(classname):
    if hasattr(__builtins__, classname):
        return getattr(__builtins__, classname)
    if len(classname.split('.')) > 1:
        cls_string = classname.split('.')
        cls = getattr(sys.modules[__name__], cls_string[0])
        func = cls
        for atr in cls_string[1:]:
            func = getattr(func, atr)
        return func
    else:
        return getattr(sys.modules[__name__], classname)

def safeget(dct, *keys):
    '''... from dictionary'''
    result = []
    for key in keys:
        val = None
        try:
            val = dct[key]
        except KeyError:
            pass
        result.append(val)
    return result

def safedel(dct, *keys):
    '''... from dictionary'''
    for key in keys:
        try:
            del(dct[key])
        except KeyError:
            pass
            #print('safedel: no \'{}\' key'.format(key))

def safeint(s):
    '''none if '' '''
    try:
        return int(s)
    except ValueError:
        return None

def get_signals(source):
    cls = source if isinstance(source, type) else type(source)
    signal = type(pyqtSignal())
    for subcls in cls.mro():
        clsname = "{}.{}".format(subcls.__module__, subcls.__name__)
        for key, value in sorted(vars(subcls).items()):
            if isinstance(value, signal):
                print_err("{} [{}]".format(key, clsname))

import re

def gen_grep(pat, lines):
    patc = re.compile(pat)
    return (line for line in lines if patc.search(line))

def pgp(item, string, opt = None):
    '''Print attributes
    item - where to search
    string - regex string
    opt - if __dir__() requires argument'''
    if opt != None:
        lines = (str(type(getattr(item,attr))) + ': ' + str(attr) for attr in item.__dir__(opt))
    else:
        lines = (str(type(getattr(item,attr))) + ': ' + str(attr) for attr in item.__dir__())
    filtered = gen_grep(string, lines)
    for line in filtered: print_err(line)

def filter_from_none(d, keys = None):
    if keys:
        in_keys = (key for key in keys if key in d.keys())
        return {key: d[key] for key in in_keys if d[key] is not None}
    else:
        return {k: v for k,v in d.items() if v is not None}

def delNone(s):
    while None in s:
        del s[None]

def prop(func, target, *arg, **kw):
    if callable(func):
        return func(target, *arg, **kw)
    elif type(func) is str:
        return getattr(target, func)(*arg, **kw)
    else: raise TypeError('type(func) is {}'.format(type(func)))

def min_layout(*layouts):
    for layout in layouts:
        zeroMargins(layout)
        layout.setSizeConstraint(QLayout.SetFixedSize)
        layout.setSpacing(0)

def min_wid(*widgets):
    for widget in widgets:
        zeroMargins(widget)
        widget.setSizePolicy(*policyFix)

def min_wid_main(widget):
    widget.setLayout(widget.mainLayout)
    min_wid(widget)
    min_layout(widget.mainLayout)

def add_to_combo(combo, text):
    if combo.findText(text) == -1:
        combo.addItem(text)

def del_from_combo(combo, text):
    while combo.findText(text) != -1:
        combo.removeItem(combo.findText(text))

def update_combo(combo, filtered_set):
    try:
        combo_set = {combo.itemText(item) for item in range(combo.count())}
        delNone(filtered_set)
        combo_item_to_remove = combo_set - filtered_set
        combo_item_to_add = filtered_set - combo_set
        for text in combo_item_to_remove:
            del_from_combo(combo, text)
        for text in combo_item_to_add:
            add_to_combo(combo, text)
    except Exception as ex:
        print_err('update_combo:{}'.format(ex))

def item_counter(items):
    i = 0
    for item in items:
        i += 1
    return i
