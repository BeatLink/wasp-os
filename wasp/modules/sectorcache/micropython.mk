# Only the boards with an SPI flash filesystem need the sector buffer.
ifneq ($(filter pinetime p8 k9,$(BOARD)),)
SECTORCACHE_MOD_DIR := $(USERMOD_DIR)
SRC_USERMOD += $(SECTORCACHE_MOD_DIR)/sectorcache.c
endif
