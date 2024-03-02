# hocr

Transcribe (OCR) image of hieroglyphic to Unicode

## To run OCR of hieroglyphic

```
cd src
unzip gardiner.zip
unzip newgardiner.zip
unzip letters.zip
python tables.py
python train.py
python transcribe.py
```

This is experimental code at an early stage of development.

## To run OCR on page

Assume `1.png` is image of page and `1.png.json` is output of Azure.

```
python pipeline.py 1.png
```

This will open window for manually correcting recognition of hieroglyphic. 
Save. Edit `1.png.csv` to correct hieroglyphic. Run again:
```
python pipeline.py 1.png
```

This will put HTML file in `transcriptions`.
