# -*- coding: utf-8 -*-
"""
BLISSCRIBE:

    A Python module for translating text to Blissymbols.

    All relevant parts-of-speech tags (used throughout) and
    their meanings are enumerated here:
    https://www.ling.upenn.edu/courses/Fall_2003/ling001/penn_treebank_pos.html
"""
import collections
import os
import sys
import nltk
import pattern.text
from PIL import Image, ImageDraw, ImageFont, ImageChops
from fpdf import FPDF
from nltk.corpus import wordnet
from pattern.text import en, es, fr, de, it, nl

try:
    import parse_lexica
except ImportError:
    print("Parse_lexica module could not be imported.\n\
    Please find the local module parse_lexica.py \n\
    and relocate it to the same directory as blisscribe.py.")
else:
    import parse_lexica

FILE_PATH = sys.path[0] + "/"


class BlissTranslator:
    """
    A class for translating text in select languages to Blissymbols.
    ~
    Currently supported languages:
        - English (default)
        - Spanish
        - German
        - French
        - Italian
        - Dutch
        - Polish
    ~
    Begin by initializing a BlissTranslator with a supported language.
    Pass a string in your chosen language to translate() for an output
    PDF of the given text with Blissymbols.
    ~
    Use chooseTranslatables() to set whether to translate nouns,
    verbs, adjectives, and/or other parts of speech.
    ~
    By default, a BlissTranslator will translate all parts of
    speech in CHOSEN_POS, i.e., nouns, verbs, and adjectives.
    To translate all other parts of speech, set self.other to True.
    ~
    Contains methods for:
        1) selecting which parts of speech to translate
           --> chooseTranslatables()
           --> chooseNouns()
           --> chooseVerbs()
           --> chooseAdjs()
           --> chooseOtherPOS()
        2) selecting whether to translate text to Blissymbols
           immediately or gradually
           --> setFastTranslate()
        3) selecting font & font size for output PDF translations
           --> setFont()
        4) selecting whether to subtitle all Blissymbols or only
           new Blissymbols
           --> setSubAll()
    """
    # Fonts
    ROMAN_FONT = "/Library/Fonts/Times New Roman.ttf"
    SANS_FONT = "/Library/Fonts/Arial.ttf"
    HIP_FONT = "/Library/Fonts/Helvetica.dfont"
    DEFAULT_FONT_SIZE = 30
    # Images
    IMG_PATH = FILE_PATH + "symbols/png/whitebg/"
    IMAGES_SAVED = 0
    # Language
    STARTING_PUNCT = set(["(", '"', "-", "\xe2\x80\x9c", "\xe2\x80\x98", "\xe2\x80\x9e"])  # spaces BEFORE
    ENDING_PUNCT = set([".", ",", ";", ":", "?", "!", ")", '"', "-", "\xe2\x80\x9d", "\xe2\x80\x99", u"\u201d"]) # spaces AFTER
    PUNCTUATION = STARTING_PUNCT.union(ENDING_PUNCT)
    PUNCTUATION.add("'")
    PARTS_OF_SPEECH = set(["CC", "CD", "DT", "EX", "FW", "IN", "JJ", "JJR", "JJS", "LS",
                           "MD", "NN", "NNS", "NNP", "NNPS", "PDT", "POS", "PRP", "PRP$",
                           "RB", "RBR", "RBS", "RP", "TO", "UH", "VB", "VBD", "VBG",
                           "VBN", "VBP", "VBZ", "WDT", "WP", "WP$", "WRB"])
    DEFAULT_POS = set(["NN", "NNS", "VB", "VBD", "VBG", "VBN", "JJ", "JJR", "JJS"])
    CHOSEN_POS = DEFAULT_POS
    LANG_CODES = {"Arabic": "arb", "Bulgarian": 'bul', "Catalan": 'cat', "Danish": 'dan',
                  "Greek": 'ell', "English": 'eng', "Basque": 'eus', "Persian": 'fas',
                  "Finnish": 'fin', "French": 'fra', "Galician": 'glg', "Hebrew": 'heb',
                  "Croatian": 'hrv', "Indonesian": 'ind', "Italian": 'ita', "Japanese": 'jpn',
                  "Norwegian Nyorsk": 'nno', "Norwegian Bokmal": 'nob', "Polish": 'pol',
                  "Portuguese": 'por', "Chinese": "qcn", "Slovenian": 'slv', "Spanish": 'spa',
                  "Swedish": 'swe', "Thai": 'tha', "Malay": 'zsm'}

    def __init__(self, language="English", font_path=ROMAN_FONT, font_size=DEFAULT_FONT_SIZE):
        # Fonts
        self.font_size = font_size
        self.font_path = font_path
        self.font = ImageFont
        self.setFont(self.font_path, self.font_size)
        # Images
        self.image_heights = self.font_size * 5
        self.pages = []
        self.sub_all = False
        self.page_nums = True
        # Language
        self.bliss_dict = dict
        self.polish_lexicon = dict
        self.language = str
        self.lang_code = str
        self.setLanguage(language)
        self.fast_translate = False
        self.words_seen = dict
        self.words_changed = dict
        self.initSeenChanged()
        self.defns_chosen = {}  # holds user choices for correct word definitions
        # --> parts of speech
        self.nouns = True
        self.verbs = True
        self.adjs = True
        self.other = False

    # GETTERS/SETTERS
    # ===============
    def getFont(self, font_path, font_size):
        """
        Returns an ImageFont with given font_path and font_size.
        ~
        If font_path is invalid, returns an ImageFont using this
        BlissTranslator's ROMAN_FONT and font_size.

        :param font_path: str, path to font file
        :param font_size: int, desired font size
        :return: ImageFont, font with given path and font size
        """
        try:
            ImageFont.truetype(font_path, font_size)
        except IOError:
            self.font_path = self.ROMAN_FONT
            return ImageFont.truetype(self.ROMAN_FONT, font_size)
        else:
            return ImageFont.truetype(font_path, font_size)

    def setFont(self, font_path, font_size):
        """
        Sets this BlissTranslator's default font to an ImageFont
        with given font_path and font_size.
        ~
        If font_path is invalid, uses BlissTranslator's ROMAN_FONT.

        :param font_path: str, path to font file
        :param font_size: int, desired font size
        :return: None
        """
        self.font = self.getFont(font_path, font_size)

    def setLanguage(self, language):
        """
        Sets this BlissTranslator's native language
        to the input language.
        ~
        If given language is invalid, do not change this
        BlissTranslator's default language.

        :param language: str, language to set to default
        :return: None
        """
        try:
            BlissTranslator.LANG_CODES[self.language]
            parse_lexica.getDefns(parse_lexica.LEX_PATH, language)
        except KeyError, IOError:
            self.language = "English"
        else:
            self.language = language
        finally:
            self.setLangCode()
            self.setBlissDict()

    def setLangCode(self):
        """
        Sets this BlissTranslator's lang_code to
        this BlissTranslator's native language code.

        :return: None
        """
        self.lang_code = BlissTranslator.LANG_CODES[self.language]

    def initBlissDict(self):
        """
        Returns a Bliss dictionary in this BlissTranslator's
        set language.

        :return: dict, where...
            keys (str) - words in desired language
            vals (str) - corresponding Blissymbol image filenames
        """
        return parse_lexica.getDefnImgDict(parse_lexica.LEX_PATH, self.language)

    def setBlissDict(self):
        """
        Initializes this BlissTranslator's bliss_dict in
        its native language.

        :return: None
        """
        self.bliss_dict = self.initBlissDict()

        if self.language == "Polish":
            self.polish_lexicon = parse_lexica.parseLexicon("resources/lexica/polish.txt")

    def initSeenChanged(self):
        """
        Initializes this BlissTranslator's words_seen
        as a default dict.

        :return: None
        """
        self.words_seen = collections.defaultdict(bool)
        self.words_changed = collections.defaultdict(bool)

    def setSubAll(self, sub_all):
        """
        Sets self.sub_all equal to input sub_all value.
        ~
        Setting sub_all to True will produce subtitles under
        all words translated to Blissymbols.
        Setting sub_all to False will produce subtitles only
        under new words translated to Blissymbols.
        ~
        Sets subtitle settings for this BlissTranslator's
        translate() method.

        :param sub_all: bool, whether to subtitle all words
        :return: None
        """
        self.sub_all = sub_all

    def setPageNums(self, page_nums):
        """
        Sets self.page_nums to page_nums.
        ~
        Setting page_nums to True will cause this
        BlissTranslator to enumerate the bottom of each
        PDF page from translate().
        Setting page_nums to False will result in no page
        numbers.

        :param page_nums: bool, whether to enumerate
            translated PDF pages
        :return: None
        """
        self.page_nums = page_nums

    def setFastTranslate(self, fast_translate):
        """
        Set's self.fast_translate to fast_translate.
        ~
        Setting fast_translate to True will cause this
        BlissTranslator to translate the first instances of
        every word.
        Setting fast_translate to False will cause it to
        only translate a word after having seen it once.
        ~
        Sets translation speed for this BlissTranslator's
        translate() method.

        :param fast_translate: bool, whether to translate
            words to Blissymbols immediately
        :return: None
        """
        self.fast_translate = fast_translate

    def setTranslatables(self):
        """
        Resets CHOSEN_POS according to this BlissTranslator's translatables
        (i.e., nouns, verbs, adjs, and other).

        :return: None
        """
        BlissTranslator.CHOSEN_POS = set()

        if self.nouns:
            BlissTranslator.CHOSEN_POS.add("NN")
            BlissTranslator.CHOSEN_POS.add("NNS")
        if self.verbs:
            BlissTranslator.CHOSEN_POS.add("VB")
            BlissTranslator.CHOSEN_POS.add("VBD")
            BlissTranslator.CHOSEN_POS.add("VBG")
            BlissTranslator.CHOSEN_POS.add("VBN")
        if self.adjs:
            BlissTranslator.CHOSEN_POS.add("JJ")
            BlissTranslator.CHOSEN_POS.add("JJR")
            BlissTranslator.CHOSEN_POS.add("JJS")
        if self.other:
            for pos in BlissTranslator.PARTS_OF_SPEECH.difference(BlissTranslator.DEFAULT_POS):
                # adds all non-default parts of speech
                BlissTranslator.CHOSEN_POS.add(pos)

    def chooseNouns(self, nouns):
        """
        Allows user to set whether to translate nouns.

        :param nouns: bool, True to translate nouns
        :return: None
        """
        self.nouns = nouns
        self.setTranslatables()

    def chooseVerbs(self, verbs):
        """
        Allows user to set whether to translate verbs.

        :param verbs: bool, True to translate verbs
        :return: None
        """
        self.verbs = verbs
        self.setTranslatables()

    def chooseAdjs(self, adjs):
        """
        Allows user to set whether to translate adjectives.

        :param adjs: bool, True to translate adjectives
        :return: None
        """
        self.adjs = adjs
        self.setTranslatables()

    def chooseOtherPOS(self, other):
        """
        Allows user to set whether to translate all other
        parts of speech.

        :param other: bool, True to translate other parts of speech
        :return: None
        """
        self.other = other
        self.setTranslatables()

    def chooseTranslatables(self, nouns, verbs, adjs, other):
        """
        Allows user to set whether to translate nouns, verbs,
        adjectives, and/or all other parts of speech.
        ~
        Changes this BlissTranslator's variables with the same names.

        :param nouns: bool, True to translate nouns
        :param verbs: bool, True to translate verbs
        :param adjs: bool, True to translate adjectives
        :param other: bool, True to translate all other parts of speech
        :return: None
        """
        self.chooseNouns(nouns)
        self.chooseVerbs(verbs)
        self.chooseAdjs(adjs)
        self.chooseOtherPOS(other)
        self.setTranslatables()

    def isSeen(self, word):
        """
        Returns True if the given word is part of the
        words_seen dict.

        :param word: str, word to check if in words_seen
        :return: bool, whether given word is in words_seen
        """
        return word in self.words_seen

    def addSeen(self, word):
        """
        Adds word to words_seen dict.

        :param word: str, word to add to words_seen
        :return: None
        """
        self.words_seen[word] = True

    def isChanged(self, word):
        """
        Returns True if the given word is part of the
        words_changed dict.

        :param word: str, word to check if in words_changed
        :return: bool, whether given word is in words_changed
        """
        return word in self.words_changed

    def addChanged(self, word):
        """
        Adds word to words_changed dict.

        :param word: str, word to add to words_changed
        :return: None
         """
        self.words_changed[word] = True

    # IMAGES
    # ======
    def getWordWidth(self, word):
        """
        Returns the width of the given string or Image in pixels.

        :param word: str or Image
        :return: int, word width in pixels
        """
        if word == "\n":
            return 0
        elif type(word) == str:
            return self.trimHorizontal(self.getWordImg(word, self.font_size)).size[0]
        else:
            try:
                return word.size[0]
            except AttributeError:
                return self.font_size

    def makeBlankImg(self, x, y):
        """
        Returns a blank image of dimensions x and y.

        :param x: int, x-dimension of image
        :param y: int, y-dimension of image
        :return: Image, blank image
        """
        return Image.new("RGBA", (x, y), (255, 255, 255, 255))

    def getWordImg(self, word, font_size=DEFAULT_FONT_SIZE):
        """
        Draws and returns an Image of given word in given font_size.

        :param word: str, word to render to Image
        :param font_size: int, desired font size for string
        :return: Image, image of input str
        """
        img = self.makeBlankImg(len(word) * font_size,
                                self.image_heights)
        if word == "\n":
            return img
        else:
            word = self.unicodize(word)
            sketch = ImageDraw.Draw(img)
            sketch.text((0, font_size),
                        word,
                        font=ImageFont.truetype(font=self.font_path, size=font_size),
                        fill="black")
            return self.trimHorizontal(img)

    def getBlissImg(self, word, max_width, max_height, choosing=False):
        """
        Draws and returns a thumbnail Image of the given word's
        Blissymbol, with width not exceeding max_width.
        ~
        If a word has multiple meanings, then return the Blissymbol
        corresponding to the first meaning listed in bliss_dict.

        :param word: str, word to render to Image
        :param max_width: int, maximum width of Image (in pixels)
        :param max_height: int, maximum height of Image (in pixels)
        :param choosing: bool, whether user can choose definitions for
            ambiguous words
        :return: Image, image of input str's Blissymbol
        """
        if word == "indicator (plural)":
            bliss_word = Image.open(BlissTranslator.IMG_PATH +
                                    "indicator_(plural).png")
        elif type(self.bliss_dict[word]) == list:
            if choosing:
                choice = self.chooseDefn(word)
            else:
                choice = 0
            bliss_word = Image.open(str(BlissTranslator.IMG_PATH +
                                   self.bliss_dict[word][choice]))
        else:
            bliss_word = Image.open(str(BlissTranslator.IMG_PATH +
                                    self.bliss_dict[word]))
        img = bliss_word
        img.thumbnail((max_width, max_height))
        return img

    def getPluralImg(self, img, max_width=(816/2)):
        """
        Returns the given Blissymbol image with the plural
        Blissymbol at the end.

        :param img: Image, Blissymbol image to pluralize
        :return: Image, input image pluralized
        """
        plural = self.getBlissImg("indicator (plural)", max_width, self.image_heights/2)
        plural = self.trim(plural)
        bg = self.makeBlankImg(img.size[0] + plural.size[0], self.image_heights/2)
        bg.paste(img, (0, 0))
        bg.paste(plural, (bg.size[0]-plural.size[0], (bg.size[1]/2)))
        return bg

    def trim(self, img):
        """
        Trims the input image's whitespace.

        :param img: Image, image to be trimmed
        :return: Image, trimmed image

        Taken from http://stackoverflow.com/questions/10615901/trim-whitespace-using-pil/29192070.
        """
        bg = Image.new(img.mode, img.size, img.getpixel((0, 0)))
        diff = ImageChops.difference(img, bg)
        diff = ImageChops.add(diff, diff, 2.0, -100)
        bbox = diff.getbbox()

        if bbox:
            return img.crop(bbox)
        else:
            return img

    def trimHorizontal(self, img):
        """
        Trims the input image's whitespace only
        in the x-dimension.

        :param img: Image, image to be trimmed
        :return: Image, trimmed image

        Adapted from http://stackoverflow.com/questions/10615901/trim-whitespace-using-pil/29192070.
        """
        bg = Image.new(img.mode, img.size, img.getpixel((0, 0)))
        diff = ImageChops.difference(img, bg)
        diff = ImageChops.add(diff, diff, 2.0, -100)
        bbox = diff.getbbox()
        bbox = (bbox[0], 0, bbox[2], img.height)

        if bbox:
            return img.crop(bbox)
        else:
            return img

    def trimHorizontalStd(self, img, std):
        """
        Trims input image's whitespace in x-dimension
        and crops image in y-dimension to fit std,
        then returns the result.

        :param img: Image, image to be trimmed
        :return: Image, trimmed image

        Adapted from http://stackoverflow.com/questions/10615901/trim-whitespace-using-pil/29192070.
        """
        bg = Image.new(img.mode, img.size, img.getpixel((0, 0)))
        diff = ImageChops.difference(img, bg)
        diff = ImageChops.add(diff, diff, 2.0, -100)
        bbox = diff.getbbox()
        bbox = (bbox[0], 0, bbox[2], min(std, img.height))

        if bbox:
            return img.crop(bbox)
        else:
            return img

    def incLine(self, line_no, inc=DEFAULT_FONT_SIZE*3):
        """
        Returns current line_no multiplied by inc to get the
        y-coordinate for this line in pixels.

        :param line_no: int, the current line number
        :param inc: int, factor to multiply line_no by
        :return: int, y-coordinate for this line (in px)
        """
        return line_no * inc

    def getSubtitleSize(self):
        """
        Returns a font size suitable as a subtitle for this
        BlissTranslator's default font_size.

        :return: int, subtitle font size
        """
        return self.font_size - int(self.font_size/2)

    def getSpaceSize(self):
        """
        Returns an appropriate space size relative to this
        BT's font_size in pixels.

        :return: int, space size (in pixels)
        """
        return int(self.font_size / 1.5)

    def getMinSpace(self):
        """
        Returns the minimum spacing between characters
        in pixels.

        Useful for standardizing punctuation spacing.

        :return: int, minimum space size (in pixels)
        """
        return 2

    def drawAlphabet(self, words, columns=10):
        """
        Returns alphabet-style definition image containing each word in words,
        with word definition on bottom and corresponding Blissymbol on top.
        ~
        If a word in words has no corresponding Blissymbol, this method does
        not draw it.

        :param words: str, words (separated by spaces) to render
        :param columns: int, maximum number of columns
        :return: Image, drawn alphabet of given words
        """
        # TODO: standardize image sizes in BlissTranslator to simplify rendering
        # TODO: refactor translate() & drawAlphabet() for less repetition
        words_list = words.split(" ")

        glyph_bg_wh = self.image_heights
        start_x = glyph_bg_wh / 2
        start_y = self.font_size*2
        space = self.getMinSpace()

        bliss_alphabet = []

        for word in words_list:
            bg = self.makeBlankImg(glyph_bg_wh, glyph_bg_wh)

            if self.isTranslatable(word) or self.isSynonymTranslatable(word):
                try:
                    self.bliss_dict[word]
                except KeyError:
                    if self.isTranslatable(word):
                        lexeme = self.getLexeme(word)
                    else:
                        lexeme = self.translateUntranslatable(word)
                    bliss_word = self.getBlissImg(lexeme, glyph_bg_wh, glyph_bg_wh/2)
                else:
                    bliss_word = self.getBlissImg(word, glyph_bg_wh, glyph_bg_wh/2)
                bliss_word = self.trim(bliss_word)
                text_word = self.getWordImg(word.upper(), font_size=self.getSubtitleSize())
                text_word = self.trim(text_word)

                text_width = text_word.width
                bliss_width = bliss_word.width
                bliss_height = bliss_word.height

                start_bliss_word_x = start_x - (bliss_width/2)
                start_bliss_word_y = start_y - space - bliss_height  # above origin pt
                start_text_word_x = start_x - (text_width/2)
                start_text_word_y = start_y + space                  # below origin pt

                bg.paste(text_word, (start_text_word_x, start_text_word_y))
                bg.paste(bliss_word, (start_bliss_word_x, start_bliss_word_y))

            bliss_alphabet.append(bg)

        alphabet_bg_width = glyph_bg_wh * min(len(bliss_alphabet), columns)
        alphabet_bg_height = glyph_bg_wh * (len(bliss_alphabet) / columns + 1)
        alphabet_bg = self.makeBlankImg(alphabet_bg_width, alphabet_bg_height)
        indent = 0
        line_height = 0

        for defn in bliss_alphabet:
            if (indent + glyph_bg_wh) > alphabet_bg_width:
                indent = 0
                line_height += 1

            if (line_height * glyph_bg_wh) > alphabet_bg_height:
                alphabet_bg.show()
                alphabet_bg = self.makeBlankImg(alphabet_bg_width, alphabet_bg_height)

            alphabet_bg.paste(defn, (indent, self.incLine(line_height, glyph_bg_wh)))
            indent += glyph_bg_wh

        try:
            self.trimHorizontal(alphabet_bg)
        except TypeError:
            return alphabet_bg
        else:
            if len(bliss_alphabet) > columns:
                return self.trimHorizontal(alphabet_bg)
            else:
                return self.trimHorizontalStd(alphabet_bg, self.image_heights)

    def displayImages(self, pages):
        """
        Displays each image in pages.

        :param pages: List[Image], images to display
        :return: None
        """
        for page in pages:
            page.show()

    def saveImages(self, pages):
        """
        Saves each image in pages as a .png file.
        ~
        Names each image beginning at this BlissTranslator's
        IMAGES_SAVED variable and incrementing by 1.
        ~
        After loop terminates, sets IMAGES_SAVED to the
        final accumulated value.
        ~
        Returns a list of the image filenames created.

        :param pages: List[Image], images to save to file
        :return: None
        """
        filenames = []
        start = BlissTranslator.IMAGES_SAVED

        for page in pages:
            filename = "bliss_img" + str(start) + ".png"
            page.save(filename)
            filenames.append(filename)
            start += 1

        BlissTranslator.IMAGES_SAVED = start
        return filenames

    def makeTitlePage(self, title, x, y):
        """
        Returns a title page of given dimensions x and y with the given
        title.

        :param title: str, title name
        :param x: int, x-dimension of output title page
        :param y: int, y-dimension of output title page
        :return: Image, title page
        """
        img = self.makeBlankImg(x, y)
        title_img = self.getWordImg(title, self.font_size)

        img_x = x/2 - title_img.size[0]/2
        img_y = y/3

        img.paste(title_img, (img_x, img_y))
        return img

    def makePdf(self, filename, pages, margins=0, delete=True):
        """
        Pastes each image file linked to in pages to a PDF.
        ~
        Saves PDF under given filename in this directory.
        ~
        If delete is set to True, this method deletes all
        image files from pages.
        If delete is set to False, does not delete any
        image files from pages.

        Taken from:
        https://stackoverflow.com/questions/27327513/create-pdf-from-a-list-of-images

        :param filename: str, filename for output PDF
        :param pages: List[str], image filenames to paste in PDF
        :param margins: int, space in margins (in pixels)
        :param delete: bool, whether to delete image files
        :return: None
        """
        width, height = Image.open(pages[0]).size
        new_w, new_h = width+(margins*2), height+(margins*2)

        pdf = FPDF(unit="pt", format=[new_w, new_h])
        idx = 0

        for page in pages:
            pdf.add_page()
            pdf.image(page, x=margins, y=margins)
            if len(pages)>2 and idx>0 and self.page_nums:
                number = self.getWordImg(str(idx), self.font_size)
                number = self.trim(number)
                num_fn = "num" + str(idx) + ".png"
                number.save(num_fn)
                x = new_w/2-number.size[0]
                y = new_h-(margins/2)-number.size[1]
                pdf.image(num_fn, x=x, y=y)
                os.remove(num_fn)
            if delete:
                os.remove(page)
            idx += 1

        pdf.output("bliss pdfs/" + filename + ".pdf", "F")

    # LANGUAGE PROCESSING
    # ===================
    def unicodize(self, text):
        """
        Returns the given text in unicode.
        ~
        Ensures all text is in unicode for parsing.

        :param text: str, text to return in unicode
        :return: str, text in unicode
        """
        if not isinstance(text, unicode):
            text = text.decode("utf-8")
        return text

    def getWordAndTag(self, word):
        """
        Returns a tuple of the given word and its tag.

        :param word: str, word to tag
        :return: (str, str) tuple, given word and its tag
        """
        return nltk.pos_tag([word], lang=self.lang_code)[0]

    def getWordTag(self, word):
        """
        Returns the given word's tag.

        Caveat: tagging single words outside the context of
        a sentence results in higher errors.

        :param word: str, word to tag
        :return: str, given word's tag
        """
        return self.getWordAndTag(word)[1]

    def tokensToTags(self, token_phrase):
        """
        Given a list of strings composing a phrase, returns a list of words'
        part-of-speech tags in that order.

        :param token_phrase: List[str], list of word tokens from a phrase
        :return: List[str], list of word part-to-speech tags
        """
        tagged_phrase = nltk.pos_tag(token_phrase, lang=self.lang_code)  # tokens tagged according to word type
        tagged_list = []
        for tup in tagged_phrase:
            tagged_list.append(tup[1])
        return tagged_list

    def getTokenPhrase(self, phrase):
        """
        Returns a list of word tokens in phrase.

        :param phrase: str, text with >=1 words
        :return: List[str], list of word tokens
        """
        return [word for word in nltk.word_tokenize(phrase, language=self.language.lower())]

    def getTokenPhrases(self, phrases):
        """
        Returns a list of word tokens in phrases,
        with a newline in between each phrase.

        :param phrases: List[str], phrases to tokenize
        :return: List[str], list of word tokens
        """
        token_phrases = []
        for phrase in phrases:
            token_phrases.extend(self.getTokenPhrase(phrase))
            token_phrases.append("\n")
        return token_phrases

    def isNoun(self, word):
        """
        Returns True if word is a noun, False otherwise.

        :param word: str, word to test whether a noun
        :return: bool, whether given word is a noun
        """
        tag = self.getWordTag(word)
        return tag[0:2] == "NN"

    def isPluralNoun(self, word):
        """
        Returns True if word is a plural noun, False otherwise.

        :param word: str, word to test whether a plural noun
        :return: bool, whether given word is a plural noun
        """
        return self.getWordTag(word) == "NNS"

    def isVerb(self, word):
        """
        Returns True if word is a verb, False otherwise.

        :param word: str, word to test whether a verb
        :return: bool, whether given word is a verb
        """
        tag = self.getWordTag(word)
        return tag[0:2] == "VB"

    def isAdj(self, word):
        """
        Returns True if word is an adjective, False otherwise.

        :param word: str, word to test whether an adjective
        :return: bool, whether given word is an adjective
        """
        tag = self.getWordTag(word)
        return tag[0:2] == "JJ"

    def isPunctuation(self, word):
        """
        Returns True if the input is a punctuation mark.

        :param word: str, word to see if punctuation
        :return: bool, whether word is punctuation
        """
        return word in BlissTranslator.PUNCTUATION

    def isStartingPunct(self, word):
        """
        Returns True if the input is starting punctuation.

        :param word: str, word to see if starting punctuation
        :return: bool, whether word is starting punctuation
        """
        return word in BlissTranslator.STARTING_PUNCT

    def isEndingPunct(self, word):
        """
        Returns True if the input is ending punctuation.

        :param word: str, word to see if ending punctuation
        :return: bool, whether word is ending punctuation
        """
        return word in BlissTranslator.ENDING_PUNCT

    def isNewline(self, word):
        """
        Returns True if the input is a newline.

        :param word: str, word to see if newline
        :return: bool, whether word is newline
        """
        return word == "\n"

    def getWordPOS(self, word):
        """
        Returns the given word's part of speech, abbreviated as a
        single letter.

        POS constants (from WordNet.py):
            ADJ, ADJ_SAT, ADV, NOUN, VERB = 'a', 's', 'r', 'n', 'v'

        :param word: str, word to determine pos
        :return: str, letter representing input word's pos
        """
        if self.isNoun(word):
            return "n"
        elif self.isVerb(word):
            return "v"
        elif self.isAdj(word):
            return "a"
        elif self.getWordTag(word)[0:2] == "RB":
            return "r"
        else:
            return "n"
        #elif self.getWordTag(word) == "JJS":
        #    return "s"

    def isChosenPOS(self, pos):
        """
        Returns True if words with the given part of
        speech should be translated, False otherwise.

        :param pos: str, part-of-speech tag
        :return: bool, whether to translate pos
        """
        return pos in BlissTranslator.CHOSEN_POS

    def getSingular(self, word):
        """
        Returns the singular form of the given word
        in this BlissTranslator's set language.
        ~
        If word cannot be singularized for this
        language, this method returns the input.

        :param word: str, word to singularize
        :return: str, singularized input
        """
        if self.language == "English":
            return pattern.text.en.singularize(word)
        elif self.language == "Spanish":
            return pattern.text.es.singularize(word)
        elif self.language == "German":
            return pattern.text.de.singularize(word)
        elif self.language == "French":
            return pattern.text.fr.singularize(word)
        elif self.language == "Italian":
            return pattern.text.it.singularize(word)
        elif self.language == "Dutch":
            return pattern.text.nl.singularize(word)
        else:
            return word

    def getInfinitive(self, verb):
        """
        Returns the infinitive of the given verb
        in this BlissTranslator's set language.
        ~
        If no infinitive can be found in set language,
        this method returns the input.

        :param verb: str, verb
        :return: str, lemma of verb
        """
        if self.language == "English":
            return pattern.text.en.lemma(verb)
        elif self.language == "Spanish":
            return pattern.text.es.lemma(verb)
        elif self.language == "German":
            return pattern.text.de.lemma(verb)
        elif self.language == "French":
            return pattern.text.fr.lemma(verb)
        elif self.language == "Italian":
            return pattern.text.it.lemma(verb)
        elif self.language == "Dutch":
            return pattern.text.nl.lemma(verb)
        else:
            return verb

    def getPredicative(self, adj):
        """
        Returns the base form of the given adjective
        in this BlissTranslator's set language.
        ~
        If no base form can be found in set language,
        this method returns the input.

        e.g. well   -> good
             belles -> beau

        :param adj: str, adjective
        :return: str, base form of input adj
        """
        if self.language == "English":
            return pattern.text.en.predicative(adj)
        elif self.language == "Spanish":
            return pattern.text.es.predicative(adj)
        elif self.language == "German":
            return pattern.text.de.predicative(adj)
        elif self.language == "French":
            return pattern.text.fr.predicative(adj)
        elif self.language == "Italian":
            return pattern.text.it.predicative(adj)
        elif self.language == "Dutch":
            return pattern.text.nl.predicative(adj)
        else:
            return adj

    def getLexeme(self, word):
        """
        Retrieves the given word's lexeme,
        i.e., the word in dictionary entry form.

        e.g. getLexeme(ran) -> "run"
             getLexeme(puppies) -> "puppy"

        Note: if a lexeme for the given word cannot
        be found, this method returns the input.

        :param word: str, word to convert to lexeme
        :return: str, lexeme of input word
        """
        if word in self.bliss_dict:
            return word
        elif self.language == "Polish":
            try:
                self.polish_lexicon[word]
            except KeyError:
                return word
            else:
                return self.polish_lexicon[word]
        else:
            if self.getSingular(word) in self.bliss_dict:
                return self.getSingular(word)
            elif self.getInfinitive(word) in self.bliss_dict:
                return self.getInfinitive(word)
            elif self.getPredicative(word) in self.bliss_dict:
                return self.getPredicative(word)
            else:
                return word

    def isTranslatable(self, word):
        """
        Returns True if word or word lexeme can be translated to
        Blissymbols, False otherwise.

        :param word: str, word to test whether translatable
        :return: bool, whether given word is translatable
        """
        return self.getLexeme(word) in self.bliss_dict

    def isSynonymTranslatable(self, word):
        """
        Given a word, returns True if any of its synonyms
        are translatable.

        :param word: str, word to generate synonyms
        :return: bool, whether word synonyms are translatable
        """
        synonym = self.translateUntranslatable(word)
        return synonym != ""

    def canBeTranslated(self, word):
        """
        Returns True if given word or any of its synonyms
        are translatable, False otherwise.

        :param word: str, word to see if can be translated
        :return: bool, whether word can be translated
        """
        return self.isTranslatable(word) or self.isSynonymTranslatable(word)

    def chooseDefn(self, word):
        """
        Returns an integer representing user's selection for
        the correct word definition by as an index in given word's
        list of definitions.
        ~
        If list of definitions contains only 1 item, returns 0.

        :param word: str, a word to choose a definition for
        :return: int, the index of the given word's proper definition
        """
        if word not in self.defns_chosen.keys():
            defns = self.bliss_dict[word]
            assert type(defns) == list
            idx = 1
            print("The word '" + word + "' has multiple definitions:\n")

            for defn in defns:
                print("Definition " + str(idx) + ": " + defn[:-4] + "\n")
                idx += 1

            choice = input("Which of these definitions is most appropriate? ")
            print("\n")

            try:
                defns[choice]
            except IndexError:
                choice = 0
            else:
                choice -= 1  # subtract 1 from choice for 0-based indexing
                self.defns_chosen[word] = choice
            return choice
        else:
            return self.defns_chosen[word]

    def getWordSynsets(self, word):
        """
        Returns a list of WordNet synsets for the given word.

        WordNet lookup link here:
        http://wordnetweb.princeton.edu/perl/webwn?s=&sub=Search+WordNet

        :param lexeme: str, a word to lookup in WordNet
        :return: List[Synset], the word's synsets
        """
        pos = self.getWordPOS(word)
        synsets = wordnet.synsets(word, pos, lang=self.lang_code)
        if len(synsets) == 0:
            synsets = wordnet.synsets(word, lang=self.lang_code)
        return synsets

    def getSynsetLemmas(self, synset):
        """
        Given a synset, returns a list of its lemma names.

        :param synset: Synset, WordNet synset
        :return: List[str], WordNet lemma names
        """
        return synset.lemma_names(lang=self.lang_code)

    def getSynsetsLemmas(self, synsets):
        """
        Given a list of WordNet synsets, returns a list
        of all of their lemma names.

        :param synsets: List[Synset], synsets
        :return: List[str], lemmas for all synsets
        """
        lemmas = []
        for synset in synsets:
            lemmas.extend(self.getSynsetLemmas(synset))
        return lemmas

    def getWordSynsetsLemmas(self, word):
        """
        Returns all lemma names in all synsets
        associated with given word.

        :param word: str, a word to lookup in WordNet
        :return: List[str], all this word's synsets' lemmas
        """
        return self.getSynsetsLemmas(self.getWordSynsets(word))

    def translateSynsets(self, synsets):
        """
        Given a list of synsets, attempts to translate each
        synset into Blissymbols.
        ~
        If a synonym is translatable to Blissymbols, return
        that synonym. Otherwise, return the empty string.

        :param synsets: List[Synset], a root word and its synonyms
        :return: str, first word in synset translatable to Blissymbols
        """
        for synset in synsets:
            for lemma in self.getSynsetLemmas(synset):
                if self.isTranslatable(lemma):
                    return self.getLexeme(lemma)
        return ""

    def translateUntranslatable(self, word):
        """
        Attempts to translate the given word's synonyms to
        Blissymbols.
        ~
        If a synonym can be translated, this method returns
        that synonym. Otherwise, this method returns the
        input word.

        :param word: str, word to translate to Blissymbols
        :return: str, translatable synonym of given word
        """
        return self.translateSynsets(self.getWordSynsets(word))

    def getSynsetDefn(self, synset):
        """
        Returns this Synset's definition.

        :param synset: Synset, a WordNet synset
        :return: str, the given synset's definition
        """
        return synset.definition()

    def getWordDefn(self, word):
        """
        Returns the first possible definition for the
        given word.

        :param word: str, the word to define
        :return: str, the word's first possible definition
        """
        return self.getSynsetDefn(self.getWordSynsets(word)[0])

    def getWordDefns(self, word, single=False):
        """
        Returns a list of possible definitions for the
        given word.
        ~
        If single is True, then this method will
        return the first definition reached.

        :param word: str, the word to define
        :param single: bool, whether to return the first
            definition reached
        :return: List[str], the word's possible definitions
        """
        defns = []
        synsets = self.getWordSynsets(word)

        for synset in synsets:
            defns.append(self.getSynsetDefn(synset))
            if single:
                return defns

        return defns

    def getWordAtIndex(self, token_phrase, idx):
        """
        A try-catch block for returning the word
        token in token_phrase at specified idx.
        ~
        If index cannot be reached, this method returns
        the empty string.

        :param token_phrase: List[str], word tokens
        :param idx: int, index to access in token_phrase
        :return: str, word token at specified idx
        """
        try:
            token_phrase[idx]
        except IndexError:
            return ""
        else:
            return token_phrase[idx]

    def getTitle(self, title, phrase):
        """
        Returns a valid title for the given phrase.
        ~
        If input title is None, this method returns the first 20
        alphabetic characters and/or spaces in phrase as a working title.
        Otherwise, this method returns the input title's valid characters.

        :param title: None or str, user-selected title
        :param phrase: str, phrase being titled
        :return: str, valid title for given phrase
        """
        if title is None:
            title = phrase[:20]
        return title

    def parsePlaintext(self, filename):
        """
        Parses plaintext file with given filename and returns a string representing
        its contents.

        :param filename: str, filename of text file
        :return: str, text file's contents
        """
        contents = []
        slash = "/" if filename[0] != "/" else ""

        with open(FILE_PATH + slash + filename, "rb") as text:
            for line in text:
                contents.append(line)

        return "".join(contents)

    # TRANSLATOR
    # ==========
    def translate(self, phrase, title=None, img_w=816, img_h=1056):
        """
        Translates input phrase to Blissymbols according to this
        BlissTranslator's POS and language preferences.
        ~
        Saves translation to a PDF file in this directory's
        bliss pdfs folder with the given title, or otherwise
        titled after the given phrase's first 20 characters.
        ~
        Default image size is 816x1056px (standard PDF page).

        :param phrase: str, text in BlissTranslator's native language
        :param title: None or str, desired title for output PDF
        :param img_w: int, desired width of PDF images (in pixels)
        :param img_h: int, desired height of PDF images (in pixels)
        :return: None, saves PDF with translation to bliss pdfs folder
        """
        # TODO: refactor translate() & drawAlphabet() for less repetition
        # TODO: refactor tokenizing to allow translating compound words & hyphenates
        title, phrase = self.unicodize(title), self.unicodize(phrase)
        phrase = phrase.replace("-", " - ")
        phrases = phrase.split("\n")  # split input by newlines
        token_phrase = self.getTokenPhrases(phrases)
        tagged_list = self.tokensToTags(token_phrase)
        raw_phrase = [word.lower() for word in token_phrase]

        pages = []  # translated images to convert to PDF
        title_page = self.makeTitlePage(title, img_w, img_h)
        pages.append(title_page)

        bg = self.makeBlankImg(img_w, img_h)
        indent = self.font_size
        line_no = 0
        idx = 0

        for word in raw_phrase:
            lexeme = self.getLexeme(word)

            if not self.isPunctuation(word) and self.isChosenPOS(tagged_list[idx]) and self.canBeTranslated(lexeme):
                # checks if word can be validly translated into Blissymbols
                # and it suits our part-of-speech selections
                if self.fast_translate or self.isSeen(lexeme):
                    # checks if we've already seen/translated the word before
                    # or if we want to translate words immediately
                    if self.isTranslatable(lexeme):
                        new_lexeme = lexeme
                    else:
                        new_lexeme = self.getLexeme(self.translateUntranslatable(word))

                    try:
                        self.getBlissImg(new_lexeme, img_w/2, self.image_heights/2)
                    except KeyError or IOError:
                        img = self.getWordImg(token_phrase[idx], self.font_size)
                    else:
                        if self.isChanged(lexeme) and not self.sub_all:
                            img = self.getBlissImg(new_lexeme, img_w/2, self.image_heights/2)
                        else:
                            # adds subtitles to new words
                            img = self.drawAlphabet(word)
                            self.addChanged(lexeme)
                        # affixes plural Blissymbol to plural nouns
                        if self.isPluralNoun(word):
                            img = self.getPluralImg(img, img_w/2)
                else:
                    # if we haven't seen the word before,
                    # then render text
                    img = self.getWordImg(token_phrase[idx], self.font_size)
                    self.addSeen(lexeme)
            else:
                # if word can't be translated to Blissymbols,
                # then render text
                img = self.getWordImg(token_phrase[idx], self.font_size)

            space = self.getSpaceSize()
            x_inc = indent + self.getWordWidth(img)
            y_inc = self.font_size * 3

            this_word = raw_phrase[idx]
            next_word1 = self.getWordAtIndex(raw_phrase, idx+1)
            next_word2 = self.getWordAtIndex(raw_phrase, idx+2)

            # TODO: design a method to handle spacing between irregular characters
            if next_word1 == "n't":
                space = self.getMinSpace()
            elif self.isEndingPunct(this_word) and self.isEndingPunct(next_word1):
                space = self.getMinSpace()
            elif self.isStartingPunct(next_word1) or self.isEndingPunct(this_word):
                space = self.getSpaceSize()
            elif self.isEndingPunct(next_word1) or self.isStartingPunct(this_word):
                space = self.getMinSpace()

            # TODO: design a method to handle indentation/linenumbers
            if x_inc > img_w:
                indent = 0
                line_no += 1
            elif self.isEndingPunct(next_word2) or self.isStartingPunct(next_word1):
                if (x_inc + self.getWordWidth(next_word1) + space*2 + self.getWordWidth(next_word2)) > img_w:
                    # don't let punctuation trail onto next line alone
                    indent = 0
                    line_no += 1
            elif this_word == "\n":
                indent = self.font_size
                line_no += 1

            if (line_no + 1) * y_inc > img_h:
                # if the next line would go beyond the image,
                # store the current page and go onto a new one
                pages.insert(0, bg)
                bg = self.makeBlankImg(img_w, img_h)
                line_no = 0

            # TODO: modify paste to work with vector bliss files (for aesthetic resizing)
            bg.paste(img, (indent, self.incLine(line_no, y_inc)))
            indent += self.getWordWidth(img) + space
            idx += 1

        pages.insert(0, bg)
        self.makePdf(title, self.saveImages(pages[::-1]), margins=50)
        self.initSeenChanged()

    def translateFile(self, filename, title=None, img_w=816, img_h=1056):
        """
        Parses a plaintext file in this directory with given filename
        to a string, then passes the result as a phrase to translate().

        :param filename: str, .txt file in this directory
        :param title: None or str, desired title for output PDF
        :param img_w: int, desired width of PDF images (in pixels)
        :param img_h: int, desired height of PDF images (in pixels)
        :return: None
        """
        phrase = self.parsePlaintext(filename)
        self.translate(phrase, title, img_w, img_h)