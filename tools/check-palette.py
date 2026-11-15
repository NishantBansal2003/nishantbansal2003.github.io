#!/usr/bin/env python3
"""Fail if the site palette no longer overrides Chirpy's colors.

_sass/_palette.scss beats Chirpy's theme by reusing its selectors later in
the stylesheet. A Chirpy upgrade that changes those selectors makes the
palette silently lose (links turn blue again). This script reads the
compiled CSS and checks that it still wins:

1. For every theme state of the page root (data-bs-theme light / dark /
   absent, under a light and a dark OS), it resolves each palette variable
   the way the browser cascade would, and requires the winning value to come
   from the palette, for the right mode.
2. Every selector Chirpy styles with a hard-coded hover color (#d2603a,
   #007bff) must be overridden later by the palette.

Usage: python3 tools/check-palette.py _site/assets/css/jekyll-theme-chirpy.css
"""

import re
import sys

HARD_CODED = ('#d2603a', '#007bff')
ATTR = 'data-bs-theme'
SCENARIOS = [  # (data-bs-theme attribute or None, OS color scheme)
    (attr, os) for attr in ('light', 'dark', None) for os in ('light', 'dark')
]


def parse(css):
    """Flatten CSS into (order, media, selectors, declarations) rules."""
    css = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
    rules, stack, i, start = [], [], 0, 0
    while i < len(css):
        ch = css[i]
        if ch == '{':
            stack.append(css[start:i].strip())
            start = i + 1
        elif ch == '}':
            body = css[start:i]
            prelude = stack.pop() if stack else ''
            if not prelude.startswith('@') and ':' in body:
                media = ' '.join(p for p in stack if p.startswith('@media'))
                decls = {}
                for d in body.split(';'):
                    if ':' in d:
                        k, v = d.split(':', 1)
                        decls[k.strip()] = v.strip()
                sels = [s.strip() for s in prelude.split(',') if s.strip()]
                rules.append((len(rules), media, sels, decls))
            start = i + 1
        i += 1
    return rules


def norm(sel):
    return re.sub(r'\s+', ' ', sel.replace('"', '').replace("'", '')).strip()


ROOT_PART = re.compile(r'^(:root|html|\[[^\]]+\]|:not\(\[[^\]]+\]\))')


def root_match(sel, attr, os_scheme):
    """Specificity if `sel` matches the root element in this state, else None.

    Only plain root selectors (:root / html with attribute conditions) are
    considered; anything else is not a root-level theme rule.
    """
    sel = norm(sel)
    if ' ' in sel or '>' in sel or '+' in sel or '~' in sel:
        return None
    a = b = c = 0
    rest = sel
    while rest:
        m = ROOT_PART.match(rest)
        if not m:
            return None
        part = m.group(0)
        rest = rest[len(part):]
        if part == ':root':
            b += 1
        elif part == 'html':
            c += 1
        else:
            negate = part.startswith(':not(')
            cond = part[6:-2] if negate else part[1:-1]
            name, _, val = cond.partition('=')
            if name == ATTR:
                ok = attr is not None if not val else attr == val
            else:
                ok = False  # e.g. Chirpy 7.4's data-mode, never set in 7.6
            if negate:
                ok = not ok
            if not ok:
                return None
            b += 1
    return (a, b, c)


def media_ok(media, os_scheme):
    for scheme in re.findall(r'prefers-color-scheme:\s*(\w+)', media):
        if scheme != os_scheme:
            return False
    return True


def main(path):
    rules = parse(open(path, encoding='utf-8').read())
    palette_start = next((r[0] for r in rules if '--accent' in r[3]), None)
    if palette_start is None:
        print('FAIL: no palette (--accent) found in compiled CSS')
        return 1
    ours = [r for r in rules if r[0] >= palette_start]
    accent = {}  # mode -> --accent value, from the palette rule for that mode
    state_vars = {}  # scenario -> variables the palette sets for that state
    for _, media, sels, decls in ours:
        if '--accent' in decls:
            for attr, os_scheme in SCENARIOS:
                if media_ok(media, os_scheme) and any(root_match(s, attr, os_scheme) for s in sels):
                    accent[attr or os_scheme] = decls['--accent']
                    state_vars.setdefault((attr, os_scheme), set()).update(decls)
    palette_vars = set().union(*state_vars.values()) if state_vars else set()
    errors = []
    if len(set(accent.values())) != 2:
        errors.append(f'expected distinct light/dark --accent values, got {accent}')

    # 1. cascade simulation for palette variables on the root element
    for attr, os_scheme in SCENARIOS:
        mode = attr or os_scheme
        state = f'{ATTR}={attr or "(absent)"}, OS {os_scheme}'
        if (attr, os_scheme) not in state_vars:
            errors.append(f'{state}: no palette rule applies')
            continue
        for var in sorted(state_vars[(attr, os_scheme)]):
            best = None  # (specificity, order, rule)
            for rule in rules:
                order, media, sels, decls = rule
                if var not in decls or not media_ok(media, os_scheme):
                    continue
                for s in sels:
                    spec = root_match(s, attr, os_scheme)
                    if spec is not None and (best is None or (spec, order) > best[:2]):
                        best = (spec, order, rule)
            if best is None:
                errors.append(f'{state}: {var} is never applied')
                continue
            order, media, sels, decls = best[2]
            if order < palette_start:
                errors.append(f'{state}: {var} = {decls[var]!r} from Chirpy rule '
                              f'{", ".join(sels)!r} {media} beats the palette')
            elif '--accent' in decls and decls['--accent'] != accent.get(mode):
                errors.append(f'{state}: palette applies the wrong mode for {var}')

    # 2. hard-coded hover colors must be overridden by a later palette rule
    our_sels = {norm(s) for r in ours for s in r[2]}
    for order, media, sels, decls in rules[:palette_start]:
        if any(h in v.lower() for v in decls.values() for h in HARD_CODED):
            for s in sels:
                if norm(s) not in our_sels:
                    errors.append(f'hard-coded color on {s!r} is not overridden by the palette')

    if errors:
        print('FAIL: the site palette no longer overrides Chirpy everywhere.')
        print('Update _sass/_palette.scss to match the current Chirpy version.\n')
        print('\n'.join(f'  - {e}' for e in errors))
        return 1
    print(f'OK: palette wins for {len(palette_vars)} variables in {len(SCENARIOS)} theme states, '
          'and all hard-coded hover colors are overridden.')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1]))
