import sublime
import sublime_plugin
import re

if int(sublime.version()) < 3000:
    from mathsymbols import maths, inverse_maths, synonyms, inverse_synonyms, symbol_by_name, names_by_symbol, get_settings
else:
    from UnicodeMath.mathsymbols import maths, inverse_maths, synonyms, inverse_synonyms, symbol_by_name, names_by_symbol, get_settings

def log(message):
    print(u'UnicodeMath: {0}'.format(message))

def get_line_contents(view, location):
    """
    Returns the contents of the line at the given location
    """
    return view.substr(sublime.Region(view.line(location).a, location))

UNICODE_PREFIX_RE = re.compile(r'.*(\\([^\s]+))$')
SYNTAX_RE = re.compile(r'(.*?)/(?P<name>[^/]+)\.tmLanguage')

def get_unicode_prefix(view, location):
    """
    Returns unicode prefix at given location and it's region
    or None if there is no unicode prefix
    """
    cts = get_line_contents(view, location)
    RE = UNICODE_PREFIX_RE
    res = RE.match(cts)
    if res:
        (full_, pref_) = res.groups()
        return (pref_, sublime.Region(location - len(full_), location))
    else:
        return None

def is_unicode_prefix(view, location):
    """
    Returns True if prefix at given location is prefixed with backslash
    """
    cts = get_line_contents(view, location)
    return UNICODE_PREFIX_RE.match(cts) != None

def can_convert(view):
    """
    Determines if there are any regions, where symbol can be converted
    Used not to call command when it will not convert anything, because such call
    modified edit, which lead to call of on_modified recursively
    Some times (is it sublime bug?) on_modified called twice on every change, which makes
    hard to detect whether this on_modified was called as result of previous call of command
    """
    for r in view.sel():
        if r.a == r.b:
            p = get_unicode_prefix(view, r.a)
            if p:
                rep = symbol_by_name(p[0])
                if rep:
                    return True
    return False

def syntax_allowed(view):
    """
    Returns whether syntax in view is not in ignore list
    """
    syntax_in_view = SYNTAX_RE.match(view.settings().get('syntax'))
    if syntax_in_view and syntax_in_view.group('name').lower() in get_settings().get('ignore_syntax', []):
        return False
    return True


class UnicodeMathComplete(sublime_plugin.EventListener):
    def on_query_completions(self, view, prefix, locations):
        # is prefix starts with '\\'
        if not is_unicode_prefix(view, locations[0]):
            return

        # returns completions
        return [(k + '\t' + maths[k], k + ' ') for k in filter(lambda s: s.startswith(prefix), maths.keys())]

    def on_query_context(self, view, key, operator, operand, match_all):
        if key == 'unicode_math_syntax_allowed':
            return syntax_allowed(view)
        elif key == 'unicode_math_can_convert':
            return can_convert(view)
        else:
            return False

class UnicodeMathConvert(sublime_plugin.TextCommand):
    def run(self, edit):
        log('called!')
        for r in self.view.sel():
            if r.a == r.b:
                p = get_unicode_prefix(self.view, r.a)
                if p:
                    rep = symbol_by_name(p[0])
                    if rep:
                        self.view.replace(edit, p[1], rep)

class UnicodeMathSwap(sublime_plugin.TextCommand):
    def run(self, edit):
        for r in self.view.sel():
            upref = get_unicode_prefix(self.view, self.view.word(r).b)
            sym = symbol_by_name(upref[0]) if upref else None
            if upref and sym:
                self.view.replace(edit, upref[1], sym)
            elif r.b - r.a <= 1:
                u = sublime.Region(r.b - 1, r.b)
                usym = self.view.substr(u)
                names = names_by_symbol(usym)
                if not names:
                    self.view.replace(edit, u, u'\\u%04X' % ord(usym))
                else:
                    self.view.replace(edit, u, u'\\' + names[0])

class UnicodeMathInsert(sublime_plugin.WindowCommand):
    def run(self):
        self.menu_items = []
        self.symbols = []
        for k, v in maths.items():
            value = v + ' ' + k
            if k in inverse_synonyms:
                value += ' ' + ' '.join(inverse_synonyms[k])
            self.menu_items.append(value)
            self.symbols.append(v)

        self.window.show_quick_panel(self.menu_items, self.on_done)

    def on_done(self, idx):
        if idx == -1:
            return
        view = self.window.active_view()
        if not view:
            return
        edit = view.begin_edit()
        for r in view.sel():
            view.replace(edit, r, self.symbols[idx])
        view.end_edit(edit)
