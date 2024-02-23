import sys
import tkinter as tk

from extraction import LetterExtractor

if __name__ == '__main__':
	root = tk.Tk()
	app = LetterExtractor(root)
	if len(sys.argv) >= 2:
		filename = sys.argv[1]
		app.set_image(filename)
	app.mainloop()
