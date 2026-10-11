export PYTHONPATH := $(CURDIR)/tools/nrfutil:$(CURDIR)/tools/intelhex:$(PYTHONPATH)

PYTHON ?= python3
PYTEST ?= $(PYTHON) -m pytest

all : bootloader reloader micropython

# If BOARD is undefined then set it up so that expanding it issues an
# error. That ensures that rules that expand BOARD will be automatically
# disabled (and give a useful error message) but it creates an additional
# problem which is that we must never unconditionally expand BOARD.
# We workaround this by using BOARD_SAFE for every unconditional
# expansion.
ifdef BOARD
BOARD_SAFE = $(BOARD)
endif
BOARD ?= $(error Please set BOARD=)
VERSION ?= $(patsubst v%,%,$(shell git describe --tags))

# SD=s112 builds for the peripheral-only SoftDevice, 52 KB smaller than s132, into separate build directories.
SD ?= s132
ifneq ($(filter-out s112 s132,$(SD)),)
$(error SD must be s112 or s132)
endif
# Each image names the SoftDevice it was linked for, so a bootloader on the other one refuses it.
SD_FWID = $(if $(filter s112,$(SD)),0xB8,0xB7)
SD_HEX = bootloader/lib/softdevice/$(SD)_nrf52_6.1.1/$(SD)_nrf52_6.1.1_softdevice.hex
SD_SUFFIX = $(if $(filter s112,$(SD)),-s112)
OUT = build-$(BOARD_SAFE)$(SD_SUFFIX)
BL_BUILD = bootloader/_build-$(BOARD_SAFE)_nrf52832$(SD_SUFFIX)

clean :
	$(RM) -r \
		bootloader/_build-$(BOARD)_nrf52832 bootloader/_build-$(BOARD)_nrf52832-s112 \
		reloader/build-$(BOARD) reloader/build-$(BOARD)-s112 reloader/src/boards/$(BOARD)/bootloader.h \
		micropython/mpy-cross/build \
		micropython/ports/nrf/build-$(BOARD)-s132 micropython/ports/nrf/build-$(BOARD)-s112 \
		apps/*.mpy faces/*.mpy \
		build-$(BOARD) build-$(BOARD)-s112 \
		wasp/boards/$(BOARD)/watch.py \
		wasp/apps/user \
		wasp/boards/manifest_user_apps.py \
		wasp/appregistry.py
	find . -type f -name '*.py[co]' -delete -o -type d -name __pycache__ -delete

# Avoid a recursive update... it grabs far too much
submodules :
	git submodule update --init
	(cd bootloader; git submodule update --init)
	(cd micropython/ports/nrf; $(MAKE) submodules)
	(cd reloader; git submodule update --init)
	(cd wasp/modules/bma42x-upy; git submodule update --init)

bootloader: $(OUT)
	$(RM) $(BL_BUILD)/$(BOARD)_nrf52832_bootloader-*-nosd.hex
	$(MAKE) -C bootloader/ BOARD=$(BOARD)_nrf52832 SD_NAME=$(SD) BUILD=$(BL_BUILD:bootloader/%=%) all genhex
	$(PYTHON) tools/hexmerge.py \
		$(BL_BUILD)/$(BOARD)_nrf52832_bootloader-*-nosd.hex \
		$(SD_HEX) \
		-o $(OUT)/bootloader.hex
	$(PYTHON) tools/hex2c.py $(OUT)/bootloader.hex > \
		reloader/src/boards/$(BOARD)/bootloader.h
	$(PYTHON) -m nordicsemi dfu genpkg \
		--bootloader $(BL_BUILD)/$(BOARD)_nrf52832_bootloader-*-nosd.hex \
		--softdevice $(SD_HEX) \
		$(OUT)/bootloader-daflasher.zip

# The reloader embeds whichever bootloader was built last, so it always rebuilds after one.
reloader: bootloader $(OUT)
	$(MAKE) -C reloader/ BOARD=$(BOARD) OBJDIR=build-$(BOARD)$(SD_SUFFIX)
	cp reloader/build-$(BOARD)$(SD_SUFFIX)/reloader*.zip $(OUT)

softdevice:
	micropython/ports/nrf/drivers/bluetooth/download_ble_stack.sh

wasp/boards/$(BOARD_SAFE)/watch.py : wasp/boards/$(BOARD_SAFE)/watch.py.in
	(cd wasp; ../tools/preprocess.py boards/$(BOARD)/watch.py.in > boards/$(BOARD)/watch.py) \
		|| ($(RM) wasp/boards/$(BOARD)/watch.py; false)

micropython/mpy-cross/build/mpy-cross:
	$(MAKE) -C micropython/mpy-cross

# ACCEL=bma421 or ACCEL=bma425 builds firmware for that accelerometer alone, 6 KB smaller; the default supports both.
ifneq ($(filter-out bma421 bma425,$(ACCEL)),)
$(error ACCEL must be bma421 or bma425)
endif
ACCEL_CFLAGS = $(if $(ACCEL),-DBMA42X_ONLY_$(shell echo $(ACCEL) | tr a-z A-Z))

# Read a symbol's address from the firmware the nrf port just linked, when the recipe line runs.
elf_symbol = 0x$$(arm-none-eabi-nm micropython/ports/nrf/build-$(BOARD)-$(SD)/firmware.elf | awk '$$3 == "$(1)" {print $$1}')

micropython: $(OUT) wasp/boards/manifest_user_apps.py wasp/boards/$(BOARD_SAFE)/watch.py micropython/mpy-cross/build/mpy-cross
	$(RM) micropython/ports/nrf/build-$(BOARD)-$(SD)/frozen_content.c
	# The accelerometer choice is a compiler flag, which make does not track, so always rebuild that driver.
	find micropython/ports/nrf/build-$(BOARD)-$(SD) -name 'bma42*.o' -delete 2>/dev/null || true
	$(MAKE) -C micropython/ports/nrf \
		BOARD=$(BOARD) SD=$(SD) \
		MICROPY_VFS_LFS2=1 \
		FROZEN_MANIFEST=$(CURDIR)/wasp/boards/$(BOARD)/manifest.py \
		USER_C_MODULES=$(CURDIR)/wasp/modules \
		CFLAGS_EXTRA="$(ACCEL_CFLAGS)"
ifneq ($(wildcard wasp/boards/$(BOARD_SAFE)/manifest_romfs.py),)
	# The modules the firmware does not freeze go in a ROMFS image, written by the same package.
	$(PYTHON) tools/romfs.py build wasp --manifest wasp/boards/$(BOARD)/manifest_romfs.py -o $(OUT)/romfs.img
	$(PYTHON) tools/romfs.py hex micropython/ports/nrf/build-$(BOARD)-$(SD)/firmware.hex $(OUT)/romfs.img \
		--address $(call elf_symbol,_micropy_hw_romfs_part0_start) \
		--size $(call elf_symbol,_micropy_hw_romfs_part0_size) \
		-o $(OUT)/firmware.hex
else
	cp micropython/ports/nrf/build-$(BOARD)-$(SD)/firmware.hex $(OUT)/firmware.hex
endif
	$(PYTHON) -m nordicsemi dfu genpkg \
		--dev-type 0x0052 \
		--sd-req $(SD_FWID) \
		--application $(OUT)/firmware.hex \
		$(OUT)/micropython.zip

# The copies under wasp/apps/user are built from these sources, so editing an
# app has to rebuild them or the firmware is flashed with stale code.
APP_SOURCES = $(wildcard apps/*/*.py apps/*.py)

wasp/boards/manifest_user_apps.py: wasp.toml $(APP_SOURCES)
	$(RM) -r \
		wasp/apps/user \
		wasp/boards/manifest_user_apps.py \
		wasp/appregistry.py
	mkdir -p wasp/apps/user
	$(PYTHON) tools/configure_wasp_apps.py wasp.toml

$(OUT):
	mkdir -p $(OUT)

dfu:
	$(PYTHON) -m nordicsemi dfu serial --package micropython.zip --port /dev/ttyACM0

flash:
	pyocd erase -t nrf52 --mass
	pyocd flash -t nrf52 bootloader.hex

debug:
	arm-none-eabi-gdb \
		$(BL_BUILD)/$(BOARD)_nrf52832_bootloader-*-nosd.out \
		-ex "target extended-remote /dev/ttyACM0" \
		-ex "monitor swdp_scan" \
		-ex "attach 1" \
		-ex "load"

apps/%.mpy: apps/%/app.py micropython/mpy-cross/build/mpy-cross
	./micropython/mpy-cross/build/mpy-cross -march=armv7m -o $@ $<
faces/%.mpy: faces/%/app.py micropython/mpy-cross/build/mpy-cross
	./micropython/mpy-cross/build/mpy-cross -march=armv7m -o $@ $<
APPS_PY=$(wildcard apps/*/app.py)
APPS_MPY=$(patsubst apps/%/app.py,apps/%.mpy,$(APPS_PY))
FACES_PY=$(wildcard faces/*/app.py)
FACES_MPY=$(patsubst faces/%/app.py,faces/%.mpy,$(FACES_PY))
.PHONY: apps
apps: $(APPS_MPY) $(FACES_MPY)

docs: wasp/boards/manifest_user_apps.py
	$(RM) -rf docs/build/html/*
	$(MAKE) -C docs html
	touch docs/build/html/.nojekyll

sim: wasp/boards/manifest_user_apps.py
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:wasp/boards/simulator:wasp \
	$(PYTHON) -i wasp/boards/simulator/main.py

ifeq ("$(origin K)", "command line")
  PYTEST_RESTRICT = -k '$(K)'
endif

lint:
	ruff check .

check: wasp/boards/manifest_user_apps.py
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:wasp/boards/simulator:wasp:wasp/apps/system \
	$(PYTEST) -v -W ignore $(PYTEST_RESTRICT) wasp/boards/simulator


.PHONY: bootloader reloader docs micropython lint

dist: DIST=../wasp-os-$(VERSION)
dist: k9
k9: p8
p8: pinetime
pinetime : mrproper
mrproper :
	$(RM) -r \
		$(DIST) build-* \
		bootloader/_build-* \
		reloader/build-* \
		reloader/src/boards/*/bootloader.h \
		micropython/mpy-cross/build \
		micropython/ports/nrf/build-*
k9 p8 pinetime:
	$(RM) wasp/boards/$@/watch.py
	$(MAKE) BOARD=$@ all
dist: docs
	mkdir -p $(DIST)/docs
	cp COPYING COPYING.LGPL README.rst $(DIST)
	cp -r docs/build/html/* $(DIST)/docs
	cp -r build-*/ $(DIST)
	cp -r tools/ $(DIST)
	(cd $(DIST); ln -s docs/_images/ res)
	find $(DIST) -name __pycache__ | xargs $(RM) -r
	tar -C .. -zcf $(DIST).tar.gz $(notdir $(DIST))
	(cd ..; zip -9r $(DIST).zip $(notdir $(DIST)))

build-docker-image:
	docker compose \
	    --file ./tools/docker/docker-compose-build.yml \
	    build \
	        --pull

push-docker-image:
	docker compose \
	    --file ./tools/docker/docker-compose-build.yml \
	    push

run-docker-image:
	docker run \
	    --rm \
	    --volume=$$(pwd):/project/ \
	    --volume=/run/dbus:/run/dbus:ro \
	    --user=$$(id -u):$$(id -g) \
	    --userns=host \
	    --net=host \
	    --hostname="wasp-os-dev" \
	    --name="wasp-os-dev" \
	    --init \
	    --interactive \
	    --tty \
	    --entrypoint="" \
	    wasp-os/wasp-os-dev:0.1.0 \
	        bash
