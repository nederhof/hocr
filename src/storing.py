import os
import sys
import json
import tkinter as tk
from PIL import Image, ImageTk

from tables import get_name_to_unicode, get_unicode_to_name
from transcribe import FontInfo as FontInfoSigns, classify_image_full
from simpleocr import FontInfo as FontInfoLetters, classify_image_letter, style_list

name_to_unicode = get_name_to_unicode()
unicode_to_name = get_unicode_to_name()

exemplar_sign_dir = 'newgardiner'
target_sign_dir = 'topbibhiero'
target_letter_dir = 'letters'

CANVAS_SIZE = 200

def classify_sign(im, fontinfo):
	indexes = classify_image_full(im, 1, fontinfo)
	return ord(fontinfo.chars[indexes[0]])

def classify_letter(im, fontinfo):
	index = classify_image_letter(im, 1, fontinfo)[0]
	return fontinfo.chars[index], fontinfo.styles[index]

def white_image():
	im = Image.new('RGBA', (CANVAS_SIZE, CANVAS_SIZE), 'WHITE')
	return 0, 0, im

class Storer(tk.Frame):
	def __init__(self, root, im, fontinfo, callback):
		self.root = root
		self.im = im
		self.fontinfo = fontinfo
		self.callback = callback
		tk.Frame.__init__(self, self.root)
		self.master.protocol('WM_DELETE_WINDOW', self.root.destroy)
		self.add_token(im)
		self.add_class(im)
		self.add_buttons()

	def add_token(self, im):
		self.token = tk.Canvas(self.master, width=CANVAS_SIZE, height=CANVAS_SIZE, bg='gray')
		self.token.pack()
		x_offset, y_offset, rescaled = self.rescale_image(im)
		self.im_token = ImageTk.PhotoImage(rescaled)
		self.token.create_image(x_offset, y_offset, anchor=tk.NW, image=self.im_token)

	def add_buttons(self):
		self.buttons = tk.Frame(self.master)
		self.buttons.pack(pady=5)
		self.accept_button = tk.Button(self.buttons, text='Store', height=2, bg='green', fg='white', \
			font=('bold', 30), command=self.store)
		self.accept_button.pack(side=tk.LEFT)
		self.ignore_button = tk.Button(self.buttons, text='Ignore', height=2, bg='gray', fg='white', \
			font=('bold', 30), command=self.next)
		self.ignore_button.pack()

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
		self.im.save(self.target_filename_unique())
		self.next()

	def next(self):
		self.callback()
		self.root.destroy()

	def target_filename_unique(self):
		i = 0
		while os.path.exists(self.target_filename(index=i)):
			i += 1
		return self.target_filename(index=i)

class SignStorer(Storer):
	def __init__(self, root, im, fontinfo, callback):
		Storer.__init__(self, root, im, fontinfo, callback)
		self.master.title('Store classified sign')
		self.code = classify_sign(im, fontinfo)
		name = self.update_from_code()
		self.name.set(name)

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

	def update_from_name(self):
		name = self.name.get()
		if name in name_to_unicode:
			self.code = name_to_unicode[name]
			self.update_from_code()
		elif name == 'shade':
			self.code = 0x13443
			self.update_from_code()
		elif name in ['[', ']']:
			self.code = ord(name)
			self.update_from_code()

	def update_from_code(self):
		self.number.set(self.code)
		filename = os.path.join(exemplar_sign_dir, str(self.code) + '.png')
		if os.path.exists(self.target_filename()):
			 self.accept_button.configure(bg='red', activebackground='red')
		else:
			 self.accept_button.configure(bg='green', activebackground='green')
		if os.path.exists(filename):
			im = Image.open(filename)
			x_offset, y_offset, rescaled = self.rescale_image(im)
		else:
			x_offset, y_offset, rescaled = white_image()
		self.im_code = ImageTk.PhotoImage(rescaled)
		self.exemplar.create_image(x_offset, y_offset, anchor=tk.NW, image=self.im_code)
		if chr(self.code) in unicode_to_name:
			return unicode_to_name[chr(self.code)]
		elif self.code == 0x13443:
			return 'shade'
		else:
			return chr(self.code)

	def target_filename(self, index=0):
		suffix = '-'+str(index) if index > 0 else ''
		return os.path.join(target_sign_dir, str(self.code) + suffix + '.png')

class LetterStorer(Storer):
	def __init__(self, root, im, fontinfo, callback):
		Storer.__init__(self, root, im, fontinfo, callback)
		self.add_height()
		self.master.title('Store classified letter')
		self.code, self.style = classify_letter(im, fontinfo)
		self.name.set(self.code)
		self.stylename.set(self.style)
		self.update_buttons()

	def add_height(self):
		height = round(self.im.size[1] / self.fontinfo.unit_height, 2)
		height_var = tk.StringVar()
		self.height_label = tk.Label(self.master, textvariable=height_var, width=8, font=('bold', 20))
		self.height_label.pack()
		height_var.set(height)

	def add_class(self, im):
		self.name = tk.StringVar()
		self.entry = tk.Entry(self.master, textvariable=self.name, width=8, font=('bold', 30))
		self.entry.pack()
		self.entry.bind('<Return>', lambda event: self.update_from_name())
		self.entry.bind("<KeyRelease>", lambda event: self.update_from_name())
		self.entry.bind("<Motion>", lambda event: self.update_from_name())
		self.stylename = tk.StringVar()
		self.stylemenu = tk.OptionMenu(self.master, self.stylename, \
			command=lambda event: self.update_from_style(), *style_list)
		self.stylemenu.config(font=('bold', 30))
		self.stylemenu.pack()

	def update_from_name(self):
		self.code = self.name.get()
		self.update_buttons()

	def update_from_style(self):
		self.style = self.stylename.get()
		self.update_buttons()

	def update_buttons(self):
		if self.code == '':
			 self.accept_button.configure(bg='red', activebackground='red')
		elif os.path.exists(self.target_filename()):
			 self.accept_button.configure(bg='red', activebackground='red')
		else:
			 self.accept_button.configure(bg='green', activebackground='green')

	def target_filename(self, index=0):
		suffix = '-'+str(index) if index > 0 else ''
		filename = self.style + ':' + '+'.join([str(ord(ch)) for ch in self.code])
		return os.path.join(target_letter_dir, filename + suffix + '.png')

# For testing
if __name__ == '__main__':
	root = tk.Tk()
	im = Image.open('tests/test4.png')
	gray = im.convert('L')
	# app = SignStorer(root, gray, lambda: None)
	app = LetterStorer(root, gray, lambda: None)
	app.mainloop()

