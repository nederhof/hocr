import sys
import os
import json
from PIL import Image

from imageprocessing import make_image
from segments import Segment
from ocrresults import OcrPage, OcrPara, OcrLine, OcrWord

class TextractPage(OcrPage):
	def __init__(self, filename):
		OcrPage.__init__(self, filename)
		json_name = filename + '.textract.json'
		if not os.path.exists(json_name):
			print('Need JSON in', json_name)
			exit(0)
		with open(json_name, 'r') as f:
			self.results = json.load(f)
		blocks = self.results['Blocks']
		self.id_to_word = {}
		self.length = 0
		for block in blocks:
			if block['BlockType'] == 'WORD':
				self.make_word(block)
		self.id_to_line = {}
		self.lines = []
		for block in blocks:
			if block['BlockType'] == 'LINE':
				self.make_line(block)
		self.paras = []
		for block in blocks:
			if block['BlockType'] == 'LAYOUT_TEXT':
				self.make_para(block)
		self.text_corners = self.get_text_corners()

	def make_word(self, block):
		content = block['Text']
		confidence = block['Confidence'] / 100
		offset = self.length
		length = len(content)
		bb = block['Geometry']['BoundingBox']
		x = round(bb['Left'] * self.w)
		y = round(bb['Top'] * self.h)
		w = round(bb['Width'] * self.w)
		h = round(bb['Height'] * self.h)
		ident = block['Id']
		self.id_to_word[ident] = OcrWord(content, confidence, offset, length, x, y, w, h)

	def make_line(self, block):
		ids = block['Relationships'][0]['Ids']
		offset = None
		length = 0
		words = []
		for ident in ids:
			word = self.id_to_word[ident]
			if offset is None:
				offset = word.offset
			length += word.length
			words.append(word)
		line = OcrLine(offset, length)
		line.words = words
		self.lines.append(line)
		ident = block['Id']
		self.id_to_line[ident] = line

	def make_para(self, block):
		ids = block['Relationships'][0]['Ids']
		offset = None
		length = 0
		lines = []
		for ident in ids:
			line = self.id_to_line[ident]
			if offset is None:
				offset = line.offset
			length += line.length
			lines.append(line)
		bb = block['Geometry']['BoundingBox']
		x = round(bb['Left'] * self.w)
		y = round(bb['Top'] * self.h)
		w = round(bb['Width'] * self.w)
		h = round(bb['Height'] * self.h)
		para = OcrPara(offset, length, x, y, w, h)
		para.lines = lines
		self.paras.append(para)

# For testing
def open_window(filename):
	import tkinter as tk
	from rectangleselection import RectangleSelector
	root = tk.Tk()
	app = RectangleSelector(root, lambda segments: print(len(segments)))
	page = TextractPage(filename)
	# segments = [word.white_segment() for line in page.lines for word in line.words if word.confidence < 0.8]
	segments = [para.white_segment() for para in page.paras]
	app.set_image(filename)
	app.set_segments(segments)
	app.mainloop()

# For testing
def list_words(filename):
	page = TextractPage(filename)
	for line in page.lines:
		for word in line.words:
			if word.confidence < 0.8:
				print(word.x, word.y, word.w, word.h, word.content, word.confidence)

# For testing
if __name__ == '__main__':
	if len(sys.argv) >= 2:
		filename = sys.argv[1]
		open_window(filename)
		# list_words(filename)
