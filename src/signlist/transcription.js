var cutoutButton;
var colorButton;
var hidden = true
var colored = false

function toggleCutouts() {
	if (hidden) {
		cutoutButton.textContent = 'hide cutouts';
		hidden = false;
	} else {
		cutoutButton.textContent = 'show cutouts';
		hidden = true;
	}
	const imgs = document.getElementsByTagName("img");
	for (let i = 0; i < imgs.length; i++) { 
		const im = imgs[i];
		if (hidden) 
			im.classList.add('hidden');
		else
			im.classList.remove('hidden');
	}
	const ps = document.getElementsByTagName("p");
	for (let i = 0; i < ps.length; i++) { 
		const p = ps[i];
		if (hidden) 
			p.classList.remove('highlight');
		else
			p.classList.add('highlight');
	}
	const hs = document.getElementsByTagName("h1");
	for (let i = 0; i < hs.length; i++) { 
		const h = hs[i];
		if (hidden) 
			h.classList.remove('highlight');
		else
			h.classList.add('highlight');
	}
}

function toggleColors() {
	if (colored) {
		colorButton.textContent = 'color';
		colored = false;
	} else {
		colorButton.textContent = 'black';
		colored = true;
	}
	const bs = document.getElementsByTagName("b");
	for (let i = 0; i < bs.length; i++) { 
		const b = bs[i];
		if (colored) 
			b.classList.add('colored');
		else
			b.classList.remove('colored');
	}
	const is = document.getElementsByTagName("i");
	for (let i = 0; i < is.length; i++) { 
		const it = is[i];
		if (colored) 
			it.classList.add('colored');
		else
			it.classList.remove('colored');
	}
	const cites = document.getElementsByTagName("cite");
	for (let i = 0; i < cites.length; i++) { 
		const cite = cites[i];
		if (colored) 
			cite.classList.add('colored');
		else
			cite.classList.remove('colored');
	}
	const spans = document.getElementsByTagName("span");
	for (let i = 0; i < spans.length; i++) { 
		const sc = spans[i];
		if (sc.classList.contains('sc')) {
			if (colored) 
				sc.classList.add('colored');
			else
				sc.classList.remove('colored');
		}
	}
}

function addButtons() {
	cutoutButton = document.createElement('button');
	cutoutButton.addEventListener('click', () => { toggleCutouts(); });
	document.body.prepend(cutoutButton);

	colorButton = document.createElement('button');
	colorButton.addEventListener('click', () => { toggleColors(); });
	document.body.prepend(colorButton);
}

document.addEventListener('DOMContentLoaded', function() {
	addButtons();
	toggleCutouts();
	toggleColors();
}, false);
