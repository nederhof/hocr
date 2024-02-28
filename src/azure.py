import sys
import json

from imageprocessing import make_image
from segments import Segment

class AzurePage:
	def __init__(self, filename):
		with open(filename, 'r') as f:
			self.results = json.load(f)

	def words(self):
		return [AzureWord(word) for word in self.results['analyzeResult']['pages'][0]['words']]

class AzureWord:
	def __init__(self, word):
		self.content = word['content']
		self.confidence = word['confidence']
		polygon = word['polygon']
		self.x = polygon[0]
		self.y = polygon[1]
		self.w = polygon[2] - polygon[0]
		self.h = polygon[5] - polygon[1]
		
	def white_segment(self):
		im = make_image(self.w, self.h, [])
		return Segment(im, self.x, self.y)

# For testing
def open_window(filename):
	import tkinter as tk
	from rectangleselection import RectangleSelector
	root = tk.Tk()
	app = RectangleSelector(root, lambda segments: print(len(segments)))
	jsonfile = filename + '.json'
	page = AzurePage(jsonfile)
	segments = [word.white_segment() for word in page.words() if word.confidence < 0.8]
	app.set_image(filename)
	app.set_segments(segments)
	app.mainloop()

# For testing
def list_words(filename):
	page = AzurePage(filename)
	for word in page.words():
		if word.confidence < 0.8:
			print(word.x, word.y, word.w, word.h, word.content, word.confidence)

# For testing
if __name__ == '__main__':
	if len(sys.argv) >= 2:
		filename = sys.argv[1]
		open_window(filename)
