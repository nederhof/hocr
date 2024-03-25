import os
import pickle
import json
from PIL import Image, ImageOps, ImageFont, ImageDraw

from controls import TS, BS, TE, BE, M, T, B

signlist_dir = 'signlist'
font_name = 'NewGardinerSMP.ttf'
font_size = 50
first_char = 0x13000
last_char = 0x1342F

def get_name_to_unicode():
	filename = os.path.join(signlist_dir, 'unipoints.json')
	with open(filename, 'r') as f:
		name_to_unicode = json.load(f)
	return name_to_unicode

def make_names():
	name_to_unicode = get_name_to_unicode()
	names = {chr(u): n for n, u in name_to_unicode.items()}
	picklename = os.path.join(signlist_dir, 'names.pickle')
	with open(picklename, 'wb') as handle:
		pickle.dump(names, handle)

def get_unicode_to_name():
	picklename = os.path.join(signlist_dir, 'names.pickle')
	with open(picklename, 'rb') as handle:
		names = pickle.load(handle)
	return names

# Numerals that are composite or that look very much like other signs.
# Not to be recognized directly, but reconstructed as one or more other signs,
# possibly analyzing context.
numerals = {'D50a', 'D50b', 'D50c', 'D50d', 'D50e', 'D50f', 'D50g', 'D50h', 'D50i', \
		'D67a', 'D67b', 'D67c', 'D67d', 'D67e', 'D67f', 'D67g',  'D67h', \
		'M12a', 'M12b', 'M12c', 'M12d', 'M12e', 'M12f', 'M12g',  'M12h', \
		'V1a', 'V1b', 'V1c', 'V1d', 'V1e', 'V1f', 'V1g',  'V1h', 'V1i', \
		'V20a', 'V20b', 'V20c', 'V20d', 'V20e', 'V20f', 'V20g',  'V20h', \
		'V20i', 'V20j', 'V20k', 'V20l', 'V40a', \
		'Z15', 'Z15a', 'Z15b', 'Z15c', 'Z15d', 'Z15e', 'Z15f', 'Z15g',  'Z15h', 'Z15i', \
		'Z16a', 'Z16b', 'Z16c', 'Z16d', 'Z16e', 'Z16f', 'Z16g',  'Z16h'}

# Composite signs that should only be recognized as such if occurring as a single component.
# If occurring as multiple components, they can be recognized using controls.
composite = {'D31', 'D31a', 'F51a', 'F51b', 'G43a', 'I11a', 'M17a', 'M22a', 'O30a', 'W24a'}

# Composite signs consisting of repeated occurrences of the same shape
# that is itself also in the sign list, so the composite sign can be
# reconstructed from the multiple occurences of the single shape.
repeated_single = {'N33a', 'N35a', 'Z2', 'Z2a', 'Z2b', 'Z2c', 'Z2d', 'Z3', 'Z3a', 'Z3b', 'Z4a'}

# Composite signs consisting of repeated occurrences of the same shape,
# but the individual shape is not in the sign list.
# Special treatment is needed.
repeated_non_single = {'M33', 'M33a', 'M33b', 'Z4'}

# Default positions of corner insertion. May be overridden for specific signs.
corner_position = { 'ts': [0,0], 'bs': [0,1], 'te': [1,0], 'be': [1,1], \
	'm': [0.5,0.5], 't': [0.5,0], 'b': [0.5,1] }

corner_control = { 'ts': TS, 'bs': BS, 'te': TE, 'be': BE, 'm': M, 't': T, 'b': B }

def make_insertions():
	filename = os.path.join(signlist_dir, 'insertions.json')
	with open(filename, 'r') as f:
		name_to_insertions = json.load(f)
	insertions = {}
	for name, glyphs in name_to_insertions.items():
		insertions[name] = {}
		for glyph in glyphs:
			for corner in ['ts', 'bs', 'te', 'be', 'm', 't', 'b']:
				if corner in glyph and corner not in insertions[name]:
					control = corner_control[corner]
					insertions[name][control] = corner_position[corner].copy()
					if 'x' in glyph[corner]:
						insertions[name][control][0] = glyph[corner]['x']
					if 'y' in glyph[corner]:
						insertions[name][control][1] = glyph[corner]['y']
	picklename = os.path.join(signlist_dir, 'insertions.pickle')
	with open(picklename, 'wb') as handle:
		pickle.dump(insertions, handle)

def get_insertions():
	picklename = os.path.join(signlist_dir, 'insertions.pickle')
	with open(picklename, 'rb') as handle:
		insertions = pickle.load(handle)
	return insertions

def glyph_size(c, font, font_size):
	img = Image.new('RGB', (font_size * 2, font_size * 2), (255, 255, 255))
	draw = ImageDraw.Draw(img)
	draw.text((0, 0), c, font=font, fill='black')
	inverted = ImageOps.invert(img)
	bbox = inverted.getbbox()
	return bbox[2]-bbox[0], bbox[3]-bbox[1]

def rel_dimensions(font, font_size, first_char, last_char):
	c_first = chr(first_char)
	_, unit = glyph_size(c_first, font, font_size)
	ch_to_size = {}
	chars = list(range(first_char, last_char+1)) + [0x5B, 0x5D]
	for num in chars:
		c = chr(num)
		w, h = glyph_size(c, font, font_size)
		ch_to_size[c] = (w / unit, h / unit)
	return ch_to_size

def make_dimensions():
	font_path = os.path.join(signlist_dir, font_name)
	font = ImageFont.truetype(font_path, font_size)
	dims = rel_dimensions(font, font_size, first_char, last_char)
	with open(os.path.join(signlist_dir, 'dimensions.pickle'), 'wb') as handle:
		pickle.dump(dims, handle)

if __name__ == '__main__':
	make_names()
	make_insertions()
	make_dimensions()
