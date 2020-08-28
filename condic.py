#!/usr/bin/env python3
# vim: set fileencoding=utf-8 fileformat=unix :

"""{description}

Usage: {script} [options] WORD...
       {script} --list

Options:
  -h, --help                show this
  --version                 show version
  --list                    show supported languages
  -l, --language=LANG       target language in 3-letter code [default: epo]
  -d, --dictionary=FILE     use dictionary file
  -r, --reverse             search descriptions
  -p, --phrase              search phrases also
  -A, --literal             search literally (not ambiguous)
  -n, --normalize           search normalized form (experimental)
  -v, --verbose             report if word not found

Output options:
  -o, --output=FILE         output to FILE in UTF-8 [default: -]
  --output-encoding=ENC     output encoding [default: utf-8]
  --output-errors=METHOD    output erros [default: strict]; see below
  --output-newline=NL       output newline [default: crlf]

Error handling in output encoding:
  Valid arguments METHOD for option --output-errors are:
    strict                  raise ValueError
    ignore                  simply dispose
    replace                 replace with '?'
    surrogateescape         replace bytes 0x80-U+0xFF with U+DC80-U+DCFF
    xmlcharrefreplace       use XML entity ref (&#ddd);
    backslashreplace        use Python backslashed escape sequence (\\xx)
    namereplace             use \\N{{...}} escape sequence

Newline:
  Lines are separated by os.linesep for option --output-newline=none

PDIC files must comply with PDIC 1-line text format in UTF-8.
"""

import sys
import os
import re
import codecs

import docopt


__author__ = "HAYASHI Hideki"
__email__ = "hideki@hayasix.com"
__copyright__ = "Copyright (C) 2018 HAYASHI Hideki <hideki@hayasix.com>"
__license__ = "ZPL 2.1"
__version__ = "1.0.2"
__status__ = "Production"
__description__ = "Look up PDIC dictionay"


LANG = dict()
ASC = "abcdefghijklmnopqrstuvwxyz0123456789 -?*/#"
DEL = chr(127)
NEWLINES = {"none": None, "cr": "\x0d", "lf": "\x0a", "crlf": "\x0d\x0a"}


def translate(s, from_, to_):
    for (f, t) in zip(from_.split(), to_.split()):
        s = s.replace(f, t)
    return s


class Language:

    iso639_1 = None  # "xx"
    # iso639_2 is not used.
    iso639_3 = None  # "xxx"
    path = None  # "xxx.dic"
    trans = "".maketrans("", "")

    def __init_subclass__(cls, **kw):
        if cls.iso639_1: LANG[cls.iso639_1] = cls
        if cls.iso639_3: LANG[cls.iso639_3] = cls

    def decompose(self, s):
        return s

    def compose(self, s):
        return s

    def normalize(self, s):
        return s

    def asciify(self, s):
        return s.translate(type(self).trans)


class Bahasa_Indonesia(Language):

    iso639_1 = "id"
    iso639_3 = "ind"
    path = "ind.dic"


class Lojban(Language):

    iso639_3 = "jbo"
    path = "jbo.dic"

    def compose(self, s):
        s = s.replace("h", "'")
        return s


class Esperanto(Language):

    iso639_1 = "eo"
    iso639_3 = "epo"
    path = "epo.dic"
    trans = "".maketrans("ĉĝĥĵŝŭ", "cghjsu")

    def decompose(self, s, accent="^"):
        return translate(s,
                "ĉ    ĝ    ĥ    ĵ    ŝ    ŭ",
                "c{x} g{x} h{x} j{x} s{x} u{x}".format(x=accent))

    def compose(self, s):
        s = translate(s, "c^ g^ h^ j^ s^ u^", "ĉ ĝ ĥ ĵ ŝ ŭ")
        s = translate(s, "cx gx hx jx sx ux", "ĉ ĝ ĥ ĵ ŝ ŭ")
        return s

    def normalize(self, s):
        "Turn a verb into base form, caring wildcards."
        prefix = "*" if s[0] == "*" else ""
        suffix = "*" if s[-1] == "*" else ""
        s = s.strip("*")
        if s in ("bis cis gxis cxiu cxu du hu iu ju plu kiu mu neniu "
                 "unu nu plu tiu u jxus minus plus").split():
            return prefix + s + suffix
        if s[-1:] == "u": s = s[:-1] + "i"
        if s[-2:] in ("as", "is", "os", "us"): s = s[:-2] + "i"
        return prefix + s + suffix


class Español(Language):

    iso639_1 = "es"
    iso639_3 = "spa"
    path = "spa.dic"
    trans = "".maketrans("áéíóúüñ", "aeiouun")

    def decompose(self, s):
        return translate(s,
                "á  é  í  ó  ú  ü  ñ  ¿  ¡",
                "a' e' i' o' u' u: n~ \? \!")

    def compose(self, s):
        return translate(s,
                "a' e' i' o' u' u: n~ \? \!",
                "á  é  í  ó  ú  ü  ñ  ¿  ¡")


def listlanguages():
    t = dict()
    for c, d in LANG.items():
        d = d.__name__
        if d in t:
            t[d].append(c)
        else:
            t[d] = [c]
    for d in t:
        print(f"{d.replace('_', ' ')}: {', '.join(sorted(t[d]))}")


def main(words, lang, dictionary, file=sys.stdout, **opts):
    newline = opts.get("newline", "\n")
    asciify = opts.get("asciify", lambda s: s)
    langobj = LANG[lang]()
    with open(dictionary, "r", encoding="utf-8") as in_:
        for word in words:
            in_.seek(0)
            word = langobj.compose(word.lower())
            if opts.get("normalize"):
                word = langobj.normalize(word)
            pat = asciify(word).replace("*", ".*")
            if not opts.get("reverse"):
                if opts.get("phrase"):
                    pat = f"{pat} "
                else:
                    pat = f"^{pat}[.]?( #[0-9]+)? /"
            regex = re.compile(pat, re.I)
            found = 0
            for line in in_:
                if opts.get("reverse"):
                    t = asciify(line)
                else:
                    t = asciify(line[:line.index("/") + 1])
                if regex.search(t):
                    found += 1
                    print(line.rstrip(), end=newline, file=file)
            if not found and opts.get("verbose"):
                print(f"E: '{word}' is not found", end=newline, file=file)


def __main__():
    args = docopt.docopt(__doc__.format(
                script=os.path.basename(__file__),
                description=__description__,
            ), version=__version__)
    if args["--list"]:
        listlanguages()
        return
    lang = args["--language"].lower()
    langobj = LANG[lang]()
    dictionary = (args["--dictionary"] or
               os.path.join(os.path.dirname(__file__), langobj.path))
    opts = dict(
            newline=NEWLINES[args["--output-newline"].lower()],
            asciify=(lambda s: s) if args["--literal"] else langobj.asciify,
            phrase=args["--phrase"],
            reverse=args["--reverse"],
            normalize=args["--normalize"],
            verbose=args["--verbose"],
            )
    if args["--output"] == "-":
        target, buffering = sys.stdout.fileno(), 0
    else:
        target, buffering = args["--output"], 1
    with codecs.open(target, "w",
            encoding=args["--output-encoding"],
            errors=args["--output-errors"],
            buffering=buffering) as out:
        main(args["WORD"], lang, dictionary, file=out, **opts)


if __name__ == "__main__":
    sys.exit(__main__())
