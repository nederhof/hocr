import re
import sys
import csv
import os
import string

from findhiero import find_hiero_in_page
from train import default_letter_model_dir
from azure import AzurePage
from simpleocr import FontInfo, median_height, do_ocr

transcription_dir = 'transcriptions'

def recognize_hiero(imagefile):
	csvfile = imagefile + '.csv'
	if not os.path.isfile(csvfile):
		find_hiero_in_page(imagefile)
		return False
	else:
		return True

def read_csv(imagefile):
	csvfile = imagefile + '.csv'
	with open(csvfile) as handler:
		reader = csv.reader(handler, delimiter=' ')
		rows = list(reader)
	rows = [{'x': int(x), 'y': int(y), 'w': int(w), 'h': int(h), 'ch': ch} for x, y, w, h, ch in rows]
	return rows

def remove_hiero(page, hiero):
	page.remove_words(hiero['x'], hiero['y'], hiero['w'], hiero['h'])

def add_hiero(page, hiero):
	page.add_word(hiero['ch'], 'hiero', hiero['x'], hiero['y'], hiero['w'], hiero['h'])

def do_simple_ocr(page):
	unit_height = median_height(page.im)
	fontinfo = FontInfo(default_letter_model_dir, unit_height)
	for line in page.lines:
		for word in line.words:
			adjust_word(page, word, fontinfo)
	return unit_height

def adjust_word(page, word, fontinfo):
	subimage = page.im.crop((word.x, word.y, word.x+word.w, word.y+word.h))
	style, content = do_ocr(page, word, fontinfo)
	if word.style == 'normal':
		match style:
			case 'bold':
				word.style = style
			case 'smallcaps':
				if not word.content.lower() in \
					['on', 'of', 'to', 'two', 'no.', 'nos.', 'gods', 'stool']:
					word.style = style
	if word.confidence < 0.8:
		if not re.match('^[0-9\-\.,;\(\)\[\]xi]+$', word.content):
			word.content = content
	word.content = re.sub(r'\bIst\b', '1st', word.content)
	if re.match(r'[0-9]', word.content):
		word.content = word.content.replace('o', '0')
		word.content = word.content.replace('I', '1')
		word.content = word.content.replace('l', '1')
		word.content = word.content.replace('z', '2')
	if word.style == 'smallcaps':
		word.content = word.content.title()

def get_page(imagefile):
	return AzurePage(imagefile)

def produce_html(imagefile):
	if not os.path.exists(transcription_dir):
		os.mkdir(transcription_dir)
	name, _ = os.path.splitext(os.path.basename(imagefile))
	page = get_page(imagefile)
	hieros = read_csv(imagefile)
	for hiero in hieros:
		remove_hiero(page, hiero)
	for hiero in hieros:
		add_hiero(page, hiero)
	unit_height = do_simple_ocr(page)
	page.merge_paras(2 * unit_height)
	page.to_html(transcription_dir, name, cutouts=False)
	page.to_html(transcription_dir, name, cutouts=True)

if __name__ == '__main__':
	if len(sys.argv) >= 2:
		imagefile = sys.argv[1]
		recognize_hiero(imagefile) and produce_html(imagefile)
