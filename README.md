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

Assume `1.png` is image of page and `1.png.json` is output of Azure in the same directory as `1.png`

```
python pipeline.py somepath/1.png
```

This will open window for manually correcting recognition of hieroglyphic. 
Save. Manually edit `1.png.csv` to correct hieroglyphic, e.g. using `https://nederhof.github.io/hierojax/edit.html`.

Run again:
```
python pipeline.py 1.png
```

This will put HTML file `1.html` in folder `transcriptions`.

To correct this manually, do:
```
cd transcriptions
correctpage.sh 1.html
```

Click on shaded areas to open an editor for these. Click again to close the editor.
One can toggle between views with or without the cutouts from the original scan and with or without colors
to emphasize styles.

When done, press on the button at the top saying *finish*. 
This overwrites `1.html` with the corrected version.
