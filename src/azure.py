import sys
import json
from PIL import Image

from imageprocessing import make_image
from segments import Segment

def polygon_to_rect(poly):
	x = poly[0]
	y = poly[1]
	w = poly[2] - poly[0]
	h = poly[5] - poly[1]
	return x, y, w, h

class AzurePage:
	def __init__(self, filename):
		self.im = Image.open(filename)
		self.w, self.h = self.im.size
		with open(filename + '.json', 'r') as f:
			self.results = json.load(f)
		self.lines = [AzureLine(line) for line in self.results['analyzeResult']['pages'][0]['lines']]
		words = [AzureWord(word) for word in self.results['analyzeResult']['pages'][0]['words']]
		for word in words:
			self.word_in_line(word)
		for elem in self.results['analyzeResult']['styles']:
			if 'fontStyle' in elem:
				style = elem['fontStyle']
				for span in elem['spans']:
					offset = span['offset']
					length = span['length']
					self.style_in_words(offset, length, style)

	def word_in_line(self, word):
		for line in self.lines:
			if line.offset <= word.offset and word.offset < line.offset + line.length:
				line.words.append(word)
				return
		print("Error: Word not in line", word.content)

	def style_in_words(self, offset, length, style):
		if style == 'normal':
			return
		for line in self.lines:
			if line.offset <= offset and offset < line.offset + line.length or \
					line.offset <= offset+length and offset+length < line.offset + line.length:
				for word in line.words:
					if offset <= word.offset and word.offset < offset + length:
						word.style = style

	def remove_words(self, x, y, w, h):
		None

	def add_word(self, content, x, y, w, h):
		None

class AzureLine:
	def __init__(self, line):
		self.offset = line['spans'][0]['offset']
		self.length = line['spans'][0]['length']
		self.words = []

class AzureWord:
	def __init__(self, word):
		self.content = word['content']
		self.confidence = word['confidence']
		self.offset = word['span']['offset']
		self.length = word['span']['length']
		self.x, self.y, self.w, self.h = polygon_to_rect(word['polygon'])
		self.style = 'plain'
		
	def white_segment(self):
		im = make_image(self.w, self.h, [])
		return Segment(im, self.x, self.y)

# For testing
def open_window(filename):
	import tkinter as tk
	from rectangleselection import RectangleSelector
	root = tk.Tk()
	app = RectangleSelector(root, lambda segments: print(len(segments)))
	page = AzurePage(filename)
	# segments = [word.white_segment() for line in page.lines for word in line.words if word.confidence < 0.8]
	segments = [word.white_segment() for line in page.lines for word in line.words if word.style == 'italic']
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
		# open_window(filename)
		list_words(filename)
