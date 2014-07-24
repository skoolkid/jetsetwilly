BUILD = build
SKOOLKIT = $(BUILD)/skoolkit
HTML_OPTIONS = $(HTML_OPTS)
HTML_OPTIONS += -d ../html -t

HTML_OPTIONS += $(foreach theme,$(THEMES),-T $(theme))
ifeq ($(findstring spectrum,$(THEMES)),spectrum)
  HTML_OPTIONS += -c Game/Font=spectrum.ttf
endif

.PHONY: usage
usage:
	@echo "Supported targets:"
	@echo "  usage     show this help"
	@echo "  jsw       build the Jet Set Willy disassembly"
	@echo "  snapshot  build a snapshot of Jet Set Willy"
	@echo ""
	@echo "Environment variables:"
	@echo "  SKOOLKIT_HOME  directory containing the version of SkoolKit to use (required)"
	@echo "  BUILD          directory in which to build the disassembly (default: build)"
	@echo "  THEMES         CSS theme(s) to use"
	@echo "  HTML_OPTS      extra options passed to skool2html.py"

.PHONY: skoolkit-home
skoolkit-home:
	@if [ -z "$(SKOOLKIT_HOME)" ]; then \
	    echo "SKOOLKIT_HOME is not set; aborting"; \
	    exit 1; \
	fi
	@if [ ! -d "$(SKOOLKIT_HOME)" ]; then \
	    echo "SKOOLKIT_HOME=$(SKOOLKIT_HOME): directory not found"; \
	    exit 1; \
	fi

.PHONY: skoolkit
skoolkit: skoolkit-home
	mkdir -p $(SKOOLKIT)/skoolkit $(SKOOLKIT)/resources
	cp -p $(SKOOLKIT_HOME)/skool2html.py $(SKOOLKIT)
	cp -p $(SKOOLKIT_HOME)/skoolkit/*.py $(SKOOLKIT)/skoolkit
	cp -p $(SKOOLKIT_HOME)/resources/* $(SKOOLKIT)/resources

.PHONY: jsw
jsw: jet_set_willy.z80 skoolkit
	cp -p skoolkit/jetsetwilly.py $(SKOOLKIT)/skoolkit
	cp -p resources/jet_set_willy*.css $(SKOOLKIT)/resources
	mkdir -p $(SKOOLKIT)/jet_set_willy
	utils/jsw2ctl.py jet_set_willy.z80 > jet_set_willy.ctl
	$(SKOOLKIT_HOME)/sna2skool.py -c jet_set_willy.ctl jet_set_willy.z80 > $(SKOOLKIT)/jet_set_willy/jet_set_willy.skool
	rm jet_set_willy.ctl
	cp -p jet_set_willy.ref $(SKOOLKIT)/jet_set_willy
	cd $(SKOOLKIT); ./skool2html.py $(HTML_OPTIONS) jet_set_willy/jet_set_willy.ref

jet_set_willy.z80: skoolkit-home
	$(SKOOLKIT_HOME)/tap2sna.py @jet_set_willy.t2s

.PHONY: snapshot
snapshot: jet_set_willy.z80
