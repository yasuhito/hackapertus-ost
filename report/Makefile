SHELL := /bin/sh
.DEFAULT_GOAL := all
.PHONY: all check clean

all: main.pdf

main.pdf: main.tex refs.bib figures/pipeline.tex
	mkdir -p .tex-cache
	TEXMFVAR=$(CURDIR)/.tex-cache lualatex -interaction=nonstopmode -halt-on-error -file-line-error main.tex
	bibtex main
	TEXMFVAR=$(CURDIR)/.tex-cache lualatex -interaction=nonstopmode -halt-on-error -file-line-error main.tex
	TEXMFVAR=$(CURDIR)/.tex-cache lualatex -interaction=nonstopmode -halt-on-error -file-line-error main.tex

check: main.pdf
	pdfinfo main.pdf
	! grep -E '(^!|LaTeX Warning:.*(undefined|multiply defined)|Missing character:|Overfull)' main.log

clean:
	rm -f main.aux main.bbl main.blg main.log main.out main.toc main.pdf
	rm -rf .tex-cache
