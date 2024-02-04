import re
import os 

from names import get_unicode_to_name, numerals

def get_basenames(d):
	bases = set()
	filenames = os.listdir(d)
	for filename in filenames:
		base, ext = os.path.splitext(filename)
		basename = re.sub('-[0-9]+', '', base)
		if ext == '.png':
			bases.add(basename)
	return bases

def check_completeness(examplar_dir):
	filenames = get_basenames(examplar_dir)
	unicode_to_name = get_unicode_to_name()
	for code in sorted(unicode_to_name):
		name = unicode_to_name[code]
		filename = str(ord(code))
		if re.match(r'^[A-Z].*', name) and filename not in filenames and name not in numerals:
			print(name)

if __name__ == '__main__':
	check_completeness('gardiner')
