SHELL := /bin/sh
.DEFAULT_GOAL := all
.PHONY: all check clean en

all: main.pdf

main.pdf: main.tex refs.bib figures/pipeline.tex
	mkdir -p .tex-cache
	TEXMFVAR=$(CURDIR)/.tex-cache lualatex -interaction=nonstopmode -halt-on-error -file-line-error main.tex
	bibtex main
	TEXMFVAR=$(CURDIR)/.tex-cache lualatex -interaction=nonstopmode -halt-on-error -file-line-error main.tex
	TEXMFVAR=$(CURDIR)/.tex-cache lualatex -interaction=nonstopmode -halt-on-error -file-line-error main.tex

en: main-en.pdf

main-en.pdf: main-en.tex refs.bib
	mkdir -p .tex-cache
	TEXMFVAR=$(CURDIR)/.tex-cache lualatex -interaction=nonstopmode -halt-on-error -file-line-error main-en.tex
	bibtex main-en
	TEXMFVAR=$(CURDIR)/.tex-cache lualatex -interaction=nonstopmode -halt-on-error -file-line-error main-en.tex
	TEXMFVAR=$(CURDIR)/.tex-cache lualatex -interaction=nonstopmode -halt-on-error -file-line-error main-en.tex

check: main.pdf
	pdfinfo main.pdf
	! grep -E '(^!|LaTeX Warning:.*(undefined|multiply defined)|Missing character:|Overfull)' main.log

clean:
	rm -f main.aux main.bbl main.blg main.log main.out main.toc main.pdf
	rm -f main-en.aux main-en.bbl main-en.blg main-en.log main-en.out main-en.toc main-en.pdf
	rm -rf .tex-cache
