var cutoutButton;
var colorButton;
var hidden = true;
var colored = false;

var nPars = 0;
var nHeaders = 0;

function toggleCutouts() {
	if (hidden) {
		cutoutButton.textContent = 'hide cutouts';
		hidden = false;
	} else {
		cutoutButton.textContent = 'show cutouts';
		hidden = true;
	}
	const imgs = document.getElementsByTagName('img');
	for (let i = 0; i < imgs.length; i++) { 
		const im = imgs[i];
		if (hidden) 
			im.classList.add('hidden');
		else
			im.classList.remove('hidden');
	}
	const ps = shownParagraphs();
	for (let i = 0; i < ps.length; i++)
		toggleCutoutsElem(ps[i]);
	const hs = shownHeaders();
	for (let i = 0; i < hs.length; i++)
		toggleCutoutsElem(hs[i])
}
function toggleCutoutsElem(elem) {
	if (hidden) 
		elem.classList.remove('highlight');
	else
		elem.classList.add('highlight');
}

function toggleColors() {
	if (colored) {
		colorButton.textContent = 'color';
		colored = false;
	} else {
		colorButton.textContent = 'black';
		colored = true;
	}
	const ps = shownParagraphs();
	for (let i = 0; i < ps.length; i++)
		setColorsElem(ps[i]);
	const hs = shownHeaders();
	for (let i = 0; i < hs.length; i++)
		setColorsElem(hs[i])
}
function setColorsElem(elem) {
	const bs = elem.getElementsByTagName('b');
	for (let i = 0; i < bs.length; i++) { 
		const b = bs[i];
		if (colored) 
			b.classList.add('colored');
		else
			b.classList.remove('colored');
	}
	const is = elem.getElementsByTagName('i');
	for (let i = 0; i < is.length; i++) { 
		const it = is[i];
		if (colored) 
			it.classList.add('colored');
		else
			it.classList.remove('colored');
	}
	const cites = elem.getElementsByTagName('cite');
	for (let i = 0; i < cites.length; i++) { 
		const cite = cites[i];
		if (colored) 
			cite.classList.add('colored');
		else
			cite.classList.remove('colored');
	}
	const spans = elem.getElementsByTagName('span');
	for (let i = 0; i < spans.length; i++) { 
		const sc = spans[i];
		if (sc.classList.contains('sc')) {
			if (colored) 
				sc.classList.add('colored');
			else
				sc.classList.remove('colored');
		}
	}
	hierojax.processFragmentsIn(elem);
}

function cleanExtras() {
	for (let i = 0; i < nPars; i++) {
		const showPar = document.getElementById('showpar' + i);
		const sourcePar = document.getElementById('sourcepar' + i);
		const editor = document.getElementById('editpar' + i);
		showPar.innerHTML = editor.value;
		showPar.removeAttribute('id');
		showPar.removeAttribute('class');
		sourcePar.remove();
		editor.remove();
	}
	for (let i = 0; i < nHeaders; i++) {
		const showH = document.getElementById('showh' + i);
		const sourceH = document.getElementById('sourceh' + i);
		const editor = document.getElementById('edith' + i);
		showH.innerHTML = editor.value;
		showH.removeAttribute('id');
		showH.removeAttribute('class');
		sourceH.remove();
		editor.remove();
	}
	const buttons = document.getElementsByTagName('button');
	for (let i = buttons.length-1; i >= 0; i--)
		buttons[i].remove();
}

function finishEdit() {
	cleanExtras();
	const request = new XMLHttpRequest();
	request.open('DELETE', 'end');
	request.setRequestHeader("Content-Type", "application/json;charset=UTF-8");
	const pageText = '<html>\n' + document.documentElement.innerHTML + '\n</html>\n';
	request.send(JSON.stringify({ 'text': pageText }));
}

function editParagraph(i) {
	const sourcePar = document.getElementById('sourcepar' + i);
	const editor = document.getElementById('editpar' + i);
	if (editor.classList.contains('hidden')) {
		editor.classList.remove('hidden');
	} else {
		editor.classList.add('hidden');
	}
}
function editHeader(i) {
	const sourceH = document.getElementById('sourceh' + i);
	const editor = document.getElementById('edith' + i);
	if (editor.classList.contains('hidden')) {
		editor.classList.remove('hidden');
	} else {
		editor.classList.add('hidden');
	}
}

function propagateParEdit(i) {
	const showPar = document.getElementById('showpar' + i);
	const sourcePar = document.getElementById('sourcepar' + i);
	const editor = document.getElementById('editpar' + i);
	sourcePar.innerHTML = editor.value;
	showPar.innerHTML = editor.value;
	setColorsElem(showPar);
}
function propagateHeaderEdit(i) {
	const showH = document.getElementById('showh' + i);
	const sourceH = document.getElementById('sourceh' + i);
	const editor = document.getElementById('edith' + i);
	sourceH.innerHTML = editor.value;
	showH.innerHTML = editor.value;
	setColorsElem(showH);
}

function addButtons() {
	cutoutButton = document.createElement('button');
	cutoutButton.addEventListener('click', () => { toggleCutouts(); });
	document.body.prepend(cutoutButton);

	colorButton = document.createElement('button');
	colorButton.addEventListener('click', () => { toggleColors(); });
	document.body.prepend(colorButton);

	finishButton = document.createElement('button');
	finishButton.textContent = 'finish';
	finishButton.addEventListener('click', () => { finishEdit(); });
	document.body.prepend(finishButton);
}

function prepareParagraphs() {
	const ps = document.getElementsByTagName('p');
	nPars = ps.length;
	for (let i = nPars-1; i >= 0; i--) { 
		const showPar = ps[i];
		showPar.id = 'showpar' + i;
		const sourcePar = showPar.cloneNode(true);
		sourcePar.id = 'sourcepar' + i;
		sourcePar.className = 'hidden';
		showPar.addEventListener('click', () => { editParagraph(i); });
		const editor = document.createElement('textarea');
		editor.id = 'editpar' + i;
		const nLines = showPar.innerHTML.split('br').length;
		editor.setAttribute('rows', nLines+1);
		editor.value = sourcePar.innerHTML;
		editor.addEventListener('input', () => { propagateParEdit(i); });
		editor.classList.add('hidden');
		showPar.insertAdjacentElement('afterend', sourcePar);
		showPar.insertAdjacentElement('afterend', editor);
	}
}
function prepareHeaders() {
	const hs = document.getElementsByTagName('h1');
	nHeaders = hs.length;
	for (let i = nHeaders-1; i >= 0; i--) { 
		const showH = hs[i];
		showH.id = 'showh' + i;
		const sourceH = showH.cloneNode(true);
		sourceH.id = 'sourceh' + i;
		sourceH.className = 'hidden';
		showH.addEventListener('click', () => { editHeader(i); });
		const editor = document.createElement('textarea');
		editor.id = 'edith' + i;
		editor.value = sourceH.innerHTML;
		editor.setAttribute('rows', 2);
		editor.addEventListener('input', () => { propagateHeaderEdit(i); });
		editor.classList.add('hidden');
		showH.insertAdjacentElement('afterend', sourceH);
		showH.insertAdjacentElement('afterend', editor);
	}
}

function shownParagraphs() {
	var psShown = [];
	for (let i = 0; i < nPars; i++)
		psShown.push(document.getElementById('showpar' + i));
	return psShown;
}
function shownHeaders() {
	var hsShown = [];
	for (let i = 0; i < nHeaders; i++)
		hsShown.push(document.getElementById('showh' + i));
	return hsShown;
}

document.addEventListener('DOMContentLoaded', function() {
	addButtons();
	prepareParagraphs();
	prepareHeaders();
	toggleCutouts();
	toggleColors();
}, false);
