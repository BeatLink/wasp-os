// SPDX-License-Identifier: LGPL-3.0-or-later

// Gadgetbridge and the companion send each message as a REPL line, GB({...}).
// Compiling that line takes about 5.8 ms and a free 512-byte block for the
// parser; decoding its JSON takes 1.7 ms and no large block, so a message
// still arrives on a fragmented heap.

#include <string.h>

#include "py/runtime.h"
#include "shared/runtime/pyexec.h"

#if MICROPY_REPL_LINE_HOOK

bool pyexec_repl_line_hook(vstr_t *line) {
    const char *s = line->buf;
    size_t n = line->len;
    if (n < 5 || memcmp(s, "GB(", 3) != 0 || s[n - 1] != ')') {
        return false;
    }

    mp_map_elem_t *elem = mp_map_lookup(&mp_globals_get()->map, MP_OBJ_NEW_QSTR(MP_QSTR_GB), MP_MAP_LOOKUP);
    if (elem == NULL) {
        return false;
    }

    // Anything that is not JSON goes to the compiler, as it always did.
    mp_obj_t cmd;
    nlr_buf_t nlr;
    if (nlr_push(&nlr) == 0) {
        mp_obj_t json = mp_import_name(MP_QSTR_json, mp_const_none, MP_OBJ_NEW_SMALL_INT(0));
        cmd = mp_call_function_1(mp_load_attr(json, MP_QSTR_loads), mp_obj_new_str(s + 3, n - 4));
        nlr_pop();
    } else {
        return false;
    }

    if (nlr_push(&nlr) == 0) {
        mp_call_function_1(elem->value, cmd);
        nlr_pop();
    } else {
        mp_obj_print_exception(&mp_plat_print, MP_OBJ_FROM_PTR(nlr.ret_val));
    }
    return true;
}

#endif
