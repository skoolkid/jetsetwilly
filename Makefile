SNAPSHOT = $(shell grep -Po 'SNAPSHOT=\$$JETSETWILLY_HOME/\K.*' .ddiffsrc)
T2S = jet_set_willy.t2s

MK = $(SKOOLKIT_HOME)/tools/disassembly.mk
ifeq ($(wildcard $(MK)),)
    $(error $(MK): file not found)
endif
include $(MK)
