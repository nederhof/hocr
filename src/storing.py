import os
import sys
import json
import tkinter as tk
from PIL import Image, ImageTk

from names import get_name_to_unicode, get_unicode_to_name
from transcribe import FontInfo, classify_image_full

name_to_unicode = get_name_to_unicode()
unicode_to_name = get_unicode_to_name()

model_dir = 'model'
exemplar_dir = 'newgardiner'
target_dir = 'gardiner'

fontinfo = FontInfo(model_dir)

CANVAS_SIZE = 200

def classify(im):
	indexes = classify_image_full(im, 1, fontinfo)
	return ord(fontinfo.chars[indexes[0]])

class Storer(tk.Frame):
	def __init__(self, root, im, callback):
		self.root = root
		self.im = im
		self.callback = callback
		tk.Frame.__init__(self, self.root)
		self.master.title('Store classified sign')
		self.master.protocol('WM_DELETE_WINDOW', self.root.destroy)
		self.add_token(im)
		self.code = classify(im)
		self.add_class(im)
		self.add_buttons()
		name = self.update_from_code()
		self.name.set(name)

	def add_token(self, im):
		self.token = tk.Canvas(self.master, width=CANVAS_SIZE, height=CANVAS_SIZE, bg='gray')
		self.token.pack()
		x_offset, y_offset, rescaled = self.rescale_image(im)
		self.im_token = ImageTk.PhotoImage(rescaled)
		self.token.create_image(x_offset, y_offset, anchor=tk.NW, image=self.im_token)

	def add_class(self, im):
		self.exemplar = tk.Canvas(self.master, width=CANVAS_SIZE, height=CANVAS_SIZE, bg='gray')
		self.exemplar.pack()
		self.name = tk.StringVar()
		self.entry = tk.Entry(self.master, textvariable=self.name, width=8, font=('bold', 30))
		self.entry.pack()
		self.entry.bind('<Return>', lambda event: self.update_from_name())
		self.number = tk.StringVar()
		self.label = tk.Label(self.master, textvariable=self.number, width=8, font=('bold', 30))
		self.label.pack()
		
	def add_buttons(self):
		self.buttons = tk.Frame(self.master)
		self.buttons.pack(pady=5)
		self.accept_button = tk.Button(self.buttons, text='Store', height=2, bg='green', fg='white', \
			font=('bold', 30), command=self.store)
		self.accept_button.pack(side=tk.LEFT)
		self.ignore_button = tk.Button(self.buttons, text='Ignore', height=2, bg='gray', fg='white', \
			font=('bold', 30), command=self.next)
		self.ignore_button.pack()

	def update_from_name(self):
		name = self.name.get()
		if name in name_to_unicode:
			self.code = name_to_unicode[name]
			self.update_from_code()

	def update_from_code(self):
		self.number.set(self.code)
		filename = os.path.join(exemplar_dir, str(self.code) + '.png')
		if os.path.exists(self.target_filename()):
			 self.accept_button.configure(bg='red', activebackground='red')
		else:
			 self.accept_button.configure(bg='green', activebackground='green')
		im = Image.open(filename)
		x_offset, y_offset, rescaled = self.rescale_image(im)
		self.im_code = ImageTk.PhotoImage(rescaled)
		self.exemplar.create_image(x_offset, y_offset, anchor=tk.NW, image=self.im_code)
		return unicode_to_name[chr(self.code)]

	def rescale_image(self, im):
		w, h = im.size
		s = max(w, h)
		scale = CANVAS_SIZE / s
		width = round(w * scale)
		height = round(h * scale)
		x_offset = (CANVAS_SIZE - width) // 2
		y_offset = (CANVAS_SIZE - height) // 2
		return x_offset, y_offset, im.resize((width, height))

	def store(self):
		self.im.save(self.target_filename())
		self.next()

	def target_filename(self):
		return os.path.join(target_dir, str(self.code) + '.png')

	def next(self):
		self.callback()
		self.root.destroy()

if __name__ == '__main__':
	root = tk.Tk()
	im = Image.open('tests/test4.png')
	gray = im.convert('L')
	app = Storer(root, gray)
	app.mainloop()

