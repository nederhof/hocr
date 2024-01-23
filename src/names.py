import pickle
import json

from controls import TS, BS, TE, BE, M, T, B

def make_names():
	with open('unipoints.json', 'r') as f:
		name_to_unicode = json.load(f)
	names = {chr(u): n for n, u in name_to_unicode.items()}
	with open('names.pickle', 'wb') as handle:
		pickle.dump(names, handle)

def get_names():
	with open('names.pickle', 'rb') as handle:
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
	with open('insertions.json', 'r') as f:
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
	with open('insertions.pickle', 'wb') as handle:
		pickle.dump(insertions, handle)

def get_insertions():
	with open('insertions.pickle', 'rb') as handle:
		insertions = pickle.load(handle)
	return insertions

if __name__ == '__main__':
	make_names()
	make_insertions()