# hocr

Transcribe (OCR) image of hieroglyphic to Unicode

## To run OCR on image of hieroglyphic text

```
cd src
unzip gardiner.zip
unzip letters.zip
unzip newgardiner.zip
unzip topbibhiero.zip
python tables.py
python train.py
python evaltranscribe.py
```
Now look in directory `transcriptions` for the results.

This is experimental code at an early stage of development.

## To run OCR on page possibly containing hieroglyphic text

Assume `1.png` is image of page and `1.png.json` is output of Azure.

```
python pipeline.py 1.png
```

This will open window for manually correcting recognition of hieroglyphic. 
Save. Edit `1.png.csv` to correct hieroglyphic. Run again:
```
python pipeline.py 1.png
```

This will put HTML file in folder `transcriptions`.
