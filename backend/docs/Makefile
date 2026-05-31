# Makefile mínimo para Sphinx.
#   make html      -> sitio HTML navegable en _build/html
#   make latexpdf  -> PDF en _build/latex (requiere LaTeX instalado)
#   make clean     -> borra _build y los .rst autogenerados

SPHINXBUILD   = sphinx-build
SOURCEDIR     = .
BUILDDIR      = _build

.PHONY: help apidoc html latexpdf clean

help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)"

# Regenera los .rst por módulo a partir del paquete src.
apidoc:
	sphinx-apidoc --force --separate -o api ../src

html: apidoc
	@$(SPHINXBUILD) -b html "$(SOURCEDIR)" "$(BUILDDIR)/html"

latexpdf: apidoc
	@$(SPHINXBUILD) -M latexpdf "$(SOURCEDIR)" "$(BUILDDIR)"

clean:
	rm -rf "$(BUILDDIR)" api
