import sys
import csv
import os

from findhiero import find_hiero_in_page
from azure import AzurePage

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
	rows = [{'x': x, 'y': y, 'w': w, 'h': h, 'hiero': hiero} for x, y, w, h, hiero in rows]
	return rows

def remove_hiero(page, hiero):
	None # todo

def add_hiero(page, hiero):
	None # todo

def produce_html(imagefile):
	page = AzurePage(imagefile)
	hieros = read_csv(imagefile)
	for hiero in hieros:
		remove_hiero(page, hiero)
	for hiero in hieros:
		add_hiero(page, hiero)

if __name__ == '__main__':
	if len(sys.argv) >= 2:
		imagefile = sys.argv[1]
		recognize_hiero(imagefile) and produce_html(imagefile)
