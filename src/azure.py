import sys
import os
import json
from PIL import Image

from imageprocessing import make_image
from segments import Segment
from ocrresults import OcrPage, OcrPara, OcrLine, OcrWord

def polygon_to_rect(poly):
	xmin = poly[0]
	xmax = poly[0]
	ymin = poly[1]
	ymax = poly[1]
	for i in range(2, len(poly), 2):
		xmin = min(xmin, poly[i])
		xmax = max(xmax, poly[i])
		ymin = min(ymin, poly[i+1])
		ymax = max(ymax, poly[i+1])
	return xmin, ymin, xmax-xmin, ymax-ymin

class AzurePage(OcrPage):
	def __init__(self, filename):
		OcrPage.__init__(self, filename)
		json_name = filename + '.json'
		if not os.path.exists(json_name):
			print('Need JSON in', json_name)
			exit(0)
		with open(json_name, 'r') as f:
			self.results = json.load(f)
		self.paras = [self.make_para(para) for para in self.results['analyzeResult']['paragraphs']]
		self.lines = [self.make_line(line) for line in self.results['analyzeResult']['pages'][0]['lines']]
		for line in self.lines:
			self.line_in_para(line)
		for word in self.results['analyzeResult']['pages'][0]['words']:
			self.word_in_line(self.make_word(word))
		for elem in self.results['analyzeResult']['styles']:
			if 'fontStyle' in elem:
				style = elem['fontStyle']
				for span in elem['spans']:
					offset = span['offset']
					length = span['length']
					self.style_in_words(offset, length, style)
		self.text_corners = self.get_text_corners()

	def make_para(self, para):
		offset = para['spans'][0]['offset']
		length = para['spans'][0]['length']
		x, y, w, h = polygon_to_rect(para['boundingRegions'][0]['polygon'])
		return OcrPara(offset, length, x, y, w, h)

	def make_word(self, word):
		content = word['content']
		confidence = word['confidence']
		offset = word['span']['offset']
		length = word['span']['length']
		x, y, w, h = polygon_to_rect(word['polygon'])
		return OcrWord(content, confidence, offset, length, x, y, w, h)

	def make_line(self, line):
		offset = line['spans'][0]['offset']
		length = line['spans'][0]['length']
		return OcrLine(offset, length)

	def word_in_line(self, word):
		for line in self.lines:
			if line.offset <= word.offset and word.offset < line.offset + line.length:
				line.words.append(word)
				return
		print("Error: Word not in line", word.content)

	def line_in_para(self, line):
		for para in self.paras:
			if para.offset <= line.offset and line.offset < para.offset + para.length:
				para.lines.append(line)
				return
		print("Error: Line not in paragraph")

	def style_in_words(self, offset, length, style):
		if style == 'normal':
			return
		for line in self.lines:
			if line.offset <= offset and offset < line.offset + line.length or \
					line.offset <= offset+length and offset+length < line.offset + line.length:
				for word in line.words:
					if offset <= word.offset and word.offset < offset + length:
						word.style = style

# For testing
def open_window(filename):
	import tkinter as tk
	from rectangleselection import RectangleSelector
	root = tk.Tk()
	app = RectangleSelector(root, lambda segments: print(len(segments)))
	page = AzurePage(filename)
	# segments = [word.white_segment() for line in page.lines for word in line.words if word.confidence < 0.8]
	# segments = [word.white_segment() for line in page.lines for word in line.words if word.style == 'italic']
	# segments = [word.white_segment() for line in page.lines for word in line.words]
	segments = [para.white_segment() for para in page.paras]
	app.set_image(filename)
	app.set_segments(segments)
	app.mainloop()

# For testing
def list_words(filename):
	page = AzurePage(filename)
	for line in page.lines:
		for word in line.words:
			# if word.confidence < 0.8:
			if word.style == 'italic':
				print(word.x, word.y, word.w, word.h, word.content, word.confidence)

# For testing
if __name__ == '__main__':
	if len(sys.argv) >= 2:
		filename = sys.argv[1]
		open_window(filename)
		# list_words(filename)
