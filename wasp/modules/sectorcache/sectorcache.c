// SPDX-License-Identifier: LGPL-3.0-or-later

// A 4 KB sector cache for the SPI flash driver, kept in static RAM so it never splits the heap.

#include "py/binary.h"
#include "py/objarray.h"
#include "py/runtime.h"

#define SECTOR_SIZE (4096)

static uint8_t sector[SECTOR_SIZE];

static mp_obj_array_t sector_obj = {
    {&mp_type_bytearray}, BYTEARRAY_TYPECODE, 0, SECTOR_SIZE, sector
};

static const mp_rom_map_elem_t sectorcache_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_sectorcache) },
    { MP_ROM_QSTR(MP_QSTR_buffer), MP_ROM_PTR(&sector_obj) },
};
static MP_DEFINE_CONST_DICT(sectorcache_module_globals, sectorcache_module_globals_table);

const mp_obj_module_t sectorcache_module = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&sectorcache_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_sectorcache, sectorcache_module);
